#!/bin/bash

# Startup script for the application
echo "🚀 Starting LLM Query System..."

# Wait for databases to be ready
echo "⏳ Waiting for PostgreSQL to be ready..."
while ! nc -z postgres 5432; do
  sleep 1
done
echo "✅ PostgreSQL is ready!"

echo "⏳ Waiting for Qdrant to be ready..."
while ! nc -z qdrant 6333; do
  sleep 1
done
echo "✅ Qdrant is ready!"

# Create database tables
echo "📋 Creating database tables..."
python app/create_tables.py

# Initialize Qdrant collection
echo "🔧 Initializing Qdrant collection..."
python -c "from app.vector_store import ensure_collection_correct; ensure_collection_correct()"

# Start the application
echo "🎯 Starting FastAPI application..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload