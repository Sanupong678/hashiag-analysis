"""
Script เพื่อสร้าง comment_reddit collection ทันที
"""
from database.db_config import db
from database.db_schema import initialize_collections

if __name__ == "__main__":
    print("🔄 Creating comment_reddit collection...")
    
    if db is None:
        print("❌ Database connection not available")
        exit(1)
    
    # Initialize collections (จะสร้าง comment_reddit ด้วย)
    initialize_collections(db)
    
    # ตรวจสอบว่า collection ถูกสร้างแล้วหรือไม่
    collections = db.list_collection_names()
    if "comment_reddit" in collections:
        print("✅ comment_reddit collection created successfully!")
        print(f"   Collections in database: {', '.join(collections)}")
    else:
        print("❌ comment_reddit collection not found!")
        print(f"   Available collections: {', '.join(collections)}")
        
        # ลองสร้างใหม่
        try:
            db.create_collection("comment_reddit")
            db.comment_reddit.create_index("id", unique=True)
            db.comment_reddit.create_index("post_id")
            db.comment_reddit.create_index("created_utc")
            db.comment_reddit.create_index("author")
            db.comment_reddit.create_index("symbols")
            db.comment_reddit.create_index([("post_id", 1), ("created_utc", -1)])
            print("✅ Manually created comment_reddit collection with indexes")
        except Exception as e:
            print(f"❌ Error creating collection: {e}")

