from vector_store import upsert_chunks
import numpy as np

# Simulate some chunks, vectors, and metadata
document_id = "doc_123"
chunks = ["Chunk 1 text", "Chunk 2 text"]
vectors = [np.random.rand(384).tolist(), np.random.rand(384).tolist()]
metadata_list = [
    {
        "document_id": document_id,
        "file_name": "test.pdf",
        "chunk_id": 0,
        "page_number": 1,
        "section_title": "Intro",
        "doc_type": "pdf",
        "text": "Chunk 1 text"
    },
    {
        "document_id": document_id,
        "file_name": "test.pdf",
        "chunk_id": 1,
        "page_number": 2,
        "section_title": "Content",
        "doc_type": "pdf",
        "text": "Chunk 2 text"
    }
]

# Call the function
upsert_chunks(document_id, chunks, vectors, metadata_list)
