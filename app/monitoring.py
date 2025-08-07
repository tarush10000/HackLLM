"""
Performance monitoring and metrics collection.
"""
import time
import asyncio
from typing import Dict, List
from functools import wraps
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PerformanceMonitor:
    def __init__(self):
        self.metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "average_response_time": 0,
            "embedding_time": 0,
            "retrieval_time": 0,
            "generation_time": 0,
            "response_times": []
        }
    
    def record_request(self, success: bool, response_time: float):
        """Record request metrics"""
        self.metrics["total_requests"] += 1
        if success:
            self.metrics["successful_requests"] += 1
        else:
            self.metrics["failed_requests"] += 1
        
        self.metrics["response_times"].append(response_time)
        
        # Keep only last 100 response times
        if len(self.metrics["response_times"]) > 100:
            self.metrics["response_times"] = self.metrics["response_times"][-100:]
        
        # Calculate average
        self.metrics["average_response_time"] = sum(self.metrics["response_times"]) / len(self.metrics["response_times"])
    
    def record_component_time(self, component: str, time_taken: float):
        """Record component-specific timing"""
        if component in self.metrics:
            self.metrics[component] = time_taken
    
    def get_metrics(self) -> Dict:
        """Get current metrics"""
        return self.metrics.copy()
    
    def log_metrics(self):
        """Log current metrics"""
        logger.info(f"Performance Metrics: {self.get_metrics()}")

# Global monitor instance
monitor = PerformanceMonitor()

def track_time(component: str = None):
    """Decorator to track execution time"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                success = True
                return result
            except Exception as e:
                success = False
                raise e
            finally:
                end_time = time.time()
                execution_time = end_time - start_time
                
                if component:
                    monitor.record_component_time(component, execution_time)
                else:
                    monitor.record_request(success, execution_time)
                    
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                success = True
                return result
            except Exception as e:
                success = False
                raise e
            finally:
                end_time = time.time()
                execution_time = end_time - start_time
                
                if component:
                    monitor.record_component_time(component, execution_time)
                else:
                    monitor.record_request(success, execution_time)
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator