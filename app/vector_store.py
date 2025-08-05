
"""
Manages vector insertion and similarity search in Qdrant.
"""
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, Filter, VectorParams

client = QdrantClient(host="localhost", port=6333)

def upsert_chunks(document_id, chunks, vectors, metadata_list):
    # TODO: Insert chunks + metadata into Qdrant
    pass

def search_chunks(query_vector, filters, top_k=15):
    # TODO: Perform vector search with filters
    return []