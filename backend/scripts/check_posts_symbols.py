#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
สคริปต์ตรวจสอบและแสดงข้อมูลเกี่ยวกับ symbols ใน posts
"""
import sys
import os

# เพิ่ม path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db_config import db
from utils.post_normalizer import get_collection_name
import re

def check_posts_symbols():
    """ตรวจสอบว่า posts มี symbols หรือไม่"""
    
    if db is None:
        print("❌ Database not connected")
        return
    
    # ตรวจสอบ post_reddit
    reddit_collection_name = get_collection_name('reddit')
    if hasattr(db, reddit_collection_name):
        reddit_collection = getattr(db, reddit_collection_name)
        total_reddit = reddit_collection.count_documents({})
        
        # นับ posts ที่มี symbols field
        posts_with_symbols = reddit_collection.count_documents({"symbols": {"$exists": True, "$ne": []}})
        posts_with_symbol = reddit_collection.count_documents({"symbol": {"$exists": True, "$ne": None}})
        
        print(f"\n📊 Reddit Posts ({reddit_collection_name}):")
        print(f"   Total posts: {total_reddit:,}")
        print(f"   Posts with 'symbols' field: {posts_with_symbols:,} ({posts_with_symbols/total_reddit*100:.1f}%)")
        print(f"   Posts with 'symbol' field: {posts_with_symbol:,} ({posts_with_symbol/total_reddit*100:.1f}%)")
        
        # ตัวอย่าง posts ที่มี symbols
        if posts_with_symbols > 0:
            sample = reddit_collection.find_one({"symbols": {"$exists": True, "$ne": []}})
            if sample:
                print(f"   Sample symbols: {sample.get('symbols', [])[:5]}")
        
        # ตัวอย่าง posts ที่ไม่มี symbols
        sample_no_symbols = reddit_collection.find_one({"symbols": {"$exists": False}})
        if sample_no_symbols:
            print(f"   Sample post without symbols: {list(sample_no_symbols.keys())[:10]}")
            # ตรวจสอบว่ามี text ที่มี $SYMBOL หรือไม่
            text = f"{sample_no_symbols.get('title', '')} {sample_no_symbols.get('selftext', '')}"
            ticker_pattern = re.compile(r'\$([A-Z]{1,5})\b')
            tickers_in_text = ticker_pattern.findall(text.upper())
            if tickers_in_text:
                print(f"   Found tickers in text: {tickers_in_text[:5]}")
    
    # ตรวจสอบ post_yahoo
    yahoo_collection_name = get_collection_name('yahoo')
    if hasattr(db, yahoo_collection_name):
        yahoo_collection = getattr(db, yahoo_collection_name)
        total_yahoo = yahoo_collection.count_documents({})
        
        # นับ posts ที่มี symbol field
        posts_with_symbol = yahoo_collection.count_documents({"symbol": {"$exists": True, "$ne": None}})
        
        print(f"\n📊 Yahoo Posts ({yahoo_collection_name}):")
        print(f"   Total posts: {total_yahoo:,}")
        print(f"   Posts with 'symbol' field: {posts_with_symbol:,} ({posts_with_symbol/total_yahoo*100:.1f}%)")
        
        # ตัวอย่าง posts ที่มี symbol
        if posts_with_symbol > 0:
            sample = yahoo_collection.find_one({"symbol": {"$exists": True, "$ne": None}})
            if sample:
                print(f"   Sample symbol: {sample.get('symbol')}")
    
    print("\n💡 คำแนะนำ:")
    print("   - ถ้า posts ไม่มี 'symbols' field → ข้อมูลเก่าที่ถูกบันทึกก่อนการ extract symbols")
    print("   - Scheduled updater จะ extract symbols อัตโนมัติเมื่อดึงข้อมูลใหม่")
    print("   - หรือใช้ real-time mode เพื่อดูข้อมูลจาก stocks collection ที่ถูก aggregate แล้ว")

if __name__ == "__main__":
    check_posts_symbols()
