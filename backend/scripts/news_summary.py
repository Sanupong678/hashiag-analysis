"""
Script สำหรับสรุปข้อมูลข่าวใน database
- จำนวนหุ้นที่มีข่าว
- จำนวนข่าวต่อหุ้น
- จำนวนข่าวทั้งหมด
"""
import sys
import os
from pathlib import Path

# ตั้งค่า encoding สำหรับ Windows terminal
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# เพิ่ม path ของ backend เข้าไปใน sys.path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from database.db_config import db
from datetime import datetime
from utils.post_normalizer import get_collection_name

def print_news_summary():
    """สรุปข้อมูลข่าวใน database"""
    try:
        collection_name = get_collection_name('yahoo')
        if db is None or not hasattr(db, collection_name) or getattr(db, collection_name) is None:
            print("❌ Database not available")
            return
        
        post_collection = getattr(db, collection_name)
        
        print("\n" + "="*60)
        print("📰 สรุปข้อมูลข่าวใน Database (post_yahoo)")
        print("="*60)
        
        # นับจำนวนข่าวทั้งหมด
        total_news = post_collection.count_documents({})
        print(f"\n📊 จำนวนข่าวทั้งหมด: {total_news:,} ข่าว")
        
        # นับจำนวนหุ้นที่มีข่าว (distinct symbols)
        distinct_symbols = post_collection.distinct("symbol")
        total_stocks = len(distinct_symbols)
        print(f"📈 จำนวนหุ้นที่มีข่าว: {total_stocks:,} หุ้น")
        
        if total_stocks == 0:
            print("\n⚠️  ยังไม่มีข่าวใน database")
            return
        
        # คำนวณค่าเฉลี่ย
        avg_news = total_news / total_stocks if total_stocks > 0 else 0
        print(f"📊 จำนวนข่าวเฉลี่ยต่อหุ้น: {avg_news:.2f} ข่าว/หุ้น")
        
        # นับจำนวนข่าวต่อหุ้น
        print(f"\n{'='*60}")
        print("📋 จำนวนข่าวต่อหุ้น (Top 20)")
        print("="*60)
        print(f"{'ลำดับ':<8} {'Symbol':<12} {'จำนวนข่าว':<15} {'เปอร์เซ็นต์':<15}")
        print("-"*60)
        
        news_per_stock = []
        for symbol in distinct_symbols:
            count = post_collection.count_documents({"symbol": symbol})
            news_per_stock.append({
                "symbol": symbol,
                "count": count
            })
        
        # เรียงตามจำนวนข่าว (มากไปน้อย)
        news_per_stock.sort(key=lambda x: x["count"], reverse=True)
        
        # แสดง Top 20
        for idx, item in enumerate(news_per_stock[:20], 1):
            percentage = (item["count"] / total_news * 100) if total_news > 0 else 0
            print(f"{idx:<8} {item['symbol']:<12} {item['count']:<15,} {percentage:>6.2f}%")
        
        # สรุปสถิติ
        if news_per_stock:
            max_news = max(item["count"] for item in news_per_stock)
            min_news = min(item["count"] for item in news_per_stock)
            max_symbol = next(item["symbol"] for item in news_per_stock if item["count"] == max_news)
            min_symbol = next(item["symbol"] for item in news_per_stock if item["count"] == min_news)
            
            print(f"\n{'='*60}")
            print("📊 สรุปสถิติ")
            print("="*60)
            print(f"🔝 หุ้นที่มีข่าวมากที่สุด: {max_symbol} ({max_news:,} ข่าว)")
            print(f"🔻 หุ้นที่มีข่าวน้อยที่สุด: {min_symbol} ({min_news:,} ข่าว)")
            print(f"📊 จำนวนข่าวเฉลี่ย: {avg_news:.2f} ข่าว/หุ้น")
            print(f"📈 จำนวนข่าวทั้งหมด: {total_news:,} ข่าว")
            print(f"📉 จำนวนหุ้นทั้งหมด: {total_stocks:,} หุ้น")
        
        # แสดงการกระจายจำนวนข่าว
        print(f"\n{'='*60}")
        print("📊 การกระจายจำนวนข่าว")
        print("="*60)
        
        ranges = [
            (0, 10, "0-10 ข่าว"),
            (11, 25, "11-25 ข่าว"),
            (26, 50, "26-50 ข่าว"),
            (51, 100, "51-100 ข่าว"),
            (101, float('inf'), "100+ ข่าว")
        ]
        
        for min_count, max_count, label in ranges:
            if max_count == float('inf'):
                count = sum(1 for item in news_per_stock if item["count"] >= min_count)
            else:
                count = sum(1 for item in news_per_stock if min_count <= item["count"] <= max_count)
            percentage = (count / total_stocks * 100) if total_stocks > 0 else 0
            print(f"{label:<20} {count:>5,} หุ้น ({percentage:>5.2f}%)")
        
        print(f"\n{'='*60}")
        print(f"✅ สรุปเสร็จสิ้น - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print_news_summary()

