"""
Batch Data Processor - สำหรับดึงข้อมูลหุ้นทั้งหมดแบบ batch
แทนการดึง real-time ทุกครั้งที่ request
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from database.db_config import db
from processors.data_aggregator import DataAggregator
from fetchers.yahoo_finance_fetcher import YahooFinanceFetcher
from processors.sentiment_analyzer import SentimentAnalyzer
from processors.async_stock_fetcher import AsyncStockFetcher
from processors.enhanced_sentiment_aggregator import EnhancedSentimentAggregator
# ไม่ใช้ Redis cache - ลด memory usage
# from cache.redis_cache import cache
cache = None
import asyncio
import logging
import warnings

# Suppress aiohttp warnings (Unclosed client session)
warnings.filterwarnings('ignore', category=ResourceWarning)
logging.getLogger('aiohttp').setLevel(logging.ERROR)
logging.getLogger('aiohttp.client').setLevel(logging.ERROR)
logging.getLogger('aiohttp.connector').setLevel(logging.ERROR)
import hashlib
import time

class BatchDataProcessor:
    """
    ประมวลผลข้อมูลหุ้นแบบ batch
    - ดึงข้อมูลทั้งหมดมาครั้งเดียว
    - เก็บใน database
    - อัปเดตทุก 1-2 ชั่วโมง
    - หลีกเลี่ยงข่าวซ้ำ (deduplication)
    """
    
    def __init__(self, days_back: int = 7, update_interval_hours: int = 2):
        """
        Args:
            days_back: จำนวนวันที่ดึงข่าวย้อนหลัง (default: 7 วัน)
            update_interval_hours: อัปเดตข้อมูลทุกกี่ชั่วโมง (default: 2 ชั่วโมง)
        """
        self.days_back = days_back
        self.update_interval_hours = update_interval_hours
        self.skip_reddit = False  # ข้าม Reddit ทั้งหมด
        self.reddit_from_db_only = False  # ใช้ Reddit จาก database เท่านั้น
        self.reddit_limit = 500  # จำนวน Reddit posts ต่อหุ้น
        self.reddit_priority_only = False  # ดึง Reddit เฉพาะหุ้น popular
        self.reddit_incremental = False  # ดึง Reddit เฉพาะหุ้นที่ไม่มี/เก่า
        self.data_aggregator = DataAggregator()
        self.yahoo_fetcher = YahooFinanceFetcher()
        self.sentiment_analyzer = SentimentAnalyzer()
        self.enhanced_sentiment_aggregator = EnhancedSentimentAggregator()
        # เพิ่มความเร็ว: max_concurrent=2000, rate_limit=2000 (เร็วกว่าเดิม 4 เท่า)
        # ไม่ใช้ Redis cache - ดึงข้อมูลโดยตรง
        self.async_fetcher = AsyncStockFetcher(max_concurrent=2000, rate_limit=2000)
        
        # เก็บ hash ของข่าวที่ดึงมาแล้ว (เพื่อหลีกเลี่ยงข่าวซ้ำ)
        self.processed_news_hashes: Set[str] = set()
    
    def _generate_news_hash(self, article: Dict) -> str:
        """
        สร้าง hash สำหรับข่าวเพื่อตรวจสอบว่าซ้ำหรือไม่
        
        Args:
            article: ข่าว article dict
        
        Returns:
            MD5 hash string
        """
        # ใช้ title + url + publishedAt เป็น unique identifier
        unique_string = f"{article.get('title', '')}{article.get('url', '')}{article.get('publishedAt', '')}"
        return hashlib.md5(unique_string.encode()).hexdigest()
    
    def _is_duplicate_news(self, article: Dict) -> bool:
        """
        ตรวจสอบว่าข่าวซ้ำหรือไม่
        
        Args:
            article: ข่าว article dict
        
        Returns:
            True ถ้าซ้ำ, False ถ้าไม่ซ้ำ
        """
        news_hash = self._generate_news_hash(article)
        
        # ตรวจสอบใน memory cache
        if news_hash in self.processed_news_hashes:
            return True
        
        # ตรวจสอบใน database (ใช้ collection post_yahoo)
        from utils.post_normalizer import get_collection_name
        collection_name = get_collection_name('yahoo')
        if db is not None and hasattr(db, collection_name) and getattr(db, collection_name) is not None:
            post_collection = getattr(db, collection_name)
            existing = post_collection.find_one({"newsHash": news_hash})
            if existing:
                return True
        
        # เพิ่มเข้า memory cache
        self.processed_news_hashes.add(news_hash)
        return False
    
    def _clean_old_data(self, symbol: str, days_to_keep: int = None, skip_reddit: bool = False):
        """
        ลบข้อมูลเก่าที่เกิน days_back ออกจาก database
        
        Args:
            symbol: Stock symbol
            days_to_keep: จำนวนวันที่เก็บข้อมูล (default: self.days_back)
                          ถ้าเป็น None จะไม่ลบข้อมูลเก่า (เก็บไว้ทั้งหมด)
            skip_reddit: ถ้า True จะไม่ลบ Reddit posts (Reddit bulk processor จัดการเอง)
        """
        if db is None:
            return
        
        days_to_keep = days_to_keep or self.days_back
        
        # ถ้า days_to_keep เป็น None หรือ <= 0 จะไม่ลบข้อมูลเก่า (เก็บไว้ทั้งหมด)
        if days_to_keep is None or (isinstance(days_to_keep, (int, float)) and days_to_keep <= 0):
            return  # ไม่ลบข้อมูลเก่า - เก็บไว้ทั้งหมด
        
        # ตรวจสอบว่า days_to_keep เป็นตัวเลข
        if not isinstance(days_to_keep, (int, float)):
            return
        
        days_to_keep = int(days_to_keep)
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        from utils.post_normalizer import get_collection_name
        
        try:
            # ลบข่าวเก่า (ใช้ collection post_yahoo)
            collection_name = get_collection_name('yahoo')
            if db is not None and hasattr(db, collection_name) and getattr(db, collection_name) is not None:
                post_collection = getattr(db, collection_name)
                result = post_collection.delete_many({
                    "symbol": symbol.upper(),
                    "created_utc": {"$lt": cutoff_date.isoformat()}
                })
                # ไม่แสดง print เพื่อไม่ให้ทับ progress bar
                # print(f"  🗑️ Cleaned {result.deleted_count} old news articles for {symbol}")
            
            # ✅ ไม่ลบ Reddit posts เก่า - Reddit bulk processor จัดการเอง
            # Reddit posts ถูกบันทึกโดย Reddit bulk scheduler (ทุก 45 วินาที)
            # และควรเก็บไว้เพื่อการวิเคราะห์ย้อนหลัง
            # ถ้าต้องการลบ posts เก่า ให้ทำแยกต่างหาก (ไม่ใช่ทุกครั้งที่อัปเดตหุ้น)
            if not skip_reddit:
                collection_name = get_collection_name('reddit')
                if db is not None and hasattr(db, collection_name) and getattr(db, collection_name) is not None:
                    post_collection = getattr(db, collection_name)
                    result = post_collection.delete_many({
                        "keyword": symbol.upper(),
                        "created_utc": {"$lt": cutoff_date.isoformat()}
                    })
                    # ไม่แสดง print เพื่อไม่ให้ทับ progress bar
                    # print(f"  🗑️ Cleaned {result.deleted_count} old Reddit posts for {symbol}")
        except Exception as e:
            # ไม่แสดง print เพื่อไม่ให้ทับ progress bar
            # print(f"  ⚠️ Error cleaning old data for {symbol}: {e}")
            pass
    
    def _should_update_stock(self, symbol: str) -> bool:
        """
        ตรวจสอบว่าควรอัปเดตข้อมูลหุ้นนี้หรือไม่
        
        Args:
            symbol: Stock symbol
        
        Returns:
            True ถ้าควรอัปเดต, False ถ้ายังไม่ถึงเวลา
        """
        if db is None or not hasattr(db, 'stocks') or db.stocks is None:
            return True
        
        try:
            # หาข้อมูลล่าสุดของหุ้นนี้
            latest = db.stocks.find_one(
                {"symbol": symbol.upper()},
                sort=[("fetchedAt", -1)]
            )
            
            if not latest:
                return True  # ยังไม่มีข้อมูล ต้องดึง
            
            # ตรวจสอบว่าเกิน update_interval หรือยัง
            fetched_at_str = latest.get('fetchedAt', '')
            if isinstance(fetched_at_str, str):
                fetched_at = datetime.fromisoformat(fetched_at_str.replace('Z', '+00:00'))
            else:
                fetched_at = fetched_at_str
            
            time_diff = datetime.utcnow() - fetched_at
            
            should_update = time_diff > timedelta(hours=self.update_interval_hours)
            return should_update
        except Exception as e:
            # ไม่แสดง print เพื่อไม่ให้ทับ progress bar
            # print(f"  ⚠️ Error checking update status for {symbol}: {e}")
            pass
            import traceback
            traceback.print_exc()
            return True  # ถ้า error ให้ดึงใหม่
    
    def _deduplicate_news(self, articles: List[Dict]) -> List[Dict]:
        """
        กรองข่าวซ้ำออก
        
        Args:
            articles: List of news articles
        
        Returns:
            List of unique news articles
        """
        unique_articles = []
        seen_hashes = set()
        
        for article in articles:
            news_hash = self._generate_news_hash(article)
            
            if news_hash not in seen_hashes and not self._is_duplicate_news(article):
                article['newsHash'] = news_hash  # เพิ่ม hash เข้าไปใน article
                unique_articles.append(article)
                seen_hashes.add(news_hash)
        
        return unique_articles
    
    async def process_single_stock_async(self, symbol: str) -> Optional[Dict]:
        """
        ประมวลผลข้อมูลหุ้นเดียวแบบ async
        
        Args:
            symbol: Stock symbol
        
        Returns:
            Aggregated stock data หรือ None
        """
        symbol_upper = symbol.upper()
        
        # ตรวจสอบว่าควรอัปเดตหรือไม่
        # แต่ยังคงดึงข่าวใหม่เสมอ (ไม่ skip การดึงข่าว)
        should_update_stock = self._should_update_stock(symbol_upper)
        if not should_update_stock:
            # ดึง stock info จาก database แทน (ไม่ต้องดึงใหม่)
            if db is not None and hasattr(db, 'stocks') and db.stocks is not None:
                cached_stock = db.stocks.find_one(
                    {"symbol": symbol_upper},
                    sort=[("fetchedAt", -1)]
                )
                if cached_stock:
                    stock_info = cached_stock.get('stockInfo', {})
                else:
                    stock_info = None
            else:
                stock_info = None
        else:
            stock_info = None  # จะดึงใหม่
        
        try:
            news_count_before = 0
            if db is not None and hasattr(db, 'news') and db.news is not None:
                news_count_before = db.news.count_documents({"symbol": symbol_upper})
            # 1. Clean old data ก่อนดึงข้อมูลใหม่
            # ✅ ไม่ลบ Reddit posts - Reddit bulk processor จัดการเอง
            # Reddit posts ถูกบันทึกโดย Reddit bulk scheduler (ทุก 45 วินาที)
            # และควรเก็บไว้เพื่อการวิเคราะห์ย้อนหลัง
            # ลบเฉพาะ news articles เก่า (ไม่ลบ Reddit)
            self._clean_old_data(symbol_upper, skip_reddit=True)
            
            # 2-4. ดึงข้อมูลแบบ PARALLEL (พร้อมกัน) - เร็วกว่าเดิม 3 เท่า
            # ดึง stock_info, news, reddit พร้อมกัน แทนที่จะรอทีละอัน
            async def fetch_stock_info_task():
                if not stock_info:
                    try:
                        return await self.async_fetcher.fetch_stock_info_async(symbol_upper)
                    except Exception:
                        return None
                return stock_info
            
            async def fetch_news_task():
                try:
                    # ดึงข่าวให้ได้มากที่สุด (500 ข่าวต่อหุ้น) - ไม่จำกัดวัน
                    news_articles_raw = await self.async_fetcher.fetch_stock_news_async(symbol_upper, max_results=500)
                    if news_articles_raw:
                        # กรองข่าวซ้ำ - ตรวจสอบกับ database (จะไม่บันทึกข่าวซ้ำ)
                        return self._deduplicate_news(news_articles_raw)
                    return []
                except Exception:
                    return []
            
            async def fetch_reddit_task():
                try:
                    # ถ้า skip Reddit → return empty list
                    if self.skip_reddit:
                        return []
                    
                    # ✅ ใช้ Reddit จาก database เท่านั้น (Reddit bulk processor จะดึงมาให้)
                    # ไม่ดึง Reddit per-stock อีกต่อไป (ช้าเกินไป)
                    from utils.post_normalizer import get_collection_name
                    collection_name = get_collection_name('reddit')
                    days_back_for_reddit = self.days_back if self.days_back is not None else 7
                    cutoff_time = datetime.utcnow() - timedelta(days=days_back_for_reddit)
                    
                    # ดึง Reddit จาก database (ที่ Reddit bulk processor ดึงมาแล้ว)
                    if db is not None and hasattr(db, collection_name) and getattr(db, collection_name) is not None:
                        post_collection = getattr(db, collection_name)
                        
                        # ดึง posts ที่มี symbol นี้ใน symbols array
                        # รองรับทั้ง keyword (เดิม) และ symbols (ใหม่)
                        query = {
                            "$or": [
                                {"keyword": symbol_upper},
                                {"symbols": symbol_upper}
                            ],
                            "created_utc": {"$gte": cutoff_time.isoformat()}
                        }
                        
                        reddit_posts_cursor = post_collection.find(query).sort("created_utc", -1).limit(self.reddit_limit)
                        reddit_posts = list(reddit_posts_cursor)
                        
                        if reddit_posts:
                            return reddit_posts
                    
                    # ถ้าไม่มีใน database → return empty (Reddit bulk processor จะดึงมาให้)
                    return []
                except Exception:
                    return []
            
            # ดึงข้อมูลแบบ parallel (พร้อมกัน)
            stock_info_result, news_articles, reddit_posts = await asyncio.gather(
                fetch_stock_info_task(),
                fetch_news_task(),
                fetch_reddit_task(),
                return_exceptions=True
            )
            
            # จัดการผลลัพธ์
            if isinstance(stock_info_result, Exception) or not stock_info_result:
                stock_info = {
                    'symbol': symbol_upper,
                    'name': symbol_upper,
                    'currentPrice': 0,
                    'fetchedAt': datetime.utcnow().isoformat()
                }
            else:
                stock_info = stock_info_result
            
            if isinstance(news_articles, Exception):
                news_articles = []
            
            if isinstance(reddit_posts, Exception):
                reddit_posts = []
            
            # 5. วิเคราะห์ sentiment จากข่าว (ใช้ time-weighted)
            sentiment = None
            if news_articles:
                # สร้าง items_with_dates สำหรับ time-weighted analysis
                items_with_dates = []
                for a in news_articles:
                    title = a.get('title', '') or ''
                    selftext = a.get('selftext', '') or ''
                    full_content = a.get('full_content', '') or ''
                    # ใช้ selftext ก่อน ถ้าไม่มีให้ใช้ full_content (จำกัด 500 ตัวอักษร)
                    content = selftext or (full_content[:500] if full_content else '')
                    text = f"{title} {content}".strip()
                    if text:  # เฉพาะข่าวที่มีเนื้อหา
                        items_with_dates.append({
                            'text': text,
                            'publishedAt': a.get('publishedAt') or a.get('providerPublishTime') or a.get('publish_date') or a.get('created_utc')
                        })
                
                if items_with_dates:
                    # ใช้ time-weighted analysis เพื่อให้ข่าวใหม่มีน้ำหนักมากกว่าข่าวเก่า
                    sentiment = self.sentiment_analyzer.analyze_batch(
                        texts=[item['text'] for item in items_with_dates],
                        use_time_weighting=True,
                        items_with_dates=items_with_dates
                    )
                    # ไม่แสดง print เพื่อไม่ให้ทับ progress bar
                    # ไม่ใช้ Redis cache - ลด memory usage
            
            # 6. ประมวลผล Reddit posts ที่ดึงมาแล้ว (ไม่ต้องดึงใหม่)
            aggregated_data = {
                'redditData': {},
                'twitterData': {},
                'youtubeData': {},
                'trendsData': {}
            }
            
            # ประมวลผล Reddit posts
            if reddit_posts:
                try:
                    # วิเคราะห์ sentiment (ใช้ time-weighted)
                    items_with_dates = []
                    for p in reddit_posts:
                        text = f"{p.get('title', '')} {p.get('selftext', '')}"
                        if text.strip():
                            items_with_dates.append({
                                'text': text,
                                'publishedAt': p.get('publishedAt') or p.get('created_utc') or p.get('created_at')
                            })
                    
                    if items_with_dates:
                        # ใช้ time-weighted analysis เพื่อให้ post ใหม่มีน้ำหนักมากกว่า
                        reddit_sentiment = self.sentiment_analyzer.analyze_batch(
                            texts=[item['text'] for item in items_with_dates],
                            use_time_weighting=True,
                            items_with_dates=items_with_dates
                        )
                        aggregated_data['redditData'] = {
                            'posts': reddit_posts[:20],  # เก็บแค่ 20 posts
                            'sentiment': reddit_sentiment,
                            'mentionCount': len(reddit_posts)
                        }
                except Exception:
                    pass
            
            # 7. ใช้ Enhanced Sentiment Aggregator (พร้อม market confirmation)
            # ดึง previous sentiment จาก database
            previous_sentiment = None
            if db is not None and hasattr(db, 'stocks') and db.stocks is not None:
                previous_stock = db.stocks.find_one({"symbol": symbol_upper})
                if previous_stock and previous_stock.get('overallSentiment'):
                    previous_sentiment = previous_stock.get('overallSentiment')
            
            # เตรียม news items และ reddit items สำหรับ enhanced aggregator
            news_items = []
            for article in news_articles:
                # วิเคราะห์ sentiment ถ้ายังไม่มี
                if 'sentiment' not in article:
                    title = article.get('title', '') or ''
                    selftext = article.get('selftext', '') or ''
                    text = f"{title} {selftext}".strip()
                    if text:
                        article['sentiment'] = self.sentiment_analyzer.analyze(text)
                article['source'] = article.get('source', 'yahoo_finance')
                news_items.append(article)
            
            reddit_items = []
            if reddit_posts:
                for post in reddit_posts:
                    # ใช้ sentiment ที่มีอยู่แล้ว (วิเคราะห์ครั้งเดียวต่อ post)
                    if 'sentiment' not in post:
                        title = post.get('title', '') or ''
                        selftext = post.get('selftext', '') or ''
                        text = f"{title} {selftext}".strip()
                        if text:
                            post['sentiment'] = self.sentiment_analyzer.analyze(text)
                    post['source'] = 'reddit'
                    reddit_items.append(post)
            
            # คำนวณ enhanced sentiment
            enhanced_sentiment = self.enhanced_sentiment_aggregator.aggregate_sentiment(
                news_items=news_items,
                reddit_items=reddit_items,
                stock_info=stock_info,
                previous_sentiment=previous_sentiment
            )
            
            # 8. รวมข้อมูลทั้งหมด
            result = {
                'symbol': symbol_upper,
                'fetchedAt': datetime.utcnow().isoformat(),
                'stockInfo': stock_info,
                'newsData': {
                    'articles': news_articles[:50],  # เก็บแค่ 50 ข่าวล่าสุด
                    'sentiment': sentiment,  # เก็บ sentiment เดิมไว้ด้วย
                    'articleCount': len(news_articles),
                    'source': 'yahoo_finance'
                },
                'redditData': aggregated_data.get('redditData', {}),
                'twitterData': aggregated_data.get('twitterData', {}),
                'youtubeData': aggregated_data.get('youtubeData', {}),
                'trendsData': aggregated_data.get('trendsData', {}),
                'overallSentiment': enhanced_sentiment  # ใช้ enhanced sentiment
            }
            
            # 8. บันทึกลง database
            if db is not None and hasattr(db, 'stocks') and db.stocks is not None:
                db.stocks.update_one(
                    {"symbol": symbol_upper},
                    {"$set": result},
                    upsert=True
                )
                
                # บันทึกข่าวแยกต่างหาก (บันทึกทุกข่าวที่ดึงมา) - ใช้ collection post_yahoo
                from utils.post_normalizer import normalize_post, get_collection_name
                
                collection_name = get_collection_name('yahoo')
                if db is not None and hasattr(db, collection_name) and getattr(db, collection_name) is not None and news_articles:
                    post_collection = getattr(db, collection_name)
                    saved_count = 0
                    new_count = 0
                    for article in news_articles:
                        # Normalize post structure
                        normalized_article = normalize_post(article, 'yahoo', symbol_upper)
                        normalized_article['symbol'] = symbol_upper
                        normalized_article['fetched_at'] = datetime.utcnow().isoformat()
                        
                        try:
                            # ตรวจสอบว่ามีอยู่แล้วหรือไม่ (ใช้ newsHash หรือ id)
                            news_hash = normalized_article.get('newsHash')
                            post_id = normalized_article.get('id')
                            
                            existing = None
                            if news_hash:
                                existing = post_collection.find_one({"newsHash": news_hash})
                            if not existing and post_id:
                                existing = post_collection.find_one({"id": post_id})
                            
                            is_new = existing is None
                            
                            # ใช้ id หรือ newsHash เป็น unique key
                            if news_hash:
                                post_collection.update_one(
                                    {"newsHash": news_hash},
                                    {"$set": normalized_article},
                                    upsert=True
                                )
                            elif post_id:
                                post_collection.update_one(
                                    {"id": post_id},
                                    {"$set": normalized_article},
                                    upsert=True
                                )
                            else:
                                # ถ้าไม่มี id หรือ hash ให้ insert ใหม่
                                post_collection.insert_one(normalized_article)
                            
                            saved_count += 1
                            if is_new:
                                new_count += 1
                        except Exception:
                            pass
                            continue
            
            return result
            
        except Exception as e:
            # ไม่แสดง error เพื่อให้ progress bar ดูสะอาด
            return None
    
    async def process_all_stocks_async(self, symbols: List[str], batch_size: int = 50) -> Dict[str, Dict]:
        """
        ประมวลผลหุ้นทั้งหมดแบบ batch
        
        Args:
            symbols: List of stock symbols
            batch_size: จำนวนหุ้นต่อ batch
        
        Returns:
            Dictionary {symbol: stock_data}
        """
        from utils.post_normalizer import get_collection_name
        from utils.progress_bar import draw_progress_bar, reset_progress
        
        # รีเซ็ต progress bar สำหรับงานใหม่
        reset_progress()
        
        # นับจำนวนข่าวทั้งหมดใน database ก่อนเริ่ม (ใช้ collection post_yahoo)
        total_news_before = 0
        collection_name = get_collection_name('yahoo')
        if db is not None and hasattr(db, collection_name) and getattr(db, collection_name) is not None:
            post_collection = getattr(db, collection_name)
            total_news_before = post_collection.count_documents({})
        
        all_results = {}
        total_stocks = len(symbols)
        start_time = time.time()
        
        # ✅ แสดง progress bar ทันทีเมื่อเริ่ม (0%) - แสดงทันทีเมื่อกดรัน
        # ใช้ print() เพื่อให้แน่ใจว่าแสดงทันที (โดยเฉพาะบน Windows)
        print()  # ขึ้นบรรทัดใหม่ก่อนแสดง progress bar
        import sys
        sys.stdout.flush()  # Force flush
        draw_progress_bar(0, total_stocks, bar_length=50, prefix="กำลังโหลดข่าว", show_total=True)
        sys.stdout.flush()  # Force flush อีกครั้ง
        
        for i in range(0, len(symbols), batch_size):
            batch = symbols[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(symbols) + batch_size - 1) // batch_size
            
            # ประมวลผล batch แบบ parallel
            tasks = [self.process_single_stock_async(symbol) for symbol in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # รวมผลลัพธ์
            for symbol, result in zip(batch, batch_results):
                if not isinstance(result, Exception) and result:
                    all_results[symbol.upper()] = result
            
            # แสดง progress bar หลัง batch เสร็จ (แสดงจำนวนหุ้นที่ดึงได้จริงๆ)
            processed = len(all_results)
            draw_progress_bar(processed, total_stocks, bar_length=50, prefix="กำลังโหลดข่าว", show_total=True)
            # Force flush เพื่อให้แสดงทันที
            import sys
            sys.stdout.flush()
            
            # พักระหว่าง batch (ลดเป็น 0.1 วินาที เพื่อให้เร็วขึ้นมาก)
            if i + batch_size < len(symbols):
                await asyncio.sleep(0.1)
        
        elapsed = time.time() - start_time
        
        # ✅ นับจำนวนข่าวที่บันทึกได้
        total_news_after = 0
        collection_name = get_collection_name('yahoo')
        if db is not None and hasattr(db, collection_name) and getattr(db, collection_name) is not None:
            post_collection = getattr(db, collection_name)
            total_news_after = post_collection.count_documents({})
        
        new_news = total_news_after - total_news_before
        
        # ✅ แสดงสรุปข้อมูลที่ดึงมา
        print(f"\n📊 สรุปข้อมูลที่ดึงมา:")
        print(f"   📰 Yahoo News: {new_news:,} ข่าวใหม่ (รวมทั้งหมด: {total_news_after:,} ข่าว)")
        print(f"   📈 Stocks: {len(all_results):,} หุ้น")
        print(f"   ⏱️  เวลาที่ใช้: {elapsed/60:.1f} นาที")
        
        # Cleanup: ปิด aiohttp sessions
        try:
            # ปิด Yahoo Finance async fetcher session
            if hasattr(self.async_fetcher, '_yahoo_async_fetcher'):
                await self.async_fetcher._yahoo_async_fetcher.close()
            
            # Force garbage collection
            import gc
            gc.collect()
        except:
            pass
        
        return all_results
    
    def get_stock_from_database(self, symbol: str) -> Optional[Dict]:
        """
        ดึงข้อมูลหุ้นจาก database (ไม่ต้องดึง API)
        
        Args:
            symbol: Stock symbol
        
        Returns:
            Stock data จาก database หรือ None
        """
        if not db or not db.stocks:
            return None
        
        try:
            result = db.stocks.find_one(
                {"symbol": symbol.upper()},
                sort=[("fetchedAt", -1)]
            )
            return result
        except Exception as e:
            # ไม่แสดง print เพื่อไม่ให้ทับ progress bar
            # print(f"⚠️ Error getting stock from database: {e}")
            pass
            return None
    
    def get_all_stocks_from_database(self, limit: int = None) -> List[Dict]:
        """
        ดึงข้อมูลหุ้นทั้งหมดจาก database
        
        Args:
            limit: จำกัดจำนวน (None = ทั้งหมด)
        
        Returns:
            List of stock data
        """
        if not db or not db.stocks:
            return []
        
        try:
            query = db.stocks.find().sort("fetchedAt", -1)
            if limit:
                query = query.limit(limit)
            return list(query)
        except Exception as e:
            # ไม่แสดง print เพื่อไม่ให้ทับ progress bar
            # print(f"⚠️ Error getting all stocks from database: {e}")
            pass
            return []


# Global instance
batch_processor = BatchDataProcessor(days_back=7, update_interval_hours=2)

