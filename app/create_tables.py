# app/create_tables.py (Robust version)
"""
Robust database initialization script with proper error handling.
"""
import os
import sys
import time
import psycopg2
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

# Add the app directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def wait_for_postgres(database_url, max_retries=30, delay=2):
    """Wait for PostgreSQL to be ready"""
    print("🔄 Waiting for PostgreSQL to be ready...")
    
    for attempt in range(max_retries):
        try:
            # Extract connection details from DATABASE_URL
            engine = create_engine(database_url)
            
            # Test connection
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            print("✅ PostgreSQL is ready!")
            return True
            
        except (OperationalError, psycopg2.OperationalError) as e:
            print(f"⏳ Attempt {attempt + 1}/{max_retries}: PostgreSQL not ready yet ({e})")
            if attempt < max_retries - 1:
                time.sleep(delay)
            else:
                print("❌ PostgreSQL connection timeout")
                return False
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            return False

def create_database_tables():
    """Create database tables with proper error handling"""
    try:
        # Import here to avoid circular imports
        from database import engine
        from models_db import Base
        
        print("🗑️ Dropping existing tables...")
        try:
            Base.metadata.drop_all(bind=engine)
            print("✅ Existing tables dropped successfully")
        except Exception as e:
            print(f"⚠️ No existing tables to drop: {e}")

        print("📋 Creating new tables...")
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created successfully!")
        
        # Verify tables were created
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"📊 Created tables: {tables}")
        
        if 'documents' not in tables or 'document_chunks' not in tables:
            raise Exception("Required tables were not created")
            
        # Print table schema for verification
        for table in tables:
            columns = inspector.get_columns(table)
            print(f"\n📋 Table '{table}':")
            for col in columns:
                print(f"  - {col['name']}: {col['type']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main initialization function"""
    print("🚀 Starting database initialization...")
    
    # Get database URL
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL environment variable not set")
        sys.exit(1)
    
    print(f"🔧 Database URL: {database_url}")
    
    # Wait for PostgreSQL to be ready
    if not wait_for_postgres(database_url):
        print("❌ Could not connect to PostgreSQL")
        sys.exit(1)
    
    # Create tables
    if not create_database_tables():
        print("❌ Failed to create database tables")
        sys.exit(1)
    
    print("✅ Database initialization complete!")

if __name__ == "__main__":
    main()