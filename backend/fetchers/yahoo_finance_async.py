"""
Yahoo Finance Async Fetcher - ใช้ aiohttp แทน yfinance
เร็วกว่า yfinance เพราะเป็น async จริงๆ (ไม่ใช่ blocking I/O)
"""
import aiohttp
import asyncio
from typing import Dict, List, Optional
from datetime import datetime
import json
import re

class YahooFinanceAsyncFetcher:
    """
    Async fetcher สำหรับดึงข้อมูลจาก Yahoo Finance โดยตรง
    ใช้ aiohttp แทน yfinance เพื่อให้เป็น async จริงๆ
    """
    
    def __init__(self):
        self.base_url = "https://query1.finance.yahoo.com/v8/finance/chart"
        self.news_url = "https://query2.finance.yahoo.com/v1/finance/search"
        self.info_url = "https://query2.finance.yahoo.com/v10/finance/quoteSummary"
        self.session = None
    
    async def _get_session(self):
        """Get or create aiohttp session"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=10),
                connector=aiohttp.TCPConnector(limit=100, limit_per_host=50)
            )
        return self.session
    
    async def close(self):
        """Close aiohttp session"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def fetch_stock_info_async(self, symbol: str) -> Optional[Dict]:
        """
        ดึงข้อมูลหุ้นแบบ async จาก Yahoo Finance API โดยตรง
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Stock info dictionary
        """
        session = await self._get_session()
        symbol_upper = symbol.upper()
        
        try:
            # ดึงข้อมูล price และ volume
            url = f"{self.base_url}/{symbol_upper}"
            params = {
                "interval": "1d",
                "range": "1d",
                "includePrePost": "false"
            }
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Parse data
                    result = data.get('chart', {}).get('result', [])
                    if not result:
                        return None
                    
                    result_data = result[0]
                    meta = result_data.get('meta', {})
                    indicators = result_data.get('indicators', {})
                    quote = indicators.get('quote', [{}])[0]
                    timestamps = result_data.get('timestamp', [])
                    
                    if not timestamps or not quote.get('close'):
                        return None
                    
                    # ดึงข้อมูลเพิ่มเติม (info)
                    info_data = await self._fetch_stock_info_details(session, symbol_upper)
                    
                    current_price = quote['close'][-1] if quote.get('close') else meta.get('regularMarketPrice', 0)
                    previous_close = meta.get('previousClose', current_price)
                    change = current_price - previous_close
                    change_percent = (change / previous_close * 100) if previous_close else 0
                    volume = quote['volume'][-1] if quote.get('volume') else meta.get('regularMarketVolume', 0)
                    
                    return {
                        'symbol': symbol_upper,
                        'name': info_data.get('longName', info_data.get('shortName', symbol_upper)),
                        'currentPrice': float(current_price),
                        'previousClose': float(previous_close),
                        'change': float(change),
                        'changePercent': float(change_percent),
                        'volume': int(volume),
                        'averageVolume': info_data.get('averageVolume', volume),
                        'marketCap': info_data.get('marketCap', 0),
                        'sector': info_data.get('sector', 'Unknown'),
                        'industry': info_data.get('industry', 'Unknown'),
                        'bid': info_data.get('bid', 0),
                        'ask': info_data.get('ask', 0),
                        'bidSize': info_data.get('bidSize', 0),
                        'askSize': info_data.get('askSize', 0),
                        'spread': info_data.get('ask', 0) - info_data.get('bid', 0) if info_data.get('ask') and info_data.get('bid') else 0,
                        'spreadPercent': ((info_data.get('ask', 0) - info_data.get('bid', 0)) / info_data.get('bid', 1) * 100) if info_data.get('ask') and info_data.get('bid') and info_data.get('bid') > 0 else 0,
                        'fetchedAt': datetime.utcnow().isoformat()
                    }
                else:
                    return None
        except Exception:
            # Suppress error messages
            return None
    
    async def _fetch_stock_info_details(self, session: aiohttp.ClientSession, symbol: str) -> Dict:
        """ดึงข้อมูลเพิ่มเติม (info) จาก Yahoo Finance"""
        try:
            url = f"{self.info_url}/{symbol}"
            params = {
                "modules": "summaryProfile,price,defaultKeyStatistics"
            }
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    result = data.get('quoteSummary', {}).get('result', [])
                    if result:
                        summary_profile = result[0].get('summaryProfile', {})
                        price = result[0].get('price', {})
                        default_key_statistics = result[0].get('defaultKeyStatistics', {})
                        
                        return {
                            'longName': price.get('longName', ''),
                            'shortName': price.get('shortName', ''),
                            'averageVolume': price.get('averageVolume', 0),
                            'marketCap': price.get('marketCap', {}).get('raw', 0) if isinstance(price.get('marketCap'), dict) else price.get('marketCap', 0),
                            'sector': summary_profile.get('sector', 'Unknown'),
                            'industry': summary_profile.get('industry', 'Unknown'),
                            'bid': price.get('bid', {}).get('raw', 0) if isinstance(price.get('bid'), dict) else price.get('bid', 0),
                            'ask': price.get('ask', {}).get('raw', 0) if isinstance(price.get('ask'), dict) else price.get('ask', 0),
                            'bidSize': price.get('bidSize', {}).get('raw', 0) if isinstance(price.get('bidSize'), dict) else price.get('bidSize', 0),
                            'askSize': price.get('askSize', {}).get('raw', 0) if isinstance(price.get('askSize'), dict) else price.get('askSize', 0),
                        }
        except Exception:
            pass
        
        return {}
    
    async def fetch_stock_news_async(self, symbol: str, max_results: int = 100) -> List[Dict]:
        """
        ดึงข่าวหุ้นแบบ async จาก Yahoo Finance API โดยตรง
        
        Args:
            symbol: Stock symbol
            max_results: จำนวนข่าวสูงสุด
            
        Returns:
            List of news articles
        """
        session = await self._get_session()
        symbol_upper = symbol.upper()
        
        try:
            url = f"{self.news_url}"
            params = {
                "q": symbol_upper,
                "quotesCount": 1,
                "newsCount": max_results
            }
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    news_list = data.get('news', [])
                    
                    if not news_list:
                        return []
                    
                    articles = []
                    for item in news_list[:max_results]:
                        try:
                            published_at = item.get('providerPublishTime', 0)
                            if published_at and isinstance(published_at, (int, float)):
                                published_at = datetime.fromtimestamp(published_at).isoformat()
                            elif not published_at:
                                published_at = datetime.utcnow().isoformat()
                            
                            articles.append({
                                'title': item.get('title', ''),
                                'summary': item.get('summary', ''),
                                'url': item.get('link', ''),
                                'source': item.get('publisher', 'Yahoo Finance'),
                                'publishedAt': published_at,
                                'author': item.get('publisher', 'Yahoo Finance'),
                                'type': item.get('type', 'STORY'),
                                'uuid': item.get('uuid', ''),
                                'providerPublishTime': item.get('providerPublishTime', 0)
                            })
                        except Exception:
                            continue
                    
                    return articles
                else:
                    return []
        except Exception:
            # Suppress error messages
            return []
    
    async def fetch_historical_data_async(self, symbol: str, period: str = "1mo", interval: str = "1d") -> List[Dict]:
        """
        ดึงข้อมูลราคาย้อนหลังแบบ async
        
        Args:
            symbol: Stock symbol
            period: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max
            interval: 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo
            
        Returns:
            List of historical data points
        """
        session = await self._get_session()
        symbol_upper = symbol.upper()
        
        try:
            url = f"{self.base_url}/{symbol_upper}"
            params = {
                "interval": interval,
                "range": period,
                "includePrePost": "false"
            }
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    result = data.get('chart', {}).get('result', [])
                    
                    if not result:
                        return []
                    
                    result_data = result[0]
                    timestamps = result_data.get('timestamp', [])
                    indicators = result_data.get('indicators', {})
                    quote = indicators.get('quote', [{}])[0]
                    
                    historical_data = []
                    for i, timestamp in enumerate(timestamps):
                        historical_data.append({
                            'date': datetime.fromtimestamp(timestamp).isoformat(),
                            'open': quote.get('open', [None])[i] if quote.get('open') else None,
                            'high': quote.get('high', [None])[i] if quote.get('high') else None,
                            'low': quote.get('low', [None])[i] if quote.get('low') else None,
                            'close': quote.get('close', [None])[i] if quote.get('close') else None,
                            'volume': quote.get('volume', [None])[i] if quote.get('volume') else None
                        })
                    
                    return historical_data
                else:
                    return []
        except Exception:
            return []

