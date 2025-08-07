"""
Application startup configuration and initialization.
"""
import asyncio
import os
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.vector_store import ensure_collection_correct_async
from app.database import engine, Base
from app.monitoring import monitor
from app.optimization import optimizer
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    logger.info("🚀 Starting LLM Query System...")
    
    try:
        # Initialize database
        logger.info("📊 Initializing database...")
        Base.metadata.create_all(bind=engine)
        
        # Initialize vector store
        logger.info("🔍 Initializing vector store...")
        await ensure_collection_correct_async()
        
        # Warm up services
        logger.info("🔥 Warming up services...")
        await warmup_services()
        
        logger.info("✅ Application startup complete!")
        
        yield
        
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        raise
    finally:
        # Shutdown
        logger.info("🛑 Shutting down application...")
        
        # Cleanup resources
        optimizer.cleanup()
        
        # Log final metrics
        monitor.log_metrics()
        
        logger.info("✅ Shutdown complete!")

async def warmup_services():
    """Warm up critical services"""
    try:
        # Test embedding generation
        from app.embeddings import embed_chunks_async
        await embed_chunks_async(["test query"])
        
        # Test vector search
        from app.vector_store import search_chunks_async
        import numpy as np
        test_vector = np.random.rand(768).tolist()
        await search_chunks_async(test_vector, top_k=1)
        
        logger.info("✅ Services warmed up successfully")
        
    except Exception as e:
        logger.warning(f"⚠️ Service warmup failed: {e}")

def create_optimized_app() -> FastAPI:
    """Create optimized FastAPI application"""
    app = FastAPI(
        title="LLM Query System",
        description="High-performance document query and retrieval system",
        version="1.0.0",
        lifespan=lifespan
    )
    
    # Add middleware for performance monitoring
    @app.middleware("http")
    async def performance_middleware(request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # Log slow requests
        if process_time > 5.0:
            logger.warning(f"Slow request: {request.url} took {process_time:.2f}s")
        
        response.headers["X-Process-Time"] = str(process_time)
        return response
    
    return app
