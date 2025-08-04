from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, Filter, VectorParams

client = QdrantClient(host="localhost", port=6333)

def search_relevant_clauses(query_vector, top_k=5):
    result = client.search(
        collection_name="policy_docs",
        query_vector=query_vector,
        limit=top_k,
    )
    return [hit.payload['text'] for hit in result]
