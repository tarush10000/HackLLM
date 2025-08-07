# app/models_db.py (Fixed version with correct imports)
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

# Create base class
Base = declarative_base()

class Document(Base):
    __tablename__ = "documents"
    
    id = Column(String, primary_key=True, index=True)  # UUID
    file_name = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    first_words = Column(String(500), nullable=False)  # First 20 words
    content_hash = Column(String, unique=True, index=True, nullable=False)  # MD5 hash
    processed_at = Column(DateTime, default=datetime.utcnow)
    total_chunks = Column(Integer, default=0)
    
    # Relationship to chunks
    chunks = relationship("DocumentChunk", back_populates="document")

class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(String, ForeignKey("documents.id"), index=True)
    file_name = Column(String)
    chunk_id = Column(Integer)
    page_number = Column(Integer)
    section_title = Column(String)
    doc_type = Column(String)
    text = Column(Text)
    
    # Relationship back to document
    document = relationship("Document", back_populates="chunks")