# app/document_service.py (Fixed version with better URL parsing)
"""
Document processing service with intelligent deduplication.
"""
import asyncio
import uuid
from urllib.parse import urlparse
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models_db import Document, DocumentChunk
from app.utils import hash_pdf_metadata, get_first_n_words, clean_text
from app.pdfToText import extract_text_generator_async
from app.chunkCreator import chunk_pageText
from app.embeddings import embed_chunks_async
from app.vector_store import upsert_chunks_async
import aiohttp

class DocumentService:
    """Service for managing document processing and deduplication"""
    
    def __init__(self):
        pass
    
    def extract_filename_from_url(self, url: str) -> str:
        """Extract clean filename from URL"""
        try:
            # Parse the URL and get the path
            parsed = urlparse(url)
            path = parsed.path
            
            # Get the filename from the path
            filename = path.split('/')[-1]
            
            # If no filename in path, use a default
            if not filename or filename == '':
                filename = "document.pdf"
            
            # Remove any remaining query parameters that might be in the filename
            filename = filename.split('?')[0]
            
            # Ensure it has an extension
            if '.' not in filename:
                filename += '.pdf'
            
            print(f"📄 Extracted filename: {filename} from URL: {url[:50]}...")
            return filename
            
        except Exception as e:
            print(f"⚠️ Error extracting filename: {e}")
            return "document.pdf"
    
    async def check_document_exists(self, file_name: str, file_size: int, first_words: str) -> Optional[str]:
        """
        Check if document already exists in database based on metadata.
        Returns document_id if exists, None otherwise.
        """
        content_hash = hash_pdf_metadata(file_name, file_size, first_words)
        
        def db_operation():
            db = SessionLocal()
            try:
                # Check if document with this hash already exists
                existing_doc = db.query(Document).filter(Document.content_hash == content_hash).first()
                
                if existing_doc:
                    print(f"✅ Document already processed: {existing_doc.id}")
                    print(f"📊 Processed at: {existing_doc.processed_at}, Chunks: {existing_doc.total_chunks}")
                    return existing_doc.id
                
                print(f"📋 New document detected: {file_name} (hash: {content_hash[:12]}...)")
                return None
                
            except Exception as e:
                print(f"❌ Error checking document existence: {e}")
                return None
            finally:
                db.close()
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, db_operation)
    
    async def get_document_preview(self, doc_url: str) -> Tuple[str, int, str]:
        """
        Get document metadata for deduplication check.
        Returns (file_name, file_size, first_20_words)
        """
        try:
            # Download document to get size and preview
            async with aiohttp.ClientSession() as session:
                async with session.get(doc_url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    response.raise_for_status()
                    content = await response.read()
            
            file_size = len(content)
            file_name = self.extract_filename_from_url(doc_url)
            
            # Extract first page for preview
            first_words = ""
            try:
                async for page_text in extract_text_generator_async(doc_url):
                    first_words = get_first_n_words(clean_text(page_text), 20)
                    break  # Only need first page
            except Exception as e:
                print(f"⚠️ Preview extraction failed: {e}")
                first_words = f"preview_failed_{file_size}_{file_name}"
            
            print(f"📄 Document preview - Name: {file_name}, Size: {file_size}")
            print(f"📝 Preview: {first_words[:100]}...")
            return file_name, file_size, first_words
            
        except Exception as e:
            print(f"❌ Error getting document preview: {e}")
            raise
    
    async def process_new_document(self, doc_url: str, file_name: str, file_size: int, first_words: str) -> str:
        """
        Process a new document completely.
        Returns the document_id.
        """
        doc_id = str(uuid.uuid4())
        content_hash = hash_pdf_metadata(file_name, file_size, first_words)
        
        print(f"🔄 Processing new document: {doc_id}")
        
        try:
            # Extract all text
            full_text = ""
            async for page_text in extract_text_generator_async(doc_url):
                cleaned = clean_text(page_text)
                full_text += "\n" + cleaned

            # Create chunks
            chunks = chunk_pageText(full_text)
            
            if not chunks:
                raise Exception("No chunks created from document")
            
            print(f"📝 Created {len(chunks)} chunks")
            
            # Prepare chunk data
            chunk_texts = []
            metadata_list = []
            chunk_index = 0
            
            for chunk in chunks:
                metadata = {
                    "document_id": doc_id,
                    "file_name": file_name,
                    "chunk_id": chunk_index,
                    "page_number": None,
                    "section_title": chunk["section_number"],
                    "doc_type": "policy"
                }
                chunk_texts.append(chunk["text"])
                metadata_list.append(metadata)
                chunk_index += 1
            
            # Generate embeddings and store in vector DB
            print(f"🧠 Generating embeddings for {len(chunk_texts)} chunks...")
            vectors = await embed_chunks_async(chunk_texts)
            
            # Store document metadata FIRST (before vector operations)
            print(f"💾 Storing document metadata...")
            await self._store_document_metadata(doc_id, file_name, file_size, first_words, content_hash, len(chunks))
            
            # Store in vector database
            print(f"🔍 Storing in vector database...")
            await upsert_chunks_async(doc_id, chunk_texts, vectors, metadata_list)
            
            print(f"✅ Document processing complete: {doc_id}")
            return doc_id
            
        except Exception as e:
            print(f"❌ Error processing document: {e}")
            # Clean up any partial data
            await self._cleanup_failed_processing(doc_id)
            raise
    
    async def _store_document_metadata(self, doc_id: str, file_name: str, file_size: int, 
                                     first_words: str, content_hash: str, total_chunks: int):
        """Store document metadata in PostgreSQL"""
        def db_operation():
            db = SessionLocal()
            try:
                doc = Document(
                    id=doc_id,
                    file_name=file_name,
                    file_size=file_size,
                    first_words=first_words,
                    content_hash=content_hash,
                    total_chunks=total_chunks
                )
                
                db.add(doc)
                db.commit()
                print(f"📊 Stored document metadata: {doc_id}")
                
            except Exception as e:
                db.rollback()
                print(f"❌ Error storing document metadata: {e}")
                raise
            finally:
                db.close()
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, db_operation)
    
    async def _cleanup_failed_processing(self, doc_id: str):
        """Clean up any partial data from failed processing"""
        def db_cleanup():
            db = SessionLocal()
            try:
                # Remove any chunks that were created
                db.query(DocumentChunk).filter(DocumentChunk.document_id == doc_id).delete()
                # Remove document metadata if it exists
                db.query(Document).filter(Document.id == doc_id).delete()
                db.commit()
                print(f"🧹 Cleaned up failed processing for: {doc_id}")
            except Exception as e:
                print(f"⚠️ Error during cleanup: {e}")
                db.rollback()
            finally:
                db.close()
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, db_cleanup)
    
    async def get_document_stats(self) -> dict:
        """Get statistics about processed documents"""
        def get_stats():
            db = SessionLocal()
            try:
                total_docs = db.query(Document).count()
                total_chunks = db.query(DocumentChunk).count()
                
                return {
                    "total_documents": total_docs,
                    "total_chunks": total_chunks,
                    "avg_chunks_per_doc": round(total_chunks / total_docs, 2) if total_docs > 0 else 0
                }
            except Exception as e:
                print(f"Error getting stats: {e}")
                return {"error": str(e)}
            finally:
                db.close()
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, get_stats)

# Global document service instance
document_service = DocumentService()