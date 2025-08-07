#!/bin/bash
set -e

# Startup script for the application
echo "🚀 Starting LLM Query System..."

# Function to wait for service
wait_for_service() {
    local host=$1
    local port=$2
    local service_name=$3
    
    echo "⏳ Waiting for $service_name to be ready..."
    while ! nc -z $host $port; do
        echo "Waiting for $service_name ($host:$port)..."
        sleep 2
    done
    echo "✅ $service_name is ready!"
}

# Wait for databases to be ready
wait_for_service postgres 5432 "PostgreSQL"
wait_for_service qdrant 6333 "Qdrant"

# Additional wait to ensure services are fully initialized
echo "⏳ Waiting for services to fully initialize..."
sleep 10

# Create database tables
echo "📋 Creating database tables..."
python app/create_tables.py

# Initialize Qdrant collection with retry logic
echo "🔧 Initializing Qdrant collection..."
max_retries=5
retry_count=0

while [ $retry_count -lt $max_retries ]; do
    if python -c "from app.vector_store import ensure_collection_correct; ensure_collection_correct()"; then
        echo "✅ Qdrant collection initialized successfully"
        break
    else
        retry_count=$((retry_count + 1))
        echo "⚠️ Qdrant initialization failed, retrying... ($retry_count/$max_retries)"
        sleep 5
    fi
done

if [ $retry_count -eq $max_retries ]; then
    echo "❌ Failed to initialize Qdrant after $max_retries attempts"
    exit 1
fi

# Start the application
echo "🎯 Starting FastAPI application..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload