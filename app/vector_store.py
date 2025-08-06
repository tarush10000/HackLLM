from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, Filter, FieldCondition, MatchValue, VectorParams
from qdrant_client.models import Distance
from uuid import uuid4

from database import SessionLocal
from models_db import DocumentChunk

COLLECTION_NAME = "document_chunks"
VECTOR_SIZE = 384  # Assuming 768-dimensional embeddings
DISTANCE = Distance.COSINE

client = QdrantClient(host="localhost", port=6333)

# Ensure collection exists
client.recreate_collection(
    collection_name=COLLECTION_NAME,
    vectors_config=VectorParams(size=VECTOR_SIZE, distance=DISTANCE)
)

def upsert_chunks(document_id, chunks, vectors, metadata_list):
    db = SessionLocal()
    try:
        points = []
        for i, (chunk, vector, metadata) in enumerate(zip(chunks, vectors, metadata_list)):
            point_id = str(uuid4())
            db_chunk = DocumentChunk(
                document_id=metadata["document_id"],
                file_name=metadata["file_name"],
                chunk_id=metadata["chunk_id"],
                page_number=metadata["page_number"],
                section_title=metadata.get("section_title"),
                doc_type=metadata.get("doc_type"),
                text=chunk  # Save text in DB
            )
            db.add(db_chunk)

            points.append(
                PointStruct(
                    id=point_id,
                    vector=vector,
                    payload={
                        "document_id": document_id,
                        "text": chunk,
                        "page_number": metadata["page_number"],
                        "chunk_id": metadata["chunk_id"],
                        "file_name": metadata["file_name"],
                        "doc_type": metadata["doc_type"]
                    }
                )
            )

        client.upsert(collection_name=COLLECTION_NAME, points=points)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[ERROR] Failed to insert metadata or vectors: {e}")
    finally:
        db.close()

def search_chunks(query_vector, filters, top_k=15):
    conditions = []
    for key, value in filters.items():
        conditions.append(FieldCondition(key=key, match=MatchValue(value=value)))

    q_filter = Filter(must=conditions)

    search_result = client.search(
        collection_name=COLLECTION_NAME,
        query_vector=query_vector,
        limit=top_k,
        query_filter=q_filter
    )

    top_chunks = []
    for hit in search_result:
        top_chunks.append(hit.payload)

    return top_chunks
