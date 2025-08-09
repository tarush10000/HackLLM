# app/explore_data.py
"""
Interactive PostgreSQL data explorer for your document chunks
"""
import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.models_db import Document, DocumentChunk
from app.database import SessionLocal

def explore_documents():
    """Explore document metadata"""
    db = SessionLocal()
    try:
        print("📄 DOCUMENTS OVERVIEW")
        print("=" * 50)
        
        # Get all documents
        docs = db.query(Document).all()
        
        if not docs:
            print("❌ No documents found!")
            return
            
        for i, doc in enumerate(docs, 1):
            print(f"\n{i}. Document ID: {doc.id}")
            print(f"   📁 File: {doc.file_name}")
            print(f"   📊 Size: {doc.file_size:,} bytes")
            print(f"   🧩 Chunks: {doc.total_chunks}")
            print(f"   ⏰ Processed: {doc.processed_at}")
            print(f"   🔤 Preview: {doc.first_words[:100]}...")
            print(f"   🔗 Hash: {doc.content_hash[:12]}...")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        db.close()

def explore_chunks(document_id=None, limit=10):
    """Explore document chunks"""
    db = SessionLocal()
    try:
        print(f"\n📝 DOCUMENT CHUNKS (Limit: {limit})")
        print("=" * 50)
        
        query = db.query(DocumentChunk)
        
        if document_id:
            query = query.filter(DocumentChunk.document_id == document_id)
            print(f"🔍 Filtering by document: {document_id}")
        
        chunks = query.order_by(DocumentChunk.document_id, DocumentChunk.chunk_id).limit(limit).all()
        
        if not chunks:
            print("❌ No chunks found!")
            return
            
        for i, chunk in enumerate(chunks, 1):
            print(f"\n{i}. Chunk ID: {chunk.id}")
            print(f"   📄 Document: {chunk.document_id[:12]}...")
            print(f"   📁 File: {chunk.file_name}")
            print(f"   🔢 Chunk #: {chunk.chunk_id}")
            print(f"   📄 Page: {chunk.page_number or 'N/A'}")
            print(f"   📂 Section: {chunk.section_title or 'N/A'}")
            print(f"   📝 Text Preview: {chunk.text[:150]}...")
            print(f"   📏 Text Length: {len(chunk.text)} chars")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        db.close()

def search_content(search_term, limit=5):
    """Search for content in chunks"""
    db = SessionLocal()
    try:
        print(f"\n🔍 SEARCH RESULTS for '{search_term}' (Limit: {limit})")
        print("=" * 50)
        
        chunks = db.query(DocumentChunk).filter(
            DocumentChunk.text.ilike(f'%{search_term}%')
        ).limit(limit).all()
        
        if not chunks:
            print(f"❌ No results found for '{search_term}'")
            return
            
        for i, chunk in enumerate(chunks, 1):
            # Highlight search term in preview
            text_preview = chunk.text[:200]
            highlighted = text_preview.replace(
                search_term, 
                f"**{search_term}**"
            )
            
            print(f"\n{i}. Match in {chunk.file_name}")
            print(f"   📄 Document: {chunk.document_id[:12]}...")
            print(f"   🔢 Chunk #: {chunk.chunk_id}")
            print(f"   📝 Context: ...{highlighted}...")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        db.close()

def get_stats():
    """Get database statistics"""
    db = SessionLocal()
    try:
        print("\n📊 DATABASE STATISTICS")
        print("=" * 50)
        
        # Count documents and chunks
        doc_count = db.query(Document).count()
        chunk_count = db.query(DocumentChunk).count()
        
        print(f"📄 Total Documents: {doc_count}")
        print(f"🧩 Total Chunks: {chunk_count}")
        
        if doc_count > 0:
            avg_chunks = chunk_count / doc_count
            print(f"📈 Avg Chunks per Document: {avg_chunks:.1f}")
        
        # Get file types
        file_types = db.query(DocumentChunk.doc_type).distinct().all()
        print(f"📁 Document Types: {[ft[0] for ft in file_types if ft[0]]}")
        
        # Get unique files
        unique_files = db.query(DocumentChunk.file_name).distinct().count()
        print(f"📂 Unique Files: {unique_files}")
        
        # Text length stats
        result = db.execute(text("""
            SELECT 
                MIN(LENGTH(text)) as min_length,
                MAX(LENGTH(text)) as max_length,
                AVG(LENGTH(text))::int as avg_length
            FROM document_chunks
        """)).fetchone()
        
        if result:
            print(f"📏 Text Length - Min: {result[0]}, Max: {result[1]}, Avg: {result[2]} chars")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        db.close()

def interactive_menu():
    """Interactive menu for data exploration"""
    while True:
        print("\n" + "="*60)
        print("🗄️  POSTGRESQL DATA EXPLORER")
        print("="*60)
        print("1. 📄 View Documents")
        print("2. 📝 View Chunks (all)")
        print("3. 🔍 Search Content")
        print("4. 📊 Database Statistics")
        print("5. 🎯 View Chunks for Specific Document")
        print("0. ❌ Exit")
        print("-"*60)
        
        choice = input("Choose an option (0-5): ").strip()
        
        if choice == "0":
            print("👋 Goodbye!")
            break
        elif choice == "1":
            explore_documents()
        elif choice == "2":
            limit = input("Enter limit (default 10): ").strip() or "10"
            explore_chunks(limit=int(limit))
        elif choice == "3":
            term = input("Enter search term: ").strip()
            if term:
                limit = input("Enter limit (default 5): ").strip() or "5"
                search_content(term, int(limit))
        elif choice == "4":
            get_stats()
        elif choice == "5":
            explore_documents()
            doc_id = input("Enter document ID: ").strip()
            if doc_id:
                limit = input("Enter limit (default 10): ").strip() or "10"
                explore_chunks(doc_id, int(limit))
        else:
            print("❌ Invalid choice!")

if __name__ == "__main__":
    # Check if we're in the right environment
    try:
        from app.database import SessionLocal
        interactive_menu()
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure you're running this from the app directory")
        print("Try: docker-compose exec app python app/explore_data.py")