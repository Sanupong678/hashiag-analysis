"""
Script สำหรับดึงข่าวจากหุ้นทั้งหมดที่มีใน database
"""
import sys
import os
from pathlib import Path
import asyncio

# ตั้งค่า encoding สำหรับ Windows terminal
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# เพิ่ม path ของ backend เข้าไปใน sys.path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from database.db_config import db
from processors.batch_data_processor import batch_processor
from utils.stock_list_fetcher import stock_list_fetcher
from datetime import datetime

def fetch_all_news(force_refresh=False, batch_size=50):
    """
    ดึงข่าวจากหุ้นทั้งหมดที่มีใน database
    
    Args:
        force_refresh: ถ้า True จะดึงใหม่แม้จะมีข่าวอยู่แล้ว
        batch_size: จำนวนหุ้นต่อ batch
    """
    try:
        print("\n" + "="*60)
        print("📰 ดึงข่าวจากหุ้นทั้งหมดใน Database")
        print("="*60)
        
        if db is None:
            print("❌ Database not available")
            return
        
        # ดึงรายชื่อหุ้นจาก database
        symbols = []
        
        # วิธีที่ 1: ดึงจาก db.stock_tickers
        if hasattr(db, 'stock_tickers') and db.stock_tickers is not None:
            ticker_docs = db.stock_tickers.find({"isActive": True})
            symbols = [doc["ticker"] for doc in ticker_docs if doc.get("ticker")]
            print(f"\n✅ Found {len(symbols)} stocks from db.stock_tickers")
        
        # วิธีที่ 2: ถ้าไม่มีใน stock_tickers ให้ดึงจาก stock_list_fetcher
        if not symbols:
            print(f"\n📋 Fetching from stock_list_fetcher...")
            all_symbols = stock_list_fetcher.get_all_valid_tickers(force_refresh=False)
            symbols = list(all_symbols) if all_symbols else []
            print(f"✅ Found {len(symbols)} stocks from stock_list_fetcher")
        
        # วิธีที่ 3: ดึงจาก db.stocks (หุ้นที่มีข้อมูลอยู่แล้ว)
        if not symbols and hasattr(db, 'stocks') and db.stocks is not None:
            stock_docs = db.stocks.find({}, {"symbol": 1})
            symbols = [doc["symbol"] for doc in stock_docs if doc.get("symbol")]
            symbols = list(set(symbols))  # Remove duplicates
            print(f"✅ Found {len(symbols)} stocks from db.stocks")
        
        if not symbols:
            print("\n❌ No stock symbols found in database")
            print("   Please ensure stock tickers are loaded in database first")
            return
        
        print(f"\n📊 Total stocks to process: {len(symbols):,}")
        print(f"   Batch size: {batch_size}")
        print(f"   Force refresh: {force_refresh}")
        
        from utils.post_normalizer import get_collection_name
        
        # นับจำนวนข่าวก่อนเริ่ม (ใช้ collection post_yahoo)
        collection_name = get_collection_name('yahoo')
        total_news_before = 0
        if hasattr(db, collection_name) and getattr(db, collection_name) is not None:
            post_collection = getattr(db, collection_name)
            total_news_before = post_collection.count_documents({})
            print(f"   📰 Current news in database: {total_news_before:,}")
        
        # ถ้า force_refresh = False ให้ skip หุ้นที่มีข่าวอยู่แล้ว
        if not force_refresh:
            print(f"\n⏭️  Skipping stocks that already have news...")
            symbols_to_process = []
            skipped_count = 0
            for symbol in symbols:
                symbol_upper = symbol.upper()
                if hasattr(db, collection_name) and getattr(db, collection_name) is not None:
                    post_collection = getattr(db, collection_name)
                    news_count = post_collection.count_documents({"symbol": symbol_upper})
                    if news_count == 0:
                        symbols_to_process.append(symbol)
                    else:
                        skipped_count += 1
            symbols = symbols_to_process
            print(f"   ✅ {len(symbols):,} stocks need news fetching")
            print(f"   ⏭️  {skipped_count:,} stocks skipped (already have news)")
        
        if not symbols:
            print("\n✅ All stocks already have news in database!")
            return
        
        # ตั้งค่า batch processor
        batch_processor.days_back = 7
        
        print(f"\n🚀 Starting news fetching...")
        print("="*60)
        
        # รัน batch processing (async)
        start_time = datetime.now()
        results = asyncio.run(
            batch_processor.process_all_stocks_async(symbols, batch_size=batch_size)
        )
        end_time = datetime.now()
        elapsed = (end_time - start_time).total_seconds()
        
        # นับจำนวนข่าวหลังเสร็จ (ใช้ collection post_yahoo)
        total_news_after = 0
        if hasattr(db, collection_name) and getattr(db, collection_name) is not None:
            post_collection = getattr(db, collection_name)
            total_news_after = post_collection.count_documents({})
        
        new_news = total_news_after - total_news_before
        
        print("\n" + "="*70)
        print("🎉" * 35)
        print("="*70)
        print("✅ NEWS FETCHING COMPLETED! ✅")
        print("="*70)
        print(f"📊 Stocks processed: {len(results):,}/{len(symbols):,}")
        print(f"📰 News articles fetched: {new_news:,} new articles")
        print(f"📚 Total news in database: {total_news_after:,} articles")
        print(f"⏱️  Time elapsed: {elapsed:.1f} seconds ({elapsed/60:.1f} minutes)")
        if len(results) > 0:
            print(f"⚡ Average: {elapsed/len(results):.2f} seconds per stock")
        print("="*70)
        print("🎉" * 35)
        print("="*70 + "\n")
        
        # 🔊 แจ้งเตือนด้วยเสียง
        try:
            import sys
            if sys.platform == 'win32':
                import winsound
                winsound.Beep(1000, 500)
                winsound.Beep(1500, 500)
            elif sys.platform == 'darwin':
                import subprocess
                subprocess.run(['say', 'News fetching completed!'])
            elif sys.platform.startswith('linux'):
                print('\a')
        except Exception:
            pass
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Fetch news for all stocks in database')
    parser.add_argument('--force-refresh', action='store_true', 
                       help='Fetch news even if stocks already have news')
    parser.add_argument('--batch-size', type=int, default=50,
                       help='Number of stocks per batch (default: 50)')
    
    args = parser.parse_args()
    
    fetch_all_news(force_refresh=args.force_refresh, batch_size=args.batch_size)

