"""
Stock Price Data Module
Fetches stock prices and historical data using yfinance
"""
import yfinance as yf
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import pandas as pd

class StockDataFetcher:
    def __init__(self):
        pass
    
    def get_stock_info(self, symbol: str) -> Optional[Dict]:
        """
        Get current stock information
        
        Returns:
            Dictionary with stock info including price, market cap, volume, etc.
        """
        try:
            ticker = yf.Ticker(symbol)
            
            # Get current price data first (more reliable)
            hist = ticker.history(period="1d")
            
            if hist.empty:
                # Try to get info even if history is empty (for some tickers like indices)
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
    
    def get_historical_data(self, symbol: str, period: str = "1mo", interval: str = "1d") -> Optional[List[Dict]]:
        """
        Get historical stock price data
        
        Args:
            symbol: Stock symbol
            period: Period to fetch (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
            interval: Data interval (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)
            
        Returns:
            List of price data points
        """
        try:
            ticker = yf.Ticker(symbol)
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
    
    def get_multiple_stocks(self, symbols: List[str]) -> Dict[str, Dict]:
        """Get info for multiple stocks"""
        results = {}
        for symbol in symbols:
            info = self.get_stock_info(symbol)
            if info:
                results[symbol.upper()] = info
        return results

