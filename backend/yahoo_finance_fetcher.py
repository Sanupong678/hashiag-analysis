"""
Yahoo Finance Data Fetcher
ดึงข้อมูลจาก Yahoo Finance เป็นหลัก - ฟรี, เร็ว, แม่นยำ
"""
import yfinance as yf
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import time

class YahooFinanceFetcher:
    """ดึงข้อมูลจาก Yahoo Finance ผ่าน yfinance library"""
    
    def __init__(self):
        pass
    
    def get_stock_news(self, symbol: str, max_results: int = 50) -> List[Dict]:
        """
        ดึงข่าวจาก Yahoo Finance สำหรับหุ้น
        มี retry logic และ error handling
        
        Args:
            symbol: Stock symbol
            max_results: จำนวนข่าวสูงสุด
            
        Returns:
            List of news articles
        """
        import time
        
        # Retry logic - ลอง 3 ครั้ง
        max_retries = 3
        retry_delay = 0.5  # 0.5 seconds
        
        for attempt in range(max_retries):
            try:
                ticker = yf.Ticker(symbol.upper())
                
                # เพิ่ม delay เพื่อหลีกเลี่ยง rate limiting
                if attempt > 0:
                    time.sleep(retry_delay * attempt)
                
                # ดึงข่าว - ใช้ try-except เพื่อจับ error เฉพาะเจาะจง
                try:
                    news_list = ticker.news
                except Exception as news_error:
                    # ถ้าเป็น disk I/O error หรือ network error ให้ retry
                    if "disk" in str(news_error).lower() or "I/O" in str(news_error) or "network" in str(news_error).lower():
                        if attempt < max_retries - 1:
                            print(f"  ⏳ Retry {attempt + 1}/{max_retries} for {symbol} (disk I/O error)...")
                            continue
                        else:
                            print(f"  ⚠️ Failed to fetch news for {symbol} after {max_retries} attempts: {news_error}")
                            return []
                    else:
                        raise
                
                if not news_list:
                    return []
                
                articles = []
                for item in news_list[:max_results]:
                    try:
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
                    except Exception as item_error:
                        # Skip invalid items
                        continue
                
                return articles
                
            except Exception as e:
                error_str = str(e).lower()
                # ถ้าเป็น disk I/O error หรือ network error ให้ retry
                if ("disk" in error_str or "i/o" in error_str or "network" in error_str or 
                    "timeout" in error_str or "connection" in error_str):
                    if attempt < max_retries - 1:
                        print(f"  ⏳ Retry {attempt + 1}/{max_retries} for {symbol} ({e})...")
                        time.sleep(retry_delay * (attempt + 1))
                        continue
                    else:
                        print(f"  ⚠️ Failed to fetch news for {symbol} after {max_retries} attempts: {e}")
                        return []
                else:
                    # Error อื่นๆ ไม่ retry
                    print(f"  ⚠️ Error fetching Yahoo Finance news for {symbol}: {e}")
                    return []
        
        return []
    
    def get_stock_info(self, symbol: str) -> Optional[Dict]:
        """
        ดึงข้อมูลหุ้นจาก Yahoo Finance
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Dictionary with stock information
        """
        try:
            ticker = yf.Ticker(symbol.upper())
            
            # Get current price data
            hist = ticker.history(period="1d")
            
            if hist.empty:
                # Try to get info even if history is empty
                try:
                    info = ticker.info
                    if info and info.get('regularMarketPrice'):
                        current_price = info.get('regularMarketPrice')
                        previous_close = info.get('previousClose', current_price)
                        change = current_price - previous_close
                        change_percent = (change / previous_close * 100) if previous_close else 0
                        
                        return {
                            'symbol': symbol.upper(),
                            'name': info.get('longName', info.get('shortName', symbol)),
                            'currentPrice': float(current_price),
                            'previousClose': float(previous_close),
                            'change': float(change),
                            'changePercent': float(change_percent),
                            'volume': int(info.get('volume', 0)),
                            'marketCap': info.get('marketCap', 0),
                            'sector': info.get('sector', 'Unknown'),
                            'industry': info.get('industry', 'Unknown'),
                            'fetchedAt': datetime.utcnow().isoformat()
                        }
                except:
                    pass
                return None
            
            # Get info for additional data
            try:
                info = ticker.info
            except:
                info = {}
            
            current_price = hist['Close'].iloc[-1]
            previous_close = info.get('previousClose', current_price)
            change = current_price - previous_close
            change_percent = (change / previous_close * 100) if previous_close else 0
            
            return {
                'symbol': symbol.upper(),
                'name': info.get('longName', info.get('shortName', symbol)),
                'currentPrice': float(current_price),
                'previousClose': float(previous_close),
                'change': float(change),
                'changePercent': float(change_percent),
                'volume': int(hist['Volume'].iloc[-1]) if 'Volume' in hist.columns else 0,
                'marketCap': info.get('marketCap', 0),
                'sector': info.get('sector', 'Unknown'),
                'industry': info.get('industry', 'Unknown'),
                'fetchedAt': datetime.utcnow().isoformat()
            }
        except Exception as e:
            print(f"❌ Error fetching stock info for {symbol}: {e}")
            return None
    
    def get_recommendations(self, symbol: str) -> Dict:
        """
        ดึงคำแนะนำจาก analysts (Buy/Hold/Sell)
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Dictionary with recommendations
        """
        try:
            ticker = yf.Ticker(symbol.upper())
            recommendations = ticker.recommendations
            
            if recommendations is None or recommendations.empty:
                return {
                    'buy': 0,
                    'hold': 0,
                    'sell': 0,
                    'strongBuy': 0,
                    'strongSell': 0,
                    'total': 0
                }
            
            # Count recommendations
            rec_counts = {
                'buy': 0,
                'hold': 0,
                'sell': 0,
                'strongBuy': 0,
                'strongSell': 0,
                'total': len(recommendations)
            }
            
            # Get latest recommendations
            latest_recs = recommendations.tail(30)  # Last 30 recommendations
            
            for _, row in latest_recs.iterrows():
                # Recommendations are usually in 'To Grade' column
                if 'To Grade' in row:
                    grade = str(row['To Grade']).upper()
                    if 'STRONG BUY' in grade or 'STRONG_BUY' in grade:
                        rec_counts['strongBuy'] += 1
                    elif 'BUY' in grade:
                        rec_counts['buy'] += 1
                    elif 'HOLD' in grade or 'NEUTRAL' in grade:
                        rec_counts['hold'] += 1
                    elif 'SELL' in grade:
                        rec_counts['sell'] += 1
                    elif 'STRONG SELL' in grade or 'STRONG_SELL' in grade:
                        rec_counts['strongSell'] += 1
            
            return rec_counts
        except Exception as e:
            print(f"⚠️ Error fetching recommendations for {symbol}: {e}")
            return {
                'buy': 0,
                'hold': 0,
                'sell': 0,
                'strongBuy': 0,
                'strongSell': 0,
                'total': 0
            }
    
    def get_financials(self, symbol: str) -> Optional[Dict]:
        """
        ดึงข้อมูลทางการเงิน (Financial Statements)
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Dictionary with financial data
        """
        try:
            ticker = yf.Ticker(symbol.upper())
            
            financials = {}
            
            # Get financial statements
            try:
                financials['income_statement'] = ticker.financials.to_dict() if hasattr(ticker.financials, 'to_dict') else {}
            except:
                financials['income_statement'] = {}
            
            try:
                financials['balance_sheet'] = ticker.balance_sheet.to_dict() if hasattr(ticker.balance_sheet, 'to_dict') else {}
            except:
                financials['balance_sheet'] = {}
            
            try:
                financials['cash_flow'] = ticker.cashflow.to_dict() if hasattr(ticker.cashflow, 'to_dict') else {}
            except:
                financials['cash_flow'] = {}
            
            # Get key metrics
            info = ticker.info
            financials['key_metrics'] = {
                'pe_ratio': info.get('trailingPE', 0),
                'forward_pe': info.get('forwardPE', 0),
                'peg_ratio': info.get('pegRatio', 0),
                'price_to_book': info.get('priceToBook', 0),
                'debt_to_equity': info.get('debtToEquity', 0),
                'roe': info.get('returnOnEquity', 0),
                'roa': info.get('returnOnAssets', 0),
                'profit_margin': info.get('profitMargins', 0),
                'operating_margin': info.get('operatingMargins', 0),
                'revenue_growth': info.get('revenueGrowth', 0),
                'earnings_growth': info.get('earningsGrowth', 0)
            }
            
            return financials
        except Exception as e:
            print(f"⚠️ Error fetching financials for {symbol}: {e}")
            return None
    
    def get_historical_data(self, symbol: str, period: str = "1mo", interval: str = "1d") -> List[Dict]:
        """
        ดึงข้อมูลราคาย้อนหลัง
        
        Args:
            symbol: Stock symbol
            period: Period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
            interval: Interval (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)
            
        Returns:
            List of price data points
        """
        try:
            ticker = yf.Ticker(symbol.upper())
            hist = ticker.history(period=period, interval=interval)
            
            if hist.empty:
                return []
            
            data = []
            for date, row in hist.iterrows():
                data.append({
                    'date': date.isoformat(),
                    'open': float(row['Open']),
                    'high': float(row['High']),
                    'low': float(row['Low']),
                    'close': float(row['Close']),
                    'volume': int(row['Volume']) if 'Volume' in row else 0
                })
            
            return data
        except Exception as e:
            print(f"❌ Error fetching historical data for {symbol}: {e}")
            return []
    
    def get_multiple_stocks_info(self, symbols: List[str]) -> Dict[str, Dict]:
        """
        ดึงข้อมูลหุ้นหลายตัวพร้อมกัน (เร็วกว่า)
        
        Args:
            symbols: List of stock symbols
            
        Returns:
            Dictionary mapping symbol to stock info
        """
        results = {}
        
        # yfinance supports downloading multiple tickers at once
        try:
            tickers = yf.download(symbols, period="1d", group_by='ticker', progress=False)
            
            for symbol in symbols:
                symbol_upper = symbol.upper()
                try:
                    ticker = yf.Ticker(symbol_upper)
                    info = ticker.info
                    
                    if not tickers.empty and symbol_upper in tickers.columns.levels[0]:
                        hist = tickers[symbol_upper]
                        if not hist.empty:
                            current_price = float(hist['Close'].iloc[-1])
                            previous_close = info.get('previousClose', current_price)
                            change = current_price - previous_close
                            change_percent = (change / previous_close * 100) if previous_close else 0
                            
                            results[symbol_upper] = {
                                'symbol': symbol_upper,
                                'name': info.get('longName', info.get('shortName', symbol)),
                                'currentPrice': current_price,
                                'previousClose': float(previous_close),
                                'change': float(change),
                                'changePercent': float(change_percent),
                                'volume': int(hist['Volume'].iloc[-1]) if 'Volume' in hist.columns else 0,
                                'marketCap': info.get('marketCap', 0),
                                'sector': info.get('sector', 'Unknown'),
                                'industry': info.get('industry', 'Unknown'),
                                'fetchedAt': datetime.utcnow().isoformat()
                            }
                except Exception as e:
                    print(f"⚠️ Error fetching info for {symbol_upper}: {e}")
                    continue
        except Exception as e:
            print(f"⚠️ Error downloading multiple stocks: {e}")
            # Fallback to individual fetching
            for symbol in symbols:
                info = self.get_stock_info(symbol)
                if info:
                    results[symbol.upper()] = info
        
        return results

