"""
ใช้รายชื่อหุ้นทั้งหมดจาก Yahoo Finance
"""
import re
from typing import List, Set, Optional
from utils.stock_list_fetcher import stock_list_fetcher

class TickerValidator:
    """Validate and filter stock ticker symbols"""
    
    def __init__(self):
        # Common false positives to exclude
        self.false_positives: Set[str] = {
            'USD', 'GDP', 'CEO', 'IPO', 'ETF', 'SEC', 'IRS', 'FDA', 
            'AI', 'IT', 'TV', 'PC', 'USA', 'UK', 'EU', 'AM', 'PM',
            'API', 'URL', 'HTTP', 'HTTPS', 'PDF', 'CSV', 'JSON',
            'HTML', 'CSS', 'JS', 'SQL', 'XML', 'YTD', 'Q1', 'Q2', 'Q3', 'Q4',
            'EPS', 'PE', 'ROI', 'ROE', 'P/E', 'P/B', 'DCF', 'MACD', 'RSI',
            'NYSE', 'NASDAQ', 'DJIA'
        }
        
        # Common valid ticker patterns (1-5 uppercase letters)
        self.ticker_pattern = re.compile(r'\$([A-Z]{1,5})\b')
        
        # Known valid tickers (fallback - จะถูกแทนที่ด้วยรายชื่อจาก database)
        self.known_valid_tickers: Set[str] = {
            # Major tech
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA', 'NFLX',
            # Major banks
            'JPM', 'BAC', 'WFC', 'C', 'GS', 'MS',
            # Major indices & ETFs
            'SPY', 'QQQ', 'DIA', 'IWM', 'VTI', 'VOO',
            # Energy
            'XOM', 'CVX', 'SLB',
            # Consumer
            'WMT', 'HD', 'MCD', 'SBUX',
            # Healthcare
            'JNJ', 'PFE', 'UNH',
            # Industrial
            'CAT', 'DE', 'BA',
            # Finance
            'V', 'MA', 'PYPL'
        }
        
        # Cache สำหรับรายชื่อหุ้นทั้งหมด (จะโหลดจาก database)
        self._all_valid_tickers: Optional[Set[str]] = None
        self._tickers_loaded = False
    
    def _load_all_tickers(self):
        """โหลดรายชื่อหุ้นทั้งหมดจาก database (lazy loading)"""
        if not self._tickers_loaded:
            try:
                # โหลดจาก database
                all_tickers = stock_list_fetcher.get_all_valid_tickers(force_refresh=False)
                if all_tickers:
                    self._all_valid_tickers = all_tickers
                    # รวมกับ known_valid_tickers
                    self._all_valid_tickers.update(self.known_valid_tickers)
                else:
                    # ถ้ายังไม่มีใน database ใช้ known_valid_tickers
                    self._all_valid_tickers = self.known_valid_tickers.copy()
                self._tickers_loaded = True
            except Exception as e:
                print(f"⚠️ Error loading tickers: {e}")
                # Fallback to known_valid_tickers
                self._all_valid_tickers = self.known_valid_tickers.copy()
                self._tickers_loaded = True
    
    def is_valid_ticker(self, ticker: str) -> bool:
        """
        Check if a ticker symbol is valid
        ใช้รายชื่อหุ้นทั้งหมดจาก Yahoo Finance (NYSE, NASDAQ)
        
        Args:
            ticker: Ticker symbol to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not ticker:
            return False
        
        ticker = ticker.upper().strip()
        
        # Check length (1-5 characters)
        if len(ticker) < 1 or len(ticker) > 5:
            return False
        
        # Check if all uppercase letters
        if not ticker.isalpha() or not ticker.isupper():
            return False
        
        # Check false positives
        if ticker in self.false_positives:
            return False
        
        # โหลดรายชื่อหุ้นทั้งหมด (lazy loading)
        self._load_all_tickers()
        
        # ตรวจสอบกับรายชื่อหุ้นทั้งหมด
        if self._all_valid_tickers and ticker in self._all_valid_tickers:
            return True
        
        # Additional heuristics:
        # - Single letter tickers are usually invalid (except I, Q which are special)
        if len(ticker) == 1 and ticker not in ['I', 'Q']:
            return False
        
        # - Very common abbreviations that aren't stocks
        common_abbrevs = {'CEO', 'CFO', 'CTO', 'VP', 'HR', 'PR', 'R&D', 'IT', 'AI'}
        if ticker in common_abbrevs:
            return False
        
        return False
    
    def extract_tickers(self, text: str) -> List[str]:
        """
        Extract and validate ticker symbols from text
        
        Args:
            text: Text to extract tickers from
            
        Returns:
            List of valid ticker symbols
        """
        if not text:
            return []
        
        # Find all $TICKER patterns
        matches = self.ticker_pattern.findall(text.upper())
        
        # Filter valid tickers
        valid_tickers = [
            ticker for ticker in matches
            if self.is_valid_ticker(ticker)
        ]
        
        return list(set(valid_tickers))  # Remove duplicates
    
    def filter_tickers(self, tickers: List[str]) -> List[str]:
        """
        Filter list of tickers to only include valid ones
        
        Args:
            tickers: List of ticker symbols
            
        Returns:
            List of valid ticker symbols
        """
        return [
            ticker.upper().strip()
            for ticker in tickers
            if self.is_valid_ticker(ticker)
        ]

# Global validator instance
ticker_validator = TickerValidator()

