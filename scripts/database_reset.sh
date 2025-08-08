#!/bin/bash

echo "🧹 Complete Database Cleanup Script"
echo "==================================="

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${YELLOW}This will completely reset your database setup.${NC}"
echo -e "${RED}⚠️  WARNING: This will delete ALL data!${NC}"
echo ""
read -p "Are you sure you want to continue? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 1
fi

echo -e "\n${BLUE}Step 1: Stopping all Docker containers...${NC}"
docker-compose down
echo "✅ Containers stopped"

echo -e "\n${BLUE}Step 2: Removing Docker volumes (database data)...${NC}"
docker-compose down -v
echo "✅ Docker volumes removed"

echo -e "\n${BLUE}Step 3: Cleaning up Docker system...${NC}"
docker system prune -f
echo "✅ Docker system cleaned"

echo -e "\n${BLUE}Step 4: Removing specific volumes if they exist...${NC}"
# Remove specific volumes that might be lingering
docker volume rm $(docker volume ls -q | grep -E "(postgres|qdrant|redis)" | head -10) 2>/dev/null || echo "No specific volumes found"
echo "✅ Specific volumes cleaned"

echo -e "\n${BLUE}Step 5: Checking for local PostgreSQL interference...${NC}"

# Check if PostgreSQL is running locally
if pgrep -x "postgres" > /dev/null; then
    echo -e "${YELLOW}⚠️  Local PostgreSQL is running on this system${NC}"
    echo "This might interfere with Docker PostgreSQL on port 5432"
    echo ""
    echo "Options to fix this:"
    echo "1. Stop local PostgreSQL: sudo systemctl stop postgresql"
    echo "2. Change Docker PostgreSQL port in docker-compose.yml"
    echo "3. Use different database name"
    echo ""
    read -p "Do you want me to suggest port changes? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${BLUE}Suggested docker-compose.yml changes:${NC}"
        echo "Change PostgreSQL port from '5432:5432' to '5433:5432'"
        echo "Update DATABASE_URL to: postgresql://postgres:password@postgres:5432/document_chunks"
        echo "(The internal port stays 5432, external becomes 5433)"
    fi
else
    echo "✅ No local PostgreSQL detected"
fi

# Check if ports are being used
echo -e "\n${BLUE}Step 6: Checking port availability...${NC}"
for port in 5432 6333 6379 8000; do
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo -e "${RED}❌ Port $port is in use${NC}"
        echo "Process using port $port:"
        lsof -Pi :$port -sTCP:LISTEN | head -2
        echo ""
    else
        echo -e "${GREEN}✅ Port $port is available${NC}"
    fi
done

echo -e "\n${BLUE}Step 7: Rebuilding Docker images...${NC}"
docker-compose build --no-cache
echo "✅ Docker images rebuilt"

echo -e "\n${GREEN}🎉 Cleanup complete!${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. If ports were in use, either:"
echo "   - Stop the conflicting services"
echo "   - Or modify docker-compose.yml to use different ports"
echo ""
echo "2. Start fresh:"
echo "   docker-compose up -d postgres redis qdrant"
echo "   docker-compose run --rm db-init"
echo "   docker-compose up -d app"
echo ""
echo "3. Or use the startup script if you created it:"
echo "   ./start.sh"