"""
Script สำหรับลบข้อมูลเก่าใน collection เก่า (db.posts, db.news)
เพื่อเตรียมเก็บข้อมูลใหม่ใน collection ใหม่ (post_reddit, post_yahoo)
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

def cleanup_old_collections():
    """ลบข้อมูลเก่าใน collection เก่า"""
    try:
        print("\n" + "="*70)
        print("🗑️  ลบข้อมูลเก่าใน Collection เก่า")
        print("="*70)
        
        if db is None:
            print("❌ Database not available")
            return
        
        # 1. ลบข้อมูลใน db.posts (จะย้ายไป post_reddit)
        if hasattr(db, 'posts') and db.posts is not None:
            count_posts = db.posts.count_documents({})
            if count_posts > 0:
                print(f"\n📊 พบข้อมูลใน db.posts: {count_posts:,} documents")
                confirm = input("⚠️  คุณแน่ใจหรือไม่ว่าต้องการลบข้อมูลทั้งหมด? (yes/no): ")
                if confirm.lower() == 'yes':
                    result = db.posts.delete_many({})
                    print(f"✅ ลบข้อมูลใน db.posts เรียบร้อย: {result.deleted_count:,} documents")
                else:
                    print("❌ ยกเลิกการลบข้อมูลใน db.posts")
            else:
                print("ℹ️  ไม่มีข้อมูลใน db.posts")
        else:
            print("ℹ️  Collection db.posts ไม่มีอยู่")
        
        # 2. ลบข้อมูลใน db.news (จะย้ายไป post_yahoo)
        if hasattr(db, 'news') and db.news is not None:
            count_news = db.news.count_documents({})
            if count_news > 0:
                print(f"\n📊 พบข้อมูลใน db.news: {count_news:,} documents")
                confirm = input("⚠️  คุณแน่ใจหรือไม่ว่าต้องการลบข้อมูลทั้งหมด? (yes/no): ")
                if confirm.lower() == 'yes':
                    result = db.news.delete_many({})
                    print(f"✅ ลบข้อมูลใน db.news เรียบร้อย: {result.deleted_count:,} documents")
                else:
                    print("❌ ยกเลิกการลบข้อมูลใน db.news")
            else:
                print("ℹ️  ไม่มีข้อมูลใน db.news")
        else:
            print("ℹ️  Collection db.news ไม่มีอยู่")
        
        # 3. ลบข้อมูลใน db.reddit_posts (ถ้ามี)
        if hasattr(db, 'reddit_posts') and db.reddit_posts is not None:
            count_reddit = db.reddit_posts.count_documents({})
            if count_reddit > 0:
                print(f"\n📊 พบข้อมูลใน db.reddit_posts: {count_reddit:,} documents")
                confirm = input("⚠️  คุณแน่ใจหรือไม่ว่าต้องการลบข้อมูลทั้งหมด? (yes/no): ")
                if confirm.lower() == 'yes':
                    result = db.reddit_posts.delete_many({})
                    print(f"✅ ลบข้อมูลใน db.reddit_posts เรียบร้อย: {result.deleted_count:,} documents")
                else:
                    print("❌ ยกเลิกการลบข้อมูลใน db.reddit_posts")
            else:
                print("ℹ️  ไม่มีข้อมูลใน db.reddit_posts")
        else:
            print("ℹ️  Collection db.reddit_posts ไม่มีอยู่")
        
        print(f"\n{'='*70}")
        print(f"✅ เสร็จสิ้น - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70 + "\n")
        print("💡 ข้อมูลใหม่จะถูกเก็บใน collection ใหม่:")
        print("   - post_reddit (Reddit posts)")
        print("   - post_yahoo (Yahoo Finance news)")
        print("   - post_x (Twitter/X posts)")
        print("   - post_youtube (YouTube posts)")
        print("   - post_news (News API posts)")
        print()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    cleanup_old_collections()

