from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

from sqlalchemy import Column, Integer, String, Text
from database import Base

class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(String, index=True)
    file_name = Column(String)
    chunk_id = Column(Integer)
    page_number = Column(Integer)
    section_title = Column(String, nullable=True)
    doc_type = Column(String, nullable=True)
    text = Column(Text)  # Required for retrieval
