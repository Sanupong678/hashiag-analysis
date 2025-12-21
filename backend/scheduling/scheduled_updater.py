"""
Scheduled Updater - อัปเดตข้อมูลหุ้นอัตโนมัติทุก 1-2 ชั่วโมง
"""
import schedule
import time
import threading
from datetime import datetime
from processors.batch_data_processor import batch_processor
from utils.stock_list_fetcher import stock_list_fetcher
import asyncio

class ScheduledUpdater:
    """
    จัดการการอัปเดตข้อมูลหุ้นแบบ scheduled
    """
    
    def __init__(self, update_interval_hours: float = 0.5):
        """
        Args:
            update_interval_hours: อัปเดตทุกกี่ชั่วโมง (รองรับทศนิยม เช่น 0.5 = 30 นาที)
        """
        self.update_interval_hours = update_interval_hours
        self.is_running = False
        self.update_thread = None
        self.initial_update_done = False  # ตรวจสอบว่าเคยรัน initial update แล้วหรือยัง
        self.last_update_time = None  # เก็บเวลาที่อัปเดตล่าสุด
    
    def _update_all_stocks(self):
        """
        อัปเดตข้อมูลหุ้นที่เก่ากว่า update_interval_hours (incremental update)
        รันใน background thread เพื่อไม่ block Flask app
        """
        # ✅ รันใน background thread แยก (ไม่ block Flask)
        def run_update_in_thread():
            print(f"\n🔄 Scheduled update (INCREMENTAL) started at {datetime.utcnow().isoformat()}")
            
            try:
                from database.db_config import db
                from datetime import timedelta
                
                # ✅ ตั้งค่าให้ใช้ Reddit จาก database เท่านั้น (Reddit bulk processor จะดึงมาให้)
                batch_processor.reddit_from_db_only = True
                batch_processor.skip_reddit = False  # ใช้ Reddit จาก DB
                
                # กรองหุ้นที่ต้องอัปเดต (เก่ากว่า 2 ชั่วโมง)
                print("📋 กำลังตรวจสอบหุ้นที่ต้องอัปเดต...")
                all_symbols = stock_list_fetcher.get_all_valid_tickers(force_refresh=False)
                
                if not all_symbols:
                    print("⚠️ No stock symbols found")
                    return
                
                # ✅ กรองหุ้นที่ต้องอัปเดต (เก่ากว่า update_interval_hours หรือยังไม่มีข้อมูล)
                # รองรับทศนิยม (เช่น 0.5 = 30 นาที)
                cutoff_time = datetime.utcnow() - timedelta(hours=self.update_interval_hours)
                stocks_to_update = []
                
                if db is not None and hasattr(db, 'stocks') and db.stocks is not None:
                    for symbol in all_symbols:
                        symbol_upper = symbol.upper()
                        latest = db.stocks.find_one(
                            {"symbol": symbol_upper},
                            sort=[("fetchedAt", -1)]
                        )
                        
                        if not latest:
                            # ยังไม่มีข้อมูล → ต้องดึง
                            stocks_to_update.append(symbol)
                        else:
                            # ตรวจสอบว่าเก่ากว่า 2 ชั่วโมงหรือไม่
                            fetched_at_str = latest.get('fetchedAt', '')
                            if isinstance(fetched_at_str, str):
                                try:
                                    fetched_at = datetime.fromisoformat(fetched_at_str.replace('Z', '+00:00'))
                                except:
                                    fetched_at = cutoff_time - timedelta(hours=1)  # ถ้า parse ไม่ได้ ให้ดึงใหม่
                            else:
                                fetched_at = fetched_at_str
                            
                            if fetched_at < cutoff_time:
                                stocks_to_update.append(symbol)
                else:
                    # ถ้าไม่มี database → ดึงทั้งหมด
                    stocks_to_update = list(all_symbols)
                
                if not stocks_to_update:
                    # ✅ แสดงเวลาที่ถูกต้อง (รองรับทศนิยม)
                    interval_display = f"{int(self.update_interval_hours * 60)} นาที" if self.update_interval_hours < 1 else f"{self.update_interval_hours} ชั่วโมง"
                    print(f"✅ ไม่มีหุ้นที่ต้องอัปเดต (ข้อมูลทั้งหมดใหม่กว่า {interval_display})")
                    return
                
                print(f"\n{'='*70}")
                # ✅ แสดงเวลาที่ถูกต้อง (รองรับทศนิยม)
                interval_display = f"{int(self.update_interval_hours * 60)} นาที" if self.update_interval_hours < 1 else f"{self.update_interval_hours} ชั่วโมง"
                print(f"📊 พบ {len(stocks_to_update):,} หุ้นที่ต้องอัปเดต (จากทั้งหมด {len(all_symbols):,} หุ้น)")
                print(f"   ⏰ หุ้นที่เก่ากว่า {interval_display}")
                print(f"   📰 คาดว่าจะใช้เวลา ~{len(stocks_to_update) * 0.05:.1f} นาที (ประมาณ 3 วินาทีต่อหุ้น)")
                print(f"   🔴 Reddit: ใช้จาก database เท่านั้น (Reddit bulk processor ดึงมาให้)")
                print(f"   🚀 รันใน background thread - Flask API ยังทำงานปกติ")
                print(f"{'='*70}\n")
                
                # ✅ แสดง progress bar จะเริ่มแสดงใน process_all_stocks_async
                # ประมวลผลเฉพาะหุ้นที่ต้องอัปเดต
                asyncio.run(
                    batch_processor.process_all_stocks_async(
                        stocks_to_update,
                        batch_size=50
                    )
                )
                
                # บันทึกเวลาที่อัปเดตเสร็จ
                self.last_update_time = datetime.utcnow()
                
                # บันทึกเวลาที่อัปเดตเสร็จ
                self.last_update_time = datetime.utcnow()
                
                print(f"\n" + "="*70)
                print("🎉 SCHEDULED UPDATE COMPLETED! 🎉")
                print("="*70)
                print(f"✅ Scheduled update (INCREMENTAL) completed at {self.last_update_time.isoformat()}")
                print(f"   📊 อัปเดต {len(stocks_to_update):,} หุ้น")
                # ✅ แสดงเวลาที่ถูกต้อง (รองรับทศนิยม)
                interval_display = f"{int(self.update_interval_hours * 60)} นาที" if self.update_interval_hours < 1 else f"{self.update_interval_hours} ชั่วโมง"
                print(f"   ⏰ ครั้งถัดไปจะอัปเดตในอีก {interval_display}")
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
                        subprocess.run(['say', 'Scheduled update completed!'])
                    elif sys.platform.startswith('linux'):
                        print('\a')
                except Exception:
                    pass
                
            except Exception as e:
                print(f"❌ Error in scheduled update: {e}")
                import traceback
                traceback.print_exc()
        
        # รันใน background thread (daemon=True เพื่อไม่ block main process)
        update_thread = threading.Thread(target=run_update_in_thread, daemon=True)
        update_thread.start()
        print(f"✅ Background update thread started (ไม่ block Flask API)")
    
    def _update_popular_stocks(self):
        """
        อัปเดตเฉพาะหุ้นยอดนิยม (เร็วกว่า)
        รันใน background thread เพื่อไม่ block Flask app
        """
        def run_popular_in_thread():
            print(f"\n🔄 Scheduled update (popular stocks) started at {datetime.utcnow().isoformat()}")
            
            try:
                # หุ้นยอดนิยม
                popular_symbols = [
                    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'AVGO', 'COST', 'NFLX',
                    'AMD', 'PEP', 'ADBE', 'CSCO', 'CMCSA', 'INTC', 'QCOM', 'INTU', 'AMGN', 'ISRG',
                    'BKNG', 'VRTX', 'REGN', 'AMAT', 'ADI', 'SNPS', 'CDNS', 'MELI', 'LRCX', 'KLAC'
                ]
                
                print(f"📊 Updating {len(popular_symbols)} popular stocks...")
                print(f"   🚀 รันใน background thread - Flask API ยังทำงานปกติ")
                
                # ประมวลผลแบบ batch
                asyncio.run(
                    batch_processor.process_all_stocks_async(
                        popular_symbols,
                        batch_size=50
                    )
                )
                
                print(f"✅ Scheduled update (popular stocks) completed at {datetime.utcnow().isoformat()}")
                
            except Exception as e:
                print(f"❌ Error in scheduled update: {e}")
                import traceback
                traceback.print_exc()
        
        # รันใน background thread
        update_thread = threading.Thread(target=run_popular_in_thread, daemon=True)
        update_thread.start()
        print(f"✅ Background popular stocks update thread started (ไม่ block Flask API)")
    
    def _run_scheduler(self):
        """
        รัน scheduler ใน background thread
        ✅ ทำงานต่อเนื่องแม้ไม่มีผู้ใช้ใช้งาน (daemon thread)
        """
        print(f"✅ Scheduler thread started - จะทำงานต่อเนื่องแม้ไม่มีผู้ใช้ใช้งาน")
        while self.is_running:
            try:
                schedule.run_pending()
                time.sleep(60)  # ตรวจสอบทุก 1 นาที
            except Exception as e:
                print(f"⚠️ Error in scheduler loop: {e}")
                time.sleep(60)  # รอ 1 นาทีแล้วลองใหม่
    
    def start(self, run_initial_update: bool = True):
        """
        เริ่ม scheduled updates
        
        Args:
            run_initial_update: ถ้า True จะรัน initial update ทันที (default: True)
                              ถ้า False จะไม่รัน initial update (ใช้เมื่อ restart)
        """
        if self.is_running:
            print("⚠️ Scheduler is already running")
            return
        
        # ✅ ตั้งค่า last_update_time ตอนเริ่มต้น (ถ้ายังไม่มี) เพื่อให้คำนวณเวลาที่เหลือได้ถูกต้อง
        if self.last_update_time is None:
            # ใช้เวลาปัจจุบันลบ interval เพื่อให้คำนวณได้ถูกต้อง
            # หรือจะใช้เวลาปัจจุบันก็ได้ (จะแสดงเวลาที่เหลือ = interval)
            from datetime import timedelta
            self.last_update_time = datetime.utcnow() - timedelta(hours=self.update_interval_hours)
        
        # ✅ แสดงเวลาที่ถูกต้อง (รองรับทศนิยม)
        interval_display = f"{int(self.update_interval_hours * 60)} นาที" if self.update_interval_hours < 1 else f"{self.update_interval_hours} ชั่วโมง"
        print(f"🚀 Starting scheduled updater (every {interval_display})...")
        
        # กำหนด schedule - ใช้ _update_all_stocks เพื่อดึงหุ้นทั้งหมด (4000+ ตัว)
        # แต่ใช้ batch_size เล็กกว่าเพื่อไม่ให้ใช้เวลานานเกินไป
        # ✅ รองรับทศนิยม (เช่น 0.5 = 30 นาที)
        if self.update_interval_hours < 1:
            # ถ้าน้อยกว่า 1 ชั่วโมง ให้ใช้ minutes
            schedule.every(int(self.update_interval_hours * 60)).minutes.do(self._update_all_stocks)
        else:
            # ถ้ามากกว่าหรือเท่ากับ 1 ชั่วโมง ให้ใช้ hours
            schedule.every(self.update_interval_hours).hours.do(self._update_all_stocks)
        
        # อัปเดตครั้งแรกทันที - ดึงหุ้นทั้งหมด (เฉพาะถ้ายังไม่เคยรัน)
        # ✅ รันใน background thread เพื่อไม่ block Flask app
        if run_initial_update and not self.initial_update_done:
            # ตรวจสอบว่ามีข้อมูลใน database หรือยัง
            from database.db_config import db
            has_data = False
            if db is not None and hasattr(db, 'stocks') and db.stocks is not None:
                stock_count = db.stocks.count_documents({})
                if stock_count > 0:
                    has_data = True
            
            if not has_data:
                print("🔄 Running initial update (all stocks) in background thread...")
                print("   🚀 Flask API ยังทำงานปกติ - ไม่ถูก block")
                # บันทึกเวลาที่เริ่ม initial update
                self.last_update_time = datetime.utcnow()
                self._update_all_stocks()  # รันใน background thread แล้ว
                self.initial_update_done = True
            else:
                print("✅ มีข้อมูลใน database แล้ว - ข้าม initial update")
                self.initial_update_done = True
        elif not run_initial_update:
            print("⏭️  ข้าม initial update (restart mode)")
        
        # เริ่ม scheduler thread
        self.is_running = True
        self.update_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.update_thread.start()
        
        print("✅ Scheduled updater started")
    
    def get_next_update_time(self):
        """
        คำนวณเวลาที่จะอัปเดตครั้งถัดไป (คำนวณใหม่ทุกครั้งที่เรียก)
        
        Returns:
            dict: {
                "next_update_time": ISO format string หรือ None,
                "remaining_minutes": จำนวนนาทีที่เหลือ,
                "remaining_seconds": จำนวนวินาทีที่เหลือ,
                "remaining_hours": จำนวนชั่วโมงที่เหลือ,
                "formatted": "X ชั่วโมง Y นาที" หรือ "X นาที"
            }
        """
        try:
            from datetime import timedelta
            
            now = datetime.utcnow()  # ✅ คำนวณเวลาปัจจุบันใหม่ทุกครั้ง
            
            # ✅ วิธีที่ 1: ใช้ schedule.get_jobs() เพื่อหา next_run time
            try:
                jobs = schedule.get_jobs()
                next_run = None
                for job in jobs:
                    # ตรวจสอบว่าเป็น job ของ _update_all_stocks หรือไม่
                    if hasattr(job, 'job_func') and job.job_func == self._update_all_stocks:
                        if hasattr(job, 'next_run'):
                            next_run = job.next_run
                            break
                
                if next_run:
                    # ถ้า next_run เป็น datetime object
                    if isinstance(next_run, datetime):
                        remaining = next_run - now
                    else:
                        # ถ้าเป็น string ให้ parse
                        try:
                            next_run_dt = datetime.fromisoformat(str(next_run).replace('Z', '+00:00'))
                            remaining = next_run_dt - now
                        except:
                            # ถ้า parse ไม่ได้ ให้ใช้ last_update_time + interval
                            if self.last_update_time:
                                # ✅ รองรับทศนิยม (เช่น 0.5 = 30 นาที)
                                next_update = self.last_update_time + timedelta(hours=self.update_interval_hours)
                                remaining = next_update - now
                            else:
                                # ✅ ถ้ายังไม่เคยอัปเดต ให้คำนวณจากเวลาปัจจุบัน + interval
                                next_update = now + timedelta(hours=self.update_interval_hours)
                                remaining = next_update - now
                else:
                    # ถ้าไม่มี job ให้คำนวณจาก last_update_time
                    if self.last_update_time:
                        next_update = self.last_update_time + timedelta(hours=self.update_interval_hours)
                        remaining = next_update - now
                    else:
                        # ✅ ถ้ายังไม่เคยอัปเดต ให้คำนวณจากเวลาปัจจุบัน + interval
                        # เพื่อให้เวลาที่เหลือลดลงตามเวลาจริง
                        next_update = now + timedelta(hours=self.update_interval_hours)
                        remaining = next_update - now
            except Exception as e:
                # ถ้า schedule.get_jobs() ไม่ทำงาน ให้ใช้ last_update_time
                if self.last_update_time:
                    # ✅ รองรับทศนิยม (เช่น 0.5 = 30 นาที)
                    next_update = self.last_update_time + timedelta(hours=self.update_interval_hours)
                    remaining = next_update - now
                else:
                    # ✅ ถ้ายังไม่เคยอัปเดต ให้คำนวณจากเวลาปัจจุบัน + interval
                    next_update = now + timedelta(hours=self.update_interval_hours)
                    remaining = next_update - now
            
            # ✅ คำนวณเวลาที่เหลือ (ใช้ max(0, ...) เพื่อไม่ให้เป็นลบ)
            remaining_seconds = max(0, int(remaining.total_seconds()))
            remaining_minutes = remaining_seconds // 60
            remaining_hours = remaining_minutes // 60
            
            # ✅ ถ้าเวลาที่เหลือเป็นลบ (เกินเวลาแล้ว) ให้คำนวณใหม่จาก last_update_time
            if remaining_seconds < 0:
                if self.last_update_time:
                    next_update = self.last_update_time + timedelta(hours=self.update_interval_hours)
                    remaining = next_update - now
                    remaining_seconds = max(0, int(remaining.total_seconds()))
                    remaining_minutes = remaining_seconds // 60
                    remaining_hours = remaining_minutes // 60
                else:
                    # ✅ ถ้ายังไม่เคยอัปเดต ให้คำนวณจากเวลาปัจจุบัน + interval
                    next_update = now + timedelta(hours=self.update_interval_hours)
                    remaining = next_update - now
                    remaining_seconds = max(0, int(remaining.total_seconds()))
                    remaining_minutes = remaining_seconds // 60
                    remaining_hours = remaining_minutes // 60
            
            # ✅ คำนวณ next_update_time (ใช้ now ที่คำนวณไว้แล้วตอนต้น)
            next_update_time = now + remaining
            
            # Format ข้อความ (แสดงวินาทีเมื่อเหลือน้อยกว่า 1 นาที)
            if remaining_hours > 0:
                mins = remaining_minutes % 60
                if mins > 0:
                    formatted = f"{remaining_hours} ชั่วโมง {mins} นาที"
                else:
                    formatted = f"{remaining_hours} ชั่วโมง"
            elif remaining_minutes > 0:
                # แสดงวินาทีเมื่อเหลือน้อยกว่า 5 นาที
                if remaining_minutes < 5:
                    secs = remaining_seconds % 60
                    if secs > 0:
                        formatted = f"{remaining_minutes} นาที {secs} วินาที"
                    else:
                        formatted = f"{remaining_minutes} นาที"
                else:
                    formatted = f"{remaining_minutes} นาที"
            elif remaining_seconds > 0:
                formatted = f"{remaining_seconds} วินาที"
            else:
                formatted = "0 วินาที"  # กำลังอัปเดต
            
            return {
                "next_update_time": next_update_time.isoformat(),
                "remaining_minutes": remaining_minutes,
                "remaining_seconds": remaining_seconds,
                "remaining_hours": remaining_hours,
                "formatted": formatted
            }
        except Exception as e:
            print(f"⚠️ Error calculating next update time: {e}")
            import traceback
            traceback.print_exc()
            return {
                "next_update_time": None,
                "remaining_minutes": None,
                "remaining_seconds": None,
                "remaining_hours": None,
                "formatted": "ยังไม่ทราบ"
            }
    
    def stop(self):
        """
        หยุด scheduled updates
        """
        if not self.is_running:
            return
        
        print("🛑 Stopping scheduled updater...")
        self.is_running = False
        schedule.clear()
        
        if self.update_thread:
            self.update_thread.join(timeout=5)
        
        print("✅ Scheduled updater stopped")
    
    def run_manual_update(self, all_stocks: bool = False):
        """
        รันการอัปเดตด้วยตนเอง (รันใน background thread)
        
        Args:
            all_stocks: True = อัปเดตทั้งหมด, False = อัปเดตเฉพาะหุ้นยอดนิยม
        """
        # ✅ รันใน background thread เพื่อไม่ block Flask API
        def run_manual_in_thread():
            if all_stocks:
                self._update_all_stocks()
            else:
                self._update_popular_stocks()
        
        update_thread = threading.Thread(target=run_manual_in_thread, daemon=True)
        update_thread.start()
        print(f"✅ Manual update thread started (ไม่ block Flask API)")


# Global instance
# ✅ เปลี่ยนเป็น 30 นาที (0.5 ชั่วโมง) แทน 2 ชั่วโมง
scheduled_updater = ScheduledUpdater(update_interval_hours=0.5)

