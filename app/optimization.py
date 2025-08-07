"""
Performance optimization utilities and configurations.
"""
import asyncio
from typing import List, Dict, Any
import concurrent.futures
from functools import lru_cache
import threading
import time

class OptimizationManager:
    """Manages various performance optimizations"""
    
    def __init__(self):
        self.thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=4)
        self.process_pool = concurrent.futures.ProcessPoolExecutor(max_workers=2)
        self._stats = {
            "cache_hits": 0,
            "cache_misses": 0,
            "parallel_executions": 0,
            "optimization_savings": 0
        }
    
    async def parallel_execute(self, tasks: List[callable], max_workers: int = None) -> List[Any]:
        """Execute multiple tasks in parallel"""
        self._stats["parallel_executions"] += 1
        
        if not tasks:
            return []
        
        # Determine optimal batch size
        batch_size = min(len(tasks), max_workers or 4)
        
        results = []
        for i in range(0, len(tasks), batch_size):
            batch = tasks[i:i + batch_size]
            batch_results = await asyncio.gather(*[
                self._execute_task(task) for task in batch
            ], return_exceptions=True)
            results.extend(batch_results)
        
        return results
    
    async def _execute_task(self, task):
        """Execute a single task safely"""
        try:
            if asyncio.iscoroutinefunction(task):
                return await task()
            else:
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(self.thread_pool, task)
        except Exception as e:
            return e
    
    @lru_cache(maxsize=1000)
    def cached_text_processing(self, text: str, operation: str) -> str:
        """Cached text processing operations"""
        self._stats["cache_hits"] += 1
        
        if operation == "clean":
            return self._clean_text_operation(text)
        elif operation == "normalize":
            return self._normalize_text_operation(text)
        else:
            return text
    
    def _clean_text_operation(self, text: str) -> str:
        """Expensive text cleaning operation"""
        import re
        # Simulate expensive operation
        cleaned = re.sub(r'\s+', ' ', text)
        cleaned = re.sub(r'[^\w\s\.\,\;\:\!\?\-\(\)]', ' ', cleaned)
        return cleaned.strip()
    
    def _normalize_text_operation(self, text: str) -> str:
        """Text normalization operation"""
        return text.lower().strip()
    
    def get_optimization_stats(self) -> Dict[str, int]:
        """Get optimization statistics"""
        return self._stats.copy()
    
    def cleanup(self):
        """Cleanup resources"""
        self.thread_pool.shutdown(wait=True)
        self.process_pool.shutdown(wait=True)

# Global optimization manager
optimizer = OptimizationManager()
