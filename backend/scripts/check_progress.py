"""
Script สำหรับตรวจสอบความคืบหน้าการอัปเดตข้อมูลหุ้น
- จำนวนหุ้นทั้งหมด
- จำนวนหุ้นที่อัปเดตแล้ว
- จำนวนหุ้นที่ยังไม่อัปเดต
- จำนวนข่าวทั้งหมด
- จำนวน Reddit posts ทั้งหมด
"""
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

# ตั้งค่า encoding สำหรับ Windows terminal
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# เพิ่ม path ของ backend เข้าไปใน sys.path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from database.db_config import db
from utils.post_normalizer import get_collection_name

def check_progress():
    """ตรวจสอบความคืบหน้าการอัปเดตข้อมูล"""
    try:
        print("\n" + "="*70)
        print("📊 ตรวจสอบความคืบหน้าการอัปเดตข้อมูล")
        print("="*70)
        
        if db is None:
            print("❌ Database not available")
            return
        
        # 1. จำนวนหุ้นทั้งหมดใน stock_tickers
        total_stocks = 0
        if hasattr(db, 'stock_tickers') and db.stock_tickers is not None:
            total_stocks = db.stock_tickers.count_documents({})
        
        print(f"\n📈 จำนวนหุ้นทั้งหมดในระบบ: {total_stocks:,} หุ้น")
        
        # 2. จำนวนหุ้นที่มีข้อมูลใน stocks collection
        stocks_with_data = 0
        if hasattr(db, 'stocks') and db.stocks is not None:
            stocks_with_data = db.stocks.count_documents({})
        
        print(f"✅ จำนวนหุ้นที่มีข้อมูลใน stocks: {stocks_with_data:,} หุ้น")
        
        # 3. จำนวนหุ้นที่อัปเดตล่าสุด (ภายใน 2 ชั่วโมง)
        recent_threshold = datetime.utcnow() - timedelta(hours=2)
        recent_stocks = 0
        if hasattr(db, 'stocks') and db.stocks is not None:
            recent_stocks = db.stocks.count_documents({
                "fetchedAt": {
                    "$gte": recent_threshold.isoformat()
                }
            })
        
        print(f"🔄 จำนวนหุ้นที่อัปเดตล่าสุด (2 ชั่วโมง): {recent_stocks:,} หุ้น")
        
        # 4. จำนวนข่าวทั้งหมด (ใช้ collection post_yahoo)
        yahoo_collection = get_collection_name('yahoo')
        total_news = 0
        if hasattr(db, yahoo_collection) and getattr(db, yahoo_collection) is not None:
            post_collection = getattr(db, yahoo_collection)
            total_news = post_collection.count_documents({})
        
        print(f"📰 จำนวนข่าวทั้งหมด (post_yahoo): {total_news:,} ข่าว")
        
        # 5. จำนวนหุ้นที่มีข่าว
        stocks_with_news = 0
        if hasattr(db, yahoo_collection) and getattr(db, yahoo_collection) is not None:
            post_collection = getattr(db, yahoo_collection)
            distinct_symbols = post_collection.distinct("symbol")
            stocks_with_news = len(distinct_symbols)
        
        print(f"📰 จำนวนหุ้นที่มีข่าว: {stocks_with_news:,} หุ้น")
        
        # 6. จำนวน Reddit posts ทั้งหมด (ใช้ collection post_reddit)
        reddit_collection = get_collection_name('reddit')
        total_reddit = 0
        if hasattr(db, reddit_collection) and getattr(db, reddit_collection) is not None:
            post_collection = getattr(db, reddit_collection)
            total_reddit = post_collection.count_documents({})
        
        print(f"💬 จำนวน Reddit posts ทั้งหมด (post_reddit): {total_reddit:,} posts")
        
        # 7. จำนวนหุ้นที่มี Reddit posts
        stocks_with_reddit = 0
        if hasattr(db, reddit_collection) and getattr(db, reddit_collection) is not None:
            post_collection = getattr(db, reddit_collection)
            distinct_symbols_reddit = post_collection.distinct("keyword")
            stocks_with_reddit = len(distinct_symbols_reddit)
        
        print(f"💬 จำนวนหุ้นที่มี Reddit posts: {stocks_with_reddit:,} หุ้น")
        
        # 8. คำนวณเปอร์เซ็นต์ความคืบหน้า
        if total_stocks > 0:
            progress_stocks = (stocks_with_data / total_stocks) * 100
            progress_news = (stocks_with_news / total_stocks) * 100
            progress_reddit = (stocks_with_reddit / total_stocks) * 100
            
            print(f"\n{'='*70}")
            print("📊 สรุปความคืบหน้า")
            print("="*70)
            print(f"📈 หุ้นที่มีข้อมูล: {progress_stocks:.2f}% ({stocks_with_data:,}/{total_stocks:,})")
            print(f"📰 หุ้นที่มีข่าว: {progress_news:.2f}% ({stocks_with_news:,}/{total_stocks:,})")
            print(f"💬 หุ้นที่มี Reddit: {progress_reddit:.2f}% ({stocks_with_reddit:,}/{total_stocks:,})")
        
        # 9. ข้อมูลล่าสุดที่อัปเดต
        if hasattr(db, 'stocks') and db.stocks is not None:
            latest_stock = db.stocks.find_one(sort=[("fetchedAt", -1)])
            if latest_stock:
                latest_time = latest_stock.get('fetchedAt', '')
                latest_symbol = latest_stock.get('symbol', '')
                print(f"\n🕐 หุ้นที่อัปเดตล่าสุด: {latest_symbol} ({latest_time})")
        
        # 10. จำนวนข้อมูลทั้งหมดใน database
        total_documents = 0
        if hasattr(db, 'stocks') and db.stocks is not None:
            total_documents += db.stocks.count_documents({})
        if hasattr(db, yahoo_collection) and getattr(db, yahoo_collection) is not None:
            post_collection = getattr(db, yahoo_collection)
            total_documents += post_collection.count_documents({})
        if hasattr(db, reddit_collection) and getattr(db, reddit_collection) is not None:
            post_collection = getattr(db, reddit_collection)
            total_documents += post_collection.count_documents({})
        if hasattr(db, 'stock_tickers') and db.stock_tickers is not None:
            total_documents += db.stock_tickers.count_documents({})
        
        print(f"\n📚 จำนวนข้อมูลทั้งหมดใน database: {total_documents:,} documents")
        
        print(f"\n{'='*70}")
        print(f"✅ ตรวจสอบเสร็จสิ้น - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70 + "\n")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_progress()

