"""
Reddit Bulk Scheduler
รัน Reddit bulk fetch ทุก 45 วินาที
"""
import asyncio
import schedule
import time
import threading
from datetime import datetime
from processors.reddit_bulk_processor import RedditBulkProcessor
from utils.stock_list_fetcher import stock_list_fetcher

class RedditBulkScheduler:
    """
    Scheduler สำหรับ Reddit bulk fetch
    """
    
    def __init__(self):
        self.processor = RedditBulkProcessor()
        self.is_running = False
        self.thread = None
        self.valid_tickers = None
        self._fetch_in_progress = False  # ✅ ตรวจสอบว่า bulk fetch กำลังรันอยู่หรือไม่
    
    def _load_valid_tickers(self):
        """โหลด valid tickers (cache)"""
        if self.valid_tickers is None:
            all_tickers = stock_list_fetcher.get_all_valid_tickers(force_refresh=False)
            self.valid_tickers = {t.upper() for t in all_tickers}
        return self.valid_tickers
    
    async def _run_bulk_fetch(self):
        """รัน bulk fetch"""
        # ✅ ตรวจสอบว่ามี bulk fetch กำลังรันอยู่หรือไม่
        if self._fetch_in_progress:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ⏭️  ข้าม Reddit bulk (ยังมีงานกำลังรันอยู่)")
            return
        
        # ✅ ตั้ง flag ว่า bulk fetch กำลังรันอยู่
        self._fetch_in_progress = True
        
        try:
            print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 🔄 เริ่มดึง Reddit bulk...")
            print(f"   💡 ระบบทำงานต่อเนื่อง - ข้อมูลจะถูกบันทึกใน database อัตโนมัติ")
            
            valid_tickers = self._load_valid_tickers()
            print(f"   📋 Valid tickers loaded: {len(valid_tickers)} tickers")
            
            result = await self.processor.run_bulk_fetch(valid_tickers)
            
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ✅ Reddit bulk เสร็จ:")
            print(f"   📊 Posts ที่ดึงได้: {result['posts_fetched']}")
            print(f"   🔍 Posts ที่มี ticker: {result['posts_processed']}")
            print(f"   💬 Symbols ที่พบ: {result['symbols_found']}")
            print(f"   💾 Posts ที่บันทึก: {result['posts_saved']}")
            
            # ✅ แสดง warning ถ้าไม่มี posts ที่บันทึก
            if result['posts_fetched'] > 0 and result['posts_saved'] == 0:
                print(f"   ⚠️  WARNING: ดึงได้ {result['posts_fetched']} posts แต่ไม่มี ticker → ไม่บันทึก")
                print(f"   💡 ตรวจสอบว่า valid_tickers มีข้อมูลหรือไม่ และ posts มี ticker symbols หรือไม่")
            
            # ✅ แสดงจำนวน posts ทั้งหมดใน database
            try:
                from utils.post_normalizer import get_collection_name
                from database.db_config import db
                collection_name = get_collection_name('reddit')
                if db is not None and hasattr(db, collection_name):
                    post_collection = getattr(db, collection_name)
                    total_posts = post_collection.count_documents({})
                    print(f"   📚 จำนวน posts ทั้งหมดใน database: {total_posts:,}")
            except Exception:
                pass
            
            print(f"   ⏰ ครั้งถัดไปจะดึงในอีก 45 วินาที")
            
        except Exception as e:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ❌ Error ใน Reddit bulk: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # ✅ ตั้ง flag ว่า bulk fetch เสร็จแล้ว
            self._fetch_in_progress = False
    
    def _run_async(self):
        """รัน async function ใน thread"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._run_bulk_fetch())
        loop.close()
    
    def _scheduled_job(self):
        """Job ที่ schedule เรียก"""
        if self.is_running:
            # รันใน thread แยกเพื่อไม่ block
            thread = threading.Thread(target=self._run_async, daemon=True)
            thread.start()
    
    def start(self):
        """เริ่ม scheduler"""
        if self.is_running:
            print("⚠️  Reddit bulk scheduler กำลังรันอยู่แล้ว")
            return
        
        self.is_running = True
        
        # ✅ Schedule ทุก 45 วินาที (ลดความถี่เพื่อหลีกเลี่ยง rate limit)
        schedule.every(45).seconds.do(self._scheduled_job)
        
        print("✅ Reddit bulk scheduler เริ่มทำงาน (ทุก 45 วินาที)")
        
        # รัน job ครั้งแรกทันที
        self._scheduled_job()
        
        # รัน scheduler loop
        # ✅ ทำงานต่อเนื่องแม้ไม่มีผู้ใช้ใช้งาน (daemon thread)
        def run_scheduler():
            print(f"✅ Reddit bulk scheduler thread started - จะทำงานต่อเนื่องแม้ไม่มีผู้ใช้ใช้งาน")
            while self.is_running:
                try:
                    schedule.run_pending()
                    time.sleep(1)
                except Exception as e:
                    print(f"⚠️ Error in Reddit scheduler loop: {e}")
                    time.sleep(5)  # รอ 5 วินาทีแล้วลองใหม่
        
        self.thread = threading.Thread(target=run_scheduler, daemon=True)
        self.thread.start()
    
    def stop(self):
        """หยุด scheduler"""
        self.is_running = False
        schedule.clear()
        print("⏹️  Reddit bulk scheduler หยุดทำงาน")
    
    def run_once(self):
        """รัน bulk fetch ครั้งเดียว (ไม่ schedule)"""
        self._run_async()

# Global instance
reddit_bulk_scheduler = RedditBulkScheduler()
