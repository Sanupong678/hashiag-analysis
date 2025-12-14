"""Script to check how many stock tickers are in the database"""
from db_config import db
from stock_list_fetcher import stock_list_fetcher

def check_tickers():
    print("🔍 Checking stock tickers in database...")
    
    # Load from database
    tickers = stock_list_fetcher.load_tickers_from_database()
    
    print(f"\n📊 Results:")
    print(f"   Total tickers in database: {len(tickers)}")
    
    if tickers:
        sample = list(tickers)[:20]
        print(f"   Sample tickers (first 20): {sample}")
        
        # Check exchange breakdown if available
        if db is not None:
            try:
                exchange_counts = {}
                ticker_docs = db.stock_tickers.find({})
                for doc in ticker_docs:
                    exchange = doc.get('exchange', 'UNKNOWN')
                    exchange_counts[exchange] = exchange_counts.get(exchange, 0) + 1
                
                print(f"\n📈 Exchange Breakdown:")
                for exchange, count in exchange_counts.items():
                    print(f"   {exchange}: {count} tickers")
            except Exception as e:
                print(f"   ⚠️ Could not get exchange breakdown: {e}")
    else:
        print("   ⚠️ No tickers found in database!")
        print("   💡 Run /api/stock-list/refresh to fetch tickers from Yahoo Finance")
    
    # Also check known_valid_tickers from ticker_validator
    from ticker_validator import ticker_validator
    known_count = len(ticker_validator.known_valid_tickers)
    print(f"\n📋 Known valid tickers (fallback): {known_count}")

if __name__ == "__main__":
    check_tickers()

