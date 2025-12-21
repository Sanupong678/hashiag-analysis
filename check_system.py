#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
สคริปต์ตรวจสอบสถานะระบบ
"""
import sys
import os
import io

# ตั้งค่า encoding สำหรับ Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# เพิ่ม path สำหรับ import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

print("=" * 60)
print("[CHECK] กำลังตรวจสอบระบบ...")
print("=" * 60)

# 1. ตรวจสอบการเชื่อมต่อ Database
print("\n[1] ตรวจสอบการเชื่อมต่อ Database...")
try:
    from database.db_config import db
    if db is not None:
        # Test connection
        db.client.admin.command('ping')
        print("   [OK] Database: เชื่อมต่อสำเร็จ")
        print(f"   [INFO] Database name: {db.name}")
        
        # ตรวจสอบ collections
        collections = db.list_collection_names()
        print(f"   [INFO] Collections: {len(collections)} collections")
        if collections:
            print(f"      - {', '.join(collections[:10])}")
            if len(collections) > 10:
                print(f"      - ... และอีก {len(collections) - 10} collections")
        
        # ตรวจสอบข้อมูลใน collections หลัก
        print("\n   [INFO] ตรวจสอบข้อมูลใน Database:")
        
        # post_reddit
        try:
            from utils.post_normalizer import get_collection_name
            reddit_collection = get_collection_name('reddit')
            if hasattr(db, reddit_collection):
                reddit_count = getattr(db, reddit_collection).count_documents({})
                print(f"      - {reddit_collection}: {reddit_count:,} documents")
            else:
                print(f"      - {reddit_collection}: ไม่พบ collection")
        except Exception as e:
            print(f"      - post_reddit: ไม่สามารถตรวจสอบได้ ({e})")
        
        # post_yahoo
        try:
            yahoo_collection = get_collection_name('yahoo')
            if hasattr(db, yahoo_collection):
                yahoo_count = getattr(db, yahoo_collection).count_documents({})
                print(f"      - {yahoo_collection}: {yahoo_count:,} documents")
            else:
                print(f"      - {yahoo_collection}: ไม่พบ collection")
        except Exception as e:
            print(f"      - post_yahoo: ไม่สามารถตรวจสอบได้ ({e})")
        
        # stocks collection
        if hasattr(db, 'stocks') and db.stocks is not None:
            stocks_count = db.stocks.count_documents({})
            print(f"      - stocks: {stocks_count:,} documents")
        else:
            print(f"      - stocks: ไม่พบ collection")
        
        # stock_data collection
        if hasattr(db, 'stock_data') and db.stock_data is not None:
            stock_data_count = db.stock_data.count_documents({})
            print(f"      - stock_data: {stock_data_count:,} documents")
        else:
            print(f"      - stock_data: ไม่พบ collection")
        
    else:
        print("   [ERROR] Database: ไม่สามารถเชื่อมต่อได้")
except Exception as e:
    print(f"   [ERROR] Database: เกิดข้อผิดพลาด - {e}")

# 2. ตรวจสอบ Backend API
print("\n[2] ตรวจสอบ Backend API...")
try:
    import requests
    try:
        response = requests.get('http://localhost:5000/api/batch/status', timeout=5)
        if response.status_code == 200:
            data = response.json()
            print("   [OK] Backend API: ทำงานอยู่")
            print(f"   [INFO] Total stocks: {data.get('total_stocks', 0):,}")
            print(f"   [INFO] Latest update: {data.get('latest_update', 'N/A')}")
        else:
            print(f"   [WARNING] Backend API: ตอบกลับด้วย status {response.status_code}")
    except requests.exceptions.ConnectionError:
        print("   [ERROR] Backend API: ไม่สามารถเชื่อมต่อได้ (server อาจยังไม่รัน)")
        print("   [TIP] วิธีแก้: รันคำสั่ง 'cd backend && python app.py'")
    except requests.exceptions.Timeout:
        print("   [WARNING] Backend API: ใช้เวลาตอบกลับนานเกินไป")
except ImportError:
    print("   [WARNING] Backend API: ไม่สามารถตรวจสอบได้ (requests library ไม่พบ)")
except Exception as e:
    print(f"   [ERROR] Backend API: เกิดข้อผิดพลาด - {e}")

# 3. ตรวจสอบ Frontend
print("\n[3] ตรวจสอบ Frontend...")
frontend_path = os.path.join(os.path.dirname(__file__), 'frontend', 'index.html')
if os.path.exists(frontend_path):
    print("   [OK] Frontend: พบไฟล์ index.html")
    print(f"   [INFO] Path: {frontend_path}")
else:
    print("   [ERROR] Frontend: ไม่พบไฟล์ index.html")

# 4. ตรวจสอบ Environment Variables
print("\n[4] ตรวจสอบ Environment Variables...")
env_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(env_path):
    print("   [OK] .env file: พบไฟล์")
    with open(env_path, 'r', encoding='utf-8') as f:
        env_content = f.read()
        if 'REDDIT_CLIENT_ID' in env_content:
            print("   [OK] REDDIT_CLIENT_ID: ตั้งค่าแล้ว")
        else:
            print("   [WARNING] REDDIT_CLIENT_ID: ยังไม่ได้ตั้งค่า")
        
        if 'MONGO_URI' in env_content:
            print("   [OK] MONGO_URI: ตั้งค่าแล้ว")
        else:
            print("   [INFO] MONGO_URI: ยังไม่ได้ตั้งค่า (ใช้จาก db_config.py)")
        
        if 'NEWS_API_KEY' in env_content:
            print("   [OK] NEWS_API_KEY: ตั้งค่าแล้ว")
        else:
            print("   [WARNING] NEWS_API_KEY: ยังไม่ได้ตั้งค่า")
else:
    print("   [WARNING] .env file: ไม่พบไฟล์ (อาจใช้ค่า default)")

# 5. สรุป
print("\n" + "=" * 60)
print("[SUMMARY] สรุปผลการตรวจสอบ:")
print("=" * 60)
print("\n[TIPS] คำแนะนำ:")
print("   1. ถ้า Database เชื่อมต่อได้ -> ระบบพร้อมใช้งาน")
print("   2. ถ้า Backend API ไม่ทำงาน -> รัน 'cd backend && python app.py'")
print("   3. ถ้ายังไม่มีข้อมูล -> ใช้ API endpoint '/api/batch/fetch-news' เพื่อดึงข้อมูล")
print("   4. เปิด Frontend -> เปิดไฟล์ 'frontend/index.html' ในเบราว์เซอร์")
print("\n" + "=" * 60)
