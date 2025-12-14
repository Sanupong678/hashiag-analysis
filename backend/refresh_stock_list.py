"""
Script to refresh stock list directly (without starting the server)
"""
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from stock_list_fetcher import stock_list_fetcher
from datetime import datetime

if __name__ == "__main__":
    print("=" * 60)
    print("🔄 Refreshing Stock List from Yahoo Finance...")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        # Call the refresh function
        tickers = stock_list_fetcher.get_all_valid_tickers(force_refresh=True)
        
        print()
        print("=" * 60)
        print("✅ SUCCESS!")
        print("=" * 60)
        print(f"Total tickers: {len(tickers)}")
        print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        if len(tickers) < 1000:
            print(f"⚠️ Warning: Expected ~4,010 tickers but only got {len(tickers)}")
            print("   Some sources may not be available. This is still usable.")
        elif len(tickers) >= 3000:
            print(f"🎉 Great! Got {len(tickers)} tickers (close to target of 4,010)")
        
    except Exception as e:
        print()
        print("=" * 60)
        print("❌ ERROR!")
        print("=" * 60)
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

