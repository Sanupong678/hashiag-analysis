"""
Cache Manager for improving performance
Simple in-memory cache with TTL support
"""
from datetime import datetime, timedelta
from typing import Any, Optional
import json
import hashlib

class CacheManager:
    """Simple in-memory cache with TTL"""
    
    def __init__(self):
        self._cache = {}
        self._default_ttl = timedelta(minutes=5)
    
    def _generate_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate cache key from arguments"""
        key_data = {
            'prefix': prefix,
            'args': args,
            'kwargs': sorted(kwargs.items())
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def get(self, prefix: str, *args, **kwargs) -> Optional[Any]:
        """Get value from cache"""
        key = self._generate_key(prefix, *args, **kwargs)
        
        if key not in self._cache:
            return None
        
        entry = self._cache[key]
        
        # Check if expired
        if datetime.utcnow() > entry['expires_at']:
            del self._cache[key]
            return None
        
        return entry['value']
    
    def set(self, prefix: str, value: Any, ttl: Optional[timedelta] = None, *args, **kwargs):
        """Set value in cache"""
        key = self._generate_key(prefix, *args, **kwargs)
        
        if ttl is None:
            ttl = self._default_ttl
        
        self._cache[key] = {
            'value': value,
            'expires_at': datetime.utcnow() + ttl,
            'created_at': datetime.utcnow()
        }
    
    def clear(self, prefix: Optional[str] = None):
        """Clear cache entries"""
        if prefix is None:
            self._cache.clear()
        else:
            # Clear entries matching prefix
            keys_to_delete = [
                key for key in self._cache.keys()
                if key.startswith(prefix)
            ]
            for key in keys_to_delete:
                del self._cache[key]
    
    def get_stats(self) -> dict:
        """Get cache statistics"""
        now = datetime.utcnow()
        total_entries = len(self._cache)
        expired_entries = sum(
            1 for entry in self._cache.values()
            if now > entry['expires_at']
        )
        
        return {
            'total_entries': total_entries,
            'active_entries': total_entries - expired_entries,
            'expired_entries': expired_entries
        }

# Global cache instance
cache = CacheManager()

