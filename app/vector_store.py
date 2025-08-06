# app/vector_store.py
import os
import uuid
from qdrant_client import QdrantClient, models
from qdrant_client.models import (
    PointStruct, Filter, FieldCondition, MatchValue,
    VectorParams, Distance, NamedVector
)

from database import SessionLocal
from models_db import DocumentChunk

# Configuration
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", 6333))
COLLECTION_NAME = "document_chunks"
VECTOR_DIM = 384  # Match your embedding size
VECTOR_NAME = "default_vector"
DISTANCE = Distance.COSINE

# Initialize Qdrant client
client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)


def ensure_collection_correct():
    """
    Ensures Qdrant collection exists with named vector configuration.
    Recreates if misconfigured.
    """
    correct_config = {
        VECTOR_NAME: VectorParams(size=VECTOR_DIM, distance=DISTANCE)
    }

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


def upsert_chunks(document_id, chunks, vectors, metadata_list):
    """
    Inserts chunks and their embeddings into both PostgreSQL and Qdrant.
    """
    ensure_collection_correct()
    db = SessionLocal()
    points = []

    try:
        for i, (chunk, vector, metadata) in enumerate(zip(chunks, vectors, metadata_list)):
            if vector is None:
                continue

            point_id = str(uuid.uuid4())

            # Save in PostgreSQL
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

            # Prepare Qdrant point
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

        client.upsert(collection_name=COLLECTION_NAME, points=points, wait=True)
        db.commit()
        print(f"✅ Upserted {len(points)} chunks into Qdrant and DB.")
    except Exception as e:
        db.rollback()
        print(f"[ERROR] Failed to insert metadata or vectors: {e}")
    finally:
        db.close()


def search_chunks(query_vector, filters, top_k=15):
    """
    Searches Qdrant with named vector and optional metadata filters.
    """
    conditions = []
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
