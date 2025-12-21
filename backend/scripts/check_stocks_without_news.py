"""
Script สำหรับตรวจสอบหุ้นที่ยังไม่มีข่าว
"""
import sys
import os
from pathlib import Path
from datetime import datetime

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
from utils.stock_list_fetcher import stock_list_fetcher

def check_stocks_without_news():
    """ตรวจสอบหุ้นที่ยังไม่มีข่าว"""
    try:
        print("\n" + "="*70)
        print("📊 ตรวจสอบหุ้นที่ยังไม่มีข่าว")
        print("="*70)
        
        if db is None:
            print("❌ Database not available")
            return
        
        # ดึงรายชื่อหุ้นทั้งหมด
        all_symbols = stock_list_fetcher.get_all_valid_tickers(force_refresh=False)
        total_stocks = len(all_symbols) if all_symbols else 0
        
        print(f"✅ พบ {total_stocks:,} หุ้นทั้งหมด\n")
        
        yahoo_collection = get_collection_name('yahoo')
        post_collection = None
        if hasattr(db, yahoo_collection) and getattr(db, yahoo_collection) is not None:
            post_collection = getattr(db, yahoo_collection)
        
        if post_collection is None:
            print("❌ Collection post_yahoo not available")
            return
        
        # หาหุ้นที่ยังไม่มีข่าว
        stocks_with_news = set(post_collection.distinct("symbol"))
        stocks_without_news = []
        stocks_with_zero_news = []
        
        print("🔍 กำลังตรวจสอบ...")
        for symbol in all_symbols:
            symbol_upper = symbol.upper()
            if symbol_upper not in stocks_with_news:
                stocks_without_news.append(symbol_upper)
            else:
                # ตรวจสอบว่ามีข่าวจริงหรือไม่ (อาจมีแต่เป็น 0)
                news_count = post_collection.count_documents({"symbol": symbol_upper})
                if news_count == 0:
                    stocks_with_zero_news.append(symbol_upper)
        
        print(f"\n📊 สรุปผล:")
        print(f"   📈 หุ้นทั้งหมด: {total_stocks:,} หุ้น")
        print(f"   📰 หุ้นที่มีข่าว: {len(stocks_with_news):,} หุ้น")
        print(f"   ⏳ หุ้นที่ยังไม่มีข่าว: {len(stocks_without_news):,} หุ้น")
        print(f"   ⚠️  หุ้นที่มี symbol ใน DB แต่ไม่มีข่าว: {len(stocks_with_zero_news):,} หุ้น")
        
        # แสดงตัวอย่างหุ้นที่ยังไม่มีข่าว
        if stocks_without_news:
            print(f"\n📋 ตัวอย่างหุ้นที่ยังไม่มีข่าว (10 ตัวแรก):")
            for i, symbol in enumerate(stocks_without_news[:10], 1):
                print(f"   {i}. {symbol}")
            if len(stocks_without_news) > 10:
                print(f"   ... และอีก {len(stocks_without_news) - 10} หุ้น")
        
        # ตรวจสอบว่ามีหุ้นที่ดึงมาแล้วแต่ไม่มีข่าวหรือไม่
        print(f"\n🔍 ตรวจสอบหุ้นที่ดึงมาแล้วแต่ไม่มีข่าว:")
        stocks_processed_but_no_news = []
        if hasattr(db, 'stocks') and db.stocks is not None:
            for symbol in stocks_without_news[:100]:  # ตรวจสอบ 100 ตัวแรก
                stock_data = db.stocks.find_one({"symbol": symbol})
                if stock_data:
                    stocks_processed_but_no_news.append(symbol)
        
        if stocks_processed_but_no_news:
            print(f"   ⚠️  พบ {len(stocks_processed_but_no_news)} หุ้นที่ดึงมาแล้วแต่ไม่มีข่าว:")
            for symbol in stocks_processed_but_no_news[:10]:
                print(f"      - {symbol}")
            if len(stocks_processed_but_no_news) > 10:
                print(f"      ... และอีก {len(stocks_processed_but_no_news) - 10} หุ้น")
        else:
            print(f"   ✅ ไม่พบหุ้นที่ดึงมาแล้วแต่ไม่มีข่าว")
        
        print("\n" + "="*70)
        print(f"✅ ตรวจสอบเสร็จสิ้น - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_stocks_without_news()

