"""
Redis Cache Manager - สำหรับ cache ข้อมูลหุ้น
ลดการดึงข้อมูลซ้ำและเพิ่มความเร็ว
"""
import redis
import json
from typing import Optional, Dict, List, Any
from datetime import timedelta
import os

class RedisCache:
    """
    Redis cache manager สำหรับข้อมูลหุ้น
    """
    def __init__(self, host: str = 'localhost', port: int = 6379, db: int = 0):
        """
        Initialize Redis connection
        
        Args:
            host: Redis host
            port: Redis port
            db: Redis database number
        """
        try:
            self.client = redis.Redis(
                host=host,
                port=port,
                db=db,
                decode_responses=True,
                socket_connect_timeout=5
            )
            # Test connection
            self.client.ping()
            print("✅ Redis connection established")
        except Exception as e:
            print(f"⚠️ Redis not available: {e}")
            self.client = None
    
    def _serialize(self, data: Any) -> str:
        """Serialize data to JSON string"""
        return json.dumps(data, default=str)
    
    def _deserialize(self, data: str) -> Any:
        """Deserialize JSON string to data"""
        return json.loads(data)
    
    def get_stock_info(self, symbol: str) -> Optional[Dict]:
        """
        ดึงข้อมูลหุ้นจาก cache
        
        Args:
            symbol: Stock symbol
        
        Returns:
            Stock info dict or None
        """
        if not self.client:
            return None
        
        try:
            cached = self.client.get(f"stock:info:{symbol.upper()}")
            if cached:
                return self._deserialize(cached)
        except Exception as e:
            print(f"⚠️ Error getting cache for {symbol}: {e}")
        
        return None
    
    def set_stock_info(self, symbol: str, data: Dict, ttl: int = 900):
        """
        บันทึกข้อมูลหุ้นลง cache
        
        Args:
            symbol: Stock symbol
            data: Stock info dict
            ttl: Time to live in seconds (default: 15 minutes)
        """
        if not self.client:
            return
        
        try:
            self.client.setex(
                f"stock:info:{symbol.upper()}",
                ttl,
                self._serialize(data)
            )
        except Exception as e:
            print(f"⚠️ Error caching {symbol}: {e}")
    
    def get_stock_news(self, symbol: str) -> Optional[List[Dict]]:
        """ดึงข่าวหุ้นจาก cache"""
        if not self.client:
            return None
        
        try:
            cached = self.client.get(f"stock:news:{symbol.upper()}")
            if cached:
                return self._deserialize(cached)
        except Exception as e:
            print(f"⚠️ Error getting news cache for {symbol}: {e}")
        
        return None
    
    def set_stock_news(self, symbol: str, news: List[Dict], ttl: int = 3600):
        """
        บันทึกข่าวหุ้นลง cache
        
        Args:
            symbol: Stock symbol
            news: List of news articles
            ttl: Time to live in seconds (default: 1 hour)
        """
        if not self.client:
            return
        
        try:
            self.client.setex(
                f"stock:news:{symbol.upper()}",
                ttl,
                self._serialize(news)
            )
        except Exception as e:
            print(f"⚠️ Error caching news for {symbol}: {e}")
    
    def get_sentiment(self, symbol: str) -> Optional[Dict]:
        """ดึง sentiment จาก cache"""
        if not self.client:
            return None
        
        try:
            cached = self.client.get(f"stock:sentiment:{symbol.upper()}")
            if cached:
                return self._deserialize(cached)
        except Exception as e:
            print(f"⚠️ Error getting sentiment cache for {symbol}: {e}")
        
        return None
    
    def set_sentiment(self, symbol: str, sentiment: Dict, ttl: int = 1800):
        """
        บันทึก sentiment ลง cache
        
        Args:
            symbol: Stock symbol
            sentiment: Sentiment dict
            ttl: Time to live in seconds (default: 30 minutes)
        """
        if not self.client:
            return
        
        try:
            self.client.setex(
                f"stock:sentiment:{symbol.upper()}",
                ttl,
                self._serialize(sentiment)
            )
        except Exception as e:
            print(f"⚠️ Error caching sentiment for {symbol}: {e}")
    
    def invalidate_stock(self, symbol: str):
        """ลบ cache ของหุ้น"""
        if not self.client:
            return
        
        try:
            keys = [
                f"stock:info:{symbol.upper()}",
                f"stock:news:{symbol.upper()}",
                f"stock:sentiment:{symbol.upper()}"
            ]
            self.client.delete(*keys)
        except Exception as e:
            print(f"⚠️ Error invalidating cache for {symbol}: {e}")
    
    def get_cache_stats(self) -> Dict:
        """ดึงสถิติ cache"""
        if not self.client:
            return {}
        
        try:
            info = self.client.info('stats')
            return {
                'keyspace_hits': info.get('keyspace_hits', 0),
                'keyspace_misses': info.get('keyspace_misses', 0),
                'total_keys': len(self.client.keys('stock:*'))
            }
        except Exception as e:
            print(f"⚠️ Error getting cache stats: {e}")
            return {}


# Global cache instance
cache = RedisCache(
    host=os.getenv('REDIS_HOST', 'localhost'),
    port=int(os.getenv('REDIS_PORT', 6379)),
    db=int(os.getenv('REDIS_DB', 0))
)


