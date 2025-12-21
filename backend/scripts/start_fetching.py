"""
Script สำหรับเริ่มดึงข้อมูลข่าวและ Reddit posts สำหรับหุ้นทั้งหมด
"""
import sys
import os
import time
from pathlib import Path
import asyncio

# ตั้งค่า encoding สำหรับ Windows terminal
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Suppress warnings และ errors ที่ไม่จำเป็น
import warnings
import logging
# sys ถูก import แล้วที่บรรทัด 4 ไม่ต้อง import ซ้ำ

# Suppress all warnings
warnings.filterwarnings('ignore')

# Suppress logging จาก libraries ต่างๆ
logging.getLogger('yfinance').setLevel(logging.CRITICAL)
logging.getLogger('aiohttp').setLevel(logging.CRITICAL)
logging.getLogger('asyncio').setLevel(logging.CRITICAL)
logging.getLogger('urllib3').setLevel(logging.CRITICAL)

# Suppress "Unclosed client session" warnings จาก aiohttp
try:
    import aiohttp
    # Suppress aiohttp warnings
    aiohttp_logger = logging.getLogger('aiohttp')
    aiohttp_logger.setLevel(logging.CRITICAL)
    # Suppress client connector warnings
    aiohttp_client_logger = logging.getLogger('aiohttp.client')
    aiohttp_client_logger.setLevel(logging.CRITICAL)
except (AttributeError, ImportError):
    # ถ้า aiohttp ไม่มีหรือไม่มี logger attribute ไม่เป็นไร
    pass

# Suppress asyncio warnings บน Windows
if sys.platform == 'win32':
    # ปิดการแสดง warnings จาก asyncio ProactorEventLoop
    logging.getLogger('asyncio').setLevel(logging.CRITICAL)
    
    # Suppress "Exception in callback" errors
    import asyncio
    def suppress_asyncio_warnings():
        """Suppress asyncio warnings on Windows"""
        original_exception_handler = asyncio.get_event_loop_policy().get_event_loop().get_exception_handler()
        def custom_exception_handler(loop, context):
            # Suppress "Exception in callback" errors
            if 'Exception in callback' in str(context.get('message', '')):
                return
            # Suppress "Unclosed client session" warnings
            if 'Unclosed client session' in str(context.get('message', '')):
                return
            # Call original handler for other exceptions
            if original_exception_handler:
                original_exception_handler(loop, context)
        
        # Set custom exception handler (จะทำใน asyncio.run)
        pass
    
    # ไม่ต้องตั้ง event loop policy ที่นี่ - จะตั้งใน start_fetching function

# เพิ่ม path ของ backend เข้าไปใน sys.path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from database.db_config import db
from processors.batch_data_processor import batch_processor
from utils.stock_list_fetcher import stock_list_fetcher
from datetime import datetime, timedelta
from utils.post_normalizer import get_collection_name

def start_fetching(force_refresh=False, batch_size=50, update_threshold_hours=24, skip_reddit=False, reddit_from_db_only=False, reddit_limit=500, reddit_priority_only=False, reddit_incremental=False):
    """
    เริ่มดึงข้อมูลข่าวและ Reddit posts สำหรับหุ้นทั้งหมด
    
    Args:
        force_refresh: ถ้า True จะดึงใหม่แม้จะมีข้อมูลอยู่แล้ว
        batch_size: จำนวนหุ้นต่อ batch
        update_threshold_hours: จำนวนชั่วโมงที่ข่าวล่าสุดเก่ากว่าให้ดึงใหม่ (default: 24 ชั่วโมง)
                                ถ้า None จะข้ามหุ้นที่มีข่าวอยู่แล้วทั้งหมด
    """
    try:
        print("\n" + "="*70)
        print("🚀 เริ่มดึงข้อมูลข่าวและ Reddit Posts")
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
        
        print(f"✅ พบ {len(all_symbols):,} หุ้น")
        
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
        
        # ถ้า force_refresh = False ให้ตรวจสอบวันที่ข่าวล่าสุด
        # แต่ถ้า force_refresh = True จะดึงใหม่ทุกหุ้น (เพื่อให้ได้ข่าวใหม่)
        if not force_refresh:
            if update_threshold_hours is None:
                # ถ้า update_threshold_hours = None ให้ข้ามหุ้นที่มีข่าวอยู่แล้วทั้งหมด (พฤติกรรมเดิม)
            print(f"\n⏭️  ข้ามหุ้นที่มีข่าวอยู่แล้ว...")
            symbols_to_process = []
            skipped_count = 0
            
            for symbol in all_symbols:
                symbol_upper = symbol.upper()
                has_news = False
                
                if hasattr(db, yahoo_collection) and getattr(db, yahoo_collection) is not None:
                    post_collection = getattr(db, yahoo_collection)
                    news_count = post_collection.count_documents({"symbol": symbol_upper})
                    if news_count > 0:
                        has_news = True
                
                if not has_news:
                    symbols_to_process.append(symbol)
                else:
                    skipped_count += 1
            
            all_symbols = symbols_to_process
            print(f"   ✅ {len(all_symbols):,} หุ้นต้องดึงข้อมูล")
            print(f"   ⏭️  {skipped_count:,} หุ้นถูกข้าม (มีข่าวอยู่แล้ว)")
            else:
                # ตรวจสอบวันที่ข่าวล่าสุด - ดึงใหม่ถ้าข่าวเก่ากว่า threshold
                print(f"\n🔄 ตรวจสอบวันที่ข่าวล่าสุด (ดึงใหม่ถ้าเก่ากว่า {update_threshold_hours} ชั่วโมง)...")
                symbols_to_process = []
                skipped_count = 0
                updated_count = 0
                cutoff_time = datetime.utcnow() - timedelta(hours=update_threshold_hours)
                
                for symbol in all_symbols:
                    symbol_upper = symbol.upper()
                    needs_update = False
                    
                    if hasattr(db, yahoo_collection) and getattr(db, yahoo_collection) is not None:
                        post_collection = getattr(db, yahoo_collection)
                        news_count = post_collection.count_documents({"symbol": symbol_upper})
                        
                        if news_count == 0:
                            # ไม่มีข่าวเลย - ต้องดึง
                            needs_update = True
                        else:
                            # ตรวจสอบวันที่ข่าวล่าสุด
                            latest_news = post_collection.find_one(
                                {"symbol": symbol_upper},
                                sort=[("publishedAt", -1), ("created_utc", -1), ("publish_date", -1)]
                            )
                            
                            if latest_news:
                                # หาวันที่ข่าวล่าสุด
                                latest_date = None
                                for date_field in ['publishedAt', 'created_utc', 'publish_date', 'providerPublishTime']:
                                    if date_field in latest_news and latest_news[date_field]:
                                        try:
                                            if isinstance(latest_news[date_field], str):
                                                if 'T' in latest_news[date_field]:
                                                    latest_date = datetime.fromisoformat(latest_news[date_field].replace('Z', '+00:00'))
                                                else:
                                                    latest_date = datetime.fromtimestamp(float(latest_news[date_field]))
                                            elif isinstance(latest_news[date_field], (int, float)):
                                                latest_date = datetime.fromtimestamp(latest_news[date_field])
                                            else:
                                                latest_date = latest_news[date_field]
                                            
                                            if latest_date:
                                                # แปลงเป็น datetime ถ้ายังไม่ใช่
                                                if isinstance(latest_date, str):
                                                    latest_date = datetime.fromisoformat(latest_date.replace('Z', '+00:00'))
                                                break
                                        except:
                                            continue
                                
                                # ถ้าไม่มีวันที่หรือวันที่เก่ากว่า threshold ให้ดึงใหม่
                                if not latest_date or latest_date.replace(tzinfo=None) < cutoff_time:
                                    needs_update = True
                                    updated_count += 1
                            else:
                                # ไม่พบข่าวล่าสุด - ต้องดึง
                                needs_update = True
                    else:
                        # ไม่มี collection - ต้องดึง
                        needs_update = True
                    
                    if needs_update:
                        symbols_to_process.append(symbol)
                    else:
                        skipped_count += 1
                
                all_symbols = symbols_to_process
                print(f"   ✅ {len(all_symbols):,} หุ้นต้องดึงข้อมูล (ใหม่: {len(all_symbols) - updated_count}, อัปเดต: {updated_count})")
                print(f"   ⏭️  {skipped_count:,} หุ้นถูกข้าม (มีข่าวใหม่อยู่แล้ว)")
        else:
            print(f"\n🔄 Force refresh: จะดึงข่าวใหม่ทุกหุ้น (รวมหุ้นที่มีข่าวอยู่แล้ว)")
            print(f"   📊 จำนวนหุ้นทั้งหมด: {len(all_symbols):,} หุ้น")
        
        if not all_symbols:
            if force_refresh:
                print("\n⚠️  ไม่พบหุ้นใน database")
            else:
                print("\n✅ หุ้นทั้งหมดมีข่าวใน database แล้ว!")
                print("   💡 ใช้ --force-refresh เพื่อดึงข่าวใหม่ทุกหุ้น")
            return
        
        print(f"\n🚀 เริ่มดึงข้อมูล...")
        print(f"   📊 จำนวนหุ้น: {len(all_symbols):,} หุ้น")
        print(f"   📦 Batch size: {batch_size} หุ้นต่อ batch")
        print(f"   📰 Yahoo: 500 ข่าวต่อหุ้น (ไม่จำกัดวัน)")
        if skip_reddit:
            print(f"   💬 Reddit: ⏭️  ข้าม (skip) - เร็วกว่า 5 นาที!")
        elif reddit_from_db_only:
            print(f"   💬 Reddit: 📂 ใช้จาก database เท่านั้น (ไม่ดึงใหม่) - เร็วกว่า 5 นาที!")
        elif reddit_priority_only:
            print(f"   💬 Reddit: ⭐ เฉพาะหุ้น popular ({reddit_limit} posts/หุ้น) - เร็วกว่า!")
        elif reddit_incremental:
            print(f"   💬 Reddit: 🔄 Incremental ({reddit_limit} posts/หุ้น) - เฉพาะหุ้นที่ไม่มี/เก่า - เร็วกว่า!")
        else:
            print(f"   💬 Reddit: {reddit_limit} posts ต่อหุ้น (7 วันล่าสุด)")
            if reddit_limit >= 500:
                print(f"      ⚠️  ใช้เวลา ~5.6 ชั่วโมง (Reddit rate limit)")
            elif reddit_limit >= 200:
                print(f"      ⚠️  ใช้เวลา ~2.2 ชั่วโมง")
            elif reddit_limit >= 100:
                print(f"      ⚠️  ใช้เวลา ~1.1 ชั่วโมง")
            else:
                print(f"      ✅ ใช้เวลา ~{reddit_limit * 6.742 / 100 / 60:.1f} นาที")
        
        if skip_reddit or reddit_from_db_only:
            print(f"   ⏱️  คาดว่าจะใช้เวลา ~3-4 นาที ✅")
        elif reddit_priority_only or reddit_incremental:
            print(f"   ⏱️  คาดว่าจะใช้เวลา ~10-30 นาที (ขึ้นอยู่กับจำนวนหุ้น)")
        else:
            if reddit_limit >= 500:
        print(f"   ⏱️  คาดว่าจะใช้เวลาหลายชั่วโมง...")
            else:
                print(f"   ⏱️  คาดว่าจะใช้เวลา ~{reddit_limit * 6.742 / 100 / 60:.1f} นาที")
        print("="*70)
        
        # รีเซ็ต progress bar สำหรับงานใหม่
        from utils.progress_bar import reset_progress, draw_progress_bar
        reset_progress()
        
        # แสดง progress bar ทันที (0%) เพื่อให้ผู้ใช้เห็นว่ากำลังเริ่มทำงาน
        # ใช้ print() เพื่อให้แน่ใจว่าแสดงทันที
        print()  # ขึ้นบรรทัดใหม่
        sys.stdout.flush()  # Force flush
        draw_progress_bar(0, len(all_symbols), bar_length=50, prefix="กำลังโหลดข่าว", show_total=True)
        sys.stdout.flush()  # Force flush อีกครั้ง
        
        # รัน batch processing (async)
        start_time = datetime.now()
        
        # Suppress asyncio warnings บน Windows
        if sys.platform == 'win32':
            # ใช้ WindowsSelectorEventLoopPolicy แทน ProactorEventLoopPolicy เพื่อหลีกเลี่ยง warnings
            try:
                asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
            except:
                pass  # ถ้าไม่สามารถเปลี่ยน policy ได้ ไม่เป็นไร
        
        # Suppress warnings during execution
        # ตั้งค่า Reddit options
        batch_processor.skip_reddit = skip_reddit
        batch_processor.reddit_from_db_only = reddit_from_db_only
        batch_processor.reddit_limit = reddit_limit
        batch_processor.reddit_priority_only = reddit_priority_only
        batch_processor.reddit_incremental = reddit_incremental
        
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            results = asyncio.run(
                batch_processor.process_all_stocks_async(list(all_symbols), batch_size=batch_size)
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
            # sys ถูก import แล้วที่ top level
            if sys.platform == 'win32':
                import winsound
                winsound.Beep(1000, 500)
                winsound.Beep(1500, 500)
            elif sys.platform == 'darwin':
                import subprocess
                subprocess.run(['say', 'Data fetching completed!'])
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
    
    parser = argparse.ArgumentParser(description='เริ่มดึงข้อมูลข่าวและ Reddit posts สำหรับหุ้นทั้งหมด')
    parser.add_argument('--force-refresh', action='store_true', 
                       help='ดึงใหม่แม้จะมีข้อมูลอยู่แล้ว')
        parser.add_argument('--batch-size', type=int, default=50,
                       help='จำนวนหุ้นต่อ batch (default: 50)')
    parser.add_argument('--update-threshold-hours', type=int, default=24,
                       help='จำนวนชั่วโมงที่ข่าวล่าสุดเก่ากว่าให้ดึงใหม่ (default: 24, ใช้ 0 เพื่อข้ามหุ้นที่มีข่าวอยู่แล้วทั้งหมด)')
    parser.add_argument('--skip-reddit', action='store_true',
                       help='ข้ามการดึง Reddit (เร็วกว่า 5 นาที) - ใช้เฉพาะ Yahoo Finance news')
    parser.add_argument('--reddit-from-db-only', action='store_true',
                       help='ใช้ Reddit จาก database เท่านั้น (ไม่ดึงใหม่) - เร็วกว่า 5 นาที')
    parser.add_argument('--reddit-limit', type=int, default=500,
                       help='จำนวน Reddit posts ต่อหุ้น (default: 500, ลดเป็น 100-200 เพื่อให้เร็วขึ้น)')
    parser.add_argument('--reddit-priority-only', action='store_true',
                       help='ดึง Reddit เฉพาะหุ้นที่ popular หรือมี mentions สูง (เร็วกว่า)')
    parser.add_argument('--reddit-incremental', action='store_true',
                       help='ดึง Reddit เฉพาะหุ้นที่ไม่มีใน database หรือเก่าเกินไป (เร็วกว่า)')
    
    args = parser.parse_args()
    
    # ถ้า update_threshold_hours = 0 ให้ใช้ None (ข้ามหุ้นที่มีข่าวอยู่แล้วทั้งหมด)
    update_threshold = None if args.update_threshold_hours == 0 else args.update_threshold_hours
    
    start_fetching(
        force_refresh=args.force_refresh, 
        batch_size=args.batch_size,
        update_threshold_hours=update_threshold,
        skip_reddit=args.skip_reddit,
        reddit_from_db_only=args.reddit_from_db_only,
        reddit_limit=args.reddit_limit,
        reddit_priority_only=args.reddit_priority_only,
        reddit_incremental=args.reddit_incremental
    )

