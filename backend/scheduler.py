"""
Scheduled tasks for automatically fetching new posts
"""
import schedule
import time
from datetime import datetime
from fetch_reddit import fetch_posts
from db_config import db
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

# Popular stock tickers to monitor
POPULAR_TICKERS = ['AAPL', 'TSLA', 'NVDA', 'MSFT', 'AMZN', 'GOOGL', 'META', 'AMD', 'NFLX', 'SPY']

def fetch_stock_posts():
    """Fetch posts for popular stock tickers"""
    print(f"\n🔄 [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting scheduled fetch...")
    
    total_fetched = 0
    for ticker in POPULAR_TICKERS:
        try:
            print(f"📊 Fetching posts for ${ticker}...")
            posts = fetch_posts(f"${ticker}", limit=20)
            total_fetched += len(posts) if posts else 0
            time.sleep(2)  # Rate limiting - wait 2 seconds between tickers
        except Exception as e:
            print(f"❌ Error fetching ${ticker}: {e}")
            continue
    
    print(f"✅ Fetched {total_fetched} total posts")
    return total_fetched

def run_scheduler():
    """Run the scheduler"""
    print("🚀 Starting scheduler for auto-fetching posts...")
    print("📅 Schedule: Every 1 hour")
    
    # Schedule tasks
    schedule.every(1).hours.do(fetch_stock_posts)
    
    # Also run once immediately
    fetch_stock_posts()
    
    # Run scheduler
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

if __name__ == "__main__":
    try:
        run_scheduler()
    except KeyboardInterrupt:
        print("\n⏹️  Scheduler stopped by user")

