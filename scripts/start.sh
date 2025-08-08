#!/bin/bash
set -e

echo "🚀 Starting LLM Query System..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check if service is running
check_service() {
    local service=$1
    local port=$2
    
    echo -e "${YELLOW}⏳ Checking $service on port $port...${NC}"
    
    for i in {1..30}; do
        if nc -z localhost $port 2>/dev/null; then
            echo -e "${GREEN}✅ $service is ready!${NC}"
            return 0
        fi
        echo "Waiting for $service... ($i/30)"
        sleep 2
    done
    
    echo -e "${RED}❌ $service failed to start${NC}"
    return 1
}

# Stop any existing containers
echo "🛑 Stopping existing containers..."
docker-compose down

# Start services
echo "🔧 Starting infrastructure services..."
docker-compose up -d postgres redis qdrant

# Wait for services to be ready
check_service "PostgreSQL" 5432
check_service "Redis" 6379
check_service "Qdrant" 6333

# Initialize database
echo "📋 Initializing database..."
docker-compose run --rm db-init

# Start the main application
echo "🎯 Starting FastAPI application..."
docker-compose up -d app

# Wait for app to be ready
echo "⏳ Waiting for application to start..."
sleep 10

check_service "FastAPI" 8000

echo -e "${GREEN}✅ System is ready!${NC}"
echo ""
echo "🌐 FastAPI API: http://localhost:8000"
echo "📚 API Docs: http://localhost:8000/docs"
echo "🔍 Qdrant UI: http://localhost:6333/dashboard"
echo ""
echo "📊 Check system status:"
echo "curl http://localhost:8000/health"
echo ""
echo "🛑 To stop all services:"
echo "docker-compose down"