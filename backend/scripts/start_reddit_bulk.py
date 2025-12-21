"""
Script สำหรับเริ่ม Reddit Bulk Scheduler
รัน Reddit bulk fetch ทุก 45 วินาที
"""
import sys
import os
from pathlib import Path

# เพิ่ม path ของ backend
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from scheduling.reddit_bulk_scheduler import reddit_bulk_scheduler
import time

def main():
    """เริ่ม Reddit bulk scheduler"""
    print("\n" + "="*70)
    print("🚀 เริ่ม Reddit Bulk Scheduler")
    print("="*70)
    print("\n📋 การตั้งค่า:")
    print("   ⏰ อัปเดตทุก 45 วินาที")
    print("   📊 Subreddits: wallstreetbets, stocks, investing, options, pennystocks")
    print("   🔍 Extract tickers จาก posts")
    print("   💬 วิเคราะห์ sentiment ครั้งเดียวต่อ post")
    print("\n💡 กด Ctrl+C เพื่อหยุด\n")
    
    try:
        # เริ่ม scheduler
        reddit_bulk_scheduler.start()
        
        # รอจนกว่าจะถูก interrupt
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\n⏹️  กำลังหยุด Reddit bulk scheduler...")
        reddit_bulk_scheduler.stop()
        print("✅ หยุดแล้ว\n")

if __name__ == "__main__":
    main()
