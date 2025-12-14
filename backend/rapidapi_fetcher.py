"""
RapidAPI Integration Module
Fetches data from various APIs through RapidAPI (Yahoo Finance, etc.)
"""
import os
from dotenv import load_dotenv
from datetime import datetime
from typing import Dict, Optional
import requests

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

class RapidAPIFetcher:
    def __init__(self):
        self.api_key = os.getenv("X_RAPIDAPI_KEY") or os.getenv("RAPIDAPI_KEY")
        self.host = os.getenv("X_RAPIDAPI_HOST") or os.getenv("RAPIDAPI_HOST")
        
        if not self.api_key or not self.host:
            print("⚠️ RapidAPI credentials not found in environment variables")
            print("   RapidAPI features will be disabled")
        else:
            print(f"✅ RapidAPI credentials loaded: {self.api_key[:10]}... | Host: {self.host}")
    
    def get_headers(self) -> Dict[str, str]:
        """Get common headers for RapidAPI requests"""
        if not self.api_key or not self.host:
            return {}
        
        return {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": self.host
        }
    
    def fetch_yahoo_finance(self, symbol: str) -> Optional[Dict]:
        """
        Fetch stock data from Yahoo Finance via RapidAPI
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Stock data dictionary
        """
        if not self.api_key or not self.host:
            return None
        
        try:
            # Common RapidAPI Yahoo Finance endpoint
            url = f"https://{self.host}/market/quote"
            headers = self.get_headers()
            params = {"ticker": symbol}
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'symbol': symbol.upper(),
                    'data': data,
                    'fetchedAt': datetime.utcnow().isoformat(),
                    'source': 'rapidapi_yahoo'
                }
            else:
                print(f"❌ RapidAPI error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Error fetching from RapidAPI for {symbol}: {e}")
            return None
    
    def fetch_stock_quote(self, symbol: str) -> Optional[Dict]:
        """Get real-time stock quote via RapidAPI"""
        return self.fetch_yahoo_finance(symbol)

