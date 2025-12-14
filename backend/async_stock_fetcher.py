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
        ดึงข้อมูลหุ้นแบบ async
        """
        async with self.semaphore:
            await self._rate_limit_wait()
            
            try:
                # ใช้ ThreadPoolExecutor สำหรับ yfinance (blocking I/O)
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
            except Exception as e:
                print(f"❌ Error fetching stock info for {symbol}: {e}")
                return None
    
    async def fetch_stock_news_async(self, symbol: str, max_results: int = 50) -> List[Dict]:
        """
        ดึงข่าวหุ้นแบบ async
        """
        async with self.semaphore:
            await self._rate_limit_wait()
            
            try:
                loop = asyncio.get_event_loop()
                with ThreadPoolExecutor() as executor:
                    ticker = await loop.run_in_executor(executor, lambda: yf.Ticker(symbol.upper()))
                    news_list = await loop.run_in_executor(executor, lambda: ticker.news)
                    
                    if not news_list:
                        return []
                    
                    articles = []
                    for item in news_list[:max_results]:
                        articles.append({
                            'title': item.get('title', ''),
                            'summary': item.get('summary', ''),
                            'url': item.get('link', ''),
                            'source': item.get('publisher', 'Yahoo Finance'),
                            'publishedAt': item.get('providerPublishTime', 0),
                            'author': item.get('publisher', 'Yahoo Finance'),
                            'type': item.get('type', 'STORY'),
                            'uuid': item.get('uuid', '')
                        })
                    return articles
            except Exception as e:
                print(f"❌ Error fetching news for {symbol}: {e}")
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


