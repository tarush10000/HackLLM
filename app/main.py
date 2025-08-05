from fastapi import FastAPI, Header, HTTPException
from app.models import QueryRequest, QueryResponse
from app.pdfToText import extract_text_generator
from app.utils import clean_text, chunk_text, get_first_n_words, hash_pdf_metadata
from app.embeddings import embed_chunks
from app.vector_store import upsert_chunks, search_chunks
from app.response_builder import build_final_response
from dotenv import load_dotenv
import os
import requests
import hashlib
import uuid

load_dotenv()
BEARER_TOKEN = os.getenv("BEARER_TOKEN")
app = FastAPI()

# In-memory set for document hashes (replace with DB check in prod)
processed_documents = set()

@app.post("/api/v1/hackrx/run", response_model=QueryResponse)
async def run_query(request: QueryRequest, authorization: str = Header(...)):
    if authorization != f"Bearer {BEARER_TOKEN}":
        raise HTTPException(status_code=403, detail="Invalid token")

    doc_url = request.documents

    # Step 1: Download document and create identifier hash
    try:
        response = requests.get(doc_url, timeout=15)
        response.raise_for_status()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Document download failed: {str(e)}")

    file_size = len(response.content)
    file_name = doc_url.split("/")[-1]
    doc_id = str(uuid.uuid4())

    # Step 2: Extract first 20 words for hash
    text_preview = ""
    for _, page_text in extract_text_generator(doc_url):
        text_preview = get_first_n_words(page_text, 20)
        break

    doc_hash = hash_pdf_metadata(file_name, file_size, text_preview)
    if doc_hash in processed_documents:
        print(f"[INFO] Document already processed: {file_name}")
    else:
        print(f"[INFO] Processing new document: {file_name}")
        all_chunks = []
        metadata_list = []
        chunk_index = 0

        for page_num, page_text in extract_text_generator(doc_url):
            cleaned = clean_text(page_text)
            chunks = chunk_text(cleaned, strategy="fixed", chunk_size=200)
            for chunk in chunks:
                metadata = {
                    "document_id": doc_id,
                    "file_name": file_name,
                    "chunk_id": chunk_index,
                    "page_number": page_num,
                    "section_title": None,
                    "doc_type": "policy"
                }
                all_chunks.append(chunk)
                metadata_list.append(metadata)
                chunk_index += 1

        # Step 3: Embed chunks and store in vector DB
        vectors = embed_chunks(all_chunks)
        upsert_chunks(doc_id, all_chunks, vectors, metadata_list)
        processed_documents.add(doc_hash)

    # Step 4: Handle questions
    answers = []
    for question in request.questions:
        query_vector = embed_chunks([question])[0]
        top_chunks = search_chunks(query_vector, filters={"document_id": doc_id}, top_k=15)
        top_texts = [chunk["text"] for chunk in top_chunks]
        final_answer = build_final_response(question, top_texts)
        answers.append(final_answer)

    return {"answers": answers}
