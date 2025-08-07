# app/vector_store.py
import os
import uuid
from qdrant_client import QdrantClient, models
from qdrant_client.models import (
    PointStruct, Filter, FieldCondition, MatchValue,
    VectorParams, Distance, NamedVector
)

from app.database import SessionLocal
from app.models_db import DocumentChunk

# Configuration
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", 6333))
COLLECTION_NAME = "document_chunks"
VECTOR_DIM = 768  # Updated for text-embedding-004 model
VECTOR_NAME = "default_vector"
DISTANCE = Distance.COSINE

# Initialize Qdrant client with retry logic
def get_qdrant_client():
    max_retries = 10
    retry_delay = 5
    
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
                print(f"Retrying in {retry_delay} seconds...")
                import time
                time.sleep(retry_delay)
            else:
                raise Exception(f"Failed to connect to Qdrant after {max_retries} attempts")

# Global client variable
client = None


def ensure_collection_correct():
    """
    Ensures Qdrant collection exists with named vector configuration.
    Recreates if misconfigured.
    """
    global client
    if client is None:
        client = get_qdrant_client()
    
    correct_config = {
        VECTOR_NAME: VectorParams(size=VECTOR_DIM, distance=DISTANCE)
    }

    try:
        if client.collection_exists(collection_name=COLLECTION_NAME):
            info = client.get_collection(collection_name=COLLECTION_NAME)
            if info.config.params.vectors != correct_config:
                print(f"⚠️ Collection '{COLLECTION_NAME}' misconfigured. Recreating...")
                client.recreate_collection(
                    collection_name=COLLECTION_NAME,
                    vectors_config=correct_config
                )
            else:
                print(f"✅ Collection '{COLLECTION_NAME}' is correctly configured.")
        else:
            print(f"ℹ️ Collection '{COLLECTION_NAME}' does not exist. Creating...")
            client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=correct_config
            )
    except Exception as e:
        print(f"Error ensuring collection: {e}")
        # Try to reconnect and create collection
        client = get_qdrant_client()
        try:
            client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=correct_config
            )
            print(f"✅ Created collection '{COLLECTION_NAME}'")
        except Exception as create_error:
            print(f"Failed to create collection: {create_error}")
            raise


def upsert_chunks(document_id, chunks, vectors, metadata_list):
    """
    Inserts chunks and their embeddings into both PostgreSQL and Qdrant.
    """
    global client
    if client is None:
        client = get_qdrant_client()
        
    ensure_collection_correct()
    db = SessionLocal()
    points = []

    try:
        for i, (chunk, vector, metadata) in enumerate(zip(chunks, vectors, metadata_list)):
            if vector is None:
                print(f"Skipping chunk {i} due to missing vector")
                continue

            point_id = str(uuid.uuid4())

            # Save in PostgreSQL
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
            except Exception as db_error:
                print(f"Error adding to database: {db_error}")
                continue

            # Prepare Qdrant point
            try:
                points.append(
                    PointStruct(
                        id=point_id,
                        vector={VECTOR_NAME: vector},
                        payload={
                            "document_id": document_id,
                            "chunk_index": i,
                            "chunk": chunk,
                            **metadata
                        }
                    )
                )
            except Exception as point_error:
                print(f"Error creating point: {point_error}")
                continue

        if points:
            client.upsert(collection_name=COLLECTION_NAME, points=points, wait=True)
            print(f"✅ Upserted {len(points)} chunks into Qdrant")
        
        db.commit()
        print(f"✅ Saved chunks to database")
        
    except Exception as e:
        db.rollback()
        print(f"[ERROR] Failed to insert metadata or vectors: {e}")
    finally:
        db.close()


def search_chunks(query_vector, filters=None, top_k=15):
    """
    Searches Qdrant with named vector and optional metadata filters.
    """
    global client
    if client is None:
        client = get_qdrant_client()
    
    try:
        conditions = []
        if filters:
            for key, value in filters.items():
                conditions.append(FieldCondition(key=key, match=MatchValue(value=value)))

        q_filter = Filter(must=conditions) if conditions else None

        results = client.search(
            collection_name=COLLECTION_NAME,
            query_vector=NamedVector(name=VECTOR_NAME, vector=query_vector),
            limit=top_k,
            query_filter=q_filter,
            with_payload=True
        )

        return [hit.payload for hit in results]
    except Exception as e:
        print(f"Error searching chunks: {e}")
        return []