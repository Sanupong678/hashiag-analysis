from pymongo import MongoClient
import sys

# ตั้งค่า encoding สำหรับ Windows console
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except (AttributeError, ValueError):
        # Python < 3.7 หรือ encoding ไม่รองรับ
        pass

MONGO_URI = "mongodb+srv://database:Tum0979359145@cluster0.0buwikd.mongodb.net/"

try:
    client = MongoClient(MONGO_URI, tls=True, tlsAllowInvalidCertificates=True)
    db = client["reddit_analytics"]
    client.admin.command("ping")
    print("✅ MongoDB connected successfully!")
except Exception as e:
    print("❌ MongoDB connection failed:", e)
    db = None  # กันไว้กรณีเชื่อมไม่ได้
