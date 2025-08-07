from app.database import SessionLocal
from app.models_db import DocumentChunk

# Create a DB session
db = SessionLocal()

# Query the first 10 rows
chunks = db.query(DocumentChunk).limit(10).all()

# Print the results
for chunk in chunks:
    print(f"ID: {chunk.id}, Chunk ID: {chunk.chunk_id}, Page: {chunk.page_number}, Text: {chunk.text[:100]}...")

db.close()
