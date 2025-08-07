"""
Intelligent caching system for embeddings and responses.
"""
import hashlib
import json
from typing import Optional, List, Dict, Any
import redis
import os
from datetime import timedelta

class IntelligentCache:
    def __init__(self):
        # Use Redis if available, otherwise use in-memory dict
        try:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            self.redis_client.ping()  # Test connection
            self.use_redis = True
            print("✅ Connected to Redis cache")
        except Exception as e:
            print(f"⚠️ Redis not available, using in-memory cache: {e}")
            self.use_redis = False
            self.memory_cache = {}
    
    def _get_cache_key(self, prefix: str, data: Any) -> str:
        """Generate cache key from data"""
        if isinstance(data, str):
            content = data
        else:
            content = json.dumps(data, sort_keys=True)
        
        hash_obj = hashlib.md5(content.encode())
        return f"{prefix}:{hash_obj.hexdigest()[:16]}"
    
    async def get_embedding(self, text: str) -> Optional[List[float]]:
        """Get cached embedding for text"""
        cache_key = self._get_cache_key("embedding", text)
        
        try:
            if self.use_redis:
                cached = self.redis_client.get(cache_key)
                if cached:
                    return json.loads(cached)
            else:
                return self.memory_cache.get(cache_key)
        except Exception as e:
            print(f"Cache get error: {e}")
        
        return None
    
    async def set_embedding(self, text: str, embedding: List[float], ttl_hours: int = 24):
        """Cache embedding for text"""
        cache_key = self._get_cache_key("embedding", text)
        
        try:
            if self.use_redis:
                self.redis_client.setex(
                    cache_key, 
                    timedelta(hours=ttl_hours), 
                    json.dumps(embedding)
                )
            else:
                self.memory_cache[cache_key] = embedding
                # Simple TTL for memory cache (not implemented for brevity)
        except Exception as e:
            print(f"Cache set error: {e}")
    
    async def get_response(self, question: str, doc_id: str) -> Optional[str]:
        """Get cached response for question-document pair"""
        cache_key = self._get_cache_key("response", f"{question}:{doc_id}")
        
        try:
            if self.use_redis:
                return self.redis_client.get(cache_key)
            else:
                return self.memory_cache.get(cache_key)
        except Exception as e:
            print(f"Cache get error: {e}")
        
        return None
    
    async def set_response(self, question: str, doc_id: str, response: str, ttl_hours: int = 6):
        """Cache response for question-document pair"""
        cache_key = self._get_cache_key("response", f"{question}:{doc_id}")
        
        try:
            if self.use_redis:
                self.redis_client.setex(cache_key, timedelta(hours=ttl_hours), response)
            else:
                self.memory_cache[cache_key] = response
        except Exception as e:
            print(f"Cache set error: {e}")

# Global cache instance
cache = IntelligentCache()
