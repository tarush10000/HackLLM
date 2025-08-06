# app/vector_store.py

print("\n\n--- EXECUTING THE CORRECT vector_store.py (VERSION WITH EXPLICIT NAMED VECTORS) ---\n\n")

import os
import uuid
from qdrant_client import QdrantClient, models
from qdrant_client.models import PointStruct, Filter, Distance

QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = os.getenv("QDRANT_PORT", 6333)
client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

collection_name = "policy_chunks"
VECTOR_DIM = 768
VECTOR_NAME = "default_vector" # Using a more specific name

def ensure_collection_correct():
    """
    Checks if the collection exists and is configured for a single, named vector.
    If not, it recreates the collection with the correct, explicit parameters.
    """
    correct_vectors_config = {
        VECTOR_NAME: models.VectorParams(size=VECTOR_DIM, distance=Distance.COSINE)
    }

    if client.collection_exists(collection_name=collection_name):
        collection_info = client.get_collection(collection_name=collection_name)
        if collection_info.config.params.vectors != correct_vectors_config:
            print(f"Collection '{collection_name}' has incorrect configuration. Recreating...")
            client.recreate_collection(
                collection_name=collection_name,
                vectors_config=correct_vectors_config
            )
    else:
        print(f"Collection '{collection_name}' does not exist. Creating...")
        client.create_collection(
            collection_name=collection_name,
            vectors_config=correct_vectors_config
        )

def upsert_chunks(document_id, chunks, vectors, metadata_list):
    ensure_collection_correct()

    points = []
    for i, (chunk, vector, metadata) in enumerate(zip(chunks, vectors, metadata_list)):
        if vector is None:
            continue
        
        point = PointStruct(
            id=str(uuid.uuid4()),
            vector={VECTOR_NAME: vector},
            payload={
                "document_id": document_id,
                "chunk_index": i,
                "chunk": chunk,
                **metadata
            }
        )
        points.append(point)

    if points:
        client.upsert(collection_name=collection_name, points=points, wait=True)
        print(f"✅ Upserted {len(points)} points into Qdrant")
    else:
        print("No valid points to upsert.")

def search_chunks(query_vector, filters, top_k=15):
    return client.search(
        collection_name=collection_name,
        query_vector=models.NamedVector(
            name=VECTOR_NAME,
            vector=query_vector
        ),
        limit=top_k,
        with_payload=True,
        query_filter=filters
    )