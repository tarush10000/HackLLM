# app/vector_store.py (Final fixed version - forces collection recreate)
import os
import uuid
import asyncio
from qdrant_client import QdrantClient, models
from qdrant_client.models import (
    PointStruct, Filter, FieldCondition, MatchValue,
    VectorParams, Distance
)
from qdrant_client.http.exceptions import UnexpectedResponse
from app.database import SessionLocal
from app.models_db import DocumentChunk

# Configuration
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", 6333))
COLLECTION_NAME = "document_chunks"
VECTOR_DIM = 768
DISTANCE = Distance.COSINE

class AsyncQdrantClient:
    def __init__(self):
        self.client = None
        self._lock = asyncio.Lock()
    
    async def get_client(self):
        if self.client is None:
            async with self._lock:
                if self.client is None:
                    loop = asyncio.get_event_loop()
                    self.client = await loop.run_in_executor(None, self._create_client)
        return self.client
    
    def _create_client(self):
        max_retries = 10
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                client = QdrantClient(
                    host=QDRANT_HOST, 
                    port=QDRANT_PORT,
                    timeout=30
                )
                # Test connection
                client.get_collections()
                print(f"✅ Connected to Qdrant on attempt {attempt + 1}")
                return client
            except Exception as e:
                print(f"❌ Qdrant connection attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    import time
                    time.sleep(retry_delay)
                else:
                    raise Exception(f"Failed to connect to Qdrant after {max_retries} attempts")

# Global async client
async_client = AsyncQdrantClient()

def collection_exists(client, collection_name):
    """Check if collection exists - works with different Qdrant versions"""
    try:
        # Try the newer method first
        if hasattr(client, 'collection_exists'):
            return client.collection_exists(collection_name)
        
        # Fallback to older method
        collections = client.get_collections()
        if hasattr(collections, 'collections'):
            collection_names = [col.name for col in collections.collections]
        else:
            collection_names = [col.name for col in collections]
        
        return collection_name in collection_names
        
    except Exception as e:
        print(f"Error checking collection existence: {e}")
        return False

def normalize_vector(vector):
    """Normalize vector to ensure it's a flat list of floats"""
    if vector is None:
        return None
    
    # Handle nested structures
    if isinstance(vector, dict):
        # If it's a dict with 'default_vector' or similar key
        for key in ['default_vector', 'vector', 'embedding']:
            if key in vector:
                return normalize_vector(vector[key])
        return None
    
    # Handle nested lists
    if isinstance(vector, list):
        if len(vector) == 0:
            return None
        
        # If it's a list of lists, take the first one
        if isinstance(vector[0], list):
            if len(vector[0]) > 0:
                vector = vector[0]
            else:
                return None
        
        # Ensure all elements are numbers
        try:
            normalized = [float(x) for x in vector if isinstance(x, (int, float))]
            if len(normalized) > 0:
                return normalized
        except (ValueError, TypeError):
            pass
    
    return None

async def ensure_collection_correct_async():
    """Force recreate collection with correct configuration"""
    client = await async_client.get_client()
    
    # Use simple vector config (not named vectors)
    vector_config = VectorParams(size=VECTOR_DIM, distance=DISTANCE)
    
    loop = asyncio.get_event_loop()
    
    try:
        # Check if collection exists
        exists = await loop.run_in_executor(None, collection_exists, client, COLLECTION_NAME)
        
        if exists:
            print(f"⚠️ Collection '{COLLECTION_NAME}' exists but may have wrong config. Deleting and recreating...")
            try:
                await loop.run_in_executor(None, client.delete_collection, COLLECTION_NAME)
                print(f"🗑️ Deleted existing collection '{COLLECTION_NAME}'")
            except Exception as e:
                print(f"Warning: Could not delete collection: {e}")
        
        # Create collection with correct config
        print(f"ℹ️ Creating collection '{COLLECTION_NAME}' with simple vector config...")
        await loop.run_in_executor(None, client.create_collection, COLLECTION_NAME, vector_config)
        print(f"✅ Created collection '{COLLECTION_NAME}' successfully")
            
    except Exception as e:
        print(f"❌ Error ensuring collection: {e}")
        raise

async def upsert_chunks_async(document_id, chunks, vectors, metadata_list):
    """Async version of chunk upserting with proper vector handling"""
    client = await async_client.get_client()
    await ensure_collection_correct_async()
    
    # Prepare database and vector operations concurrently
    db_task = asyncio.create_task(upsert_to_db_async(chunks, vectors, metadata_list))
    vector_task = asyncio.create_task(upsert_to_vector_db_async(client, document_id, chunks, vectors, metadata_list))
    
    try:
        await asyncio.gather(db_task, vector_task)
    except Exception as e:
        print(f"❌ Error in upsert_chunks_async: {e}")
        raise

async def upsert_to_db_async(chunks, vectors, metadata_list):
    """Async database operations"""
    loop = asyncio.get_event_loop()
    
    def db_operation():
        db = SessionLocal()
        try:
            valid_chunks = 0
            for chunk, vector, metadata in zip(chunks, vectors, metadata_list):
                # Normalize vector for validation
                normalized_vector = normalize_vector(vector)
                if normalized_vector is None:
                    continue
                
                try:
                    db_chunk = DocumentChunk(
                        document_id=metadata["document_id"],
                        file_name=metadata["file_name"],
                        chunk_id=metadata["chunk_id"],
                        page_number=metadata["page_number"],
                        section_title=metadata.get("section_title"),
                        doc_type=metadata.get("doc_type"),
                        text=chunk
                    )
                    db.add(db_chunk)
                    valid_chunks += 1
                except Exception as e:
                    print(f"❌ Error adding chunk to DB: {e}")
                    continue
            
            if valid_chunks > 0:
                db.commit()
                print(f"✅ Saved {valid_chunks} chunks to database")
            else:
                print("⚠️ No valid chunks to save to database")
                
        except Exception as e:
            db.rollback()
            print(f"❌ [ERROR] Failed to insert into database: {e}")
            raise
        finally:
            db.close()
    
    await loop.run_in_executor(None, db_operation)

async def upsert_to_vector_db_async(client, document_id, chunks, vectors, metadata_list):
    """Async vector database operations with proper vector handling"""
    points = []
    
    print(f"🔄 Preparing {len(chunks)} points for vector database...")
    
    for i, (chunk, vector, metadata) in enumerate(zip(chunks, vectors, metadata_list)):
        # Normalize the vector
        normalized_vector = normalize_vector(vector)
        
        if normalized_vector is None:
            print(f"⚠️ Skipping chunk {i} due to invalid vector")
            continue
        
        if len(normalized_vector) != VECTOR_DIM:
            print(f"⚠️ Skipping chunk {i} due to wrong vector dimension: {len(normalized_vector)} != {VECTOR_DIM}")
            continue
        
        point_id = str(uuid.uuid4())
        
        try:
            # Create point with simple vector (not named vector)
            point = PointStruct(
                id=point_id,
                vector=normalized_vector,  # Direct vector as list of floats
                payload={
                    "document_id": document_id,
                    "chunk_index": i,
                    "chunk": chunk,
                    **metadata
                }
            )
            points.append(point)
            
            # Debug: Print first few points to verify structure
            if i < 3:
                print(f"📋 Point {i}: vector_dim={len(normalized_vector)}, payload_keys={list(point.payload.keys())}")
            
        except Exception as e:
            print(f"❌ Error creating point for chunk {i}: {e}")
            continue
    
    if points:
        try:
            print(f"📤 Upserting {len(points)} points to Qdrant...")
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, client.upsert, COLLECTION_NAME, points, True)
            print(f"✅ Successfully upserted {len(points)} chunks into Qdrant")
        except Exception as e:
            print(f"❌ Error upserting to Qdrant: {e}")
            print(f"First point structure: {points[0].__dict__ if points else 'No points'}")
            raise
    else:
        print("⚠️ No valid points to upsert to Qdrant")

async def search_chunks_async(query_vector, filters=None, top_k=15):
    """Async chunk searching with proper vector handling"""
    client = await async_client.get_client()
    
    # Normalize the query vector
    normalized_query_vector = normalize_vector(query_vector)
    
    if normalized_query_vector is None:
        print("❌ Invalid query vector for search")
        return []
    
    if len(normalized_query_vector) != VECTOR_DIM:
        print(f"❌ Query vector wrong dimension: {len(normalized_query_vector)} != {VECTOR_DIM}")
        return []
    
    def search_operation():
        try:
            conditions = []
            if filters:
                for key, value in filters.items():
                    conditions.append(FieldCondition(key=key, match=MatchValue(value=value)))

            q_filter = Filter(must=conditions) if conditions else None

            print(f"🔍 Searching with vector dimension: {len(normalized_query_vector)}")
            
            # Use simple vector search (not named vector)
            results = client.search(
                collection_name=COLLECTION_NAME,
                query_vector=normalized_query_vector,  # Direct vector as list of floats
                limit=top_k,
                query_filter=q_filter,
                with_payload=True
            )

            print(f"✅ Found {len(results)} search results")
            return [hit.payload for hit in results]
            
        except Exception as e:
            print(f"❌ Error searching chunks: {e}")
            return []
    
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, search_operation)

# Legacy functions for backward compatibility
def ensure_collection_correct():
    """Synchronous version for backward compatibility"""
    asyncio.run(ensure_collection_correct_async())

def upsert_chunks(document_id, chunks, vectors, metadata_list):
    """Synchronous version for backward compatibility"""
    asyncio.run(upsert_chunks_async(document_id, chunks, vectors, metadata_list))

def search_chunks(query_vector, filters=None, top_k=15):
    """Synchronous version for backward compatibility"""
    return asyncio.run(search_chunks_async(query_vector, filters, top_k))