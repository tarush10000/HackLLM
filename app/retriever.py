"""
Retrieves top K chunks from relevant document(s) based on query.
"""
from app.embeddings import embed_chunks
from app.vector_store import search_chunks

def retrieve_top_chunks(query, doc_filter=None, top_k=15):
    query_vec = embed_chunks([query])[0]
    chunks = search_chunks(query_vec, filters={"document_id": doc_filter}, top_k=top_k)
    return chunks