"""
Script สำหรับตรวจสอบความคืบหน้าการดึงข่าวแบบ real-time
"""
import sys
import os
from pathlib import Path
from datetime import datetime
import time

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

def monitor_fetching(interval_seconds=30):
    """
    ตรวจสอบความคืบหน้าการดึงข่าวแบบ real-time
    
    Args:
        interval_seconds: ตรวจสอบทุกกี่วินาที (default: 30)
    """
    try:
        print("\n" + "="*70)
        print("📊 ตรวจสอบความคืบหน้าการดึงข่าว (Real-time)")
        print("="*70)
        print("💡 กด Ctrl+C เพื่อหยุดการตรวจสอบ\n")
        
        if db is None:
            print("❌ Database not available")
            return
        
        # ดึงรายชื่อหุ้นทั้งหมด
        all_symbols = stock_list_fetcher.get_all_valid_tickers(force_refresh=False)
        total_stocks = len(all_symbols) if all_symbols else 0
        
        yahoo_collection = get_collection_name('yahoo')
        post_collection = None
        if hasattr(db, yahoo_collection) and getattr(db, yahoo_collection) is not None:
            post_collection = getattr(db, yahoo_collection)
        
        if post_collection is None:
            print("❌ Collection post_yahoo not available")
            return
        
        # นับสถานะเริ่มต้น
        initial_news_count = post_collection.count_documents({})
        initial_stocks_with_news = len(post_collection.distinct("symbol"))
        initial_stocks_without_news = total_stocks - initial_stocks_with_news
        
        print(f"📊 สถานะเริ่มต้น:")
        print(f"   📈 หุ้นทั้งหมด: {total_stocks:,} หุ้น")
        print(f"   📰 หุ้นที่มีข่าว: {initial_stocks_with_news:,} หุ้น")
        print(f"   ⏳ หุ้นที่ยังไม่มีข่าว: {initial_stocks_without_news:,} หุ้น")
        print(f"   📚 ข่าวทั้งหมด: {initial_news_count:,} ข่าว")
        print(f"\n🔄 เริ่มตรวจสอบทุก {interval_seconds} วินาที...\n")
        
        last_news_count = initial_news_count
        last_stocks_with_news = initial_stocks_with_news
        iteration = 0
        
        try:
            while True:
                iteration += 1
                current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                # นับสถานะปัจจุบัน
                current_news_count = post_collection.count_documents({})
                current_stocks_with_news = len(post_collection.distinct("symbol"))
                current_stocks_without_news = total_stocks - current_stocks_with_news
                
                # คำนวณความเปลี่ยนแปลง
                news_added = current_news_count - last_news_count
                stocks_added = current_stocks_with_news - last_stocks_with_news
                
                # คำนวณเปอร์เซ็นต์
                progress_percent = (current_stocks_with_news / total_stocks * 100) if total_stocks > 0 else 0
                remaining_percent = (current_stocks_without_news / total_stocks * 100) if total_stocks > 0 else 0
                
                # แสดงผล
                print(f"[{current_time}] Iteration #{iteration}")
                print(f"   📰 หุ้นที่มีข่าว: {current_stocks_with_news:,} / {total_stocks:,} ({progress_percent:.2f}%)")
                print(f"   ⏳ หุ้นที่ยังเหลือ: {current_stocks_without_news:,} / {total_stocks:,} ({remaining_percent:.2f}%)")
                print(f"   📚 ข่าวทั้งหมด: {current_news_count:,} ข่าว")
                
                if news_added > 0 or stocks_added > 0:
                    print(f"   ✨ เปลี่ยนแปลง:")
                    if news_added > 0:
                        print(f"      +{news_added:,} ข่าวใหม่")
                    if stocks_added > 0:
                        print(f"      +{stocks_added:,} หุ้นใหม่ที่มีข่าว")
                else:
                    print(f"   ⏸️  ไม่มีการเปลี่ยนแปลง")
                
                # คำนวณความเร็ว (ถ้ามีข้อมูล)
                if iteration > 1 and news_added > 0:
                    estimated_remaining_news = current_stocks_without_news * 100  # ประมาณ 100 ข่าวต่อหุ้น
                    if news_added > 0:
                        news_per_second = news_added / interval_seconds
                        estimated_seconds = estimated_remaining_news / news_per_second if news_per_second > 0 else 0
                        estimated_minutes = estimated_seconds / 60
                        estimated_hours = estimated_minutes / 60
                        print(f"   ⚡ ความเร็ว: {news_per_second:.2f} ข่าว/วินาที")
                        if estimated_hours < 1:
                            print(f"   ⏱️  ประมาณเวลาที่เหลือ: {estimated_minutes:.1f} นาที")
                        else:
                            print(f"   ⏱️  ประมาณเวลาที่เหลือ: {estimated_hours:.1f} ชั่วโมง")
                
                print("-" * 70)
                
                # อัปเดตค่าล่าสุด
                last_news_count = current_news_count
                last_stocks_with_news = current_stocks_with_news
                
                # รอ interval
                time.sleep(interval_seconds)
                
        except KeyboardInterrupt:
            print("\n\n" + "="*70)
            print("✅ หยุดการตรวจสอบ")
            print("="*70)
            
            # สรุปสุดท้าย
            final_news_count = post_collection.count_documents({})
            final_stocks_with_news = len(post_collection.distinct("symbol"))
            final_stocks_without_news = total_stocks - final_stocks_with_news
            
            total_news_added = final_news_count - initial_news_count
            total_stocks_added = final_stocks_with_news - initial_stocks_with_news
            
            print(f"\n📊 สรุปสุดท้าย:")
            print(f"   📰 หุ้นที่มีข่าว: {final_stocks_with_news:,} / {total_stocks:,}")
            print(f"   ⏳ หุ้นที่ยังเหลือ: {final_stocks_without_news:,} / {total_stocks:,}")
            print(f"   📚 ข่าวทั้งหมด: {final_news_count:,} ข่าว")
            print(f"   ✨ ข่าวที่เพิ่มขึ้น: +{total_news_added:,} ข่าว")
            print(f"   ✨ หุ้นที่เพิ่มขึ้น: +{total_stocks_added:,} หุ้น")
            print("="*70 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='ตรวจสอบความคืบหน้าการดึงข่าวแบบ real-time')
    parser.add_argument('--interval', type=int, default=30,
                       help='ตรวจสอบทุกกี่วินาที (default: 30)')
    
    args = parser.parse_args()
    
    monitor_fetching(interval_seconds=args.interval)

