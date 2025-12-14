"""
Retry Handler - Retry failed operations with exponential backoff
"""
import time
import random
from typing import Callable, Any, Optional, Type
from functools import wraps

class RetryHandler:
    """Handle retries with exponential backoff"""
    
    @staticmethod
    def retry(
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        exceptions: tuple = (Exception,)
    ):
        """
        Decorator to retry function calls with exponential backoff
        
        Args:
            max_attempts: Maximum number of attempts
            base_delay: Base delay in seconds
            max_delay: Maximum delay in seconds
            exponential_base: Base for exponential backoff
            jitter: Add random jitter to delay
            exceptions: Tuple of exceptions to catch and retry
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs) -> Any:
                last_exception = None
                
                for attempt in range(1, max_attempts + 1):
                    try:
                        return func(*args, **kwargs)
                    except exceptions as e:
                        last_exception = e
                        
                        if attempt == max_attempts:
                            # Last attempt failed, raise exception
                            raise e
                        
                        # Calculate delay with exponential backoff
                        delay = min(
                            base_delay * (exponential_base ** (attempt - 1)),
                            max_delay
                        )
                        
                        # Add jitter if enabled
                        if jitter:
                            delay = delay * (0.5 + random.random())
                        
                        print(f"⚠️ {func.__name__} failed (attempt {attempt}/{max_attempts}): {e}")
                        print(f"   Retrying in {delay:.2f} seconds...")
                        time.sleep(delay)
                
                # Should never reach here, but just in case
                if last_exception:
                    raise last_exception
            
            return wrapper
        return decorator

# Convenience function
def retry_on_failure(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    exceptions: tuple = (Exception,)
):
    """Simple retry decorator"""
    return RetryHandler.retry(
        max_attempts=max_attempts,
        base_delay=base_delay,
        exceptions=exceptions
    )

