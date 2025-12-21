"""
Async Stock Fetcher - สำหรับดึงข้อมูลหุ้นแบบ async
รองรับการดึงข้อมูลจำนวนมากพร้อมกัน
"""
import asyncio
import aiohttp
from typing import List, Dict, Optional
from datetime import datetime
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor
import time
import hashlib
import warnings
import logging

# Suppress yfinance warnings และ logging
warnings.filterwarnings('ignore')
warnings.filterwarnings('ignore', category=ResourceWarning)  # Suppress unclosed session warnings
logging.getLogger('yfinance').setLevel(logging.ERROR)
logging.getLogger('aiohttp').setLevel(logging.ERROR)  # Suppress aiohttp warnings
logging.getLogger('aiohttp.client').setLevel(logging.ERROR)
logging.getLogger('aiohttp.connector').setLevel(logging.ERROR)

class AsyncStockFetcher:
    """
    Async fetcher สำหรับดึงข้อมูลหุ้นจำนวนมากพร้อมกัน
    """
    def __init__(self, max_concurrent: int = 50, rate_limit: int = 100):
        """
        Args:
            max_concurrent: จำนวนหุ้นที่ดึงพร้อมกัน
            rate_limit: จำนวน requests ต่อนาที
        """
        self.max_concurrent = max_concurrent
        self.rate_limit = rate_limit
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.request_times = []
        self.lock = asyncio.Lock()
    
    async def _rate_limit_wait(self):
        """Rate limiting เพื่อหลีกเลี่ยง API throttling"""
        async with self.lock:
            now = time.time()
            # ลบ request times ที่เก่ากว่า 1 นาที
            self.request_times = [t for t in self.request_times if now - t < 60]
            
            if len(self.request_times) >= self.rate_limit:
                # รอจนกว่าจะมี slot ว่าง
                oldest_time = min(self.request_times)
                wait_time = 60 - (now - oldest_time) + 0.1
                if wait_time > 0:
                    await asyncio.sleep(wait_time)
            
            self.request_times.append(time.time())
    
    async def fetch_stock_info_async(self, symbol: str) -> Optional[Dict]:
        """
        ดึงข้อมูลหุ้นแบบ async - ใช้ Yahoo Finance API โดยตรง (async จริงๆ)
        """
        async with self.semaphore:
            await self._rate_limit_wait()
            
            try:
                # ใช้ async Yahoo Finance fetcher (เร็วกว่า yfinance)
                from fetchers.yahoo_finance_async import YahooFinanceAsyncFetcher
                
                # สร้าง fetcher instance (ใช้ shared session)
                if not hasattr(self, '_yahoo_async_fetcher'):
                    self._yahoo_async_fetcher = YahooFinanceAsyncFetcher()
                
                # ดึงข้อมูลแบบ async (เร็วกว่า yfinance ~3-5 เท่า)
                stock_info = await self._yahoo_async_fetcher.fetch_stock_info_async(symbol.upper())
                
                # ถ้า async fetcher ไม่ได้ผล ให้ fallback ไปใช้ yfinance
                if not stock_info:
                    # Fallback: ใช้ ThreadPoolExecutor สำหรับ yfinance (blocking I/O)
                    loop = asyncio.get_event_loop()
                    with ThreadPoolExecutor() as executor:
                        ticker = await loop.run_in_executor(executor, lambda: yf.Ticker(symbol.upper()))
                        info = await loop.run_in_executor(executor, lambda: ticker.info)
                        hist = await loop.run_in_executor(executor, lambda: ticker.history(period="1d"))
                        
                        if hist.empty and info:
                            current_price = info.get('regularMarketPrice')
                            previous_close = info.get('previousClose', current_price)
                            change = current_price - previous_close if current_price and previous_close else 0
                            change_percent = (change / previous_close * 100) if previous_close else 0
                            
                            return {
                                'symbol': symbol.upper(),
                                'name': info.get('longName', info.get('shortName', symbol)),
                                'currentPrice': float(current_price) if current_price else 0,
                                'previousClose': float(previous_close) if previous_close else 0,
                                'change': float(change),
                                'changePercent': float(change_percent),
                                'volume': int(info.get('volume', 0)),
                                'marketCap': info.get('marketCap', 0),
                                'sector': info.get('sector', 'Unknown'),
                                'industry': info.get('industry', 'Unknown'),
                                'fetchedAt': datetime.utcnow().isoformat()
                            }
                        
                        if not hist.empty:
                            current_price = hist['Close'].iloc[-1]
                            previous_close = info.get('previousClose', current_price) if info else current_price
                            change = current_price - previous_close
                            change_percent = (change / previous_close * 100) if previous_close else 0
                            
                            return {
                                'symbol': symbol.upper(),
                                'name': info.get('longName', info.get('shortName', symbol)) if info else symbol,
                                'currentPrice': float(current_price),
                                'previousClose': float(previous_close),
                                'change': float(change),
                                'changePercent': float(change_percent),
                                'volume': int(hist['Volume'].iloc[-1]) if 'Volume' in hist.columns else 0,
                                'marketCap': info.get('marketCap', 0) if info else 0,
                                'sector': info.get('sector', 'Unknown') if info else 'Unknown',
                                'industry': info.get('industry', 'Unknown') if info else 'Unknown',
                                'fetchedAt': datetime.utcnow().isoformat()
                            }
                        
                        return None
                
                return stock_info
            except Exception:
                # Suppress error messages - ไม่แสดง error เพื่อให้ progress bar ดูสะอาด
                return None
    
    async def fetch_stock_news_async(self, symbol: str, max_results: int = 100) -> List[Dict]:
        """
        ดึงข่าวหุ้นแบบ async จาก Yahoo Finance - ใช้ async API โดยตรง (เร็วกว่า yfinance)
        """
        async with self.semaphore:
            await self._rate_limit_wait()
            
            try:
                # ใช้ async Yahoo Finance fetcher (เร็วกว่า yfinance ~3-5 เท่า)
                from fetchers.yahoo_finance_async import YahooFinanceAsyncFetcher
                
                # สร้าง fetcher instance (ใช้ shared session)
                if not hasattr(self, '_yahoo_async_fetcher'):
                    self._yahoo_async_fetcher = YahooFinanceAsyncFetcher()
                
                # ดึงข่าวแบบ async (เร็วกว่า yfinance)
                news_list = await self._yahoo_async_fetcher.fetch_stock_news_async(symbol.upper(), max_results=max_results)
                
                # ถ้า async fetcher ไม่ได้ผล ให้ fallback ไปใช้ yfinance
                if not news_list:
                    loop = asyncio.get_event_loop()
                    with ThreadPoolExecutor() as executor:
                        # ดึง Ticker object
                        ticker = await loop.run_in_executor(executor, lambda: yf.Ticker(symbol.upper()))
                        
                        # ดึงข่าว - ดึงทั้งหมดที่ Yahoo Finance มี (ไม่จำกัด)
                        news_list_raw = await loop.run_in_executor(executor, lambda: ticker.news)
                    
                        if not news_list_raw:
                            # บางหุ้นอาจไม่มีข่าว (หุ้นเล็กๆ หรือหุ้นที่เพิ่ง IPO)
                            return []
                        
                        # แปลง yfinance news format เป็น format เดียวกัน
                        news_list = []
                        for item in news_list_raw[:max_results]:
                            news_list.append({
                                'title': item.get('title', ''),
                                'summary': item.get('summary', ''),
                                'link': item.get('link', ''),
                                'publisher': item.get('publisher', 'Yahoo Finance'),
                                'providerPublishTime': item.get('providerPublishTime', 0),
                                'type': item.get('type', 'STORY'),
                                'uuid': item.get('uuid', '')
                            })
                        
                        # ใช้ max_results เพื่อจำกัดจำนวนข่าวที่ดึงมา (ถ้า Yahoo Finance มีมากกว่า)
                        # แต่ถ้า news_list มีน้อยกว่า max_results ก็ใช้ทั้งหมดที่มี
                        articles = []
                        # Import news content fetcher (optional - ถ้ามี)
                        try:
                            from fetchers.news_content_fetcher import NewsContentFetcher
                            content_fetcher = NewsContentFetcher()
                            fetch_content = True
                        except ImportError:
                            content_fetcher = None
                            fetch_content = False
                        
                        for item in news_list[:max_results]:
                            try:
                                # แปลง publishedAt จาก timestamp เป็น ISO format
                                published_at = item.get('providerPublishTime', 0)
                                if published_at and isinstance(published_at, (int, float)):
                                    published_at = datetime.fromtimestamp(published_at).isoformat()
                                elif not published_at:
                                    published_at = datetime.utcnow().isoformat()
                                
                                # สร้าง newsHash สำหรับ deduplication
                                unique_string = f"{item.get('title', '')}{item.get('link', '')}{published_at}"
                                news_hash = hashlib.md5(unique_string.encode()).hexdigest()
                                
                                # สร้าง id จาก uuid หรือ hash
                                post_id = item.get('uuid', '') or news_hash[:12]
                                
                                # ดึงรายละเอียดเพิ่มเติมจาก URL (ดึงเสมอเพื่อให้ได้เนื้อหาเต็ม)
                                article_details = {}
                                fetched_title = ''
                                fetched_full_content = ''
                                
                                article_url = item.get('link', '')
                                if fetch_content and content_fetcher and article_url:
                                    try:
                                        details = content_fetcher.fetch_article_content(article_url)
                                        if details:
                                            fetched_title = details.get('title', '')
                                            fetched_full_content = details.get('full_content', '')
                                            article_details = {
                                                'full_content': fetched_full_content,  # เก็บเนื้อหาเต็มไว้
                                                'tags': details.get('tags', []),
                                                'author': details.get('author'),
                                                'publish_date': details.get('publish_date'),
                                                'word_count': details.get('word_count', 0)
                                            }
                                    except Exception as e_content:
                                        # ถ้าดึงรายละเอียดไม่ได้ ไม่เป็นไร ยังเก็บข้อมูลพื้นฐานได้
                                        pass
                                
                                # ใช้ title และ summary จาก Yahoo Finance API ก่อน
                                # ถ้าไม่มี ให้ใช้จาก full_content ที่ดึงจาก URL
                                yahoo_title = item.get('title', '') or ''
                                yahoo_summary = item.get('summary', '') or ''
                                
                                # ใช้ title จาก full_content ถ้า Yahoo Finance ไม่มี
                                final_title = yahoo_title or fetched_title or ''
                                
                                # ใช้ summary จาก Yahoo Finance ก่อน
                                # ถ้าไม่มี ให้ใช้ full_content (จำกัด 2000 ตัวอักษรแรกเพื่อให้มีเนื้อหาพอสำหรับ sentiment analysis)
                                if yahoo_summary:
                                    final_summary = yahoo_summary
                                elif fetched_full_content:
                                    # ใช้ full_content เป็น selftext (จำกัด 2000 ตัวอักษรแรก)
                                    final_summary = fetched_full_content[:2000]
                                else:
                                    final_summary = ''
                                
                                articles.append({
                                    # Standard fields (เหมือน Reddit structure)
                                    'id': post_id,  # ใช้ uuid หรือ hash แรก 12 ตัว
                                    'title': final_title,  # ใช้ title จาก Yahoo Finance หรือ full_content
                                    'selftext': final_summary,  # ใช้ summary จาก Yahoo Finance หรือ full_content
                                    'score': 0,  # Yahoo Finance ไม่มี score
                                    'num_comments': 0,  # Yahoo Finance ไม่มี comments
                                    'created_utc': published_at,  # ใช้ publishedAt
                                    'subreddit': item.get('publisher', 'Yahoo Finance'),  # ใช้ publisher เป็น subreddit
                                    'keyword': symbol.upper(),  # เพิ่ม keyword (symbol)
                                    'url': item.get('link', '') or '',
                                    'author': article_details.get('author') or item.get('publisher', 'Yahoo Finance'),
                                    'upvote_ratio': 0,  # Yahoo Finance ไม่มี upvote_ratio
                                    'is_self': False,  # Yahoo Finance เป็น external link
                                    'over_18': False,
                                    'fetched_at': datetime.utcnow().isoformat(),
                                    
                                    # Yahoo Finance specific fields
                                    'source': item.get('publisher', 'Yahoo Finance'),
                                    'publishedAt': published_at,
                                    'type': item.get('type', 'STORY'),
                                    'uuid': item.get('uuid', ''),
                                    'newsHash': news_hash,  # สำหรับ deduplication
                                    'symbol': symbol.upper(),  # เพิ่ม symbol
                                    
                                    # Article details (ถ้าดึงได้)
                                    **article_details
                                })
                            except Exception:
                                # ถ้า item ไหนมีปัญหา ให้ skip ไป
                                continue
                        
                        return articles
            except Exception:
                # Suppress error messages - ไม่แสดง error เพื่อให้ progress bar ดูสะอาด
                return []
    
    async def fetch_multiple_stocks_async(
        self, 
        symbols: List[str],
        include_news: bool = True
    ) -> Dict[str, Dict]:
        """
        ดึงข้อมูลหลายหุ้นพร้อมกัน
        
        Args:
            symbols: List of stock symbols
            include_news: ต้องการดึงข่าวด้วยหรือไม่
        
        Returns:
            Dictionary {symbol: stock_data}
        """
        print(f"🚀 Fetching {len(symbols)} stocks asynchronously...")
        start_time = time.time()
        
        # สร้าง tasks สำหรับทุกหุ้น
        tasks = []
        for symbol in symbols:
            task = self.fetch_stock_info_async(symbol)
            tasks.append((symbol, task))
        
        # รัน tasks พร้อมกัน
        results = {}
        completed = 0
        
        # ใช้ asyncio.gather แต่จำกัดด้วย semaphore
        for symbol, task in tasks:
            try:
                stock_info = await task
                if stock_info:
                    results[symbol] = stock_info
                    
                    # ดึงข่าวถ้าต้องการ
                    if include_news:
                        news = await self.fetch_stock_news_async(symbol)
                        results[symbol]['news'] = news
                        results[symbol]['newsCount'] = len(news)
                
                completed += 1
                if completed % 10 == 0:
                    print(f"  ✅ Completed {completed}/{len(symbols)} stocks")
            except Exception as e:
                print(f"  ⚠️ Error processing {symbol}: {e}")
                completed += 1
        
        elapsed = time.time() - start_time
        print(f"✅ Fetched {len(results)} stocks in {elapsed:.2f} seconds ({len(symbols)/elapsed:.2f} stocks/sec)")
        
        return results
    
    async def fetch_stocks_in_batches(
        self,
        symbols: List[str],
        batch_size: int = 100,
        include_news: bool = True
    ) -> Dict[str, Dict]:
        """
        ดึงข้อมูลหุ้นเป็น batch
        
        Args:
            symbols: List of stock symbols
            batch_size: จำนวนหุ้นต่อ batch
            include_news: ต้องการดึงข่าวด้วยหรือไม่
        
        Returns:
            Dictionary {symbol: stock_data}
        """
        all_results = {}
        total_batches = (len(symbols) + batch_size - 1) // batch_size
        
        for i in range(0, len(symbols), batch_size):
            batch = symbols[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            
            print(f"📦 Processing batch {batch_num}/{total_batches} ({len(batch)} stocks)...")
            
            batch_results = await self.fetch_multiple_stocks_async(batch, include_news)
            all_results.update(batch_results)
            
            # พักระหว่าง batch เพื่อหลีกเลี่ยง rate limiting
            if i + batch_size < len(symbols):
                await asyncio.sleep(1)
        
        return all_results


# ตัวอย่างการใช้งาน
async def main():
    """ตัวอย่างการใช้งาน AsyncStockFetcher"""
    fetcher = AsyncStockFetcher(max_concurrent=50, rate_limit=100)
    
    # ดึงข้อมูล 100 หุ้นพร้อมกัน
    symbols = ['AAPL', 'TSLA', 'MSFT', 'GOOGL', 'AMZN'] * 20  # 100 symbols
    results = await fetcher.fetch_multiple_stocks_async(symbols, include_news=True)
    
    print(f"\n✅ Successfully fetched {len(results)} stocks")
    for symbol, data in list(results.items())[:5]:
        print(f"  {symbol}: ${data.get('currentPrice', 0):.2f} ({data.get('changePercent', 0):.2f}%)")


if __name__ == "__main__":
    asyncio.run(main())


