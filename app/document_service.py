# app/document_service.py (Simplified - PostgreSQL Only Check)
"""
Document processing service with simple PostgreSQL-only deduplication.
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
import hashlib

class DocumentService:
    """Service for managing document processing and deduplication"""
    
    def __init__(self):
        # Get number of API keys for intelligent batch sizing
        import os
        api_keys_str = os.getenv("GOOGLE_API_KEY", "")
        self.num_api_keys = len([key.strip() for key in api_keys_str.split(",") if key.strip()])
        
        # Calculate smart batch sizes based on API keys and rate limits
        max_safe_batch = max(5, min(self.num_api_keys * 3, 15))  # Between 5-15
        med_safe_batch = max(5, min(self.num_api_keys * 2, 10))  # Between 5-10  
        min_safe_batch = max(3, min(self.num_api_keys, 8))       # Between 3-8
        
        print(f"🔑 Detected {self.num_api_keys} API keys")
        print(f"📊 Batch sizes: small={max_safe_batch}, medium={med_safe_batch}, large={min_safe_batch}")
        
        # Configuration for different file sizes with rate-limit-aware batching
        self.size_configs = {
            "small": {"max_size": 10 * 1024 * 1024, "timeout": 30, "chunk_batch": max_safe_batch},
            "medium": {"max_size": 50 * 1024 * 1024, "timeout": 120, "chunk_batch": med_safe_batch},  
            "large": {"max_size": 200 * 1024 * 1024, "timeout": 300, "chunk_batch": min_safe_batch},
            "xlarge": {"max_size": float('inf'), "timeout": 600, "chunk_batch": min_safe_batch}
        }
    
    def get_config_for_size(self, file_size: int) -> dict:
        """Get appropriate configuration based on file size"""
        for size_type, config in self.size_configs.items():
            if file_size <= config["max_size"]:
                return {"type": size_type, **config}
        return {"type": "xlarge", **self.size_configs["xlarge"]}
    
    def extract_filename_from_url(self, url: str) -> str:
        """Extract clean filename from URL"""
        try:
            parsed = urlparse(url)
            path = parsed.path
            filename = path.split('/')[-1]
            
            if not filename or filename == '':
                filename = "document.pdf"
            
            filename = filename.split('?')[0]
            
            if '.' not in filename:
                filename += '.pdf'
            
            print(f"📄 Extracted filename: {filename} from URL: {url[:50]}...")
            return filename
            
        except Exception as e:
            print(f"⚠️ Error extracting filename: {e}")
            return "document.pdf"
    
    async def check_document_exists(self, file_name: str, file_size: int, first_words: str) -> Optional[str]:
        """
        SIMPLIFIED: Only check PostgreSQL for document existence.
        Trust that if it's in PostgreSQL, it should be in Qdrant too.
        Returns document_id if exists, None otherwise.
        """
        content_hash = hash_pdf_metadata(file_name, file_size, first_words)
        
        def db_operation():
            db = SessionLocal()
            try:
                # Check if document with this hash already exists in PostgreSQL
                existing_doc = db.query(Document).filter(Document.content_hash == content_hash).first()
                
                if existing_doc:
                    print(f"✅ Document found in PostgreSQL: {existing_doc.id}")
                    print(f"📅 Processed at: {existing_doc.processed_at}")
                    print(f"📊 Total chunks: {existing_doc.total_chunks}")
                    print(f"📄 File: {existing_doc.file_name}")
                    return existing_doc.id
                
                print(f"📝 New document detected: {file_name} (hash: {content_hash[:12]}...)")
                return None
                
            except Exception as e:
                print(f"❌ Error checking PostgreSQL: {e}")
                return None
            finally:
                db.close()
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, db_operation)
    
    async def get_document_preview(self, doc_url: str) -> Tuple[str, int, str]:
        """Get document metadata with progressive timeout handling."""
        file_name = self.extract_filename_from_url(doc_url)
        
        print(f"🔍 Getting document info for: {file_name}")
        
        try:
            file_size = await self._get_file_size_via_head(doc_url)
            config = self.get_config_for_size(file_size)
            
            print(f"📏 File size: {file_size:,} bytes ({config['type']} file)")
            print(f"⏱️ Using timeout: {config['timeout']}s")
            
        except Exception as e:
            print(f"⚠️ Could not get file size via HEAD request: {e}")
            file_size = 25 * 1024 * 1024  # 25MB assumption
            config = self.get_config_for_size(file_size)
        
        try:
            first_words = await self._get_document_preview_robust(doc_url, config, file_size)
            
            print(f"📄 Document preview - Name: {file_name}, Size: {file_size:,} bytes")
            print(f"📝 Preview: {first_words[:100]}...")
            return file_name, file_size, first_words
            
        except Exception as e:
            print(f"❌ Error getting document preview: {e}")
            url_hash = hashlib.md5(doc_url.encode()).hexdigest()[:8]
            fallback_preview = f"large_file_{file_size}_{url_hash}_{file_name}"
            print(f"🔄 Using fallback preview: {fallback_preview}")
            return file_name, file_size, fallback_preview
    
    async def _get_file_size_via_head(self, url: str) -> int:
        """Get file size using HEAD request without downloading"""
        timeout = aiohttp.ClientTimeout(total=10)
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.head(url) as response:
                response.raise_for_status()
                
                content_length = response.headers.get('content-length')
                if content_length:
                    return int(content_length)
                else:
                    return await self._estimate_size_via_partial_download(session, url)
    
    async def _estimate_size_via_partial_download(self, session: aiohttp.ClientSession, url: str) -> int:
        """Estimate file size via partial download"""
        headers = {'Range': 'bytes=0-1024'}
        async with session.get(url, headers=headers) as response:
            if response.status == 206:
                content_range = response.headers.get('content-range', '')
                if '/' in content_range:
                    total_size = content_range.split('/')[-1]
                    if total_size.isdigit():
                        return int(total_size)
            
            return 25 * 1024 * 1024  # 25MB
    
    async def _get_document_preview_robust(self, doc_url: str, config: dict, file_size: int) -> str:
        """Get document preview with robust error handling"""
        timeout = aiohttp.ClientTimeout(total=config['timeout'])
        
        if config['type'] in ['large', 'xlarge']:
            return await self._get_preview_streaming(doc_url, timeout)
        else:
            return await self._get_preview_standard(doc_url, timeout)
    
    async def _get_preview_streaming(self, doc_url: str, timeout: aiohttp.ClientTimeout) -> str:
        """Stream large files and extract preview from first page only"""
        print(f"📥 Using streaming preview for large file...")
        
        try:
            async for page_text in extract_text_generator_async(doc_url):
                first_words = get_first_n_words(clean_text(page_text), 20)
                if first_words and len(first_words.strip()) > 10:
                    print(f"✅ Got preview from first page streaming")
                    return first_words
                break
                
        except Exception as e:
            print(f"⚠️ Streaming preview failed: {e}")
            raise
        
        return f"no_preview_large_file_{len(doc_url)}"
    
    async def _get_preview_standard(self, doc_url: str, timeout: aiohttp.ClientTimeout) -> str:
        """Standard preview method for smaller files"""
        try:
            async for page_text in extract_text_generator_async(doc_url):
                first_words = get_first_n_words(clean_text(page_text), 20)
                if first_words:
                    return first_words
                break
                
        except Exception as e:
            print(f"⚠️ Standard preview failed: {e}")
            raise
        
        return f"no_preview_{len(doc_url)}"
    
    async def process_new_document(self, doc_url: str, file_name: str, file_size: int, first_words: str) -> str:
        """
        Process a new document with size-appropriate strategies.
        Returns the document_id.
        """
        doc_id = str(uuid.uuid4())
        content_hash = hash_pdf_metadata(file_name, file_size, first_words)
        config = self.get_config_for_size(file_size)
        
        print(f"🔄 Processing {config['type']} document: {doc_id}")
        print(f"⚙️ Config: timeout={config['timeout']}s, batch_size={config['chunk_batch']}")
        
        try:
            # Extract text with appropriate timeout handling
            full_text = await self._extract_text_robust(doc_url, config)
            
            # Create chunks
            chunks = chunk_pageText(full_text)
            
            if not chunks:
                raise Exception("No chunks created from document")
            
            print(f"📝 Created {len(chunks)} chunks")
            
            # Process in batches for large documents
            doc_id = await self._process_chunks_in_batches(
                doc_id, chunks, file_name, file_size, first_words, content_hash, config
            )
            
            print(f"✅ {config['type'].upper()} document processing complete: {doc_id}")
            return doc_id
            
        except Exception as e:
            print(f"❌ Error processing {config['type']} document: {e}")
            await self._cleanup_failed_processing(doc_id)
            raise
    
    async def _extract_text_robust(self, doc_url: str, config: dict) -> str:
        """Extract text with robust timeout handling"""
        print(f"📖 Extracting text from {config['type']} file...")
        
        full_text = ""
        page_count = 0
        
        try:
            async for page_text in extract_text_generator_async(doc_url):
                cleaned = clean_text(page_text)
                full_text += "\n" + cleaned
                page_count += 1
                
                # For very large files, show progress
                if config['type'] in ['large', 'xlarge'] and page_count % 10 == 0:
                    print(f"📄 Processed {page_count} pages...")
                
                # Optional: Limit pages for extremely large documents
                if config['type'] == 'xlarge' and page_count > 1000:
                    print(f"⚠️ Limiting to first 1000 pages for processing efficiency")
                    break
                    
        except Exception as e:
            if page_count > 0:
                print(f"⚠️ Partial extraction: got {page_count} pages before error: {e}")
                print(f"🔄 Continuing with available content...")
            else:
                raise Exception(f"Text extraction failed completely: {e}")
        
        print(f"✅ Extracted text from {page_count} pages ({len(full_text):,} characters)")
        return full_text
    
    async def _process_chunks_in_batches(self, doc_id: str, chunks: list, file_name: str, 
                                       file_size: int, first_words: str, content_hash: str, 
                                       config: dict) -> str:
        """Process chunks in batches for large documents"""
        batch_size = config['chunk_batch']
        total_chunks = len(chunks)
        
        print(f"🔄 Processing {total_chunks} chunks in batches of {batch_size}")
        
        # Store document metadata first
        await self._store_document_metadata(doc_id, file_name, file_size, first_words, content_hash, total_chunks)
        
        # Process chunks in batches
        for i in range(0, total_chunks, batch_size):
            batch_chunks = chunks[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (total_chunks + batch_size - 1) // batch_size
            
            print(f"📦 Processing batch {batch_num}/{total_batches} ({len(batch_chunks)} chunks)")
            
            try:
                await self._process_chunk_batch(doc_id, batch_chunks, i, file_name)
                print(f"✅ Batch {batch_num}/{total_batches} completed")
                
            except Exception as e:
                print(f"❌ Batch {batch_num} failed: {e}")
                # For large files, continue with other batches instead of failing completely
                if config['type'] in ['large', 'xlarge']:
                    print(f"⚠️ Continuing with remaining batches...")
                    continue
                else:
                    raise
        
        print(f"🎉 All batches processed for document: {doc_id}")
        return doc_id
    
    async def _process_chunk_batch(self, doc_id: str, chunks: list, start_idx: int, file_name: str):
        """Process a single batch of chunks with rate limit awareness"""
        chunk_texts = []
        metadata_list = []
        
        for idx, chunk in enumerate(chunks):
            chunk_index = start_idx + idx
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
        
        print(f"🧠 Generating embeddings for batch of {len(chunk_texts)} chunks...")
        print(f"🔑 Using {self.num_api_keys} API keys for parallel processing")
        
        # Add small delay between batches to respect rate limits
        if len(chunk_texts) > 5:
            print(f"⏳ Adding rate limit delay...")
            await asyncio.sleep(2)  # Small delay for larger batches
        
        # Generate embeddings for this batch
        vectors = await embed_chunks_async(chunk_texts)
        
        # Store in vector database
        await upsert_chunks_async(doc_id, chunk_texts, vectors, metadata_list)
    
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
                
                # Get size distribution
                docs = db.query(Document.file_size).all()
                sizes = [doc.file_size for doc in docs]
                
                size_stats = {
                    "small": len([s for s in sizes if s <= 10*1024*1024]),
                    "medium": len([s for s in sizes if 10*1024*1024 < s <= 50*1024*1024]),
                    "large": len([s for s in sizes if 50*1024*1024 < s <= 200*1024*1024]),
                    "xlarge": len([s for s in sizes if s > 200*1024*1024])
                }
                
                return {
                    "total_documents": total_docs,
                    "total_chunks": total_chunks,
                    "avg_chunks_per_doc": round(total_chunks / total_docs, 2) if total_docs > 0 else 0,
                    "size_distribution": size_stats
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