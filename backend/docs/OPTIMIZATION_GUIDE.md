# 🚀 คู่มือการปรับปรุงประสิทธิภาพสำหรับการดึงข้อมูลหุ้นจำนวนมาก

## 📊 สถานการณ์
- **4000+ หุ้น** ต้องวิเคราะห์
- **หลายล้านข้อมูล** (ข่าว, Reddit, Twitter, YouTube)
- **ต้องการความเร็วสูงสุด** และ **ประสิทธิภาพสูงสุด**

---

## 🎯 กลยุทธ์หลัก (5 ระดับ)

### 1. **Parallel Processing & Async Architecture** ⚡

#### ปัญหาปัจจุบัน:
- ใช้ `ThreadPoolExecutor` แต่ยังไม่เพียงพอ
- API calls เป็นแบบ sequential บางส่วน
- ไม่มี async/await สำหรับ I/O operations

#### วิธีแก้ไข:

**A. ใช้ AsyncIO แทน ThreadPoolExecutor สำหรับ I/O-bound tasks:**
```python
import asyncio
import aiohttp
from typing import List, Dict

async def fetch_stock_data_async(symbol: str, session: aiohttp.ClientSession):
    """ดึงข้อมูลหุ้นแบบ async"""
    try:
        ticker = yf.Ticker(symbol)
        # ใช้ async wrapper สำหรับ yfinance
        info = await asyncio.to_thread(ticker.info)
        news = await asyncio.to_thread(lambda: ticker.news)
        return {'symbol': symbol, 'info': info, 'news': news}
    except Exception as e:
        print(f"Error fetching {symbol}: {e}")
        return None

async def fetch_multiple_stocks_async(symbols: List[str], batch_size: int = 50):
    """ดึงข้อมูลหลายหุ้นพร้อมกัน"""
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_stock_data_async(symbol, session) for symbol in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [r for r in results if r and not isinstance(r, Exception)]
```

**B. Batch Processing:**
```python
def process_stocks_in_batches(symbols: List[str], batch_size: int = 100):
    """ประมวลผลหุ้นเป็น batch"""
    for i in range(0, len(symbols), batch_size):
        batch = symbols[i:i + batch_size]
        # Process batch concurrently
        asyncio.run(fetch_multiple_stocks_async(batch))
```

---

### 2. **Caching & Database Optimization** 💾

#### A. Redis Caching (In-Memory):
```python
import redis
import json
from datetime import timedelta

redis_client = redis.Redis(host='localhost', port=6379, db=0)

def get_cached_stock_data(symbol: str) -> Optional[Dict]:
    """ดึงข้อมูลจาก cache"""
    cached = redis_client.get(f"stock:{symbol}")
    if cached:
        return json.loads(cached)
    return None

def cache_stock_data(symbol: str, data: Dict, ttl: int = 3600):
    """บันทึกข้อมูลลง cache (TTL = 1 ชั่วโมง)"""
    redis_client.setex(
        f"stock:{symbol}",
        ttl,
        json.dumps(data)
    )
```

#### B. MongoDB Indexing:
```python
# สร้าง indexes สำหรับการค้นหาที่เร็วขึ้น
db.stocks.create_index([("symbol", 1), ("fetchedAt", -1)])
db.stocks.create_index([("overallSentiment.score", -1)])
db.stocks.create_index([("mentionCount", -1)])
db.news.create_index([("symbol", 1), ("publishedAt", -1)])
```

#### C. Incremental Updates:
```python
def should_refetch_stock(symbol: str) -> bool:
    """ตรวจสอบว่าควรดึงข้อมูลใหม่หรือไม่"""
    last_fetch = db.stocks.find_one(
        {"symbol": symbol},
        {"fetchedAt": 1}
    )
    if not last_fetch:
        return True
    
    last_time = datetime.fromisoformat(last_fetch['fetchedAt'])
    time_diff = datetime.utcnow() - last_time
    
    # ดึงใหม่ทุก 15 นาที
    return time_diff > timedelta(minutes=15)
```

---

### 3. **Background Workers & Task Queue** 🔄

#### A. ใช้ Celery สำหรับ Background Tasks:
```python
# celery_config.py
from celery import Celery

celery_app = Celery(
    'stock_analyzer',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/0'
)

@celery_app.task
def analyze_stock_batch(symbols: List[str]):
    """วิเคราะห์หุ้นเป็น batch ใน background"""
    aggregator = DataAggregator()
    results = []
    for symbol in symbols:
        data = aggregator.aggregate_stock_data(symbol)
        results.append(data)
    return results

# เรียกใช้
analyze_stock_batch.delay(['AAPL', 'TSLA', 'MSFT'])
```

#### B. Scheduled Tasks (Cron Jobs):
```python
from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    'update-all-stocks': {
        'task': 'analyze_stock_batch',
        'schedule': crontab(minute='*/15'),  # ทุก 15 นาที
        'args': (all_stock_symbols[:100],)  # 100 หุ้นต่อรอบ
    },
}
```

---

### 4. **API Rate Limiting & Optimization** 🎚️

#### A. Request Queuing:
```python
from queue import Queue
import threading

class APIRequestQueue:
    def __init__(self, max_workers: int = 10, rate_limit: int = 100):
        self.queue = Queue()
        self.rate_limit = rate_limit  # requests per minute
        self.last_request_time = {}
        self.lock = threading.Lock()
    
    def add_request(self, symbol: str, func, *args, **kwargs):
        """เพิ่ม request เข้า queue"""
        self.queue.put((symbol, func, args, kwargs))
    
    def process_queue(self):
        """ประมวลผล queue ด้วย rate limiting"""
        while not self.queue.empty():
            symbol, func, args, kwargs = self.queue.get()
            
            # Rate limiting
            with self.lock:
                now = time.time()
                if symbol in self.last_request_time:
                    time_since_last = now - self.last_request_time[symbol]
                    if time_since_last < (60 / self.rate_limit):
                        time.sleep((60 / self.rate_limit) - time_since_last)
                self.last_request_time[symbol] = time.time()
            
            # Execute request
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                print(f"Error processing {symbol}: {e}")
```

#### B. Exponential Backoff & Retry:
```python
import time
from functools import wraps

def retry_with_backoff(max_retries: int = 3, base_delay: float = 1.0):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    delay = base_delay * (2 ** attempt)
                    time.sleep(delay)
            return None
        return wrapper
    return decorator
```

---

### 5. **Data Pipeline Architecture** 🏗️

#### A. ETL Pipeline:
```
┌─────────────┐
│  Data Fetch │  →  Fetch from APIs (Yahoo, Reddit, News, etc.)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Transform │  →  Clean, normalize, extract sentiment
└──────┬──────┘
       │
       ▼
┌─────────────┐
│    Load     │  →  Store in MongoDB + Redis Cache
└─────────────┘
```

#### B. Message Queue (RabbitMQ/Redis):
```python
import pika

# Producer (ส่งงาน)
connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
channel = connection.channel()
channel.queue_declare(queue='stock_analysis')

for symbol in stock_symbols:
    channel.basic_publish(
        exchange='',
        routing_key='stock_analysis',
        body=json.dumps({'symbol': symbol})
    )

# Consumer (ประมวลผล)
def process_stock(ch, method, properties, body):
    data = json.loads(body)
    symbol = data['symbol']
    # Analyze stock
    result = analyze_stock(symbol)
    ch.basic_ack(delivery_tag=method.delivery_tag)

channel.basic_consume(
    queue='stock_analysis',
    on_message_callback=process_stock
)
channel.start_consuming()
```

---

## 📈 สถาปัตยกรรมที่แนะนำ

### **Multi-Tier Architecture:**

```
┌─────────────────────────────────────────┐
│         Frontend (React/Vue)            │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│      API Gateway (Flask/FastAPI)        │
│  - Rate Limiting                        │
│  - Authentication                       │
└──────────────┬──────────────────────────┘
               │
       ┌───────┴───────┐
       │               │
┌──────▼──────┐  ┌─────▼──────┐
│   Workers   │  │   Queue    │
│  (Celery)   │  │  (Redis)   │
└──────┬──────┘  └─────┬───────┘
       │               │
┌──────▼───────────────▼──────┐
│      Data Aggregator        │
│  - Yahoo Finance            │
│  - Reddit API               │
│  - News API                 │
│  - Twitter API              │
└──────┬──────────────────────┘
       │
┌──────▼──────────────────────┐
│   Sentiment Analyzer        │
│  - Batch Processing         │
│  - ML Models                │
└──────┬──────────────────────┘
       │
┌──────▼──────────────────────┐
│      Storage Layer          │
│  - MongoDB (Main DB)        │
│  - Redis (Cache)            │
│  - PostgreSQL (Analytics)   │
└─────────────────────────────┘
```

---

## ⚡ การปรับปรุงที่แนะนำทันที

### 1. **เพิ่ม AsyncIO Support:**
```python
# สร้าง async wrapper สำหรับ yfinance
async def fetch_yahoo_async(symbols: List[str]):
    tasks = [asyncio.to_thread(yf.Ticker(symbol).info) for symbol in symbols]
    return await asyncio.gather(*tasks)
```

### 2. **เพิ่ม Redis Caching:**
- Cache stock info (TTL: 15 นาที)
- Cache news articles (TTL: 1 ชั่วโมง)
- Cache sentiment scores (TTL: 30 นาที)

### 3. **Batch Processing:**
- ประมวลผล 100 หุ้นต่อ batch
- ใช้ parallel processing ภายใน batch
- ใช้ queue สำหรับ batch ถัดไป

### 4. **Database Optimization:**
- สร้าง indexes สำหรับการค้นหา
- ใช้ aggregation pipeline สำหรับ analytics
- Partition data by date

---

## 📊 ประมาณการประสิทธิภาพ

### **ปัจจุบัน (Sequential):**
- 4000 หุ้น × 5 วินาที/หุ้น = **5.5 ชั่วโมง**

### **หลังปรับปรุง (Parallel + Caching):**
- 4000 หุ้น ÷ 50 batch × 30 วินาที/batch = **40 นาที**
- **ลดเวลาได้ 88%** 🎉

---

## 🔧 Tools ที่แนะนำ

1. **Celery** - Background task processing
2. **Redis** - Caching & message queue
3. **RabbitMQ** - Advanced message queue
4. **Apache Kafka** - Real-time data streaming
5. **PostgreSQL** - Time-series analytics
6. **Elasticsearch** - Full-text search

---

## 📝 Next Steps

1. ✅ เพิ่ม Redis caching
2. ✅ เปลี่ยนเป็น AsyncIO
3. ✅ เพิ่ม Celery workers
4. ✅ Optimize database indexes
5. ✅ Implement batch processing
6. ✅ Add monitoring & logging


