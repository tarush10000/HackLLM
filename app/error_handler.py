"""
Comprehensive error handling and recovery mechanisms.
"""
import logging
import traceback
from typing import Optional, Any, Dict
from fastapi import HTTPException
import asyncio

logger = logging.getLogger(__name__)

class ErrorHandler:
    """Centralized error handling with recovery strategies"""
    
    def __init__(self):
        self.error_counts = {}
        self.circuit_breakers = {}
    
    async def handle_with_retry(self, 
                               func, 
                               *args, 
                               max_retries: int = 3, 
                               delay: float = 1.0,
                               backoff_factor: float = 2.0,
                               **kwargs) -> Any:
        """Execute function with exponential backoff retry"""
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                
                if attempt == max_retries:
                    break
                
                wait_time = delay * (backoff_factor ** attempt)
                logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
        
        # Log the final failure
        logger.error(f"Function {func.__name__} failed after {max_retries + 1} attempts: {last_exception}")
        self._record_error(func.__name__)
        raise last_exception
    
    def _record_error(self, function_name: str):
        """Record error for monitoring"""
        if function_name not in self.error_counts:
            self.error_counts[function_name] = 0
        self.error_counts[function_name] += 1
    
    def get_error_stats(self) -> Dict[str, int]:
        """Get error statistics"""
        return self.error_counts.copy()
    
    async def safe_execute(self, func, *args, default_return=None, **kwargs):
        """Execute function safely with default return on error"""
        try:
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            else:
                return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Safe execution failed for {func.__name__}: {e}")
            self._record_error(func.__name__)
            return default_return

# Global error handler
error_handler = ErrorHandler()
