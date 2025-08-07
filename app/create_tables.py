# app/create_tables.py (Final version)
import os
import sys

# Add the app directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import engine
from models_db import Base

print("🔧 Database URL:", os.getenv("DATABASE_URL", "Not set"))

try:
    print("🗑️ Dropping existing tables...")
    Base.metadata.drop_all(bind=engine)
    print("✅ Tables dropped successfully")
except Exception as e:
    print(f"⚠️ Error dropping tables: {e}")

try:
    print("📋 Creating new tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully!")
except Exception as e:
    print(f"❌ Error creating tables: {e}")
    sys.exit(1)

# Print table information
try:
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"📊 Created tables: {tables}")

    for table in tables:
        columns = inspector.get_columns(table)
        print(f"\n📋 Table '{table}':")
        for col in columns:
            print(f"  - {col['name']}: {col['type']}")
            
except Exception as e:
    print(f"⚠️ Could not inspect tables: {e}")

print("\n✅ Database setup complete!")