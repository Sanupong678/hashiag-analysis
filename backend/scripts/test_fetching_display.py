"""
Script ทดสอบการแสดงผล progress bar และสรุปผล
ดึงข้อมูลหุ้นจำนวนน้อยเพื่อทดสอบ
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
from utils.post_normalizer import get_collection_name

def test_fetching_display(num_stocks=10, batch_size=1000):
    """
    ทดสอบการแสดงผล progress bar และสรุปผล
    
    Args:
        num_stocks: จำนวนหุ้นที่ต้องการทดสอบ (default: 10)
        batch_size: จำนวนหุ้นต่อ batch (default: 5)
    """
    try:
        print("\n" + "="*70)
        print("🧪 ทดสอบการแสดงผล Progress Bar และสรุปผล")
        print("="*70)
        
        if db is None:
            print("❌ Database not available")
            return
        
        # ดึงรายชื่อหุ้นทั้งหมด
        print("\n📋 กำลังดึงรายชื่อหุ้น...")
        all_symbols = stock_list_fetcher.get_all_valid_tickers(force_refresh=False)
        
        if not all_symbols:
            print("❌ ไม่พบรายชื่อหุ้น")
            return
        
        # เลือกหุ้นจำนวนน้อยสำหรับทดสอบ (เลือกหุ้นยอดนิยม)
        popular_symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'AVGO', 'COST', 'NFLX']
        test_symbols = popular_symbols[:num_stocks] if len(popular_symbols) >= num_stocks else all_symbols[:num_stocks]
        
        print(f"✅ เลือก {len(test_symbols)} หุ้นสำหรับทดสอบ: {', '.join(test_symbols)}")
        
        # ตั้งค่า batch processor
        batch_processor.days_back = None  # ไม่จำกัดวัน (ดึงให้ได้มากที่สุด)
        
        # นับจำนวนข้อมูลก่อนเริ่ม
        yahoo_collection = get_collection_name('yahoo')
        reddit_collection = get_collection_name('reddit')
        
        total_news_before = 0
        total_reddit_before = 0
        
        if hasattr(db, yahoo_collection) and getattr(db, yahoo_collection) is not None:
            post_collection = getattr(db, yahoo_collection)
            total_news_before = post_collection.count_documents({})
        
        if hasattr(db, reddit_collection) and getattr(db, reddit_collection) is not None:
            post_collection = getattr(db, reddit_collection)
            total_reddit_before = post_collection.count_documents({})
        
        print(f"\n📊 สถานะปัจจุบัน:")
        print(f"   📰 ข่าว (post_yahoo): {total_news_before:,} ข่าว")
        print(f"   💬 Reddit (post_reddit): {total_reddit_before:,} posts")
        
        print(f"\n🚀 เริ่มทดสอบดึงข้อมูล...")
        print(f"   📊 จำนวนหุ้น: {len(test_symbols)} หุ้น")
        print(f"   📦 Batch size: {batch_size} หุ้นต่อ batch")
        print(f"   📰 Yahoo: 500 ข่าวต่อหุ้น (ไม่จำกัดวัน)")
        print(f"   💬 Reddit: 500 posts ต่อหุ้น (7 วันล่าสุด)")
        print("="*70)
        
        # รัน batch processing (async)
        start_time = datetime.now()
        results = asyncio.run(
            batch_processor.process_all_stocks_async(list(test_symbols), batch_size=batch_size)
        )
        end_time = datetime.now()
        elapsed = (end_time - start_time).total_seconds()
        
        # นับจำนวนข้อมูลหลังเสร็จ
        total_news_after = 0
        total_reddit_after = 0
        
        if hasattr(db, yahoo_collection) and getattr(db, yahoo_collection) is not None:
            post_collection = getattr(db, yahoo_collection)
            total_news_after = post_collection.count_documents({})
        
        if hasattr(db, reddit_collection) and getattr(db, reddit_collection) is not None:
            post_collection = getattr(db, reddit_collection)
            total_reddit_after = post_collection.count_documents({})
        
        new_news = total_news_after - total_news_before
        new_reddit = total_reddit_after - total_reddit_before
        
        # นับจำนวนข่าวจากแต่ละแหล่ง
        yahoo_news = 0
        reddit_posts = 0
        
        if hasattr(db, yahoo_collection) and getattr(db, yahoo_collection) is not None:
            post_collection = getattr(db, yahoo_collection)
            yahoo_news = post_collection.count_documents({})
        
        if hasattr(db, reddit_collection) and getattr(db, reddit_collection) is not None:
            post_collection = getattr(db, reddit_collection)
            reddit_posts = post_collection.count_documents({})
        
        # คำนวณข่าวเฉลี่ยต่อหุ้น
        stocks_with_news = 0
        if hasattr(db, yahoo_collection) and getattr(db, yahoo_collection) is not None:
            post_collection = getattr(db, yahoo_collection)
            stocks_with_news = len(post_collection.distinct("symbol"))
        
        avg_news_per_stock = yahoo_news / stocks_with_news if stocks_with_news > 0 else 0
        
        # แสดงสรุปผล
        print("\n" + "="*70)
        print("✅ ดึงข้อมูลเสร็จสิ้น!")
        print("="*70)
        print(f"\n📊 สรุปผล:")
        print(f"   📰 ข่าวที่ดึงได้ทั้งหมด: {yahoo_news:,} ข่าว")
        print(f"\n📋 จากแหล่งที่มา:")
        print(f"   📰 Yahoo Finance: {yahoo_news:,} ข่าว")
        print(f"   💬 Reddit: {reddit_posts:,} posts")
        print(f"\n📈 สถิติ:")
        print(f"   📊 หุ้นที่มีข่าว: {stocks_with_news:,} หุ้น")
        print(f"   📰 ข่าวเฉลี่ยต่อหุ้น: {avg_news_per_stock:.2f} ข่าว")
        print(f"   ⏱️  เวลาที่ใช้: {elapsed/60:.1f} นาที")
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
                subprocess.run(['say', 'Test completed!'])
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
    
    parser = argparse.ArgumentParser(description='ทดสอบการแสดงผล progress bar และสรุปผล')
    parser.add_argument('--num-stocks', type=int, default=10,
                       help='จำนวนหุ้นที่ต้องการทดสอบ (default: 10)')
    parser.add_argument('--batch-size', type=int, default=1000,
                       help='จำนวนหุ้นต่อ batch (default: 1000)')
    
    args = parser.parse_args()
    
    test_fetching_display(num_stocks=args.num_stocks, batch_size=args.batch_size)

