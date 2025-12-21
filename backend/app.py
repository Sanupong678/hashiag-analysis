from flask import Flask, jsonify, request, Response
from database.db_config import db
from fetchers.fetch_reddit import fetch_posts
from bson.json_util import dumps
from flask_cors import CORS
from dotenv import load_dotenv
from pymongo.errors import OperationFailure
import os
import random
import pandas as pd
from datetime import datetime, timedelta
from processors.data_aggregator import DataAggregator
from fetchers.stock_data import StockDataFetcher
from processors.sentiment_analyzer import SentimentAnalyzer
from database.db_schema import initialize_collections
from utils.ticker_validator import ticker_validator
from utils.retry_handler import retry_on_failure
from utils.stock_list_fetcher import stock_list_fetcher
from processors.batch_data_processor import batch_processor
from scheduling.scheduled_updater import scheduled_updater
from scheduling.reddit_bulk_scheduler import reddit_bulk_scheduler
import schedule
import threading
import time
import yfinance as yf
import asyncio

# โหลด environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

# กำหนด path สำหรับเก็บไฟล์ Excel
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_PATH = os.path.join(BASE_DIR, "data", "process")
RAW_PATH = os.path.join(BASE_DIR, "data", "row")

os.makedirs(DOWNLOAD_PATH, exist_ok=True)
os.makedirs(RAW_PATH, exist_ok=True)

# สร้าง Flask app
app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": ["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5500"]}})

# Initialize services
data_aggregator = DataAggregator()
stock_fetcher = StockDataFetcher()
sentiment_analyzer = SentimentAnalyzer()

# Setup database indexes for performance
def setup_database_indexes():
    """Create indexes for frequently queried fields"""
    try:
        if db is not None:
            from utils.post_normalizer import get_collection_name
            
            def safe_create_index(collection, index_spec, index_name=None, unique=False):
                """Safely create index, handling conflicts with existing indexes"""
                try:
                    if index_name:
                        collection.create_index(index_spec, name=index_name, background=True, unique=unique)
                    else:
                        collection.create_index(index_spec, background=True, unique=unique)
                except OperationFailure as idx_err:
                    # Handle index conflict errors
                    # Code 85: IndexOptionsConflict - index exists with different name but same fields
                    # Code 86: IndexKeySpecsConflict - index exists with same name but different options
                    if idx_err.code in [85, 86]:
                        # Index already exists (with same or different name/options) - this is OK
                        # Silently ignore, the index functionality is already there
                        pass
                    else:
                        # Only show error if it's not a conflict error
                        print(f"  ⚠️  Error creating index: {idx_err}")
                except Exception as idx_err:
                    # Handle other index errors (fallback for non-OperationFailure exceptions)
                    error_code = getattr(idx_err, 'code', None)
                    error_msg = str(idx_err).lower()
                    # Check for conflict errors in error message too
                    if error_code in [85, 86] or 'indexoptionsconflict' in error_msg or 'indexkeyspecsconflict' in error_msg:
                        # Index already exists, ignore silently
                        pass
                    else:
                        print(f"  ⚠️  Error creating index: {idx_err}")
            
            # Indexes for post_reddit collection
            reddit_collection = get_collection_name('reddit')
            if hasattr(db, reddit_collection):
                collection = getattr(db, reddit_collection)
                safe_create_index(collection, [("keyword", 1), ("created_utc", -1)])
                safe_create_index(collection, [("symbol", 1), ("created_utc", -1)])
                safe_create_index(collection, [("symbols", 1), ("created_utc", -1)])  # ใหม่: สำหรับ symbols array
                safe_create_index(collection, "created_utc")
                safe_create_index(collection, "id", unique=True)  # id should be unique
            
            # Indexes for post_yahoo collection
            yahoo_collection = get_collection_name('yahoo')
            if hasattr(db, yahoo_collection):
                collection = getattr(db, yahoo_collection)
                safe_create_index(collection, [("symbol", 1), ("created_utc", -1)])
                safe_create_index(collection, "created_utc")
                safe_create_index(collection, "newsHash")
                safe_create_index(collection, "id", unique=True)  # id should be unique
            
            print("✅ Database indexes setup completed")
    except Exception as e:
        print(f"⚠️ Error setting up indexes: {e}")

# Initialize indexes on startup
setup_database_indexes()

# Initialize stock list fetcher and load tickers on startup
def initialize_stock_list():
    """โหลดรายชื่อหุ้นทั้งหมดจาก Yahoo Finance เมื่อเริ่มต้นแอป"""
    try:
        print("📊 Initializing stock list from Yahoo Finance...")
        # โหลดรายชื่อหุ้น (จะใช้ cache จาก database ถ้ามี)
        tickers = stock_list_fetcher.get_all_valid_tickers(force_refresh=False)
        if tickers:
            print(f"✅ Loaded {len(tickers)} valid stock tickers")
        else:
            print("⚠️ No tickers loaded, will use fallback list")
    except Exception as e:
        print(f"⚠️ Error initializing stock list: {e}")

# Initialize stock list on startup (run in background to not block)
import threading
stock_list_thread = threading.Thread(target=initialize_stock_list, daemon=True)
stock_list_thread.start()

# ฟังก์ชันช่วย serialize MongoDB documents
def serialize_doc(doc):
    doc["_id"] = str(doc["_id"])
    return doc


def export_posts_to_excel(posts, keyword, output_dir):
    if not posts:
        return None

    df = pd.DataFrame(posts)
    if "_id" in df.columns:
        df["_id"] = df["_id"].astype(str)

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    file_name = f"{keyword}_{timestamp}.xlsx"
    file_path = os.path.join(output_dir, file_name)
    df.to_excel(file_path, index=False)
    return file_path


def export_keyword_from_db(keyword, output_dir):
    from utils.post_normalizer import get_collection_name
    collection_name = get_collection_name('reddit')
    if hasattr(db, collection_name):
        post_collection = getattr(db, collection_name)
        posts = list(post_collection.find({"keyword": keyword}))
        return export_posts_to_excel(posts, keyword, output_dir)
    return None


# ==========================
# Route: Download Excel
# ==========================
@app.route("/api/download")
def download_data():
    from utils.post_normalizer import get_collection_name
    keyword = request.args.get("keyword", "AI")
    collection_name = get_collection_name('reddit')
    if hasattr(db, collection_name):
        post_collection = getattr(db, collection_name)
        posts_cursor = post_collection.find({"keyword": keyword})
        posts = list(posts_cursor)
    else:
        posts = []
    if not posts:
        return jsonify({"error": "No data found"}), 404

    # แปลงเป็น DataFrame
    df = pd.DataFrame(posts)
    if "_id" in df.columns:
        df["_id"] = df["_id"].astype(str)
    file_name = f"{keyword}_posts.xlsx"
    file_path = os.path.join(DOWNLOAD_PATH, file_name)
    df.to_excel(file_path, index=False)

    return jsonify({"message": f"File saved at {file_path}"})

# ==========================
# Route: Trending Hashtags
# ==========================
@app.route("/api/hashtags")
def get_hashtags():
    keyword = request.args.get("keyword", "AI")
    print(f"🔍 Fetching posts for keyword: {keyword}")
    try:
        fetch_posts(keyword, limit=50)
    except Exception as e:
        print(f"⚠️ Error fetching posts: {e}")

    from utils.post_normalizer import get_collection_name
    collection_name = get_collection_name('reddit')
    if hasattr(db, collection_name):
        post_collection = getattr(db, collection_name)
        pipeline = [
            {"$match": {"keyword": keyword}},
            {"$group": {"_id": "$keyword", "count": {"$sum": 1}}}
        ]
        result = list(post_collection.aggregate(pipeline))
        posts = [serialize_doc(p) for p in post_collection.find({"keyword": keyword}).sort("score", -1).limit(10)]
    else:
        result = []
        posts = []

    try:
        export_keyword_from_db(keyword, RAW_PATH)
    except Exception as export_err:
        print(f"⚠️ Failed to export keyword '{keyword}' to Excel: {export_err}")

    return jsonify({"trends": result, "posts": posts})

# ==========================
# Route: Recent Posts
# ==========================
@app.route("/api/posts")
def get_posts():
    from utils.post_normalizer import get_collection_name
    collection_name = get_collection_name('reddit')
    if hasattr(db, collection_name):
        post_collection = getattr(db, collection_name)
        posts = list(post_collection.find().sort("created_utc", -1).limit(50))
        return dumps(posts)
    return dumps([])

# ==========================
# Route: Compare Keywords
# ==========================
@app.route("/api/compare")
def compare_keywords():
    kw1 = request.args.get("kw1", "AI")
    kw2 = request.args.get("kw2", "ChatGPT")
    data = []

    for kw in [kw1, kw2]:
        try:
            fetch_posts(kw, limit=50)
        except Exception as fetch_err:
            print(f"⚠️ Error fetching posts for keyword '{kw}': {fetch_err}")

        try:
            export_keyword_from_db(kw, RAW_PATH)
        except Exception as export_err:
            print(f"⚠️ Failed to export keyword '{kw}' to Excel: {export_err}")

        from utils.post_normalizer import get_collection_name
        collection_name = get_collection_name('reddit')
        counts = []
        if hasattr(db, collection_name):
            post_collection = getattr(db, collection_name)
            pipeline = [
                {"$match": {"keyword": kw}},
                {"$group": {"_id": "$created_utc", "count": {"$sum": 1}}},
                {"$sort": {"_id": 1}}
            ]
            counts = list(post_collection.aggregate(pipeline))
        data.append({
            "keyword": kw,
            "dates": [str(c["_id"]) for c in counts],
            "values": [c["count"] for c in counts],
            "color": "#" + ''.join(random.choices('0123456789ABCDEF', k=6))
        })

    dates = sorted(list(set(d for d in sum([d["dates"] for d in data], []))))
    return jsonify({"dates": dates, "series": data})

# ==========================
# NEW STOCK MONITORING ROUTES
# ==========================

@app.route("/api/stock/<symbol>")
def get_stock_data(symbol):
    """Get aggregated stock data (price, sentiment, news, trends) - ดึงจาก database ก่อน"""
    try:
        days_back = int(request.args.get("days", 7))
        
        # 1. ตรวจสอบ database ก่อน (เร็วกว่า)
        cached_data = batch_processor.get_stock_from_database(symbol.upper())
        if cached_data:
            # ตรวจสอบว่าข้อมูลยังใหม่หรือไม่ (ไม่เกิน 2 ชั่วโมง)
            fetched_at = datetime.fromisoformat(cached_data.get('fetchedAt', ''))
            time_diff = datetime.utcnow() - fetched_at
            if time_diff < timedelta(hours=2):
                print(f"✅ Using cached data for {symbol.upper()} from database")
                # Clean for JSON
                def clean_for_json(obj):
                    import pandas as pd
                    from bson import ObjectId
                    if isinstance(obj, pd.DataFrame):
                        return obj.to_dict('records')
                    elif isinstance(obj, ObjectId):
                        return str(obj)
                    elif isinstance(obj, dict):
                        return {k: clean_for_json(v) for k, v in obj.items()}
                    elif isinstance(obj, (list, tuple)):
                        return [clean_for_json(item) for item in obj]
                    elif isinstance(obj, (datetime, timedelta)):
                        return obj.isoformat()
                    else:
                        return obj
                cleaned_data = clean_for_json(cached_data)
                return jsonify(cleaned_data)
        
        # 2. ถ้าไม่มีใน database หรือเก่าเกินไป ให้ดึงใหม่
        print(f"📊 Fetching fresh data for {symbol.upper()}...")
        data = data_aggregator.aggregate_stock_data(symbol.upper(), days_back)
        
        # 3. บันทึกลง database เพื่อใช้ครั้งต่อไป (ใช้ batch_processor)
        try:
            # ใช้ batch_processor เพื่อบันทึกข้อมูล (จะ clean old data และ deduplicate news อัตโนมัติ)
            asyncio.run(batch_processor.process_single_stock_async(symbol.upper()))
        except Exception as e:
            print(f"⚠️ Error saving to database: {e}")
            # ถ้าบันทึกไม่ได้ก็ไม่เป็นไร ยังส่งข้อมูลกลับไปได้
        
        # Serialize MongoDB ObjectIds and ensure JSON serializable
        if '_id' in data:
            data['_id'] = str(data['_id'])
        
        # Additional cleanup for JSON serialization
        import pandas as pd
        from bson import ObjectId
        
        def clean_for_json(obj):
            if isinstance(obj, pd.DataFrame):
                return obj.to_dict('records')
            elif isinstance(obj, ObjectId):
                return str(obj)
            elif isinstance(obj, dict):
                return {k: clean_for_json(v) for k, v in obj.items()}
            elif isinstance(obj, (list, tuple)):
                return [clean_for_json(item) for item in obj]
            elif isinstance(obj, (datetime, timedelta)):
                return obj.isoformat()
            else:
                return obj
        
        cleaned_data = clean_for_json(data)
        
        return jsonify(cleaned_data)
    except Exception as e:
        print(f"❌ Error in get_stock_data: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/api/stock/<symbol>/price")
def get_stock_price(symbol):
    """Get current stock price and info - ใช้ Smart Caching"""
    try:
        from processors.stock_info_manager import StockInfoManager
        stock_manager = StockInfoManager()
        
        # ตรวจสอบว่าต้องการ real-time หรือไม่
        realtime = request.args.get('realtime', 'false').lower() == 'true'
        
        if realtime:
            info = stock_manager.get_stock_info_realtime(symbol.upper())
        else:
            info = stock_manager.get_stock_info_smart(symbol.upper(), force_refresh=False)
        
        if not info:
            return jsonify({"error": "Stock not found"}), 404
        return jsonify(info)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/stock/<symbol>/info")
def get_stock_info(symbol):
    """Get stock info - ใช้ Smart Caching"""
    try:
        from processors.stock_info_manager import StockInfoManager
        stock_manager = StockInfoManager()
        
        # ตรวจสอบว่าต้องการ real-time หรือไม่
        realtime = request.args.get('realtime', 'false').lower() == 'true'
        
        if realtime:
            # ดึงแบบ real-time
            info = stock_manager.get_stock_info_realtime(symbol.upper())
        else:
            # ใช้ Smart Caching
            info = stock_manager.get_stock_info_smart(symbol.upper(), force_refresh=False)
        
        if not info:
            return jsonify({"error": "Stock not found"}), 404
        return jsonify(info)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/stock-list/refresh")
def refresh_stock_list():
    """
    อัปเดตรายชื่อหุ้นทั้งหมดจาก Yahoo Finance (NYSE, NASDAQ)
    ใช้เวลาในการดึงข้อมูล อาจใช้เวลาหลายนาที
    """
    try:
        print("🔄 Refreshing stock list from Yahoo Finance...")
        tickers = stock_list_fetcher.get_all_valid_tickers(force_refresh=True)
        
        return jsonify({
            "success": True,
            "totalTickers": len(tickers),
            "message": f"Successfully refreshed stock list. Total: {len(tickers)} tickers",
            "updatedAt": datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Failed to refresh stock list"
        }), 500

@app.route("/api/stock-list/stats")
def get_stock_list_stats():
    """Get statistics about the stock list"""
    try:
        tickers = stock_list_fetcher.load_tickers_from_database()
        
        # Count by exchange if available
        exchange_counts = {}
        if db is not None:
            ticker_docs = db.stock_tickers.find({})
            for doc in ticker_docs:
                exchange = doc.get('exchange', 'UNKNOWN')
                exchange_counts[exchange] = exchange_counts.get(exchange, 0) + 1
        
        # Get last updated time
        last_updated = None
        if db is not None:
            last_doc = db.stock_tickers.find_one(sort=[("updatedAt", -1)])
            if last_doc:
                last_updated = last_doc.get('updatedAt')
        
        return jsonify({
            "totalTickers": len(tickers),
            "exchangeBreakdown": exchange_counts,
            "lastUpdated": last_updated.isoformat() if last_updated else None,
            "source": "Yahoo Finance (NYSE, NASDAQ, AMEX)"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/stock/<symbol>/history")
def get_stock_history(symbol):
    """Get historical stock price data"""
    try:
        period = request.args.get("period", "1mo")
        interval = request.args.get("interval", "1d")
        data = stock_fetcher.get_historical_data(symbol.upper(), period, interval)
        return jsonify({"symbol": symbol.upper(), "data": data})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/stock/compare")
def compare_stocks():
    """Compare multiple stocks"""
    try:
        symbols_str = request.args.get("symbols", "")
        if not symbols_str:
            return jsonify({"error": "No symbols provided"}), 400
        
        symbols = [s.strip().upper() for s in symbols_str.split(",")]
        days_back = int(request.args.get("days", 7))
        
        results = data_aggregator.compare_stocks(symbols, days_back)
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/stocks/search")
def search_stocks():
    """Search for stocks (returns cached data)"""
    try:
        query = request.args.get("q", "").upper()
        if not query:
            return jsonify({"stocks": []})
        
        # Search in database
        stocks = list(db.stock_data.find(
            {"symbol": {"$regex": query, "$options": "i"}}
        ).sort("fetchedAt", -1).limit(10))
        
        # Serialize
        for stock in stocks:
            stock["_id"] = str(stock["_id"])
        
        return jsonify({"stocks": stocks})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/dashboard")
def get_dashboard_data():
    """Get dashboard summary data"""
    try:
        time_range = request.args.get("timeRange", "24h")
        
        # Get recently tracked stocks
        recent_stocks = list(db.stock_data.find().sort("fetchedAt", -1).limit(10))
        
        # Serialize
        for stock in recent_stocks:
            stock["_id"] = str(stock["_id"])
        
        # Calculate summary stats
        total_stocks = db.stock_data.count_documents({})
        positive_sentiment = db.stock_data.count_documents({
            "overallSentiment.label": "positive"
        })
        negative_sentiment = db.stock_data.count_documents({
            "overallSentiment.label": "negative"
        })
        
        # Calculate total mentions
        total_mentions = 0
        for stock in recent_stocks:
            total_mentions += stock.get("redditData", {}).get("mentionCount", 0)
            total_mentions += stock.get("newsData", {}).get("articleCount", 0)
        
        # Calculate average sentiment
        sentiments = [s.get("overallSentiment", {}).get("compound", 0) for s in recent_stocks if s.get("overallSentiment")]
        avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0
        
        return jsonify({
            "recentStocks": recent_stocks,
            "stats": {
                "totalTracked": total_stocks,
                "positiveSentiment": positive_sentiment,
                "negativeSentiment": negative_sentiment,
                "totalMentions": total_mentions,
                "avgSentiment": avg_sentiment,
                "mentionsChange": 0,  # TODO: Calculate change
                "sentimentChange": 0,  # TODO: Calculate change
                "spikeEvents": 0,  # TODO: Calculate spikes
                "activeAlerts": 0  # TODO: Get active alerts count
            }
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/heatmap")
def get_heatmap_data():
    """Get heatmap data for market sentiment"""
    try:
        view = request.args.get("view", "ticker")
        top_n = int(request.args.get("topN", 20))
        time_range = request.args.get("timeRange", "24h")
        
        # Get stocks sorted by mentions
        stocks = list(db.stock_data.find().sort("fetchedAt", -1).limit(100))
        
        items = []
        for stock in stocks:
            reddit_count = stock.get("redditData", {}).get("mentionCount", 0)
            news_count = stock.get("newsData", {}).get("articleCount", 0)
            total_mentions = reddit_count + news_count
            
            sentiment = stock.get("overallSentiment", {}).get("compound", 0)
            
            if view == "ticker":
                items.append({
                    "ticker": stock.get("symbol"),
                    "mentions": total_mentions,
                    "sentiment": sentiment
                })
            elif view == "sector":
                sector = stock.get("stockInfo", {}).get("sector", "Unknown")
                # Aggregate by sector
                existing = next((i for i in items if i.get("sector") == sector), None)
                if existing:
                    existing["mentions"] += total_mentions
                    existing["sentiment"] = (existing["sentiment"] + sentiment) / 2
                else:
                    items.append({
                        "sector": sector,
                        "mentions": total_mentions,
                        "sentiment": sentiment
                    })
        
        # Sort by mentions and take top N
        items.sort(key=lambda x: x.get("mentions", 0), reverse=True)
        items = items[:top_n]
        
        return jsonify({"items": items})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/trending-topics")
def get_trending_topics():
    """Get trending stock tickers ($SYMBOL format) from multiple platforms"""
    try:
        source = request.args.get("source", "all")  # ✅ เปลี่ยน default เป็น "all" เพื่อดึงจากทุก source
        time_range = request.args.get("timeRange", "24h")
        
        # Calculate time cutoff
        from datetime import timedelta
        import re
        now = datetime.utcnow()
        if time_range == "24h":
            cutoff = now - timedelta(hours=24)
        elif time_range == "7d":
            cutoff = now - timedelta(days=7)
        elif time_range == "30d":
            cutoff = now - timedelta(days=30)
        elif time_range == "1h":
            cutoff = now - timedelta(hours=1)
        elif time_range == "6h":
            cutoff = now - timedelta(hours=6)
        else:
            cutoff = now - timedelta(hours=24)
        
        # ✅ ดึงจาก collection ที่ถูกต้องตาม source
        from utils.post_normalizer import get_collection_name
        
        posts = []
        
        # กำหนด collection ตาม source
        if source == "yahoo" or source == "news":
            # ดึงจาก post_yahoo collection
            collection_name = get_collection_name('yahoo')
        elif source == "reddit":
            # ดึงจาก post_reddit collection
            collection_name = get_collection_name('reddit')
        elif source == "all":
            # ดึงจากทั้งสอง collections
            yahoo_collection_name = get_collection_name('yahoo')
            reddit_collection_name = get_collection_name('reddit')
            
            # ดึงจาก post_yahoo
            if hasattr(db, yahoo_collection_name):
                yahoo_collection = getattr(db, yahoo_collection_name)
                yahoo_query = {"created_utc": {"$gte": cutoff}}
                yahoo_posts = list(yahoo_collection.find(yahoo_query).sort("created_utc", -1).limit(5000))
                if not yahoo_posts:
                    yahoo_query_str = {"created_utc": {"$gte": cutoff.isoformat()}}
                    yahoo_posts = list(yahoo_collection.find(yahoo_query_str).sort("created_utc", -1).limit(5000))
                posts.extend(yahoo_posts)
            
            # ดึงจาก post_reddit
            if hasattr(db, reddit_collection_name):
                reddit_collection = getattr(db, reddit_collection_name)
                reddit_query = {"created_utc": {"$gte": cutoff}}
                reddit_posts = list(reddit_collection.find(reddit_query).sort("created_utc", -1).limit(5000))
                if not reddit_posts:
                    reddit_query_str = {"created_utc": {"$gte": cutoff.isoformat()}}
                    reddit_posts = list(reddit_collection.find(reddit_query_str).sort("created_utc", -1).limit(5000))
                posts.extend(reddit_posts)
            
            print(f"✅ Found {len([p for p in posts if 'yahoo' in str(p.get('source', '')).lower()])} Yahoo posts and {len([p for p in posts if 'reddit' in str(p.get('source', '')).lower()])} Reddit posts")
        else:
            # Default: ดึงจาก post_reddit (backward compatibility)
            collection_name = get_collection_name('reddit')
        
        # ถ้ายังไม่ได้ดึง (source != "all")
        if source != "all" and not posts:
            # Build query - handle both datetime objects and string timestamps
            time_query = {"created_utc": {"$gte": cutoff}}
            
            if hasattr(db, collection_name):
                post_collection = getattr(db, collection_name)
                posts = list(post_collection.find(time_query).sort("created_utc", -1).limit(5000))
                
                # If no posts found, try with string comparison (in case created_utc is stored as string)
                if not posts:
                    time_query_str = {"created_utc": {"$gte": cutoff.isoformat()}}
                    posts = list(post_collection.find(time_query_str).sort("created_utc", -1).limit(5000))
                
                # If no posts with time filter, try without time filter (fallback to show all available data)
                if not posts:
                    print(f"⚠️ No posts found with time filter (cutoff: {cutoff.isoformat()}), trying without time filter to show all available data...")
                    query = {}
                    posts = list(post_collection.find(query).sort("created_utc", -1).limit(5000))
                    if posts:
                        print(f"✅ Found {len(posts)} posts from {collection_name} (showing all available data, not filtered by time)")
                        # ✅ แจ้งเตือนว่าใช้ข้อมูลทั้งหมด (ไม่กรองเวลา)
                        print(f"   💡 Note: Using all available data (not filtered by {time_range}) because no recent posts found")
        
        # ✅ ถ้ายังไม่มี posts ให้ลองดึงจาก collection อื่นหรือขยาย time range
        if not posts:
            print(f"⚠️ No posts found in {collection_name} for source: {source} with time filter ({time_range}), trying to get any available data...")
            # ลองดึงข้อมูลทั้งหมดโดยไม่กรองเวลา (fallback)
            if source == "all":
                # ถ้า source = all แต่ไม่เจอ ให้ลองดึงจากแต่ละ collection
                yahoo_collection_name = get_collection_name('yahoo')
                reddit_collection_name = get_collection_name('reddit')
                
                if hasattr(db, yahoo_collection_name):
                    yahoo_collection = getattr(db, yahoo_collection_name)
                    yahoo_posts = list(yahoo_collection.find({}).sort("created_utc", -1).limit(5000))
                    posts.extend(yahoo_posts)
                    print(f"   📊 Found {len(yahoo_posts)} Yahoo posts (no time filter)")
                
                if hasattr(db, reddit_collection_name):
                    reddit_collection = getattr(db, reddit_collection_name)
                    reddit_posts = list(reddit_collection.find({}).sort("created_utc", -1).limit(5000))
                    posts.extend(reddit_posts)
                    print(f"   📊 Found {len(reddit_posts)} Reddit posts (no time filter)")
            else:
                # ลองดึงข้อมูลทั้งหมดจาก collection ที่เลือก
                if hasattr(db, collection_name):
                    post_collection = getattr(db, collection_name)
                    posts = list(post_collection.find({}).sort("created_utc", -1).limit(5000))
                    print(f"   📊 Found {len(posts)} posts from {collection_name} (no time filter)")
        
        if not posts:
            print(f"❌ No posts found in database for source: {source}, timeRange: {time_range}")
            print(f"   💡 Suggestions:")
            print(f"      1. Try changing time range (e.g., 7d or 30d)")
            print(f"      2. Try changing source (e.g., 'all' or 'reddit')")
            print(f"      3. Wait for scheduled updater to fetch data (Reddit every 45 seconds, Yahoo every 30 minutes)")
            print(f"      4. Enable real-time mode to fetch data immediately")
            
            # ✅ ตรวจสอบว่ามี posts ใน database หรือไม่ (ไม่กรองเวลา)
            total_posts_count = 0
            if source == "all":
                yahoo_collection_name = get_collection_name('yahoo')
                reddit_collection_name = get_collection_name('reddit')
                if hasattr(db, yahoo_collection_name):
                    total_posts_count += getattr(db, yahoo_collection_name).count_documents({})
                if hasattr(db, reddit_collection_name):
                    total_posts_count += getattr(db, reddit_collection_name).count_documents({})
            else:
                if hasattr(db, collection_name):
                    total_posts_count = getattr(db, collection_name).count_documents({})
            
            return jsonify({
                "topics": [],
                "message": f"No posts found for source '{source}' in the last {time_range}. Total posts in database: {total_posts_count:,}",
                "source": source,
                "timeRange": time_range,
                "totalPosts": 0,
                "totalPostsInDatabase": total_posts_count,
                "tip": f"Try changing time range to '7d' or '30d', or change source to 'all'. Data is being fetched automatically (Reddit every 45 seconds, Yahoo every 30 minutes)."
            })
        
        # Extract stock tickers ($SYMBOL format) from all posts
        # Count ALL mentions (not just once per post) to reflect true trending
        ticker_freq = {}
        ticker_sources = {}  # Track which sources mention each ticker
        ticker_sentiment = {}  # Track average sentiment per ticker
        ticker_posts = {}  # Track unique posts mentioning each ticker
        
        # Regex pattern to match $SYMBOL format (1-5 uppercase letters after $)
        ticker_pattern = re.compile(r'\$([A-Z]{1,5})\b')
        
        print(f"📊 Processing {len(posts)} posts to extract tickers...")
        
        for post in posts:
            # Combine all text fields
            text = f"{post.get('title', '')} {post.get('selftext', '')} {post.get('text', '')} {post.get('body', '')}"
            post_source = post.get('source', 'unknown')
            
            # ✅ ดึง sentiment จาก database (ที่ถูกวิเคราะห์และบันทึกไว้แล้ว)
            post_sentiment = 0
            if post.get('sentiment'):
                if isinstance(post.get('sentiment'), dict):
                    post_sentiment = post.get('sentiment', {}).get('compound', 0)
                else:
                    post_sentiment = post.get('sentiment', 0)
            elif post.get('sentiment_score'):
                # Backward compatibility
                post_sentiment = post.get('sentiment_score', 0)
            # ✅ ถ้าไม่มี sentiment ใน database ให้คำนวณใหม่ (สำหรับ posts เก่าที่ยังไม่มี sentiment)
            elif text.strip():
                try:
                    sentiment_result = sentiment_analyzer.analyze(text)
                    post_sentiment = sentiment_result.get('compound', 0)
                    # บันทึก sentiment กลับไปที่ database (optional - เพื่อไม่ให้คำนวณซ้ำ)
                    # แต่ไม่ทำตอนนี้เพราะจะช้า - จะให้ scheduled updater จัดการ
                except Exception:
                    post_sentiment = 0
            
            # ✅ Debug: แสดงตัวอย่าง sentiment (เฉพาะ 5 posts แรก)
            if len([p for p in posts if p == post]) <= 5:
                print(f"   🔍 Debug post sentiment: {post.get('id', 'unknown')[:10]}... → {post_sentiment}")
            
            post_id = str(post.get('_id', ''))
            
            # ✅ วิธีที่ 1: ใช้ field 'symbols' หรือ 'symbol' ที่มีอยู่แล้วใน post (เร็วกว่าและแม่นยำกว่า)
            tickers = []
            if post.get('symbols') and isinstance(post.get('symbols'), list):
                # ใช้ symbols array ที่ถูก extract แล้ว
                tickers = [s.upper() for s in post.get('symbols') if s]
            elif post.get('symbol'):
                # ใช้ symbol field (backward compatibility)
                tickers = [post.get('symbol').upper()]
            
            # ✅ วิธีที่ 2: ถ้าไม่มี symbols field ให้หาจาก text ด้วย regex (fallback)
            if not tickers:
                tickers = ticker_pattern.findall(text.upper())
            
            # Track unique tickers per post for post count
            unique_tickers_in_post = set()
            
            for ticker in tickers:
                # Filter out common false positives
                if ticker in ['USD', 'GDP', 'CEO', 'IPO', 'ETF', 'SEC', 'IRS', 'FDA', 'AI', 'IT', 'TV', 'PC', 'USA']:
                    continue
                
                # Count ALL mentions (not just once per post) - this reflects true trending
                ticker_freq[ticker] = ticker_freq.get(ticker, 0) + 1
                
                # Track unique posts mentioning this ticker
                if ticker not in ticker_posts:
                    ticker_posts[ticker] = set()
                if ticker not in unique_tickers_in_post:
                    unique_tickers_in_post.add(ticker)
                    ticker_posts[ticker].add(post_id)
                
                # Track sources
                if ticker not in ticker_sources:
                    ticker_sources[ticker] = set()
                ticker_sources[ticker].add(post_source)
                
                # Track sentiment (cumulative for averaging later)
                if ticker not in ticker_sentiment:
                    ticker_sentiment[ticker] = []
                ticker_sentiment[ticker].append(post_sentiment)
        
        # ✅ Import pump and dump detector
        from processors.pump_dump_detector import PumpDumpDetector
        pump_dump_detector = PumpDumpDetector()
        
        # Convert to list with additional metadata
        topics = []
        for ticker, count in ticker_freq.items():
            # Calculate average sentiment
            sentiments = ticker_sentiment.get(ticker, [])
            avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0
            
            # Get unique post count
            unique_post_count = len(ticker_posts.get(ticker, set()))
            
            # ✅ ดึง posts สำหรับ ticker นี้เพื่อตรวจสอบ pump and dump
            ticker_posts_list = []
            for post in posts:
                post_tickers = post.get('symbols', []) or ([post.get('symbol')] if post.get('symbol') else [])
                if ticker in [t.upper() for t in post_tickers]:
                    ticker_posts_list.append(post)
            
            # ✅ ดึง stock_info จาก database เพื่อตรวจสอบ volume spike
            stock_info = {}
            if db is not None and hasattr(db, 'stocks') and db.stocks is not None:
                stock_doc = db.stocks.find_one(
                    {"symbol": ticker.upper()},
                    sort=[("fetchedAt", -1)]
                )
                if stock_doc:
                    stock_info_data = stock_doc.get('stockInfo', {})
                    stock_info = {
                        'volume': stock_info_data.get('volume', 0),
                        'averageVolume': stock_info_data.get('averageVolume', 0),
                        'changePercent': stock_info_data.get('changePercent', 0) or stock_info_data.get('priceChangePercent', 0),
                        'priceChangePercent': stock_info_data.get('changePercent', 0) or stock_info_data.get('priceChangePercent', 0),
                        'currentPrice': stock_info_data.get('currentPrice', 0) or stock_info_data.get('price', 0)
                    }
            
            # ✅ ตรวจจับ pump and dump
            pump_dump_result = pump_dump_detector.detect_pump_dump(ticker, ticker_posts_list, stock_info)
            
            # ✅ คำนวณ trust score และปรับ sentiment
            trust_score = pump_dump_detector.calculate_trust_score(ticker, ticker_posts_list, stock_info)
            adjusted_sentiment = pump_dump_detector.adjust_sentiment_by_trust(avg_sentiment, trust_score)
            
            topics.append({
                "word": ticker,  # Keep 'word' for compatibility
                "ticker": ticker,  # Add explicit ticker field
                "count": count,  # Total mentions (all occurrences)
                "mentions": count,  # Alias for count
                "uniquePosts": unique_post_count,  # Number of unique posts
                "sources": list(ticker_sources.get(ticker, set())),
                "sourceCount": len(ticker_sources.get(ticker, set())),
                "avgSentiment": round(avg_sentiment, 3),  # Original sentiment
                "adjustedSentiment": round(adjusted_sentiment, 3),  # ✅ Adjusted sentiment (filtered pump/dump)
                "trustScore": round(trust_score, 1),  # ✅ Trust score (0-100)
                "isPumpDump": pump_dump_result.get("is_pump_dump", False),  # ✅ Is pump and dump?
                "riskScore": round(pump_dump_result.get("risk_score", 0), 1),  # ✅ Risk score (0-100)
                "pumpDumpSignals": pump_dump_result.get("signals", {}),  # ✅ Detection signals
                "recommendation": pump_dump_result.get("recommendation", "")  # ✅ Recommendation
            })
        
        # Sort by mention count (most mentioned first) - ALWAYS show highest mentions first
        topics.sort(key=lambda x: x["count"], reverse=True)
        
        # Log top 5 for debugging (รวม sentiment)
        if topics:
            top5_with_sentiment = [(t['ticker'], t['count'], f"{t.get('avgSentiment', 0):.3f}") for t in topics[:5]]
            print(f"📊 Top 5 trending tickers: {top5_with_sentiment}")
            # ✅ Debug: ตรวจสอบ sentiment ของ posts
            if topics and topics[0].get('avgSentiment', 0) == 0:
                print(f"   ⚠️  WARNING: Top ticker {topics[0].get('ticker')} has avgSentiment = 0")
                print(f"   💡 ตรวจสอบว่า posts มี sentiment field หรือไม่")
        else:
            # Debug: ตรวจสอบว่าทำไมไม่เจอ ticker
            print(f"⚠️ No tickers found from {len(posts)} posts")
            if posts:
                # ตรวจสอบ posts ตัวอย่าง
                sample_post = posts[0]
                print(f"   Sample post fields: {list(sample_post.keys())}")
                print(f"   Has 'symbols' field: {sample_post.get('symbols') is not None}")
                print(f"   Has 'symbol' field: {sample_post.get('symbol') is not None}")
                if sample_post.get('symbols'):
                    print(f"   Symbols in sample: {sample_post.get('symbols')}")
                if sample_post.get('symbol'):
                    print(f"   Symbol in sample: {sample_post.get('symbol')}")
        
        result = {
            "topics": topics[:100],  # Top 100 (เพิ่มจาก 50 เพื่อให้หุ้นที่อยู่นอก 50 มีโอกาสเข้ามา)
            "source": source,
            "timeRange": time_range,
            "totalPosts": len(posts),
            "totalTickers": len(topics)
        }
        
        # If no tickers found, add helpful message
        if len(topics) == 0:
            result["message"] = f"No stock tickers found. Analyzed {len(posts)} posts. The posts may not have ticker symbols extracted yet. Scheduled updater will extract tickers automatically."
            result["debug"] = {
                "totalPosts": len(posts),
                "tip": "Posts are being processed. Tickers will be extracted automatically by the scheduled updater."
            }
        
        return jsonify(result)
    except Exception as e:
        import traceback
        print(f"Error in trending-topics: {e}")
        print(traceback.format_exc())
        return jsonify({
            "error": str(e),
            "topics": [],
            "message": f"Error processing trending topics: {str(e)}"
        }), 500

@app.route("/api/fetch-new-posts", methods=["POST"])
def fetch_new_posts():
    """Fetch new posts from Reddit for trending stock tickers (using async)"""
    import asyncio
    try:
        # Get popular stock tickers to fetch
        popular_tickers = ["AAPL", "TSLA", "NVDA", "MSFT", "AMZN", "GOOGL", "META", "AMD", "NFLX", "SPY"]
        
        async def fetch_all_posts():
            from fetchers.fetch_reddit_async import fetch_posts_async
            total_fetched = 0
            for ticker in popular_tickers:
                try:
                    print(f"📊 Fetching posts (async) for ${ticker}...")
                    posts = await fetch_posts_async(keyword=f"${ticker}", limit=20)
                    total_fetched += len(posts) if posts else 0
                except Exception as e:
                    print(f"⚠️ Error fetching posts for ${ticker}: {e}")
                    continue
            return total_fetched
        
        # Run async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        total_fetched = loop.run_until_complete(fetch_all_posts())
        loop.close()
        
        return jsonify({
            "success": True,
            "message": f"Fetched {total_fetched} new posts",
            "totalFetched": total_fetched
        })
    except Exception as e:
        import traceback
        print(f"Error in fetch-new-posts: {e}")
        print(traceback.format_exc())
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route("/api/trending-realtime")
@retry_on_failure(max_attempts=2, base_delay=0.5)
def get_trending_realtime():
    """
    Real-time Mode: ดึงข้อมูลจาก database + ดึง post ใหม่จาก API เพื่อวิเคราะห์ sentiment เพิ่มเติม
    
    เมื่อเปิด real-time mode:
    1. ดึงข้อมูลจาก database (เหมือน database mode)
    2. ดึง post ใหม่จาก Reddit, Twitter/X API สำหรับ tickers ที่ trending
    3. วิเคราะห์ sentiment จาก post ใหม่
    4. รวมข้อมูลเข้าด้วยกัน
    """
    try:
        source = request.args.get("source", "all")
        limit = int(request.args.get("limit", "100"))
        
        print(f"🔄 [REAL-TIME MODE] Fetching trending data from database + API (source: {source})")
        
        # ตรวจสอบ database
        if db is None or not hasattr(db, 'stocks') or db.stocks is None:
            return jsonify({
                "error": "Database not available",
                "topics": [],
                "message": "Database connection not available"
            }), 500
        
        # ดึงข้อมูลหุ้นทั้งหมดจาก database (เรียงตาม fetchedAt ล่าสุด)
        # จำกัดเวลาไม่เกิน 24 ชั่วโมง
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        
        # Query stocks ที่มีข้อมูลล่าสุด
        stocks_query = {
            "fetchedAt": {"$gte": cutoff_time.isoformat()}
        }
        
        # กรองตาม source ถ้าต้องการ
        if source != "all":
            # ถ้า source เป็น yahoo, reddit, news, twitter, youtube
            # จะดึงเฉพาะหุ้นที่มีข้อมูลจาก source นั้น
            pass  # ตอนนี้ยังไม่กรอง source เพราะข้อมูลถูก aggregate แล้ว
        
        stocks_cursor = db.stocks.find(stocks_query).sort("fetchedAt", -1).limit(1000)
        stocks_list = list(stocks_cursor)
        
        print(f"   ✅ Found {len(stocks_list)} stocks in database")
        
        # ✅ REAL-TIME MODE: ดึง post ใหม่จาก API สำหรับ top trending tickers
        # ดึงเฉพาะ top 20 tickers เพื่อไม่ให้ช้าเกินไป
        top_tickers_for_realtime = []
        if stocks_list:
            # เรียงตาม mentions เพื่อหา top trending
            ticker_mentions = {}
            for stock in stocks_list:
                symbol = stock.get('symbol', '').upper()
                if symbol:
                    reddit_count = stock.get('redditData', {}).get('mentionCount', 0)
                    news_count = stock.get('newsData', {}).get('articleCount', 0)
                    twitter_count = stock.get('twitterData', {}).get('tweetCount', 0)
                    total_mentions = reddit_count + news_count + twitter_count
                    ticker_mentions[symbol] = total_mentions
            
            # เรียงตาม mentions และเลือก top 20
            sorted_tickers = sorted(ticker_mentions.items(), key=lambda x: x[1], reverse=True)
            top_tickers_for_realtime = [ticker for ticker, _ in sorted_tickers[:20]]
        
        print(f"   🔄 Fetching new posts from API for top {len(top_tickers_for_realtime)} trending tickers...")
        
        # ดึง post ใหม่จาก Reddit และ Twitter/X สำหรับ top tickers
        realtime_posts = {}
        realtime_sentiments = {}
        
        if top_tickers_for_realtime and source in ['all', 'reddit']:
            # ดึง Reddit posts ใหม่
            try:
                from fetchers.fetch_reddit import fetch_posts
                for ticker in top_tickers_for_realtime[:10]:  # จำกัด 10 tickers เพื่อไม่ให้ช้า
                    try:
                        posts = fetch_posts(f"${ticker}", limit=10)
                        if posts:
                            realtime_posts[ticker] = realtime_posts.get(ticker, []) + posts
                            # วิเคราะห์ sentiment
                            for post in posts:
                                text = f"{post.get('title', '')} {post.get('selftext', '')}"
                                sentiment = sentiment_analyzer.analyze(text)
                                if ticker not in realtime_sentiments:
                                    realtime_sentiments[ticker] = []
                                realtime_sentiments[ticker].append(sentiment.get('compound', 0))
                    except Exception as e:
                        print(f"   ⚠️ Error fetching Reddit posts for {ticker}: {e}")
                        continue
            except Exception as e:
                print(f"   ⚠️ Error in Reddit fetching: {e}")
        
        if top_tickers_for_realtime and source in ['all', 'twitter']:
            # ดึง Twitter/X posts ใหม่ (ถ้ามี API key)
            try:
                from fetchers.twitter_fetcher import TwitterFetcher
                twitter_fetcher = TwitterFetcher()
                if twitter_fetcher.bearer_token:
                    for ticker in top_tickers_for_realtime[:5]:  # จำกัด 5 tickers เพื่อไม่ให้ช้า
                        try:
                            tweets = twitter_fetcher.search_tweets(f"${ticker}", max_results=10)
                            if tweets:
                                realtime_posts[ticker] = realtime_posts.get(ticker, []) + tweets
                                # วิเคราะห์ sentiment
                                for tweet in tweets:
                                    text = tweet.get('text', '')
                                    sentiment = sentiment_analyzer.analyze(text)
                                    if ticker not in realtime_sentiments:
                                        realtime_sentiments[ticker] = []
                                    realtime_sentiments[ticker].append(sentiment.get('compound', 0))
                        except Exception as e:
                            print(f"   ⚠️ Error fetching Twitter posts for {ticker}: {e}")
                            continue
            except Exception as e:
                print(f"   ⚠️ Error in Twitter fetching: {e}")
        
        if realtime_posts:
            print(f"   ✅ Fetched {sum(len(posts) for posts in realtime_posts.values())} new posts from API")
        
        # สร้าง ticker frequency และ aggregate ข้อมูล
        ticker_freq = {}
        ticker_sources = {}
        ticker_sentiment = {}
        ticker_details = {}
        ticker_prices = {}
        
        for stock in stocks_list:
            symbol = stock.get('symbol', '').upper()
            if not symbol:
                continue
            
            # นับ mentions จากทุก sources
            mentions = 0
            sources_set = set()
            sentiment_scores = []
            
            # Yahoo Finance / News
            news_data = stock.get('newsData', {})
            news_count = news_data.get('articleCount', 0)
            if news_count > 0:
                mentions += news_count
                sources_set.add('yahoo' if 'yahoo' in str(news_data.get('source', '')).lower() else 'news')
                news_sentiment = news_data.get('sentiment', {})
                if news_sentiment and news_sentiment.get('compound'):
                    sentiment_scores.append(news_sentiment.get('compound'))
            
            # Reddit
            reddit_data = stock.get('redditData', {})
            reddit_count = reddit_data.get('mentionCount', 0)
            if reddit_count > 0:
                mentions += reddit_count
                sources_set.add('reddit')
                reddit_sentiment = reddit_data.get('sentiment', {})
                if reddit_sentiment and reddit_sentiment.get('compound'):
                    sentiment_scores.append(reddit_sentiment.get('compound'))
            
            # Twitter
            twitter_data = stock.get('twitterData', {})
            twitter_count = twitter_data.get('tweetCount', 0)
            if twitter_count > 0:
                mentions += twitter_count
                sources_set.add('twitter')
                twitter_sentiment = twitter_data.get('sentiment', {})
                if twitter_sentiment and twitter_sentiment.get('compound'):
                    sentiment_scores.append(twitter_sentiment.get('compound'))
            
            # YouTube
            youtube_data = stock.get('youtubeData', {})
            youtube_count = youtube_data.get('videoCount', 0)
            if youtube_count > 0:
                mentions += youtube_count
                sources_set.add('youtube')
                youtube_sentiment = youtube_data.get('sentiment', {})
                if youtube_sentiment and youtube_sentiment.get('compound'):
                    sentiment_scores.append(youtube_sentiment.get('compound'))
            
            # ✅ REAL-TIME MODE: เพิ่ม mentions และ sentiment จาก post ใหม่ที่ดึงจาก API
            realtime_mentions = 0
            if symbol in realtime_posts:
                realtime_post_count = len(realtime_posts[symbol])
                realtime_mentions = realtime_post_count
                mentions += realtime_post_count
                
                # เพิ่ม source จาก real-time posts
                for post in realtime_posts[symbol]:
                    post_source = post.get('source', 'unknown')
                    if 'reddit' in str(post_source).lower():
                        sources_set.add('reddit')
                    elif 'twitter' in str(post_source).lower() or 'x' in str(post_source).lower():
                        sources_set.add('twitter')
                
                # เพิ่ม sentiment จาก post ใหม่
                if symbol in realtime_sentiments and realtime_sentiments[symbol]:
                    sentiment_scores.extend(realtime_sentiments[symbol])
                    print(f"   📊 {symbol}: Added {realtime_post_count} real-time posts, {len(realtime_sentiments[symbol])} new sentiment scores")
            
            # ถ้ามี mentions (จาก database หรือ real-time) ให้เพิ่มเข้าไป
            if mentions > 0:
                ticker_freq[symbol] = mentions
                ticker_sources[symbol] = sources_set
                
                # คำนวณ average sentiment (รวม sentiment จาก database และ real-time posts)
                if sentiment_scores:
                    ticker_sentiment[symbol] = sum(sentiment_scores) / len(sentiment_scores)
                else:
                    # ใช้ overall sentiment ถ้ามี
                    overall = stock.get('overallSentiment', {})
                    if overall and overall.get('compound'):
                        ticker_sentiment[symbol] = overall.get('compound')
                    else:
                        ticker_sentiment[symbol] = 0
                
                # เก็บรายละเอียดจาก news articles
                news_articles = news_data.get('articles', [])[:5]  # Top 5 articles
                ticker_details[symbol] = []
                for article in news_articles:
                    ticker_details[symbol].append({
                        "post_id": article.get('uuid', article.get('url', '')),
                        "title": article.get('title', ''),
                        "subreddit": article.get('source', 'Yahoo Finance'),
                        "score": 0,
                        "url": article.get('url', ''),
                        "created_utc": article.get('publishedAt', stock.get('fetchedAt', datetime.utcnow().isoformat()))
                    })
                
                # เก็บราคาหุ้น
                stock_info = stock.get('stockInfo', {})
                if stock_info:
                    price = stock_info.get('currentPrice') or stock_info.get('price')
                    if price:
                        ticker_prices[symbol] = price
        
        # สร้าง topics list
        topics = [
            {
                "ticker": ticker,
                "word": ticker,
                "count": count,
                "mentions": count,
                "uniquePosts": len(ticker_details.get(ticker, [])),
                "sources": list(ticker_sources.get(ticker, set())),
                "sourceCount": len(ticker_sources.get(ticker, set())),
                "avgSentiment": round(ticker_sentiment.get(ticker, 0), 3),
                "topPosts": ticker_details.get(ticker, [])[:5],
                "currentPrice": ticker_prices.get(ticker),
                "price": ticker_prices.get(ticker)
            }
            for ticker, count in ticker_freq.items()
        ]
        
        # เรียงตาม mentions
        topics.sort(key=lambda x: x["count"], reverse=True)
        
        # นับ source breakdown
        source_counts = {}
        for ticker, sources in ticker_sources.items():
            for src in sources:
                source_counts[src] = source_counts.get(src, 0) + ticker_freq.get(ticker, 0)
        
        print(f"✅ [REAL-TIME MODE] Data aggregation complete:")
        print(f"   Total tickers found: {len(topics)}")
        print(f"   Source breakdown: {source_counts}")
        if realtime_posts:
            print(f"   ✅ Real-time posts fetched: {sum(len(posts) for posts in realtime_posts.values())} posts from API")
        if topics:
            top5 = [(t['ticker'], t['count'], t['sources']) for t in topics[:5]]
            print(f"📊 Top 5: {top5}")
        
        # ส่งกลับ Top 100
        return jsonify({
            "topics": topics[:limit],
            "totalPosts": sum(ticker_freq.values()),
            "totalTickers": len(topics),
            "source": f"realtime-{source}",
            "sourceBreakdown": source_counts,
            "fetchedAt": datetime.utcnow().isoformat(),
            "realtimePostsFetched": sum(len(posts) for posts in realtime_posts.values()) if realtime_posts else 0,
            "subreddits": []
        })
        
    except Exception as e:
        import traceback
        print(f"❌ Error in trending-realtime: {e}")
        print(traceback.format_exc())
        return jsonify({
            "error": str(e),
            "topics": [],
            "message": f"Error fetching data from database: {str(e)}"
        }), 500

@app.route("/api/event-analysis")
def get_event_analysis():
    """
    วิเคราะห์เหตุการณ์สำคัญจาก YouTube และแนะนำหุ้นที่ควรลงทุน
    
    Query Parameters:
        - max_videos: จำนวนวิดีโอสูงสุดที่ต้องการวิเคราะห์ (default: 50)
        - days_back: จำนวนวันที่ต้องการดึงข้อมูลย้อนหลัง (default: 7)
    """
    try:
        from fetchers.youtube_fetcher import YouTubeFetcher
        from processors.event_analyzer import EventAnalyzer
        
        max_videos = int(request.args.get("max_videos", "50"))
        days_back = int(request.args.get("days_back", "7"))
        
        print(f"🔍 Starting event analysis from YouTube videos...")
        print(f"   Max videos: {max_videos}")
        print(f"   Days back: {days_back}")
        
        # สร้าง fetcher และ analyzer
        youtube_fetcher = YouTubeFetcher()
        event_analyzer = EventAnalyzer()
        
        if not youtube_fetcher.api_key:
            return jsonify({
                "error": "YouTube API key not configured",
                "message": "Please add YOUTUBE_API_KEY to your .env file"
            }), 400
        
        # ดึงวิดีโอจาก YouTube
        # ดึงวิดีโอข่าวสำคัญ
        print("📺 Fetching news videos from YouTube...")
        videos = youtube_fetcher.search_news_videos(max_results=max_videos)
        
        if not videos:
            return jsonify({
                "error": "No videos found",
                "message": "Could not fetch videos from YouTube API"
            }), 404
        
        # วิเคราะห์เหตุการณ์จากวิดีโอ
        print(f"🔍 Analyzing {len(videos)} videos for events...")
        events = event_analyzer.analyze_events(videos, days_back=days_back)
        
        # ส่งกลับผลลัพธ์
        return jsonify({
            "events": events,
            "totalVideos": len(videos),
            "totalEvents": len(events),
            "fetchedAt": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        import traceback
        print(f"❌ Error in event-analysis: {e}")
        print(traceback.format_exc())
        return jsonify({
            "error": str(e),
            "message": f"Error analyzing events: {str(e)}"
        }), 500

@app.route("/api/sparklines")
def get_sparklines():
    """Get mentions volume sparklines"""
    try:
        time_range = request.args.get("timeRange", "24h")
        
        # Get recent stocks
        stocks = list(db.stock_data.find().sort("fetchedAt", -1).limit(20))
        
        sparklines = []
        for stock in stocks:
            symbol = stock.get("symbol")
            if not symbol:
                continue
            
            # Generate mock sparkline data (in production, would aggregate by time)
            import random
            data = [random.randint(0, 100) for _ in range(24)]
            current = data[-1] if data else 0
            
            sparklines.append({
                "ticker": symbol,
                "data": data,
                "current": current
            })
        
        return jsonify({"sparklines": sparklines})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/divergence")
def get_divergence():
    """Get price vs sentiment divergence"""
    try:
        threshold = float(request.args.get("threshold", 0.2))
        time_range = request.args.get("timeRange", "24h")
        
        # Get stocks with price and sentiment data
        stocks = list(db.stock_data.find().sort("fetchedAt", -1).limit(50))
        
        items = []
        for stock in stocks:
            stock_info = stock.get("stockInfo", {})
            sentiment = stock.get("overallSentiment", {})
            
            if not stock_info or not sentiment:
                continue
            
            price_change = stock_info.get("changePercent", 0) / 100
            sentiment_change = sentiment.get("compound", 0)
            
            # Check for divergence
            if abs(sentiment_change - price_change) >= threshold:
                items.append({
                    "ticker": stock.get("symbol"),
                    "sentimentChange": sentiment_change,
                    "priceChange": price_change,
                    "divergence": abs(sentiment_change - price_change)
                })
        
        # Sort by divergence
        items.sort(key=lambda x: x.get("divergence", 0), reverse=True)
        
        return jsonify({"items": items[:10]})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/raw-feed")
def get_raw_feed():
    """Get raw feed of posts"""
    try:
        time_range = request.args.get("timeRange", "24h")
        limit = int(request.args.get("limit", 50))
        
        # Get posts from database (ใช้ collection post_reddit)
        from utils.post_normalizer import get_collection_name
        collection_name = get_collection_name('reddit')
        posts = []
        if hasattr(db, collection_name):
            post_collection = getattr(db, collection_name)
            posts = list(post_collection.find().sort("created_utc", -1).limit(limit))
        
        # Serialize and add sentiment
        from processors.sentiment_analyzer import SentimentAnalyzer
        analyzer = SentimentAnalyzer()
        
        result = []
        for post in posts:
            text = f"{post.get('title', '')} {post.get('selftext', '')}"
            sentiment = analyzer.analyze(text)
            
            result.append({
                "id": str(post.get("_id")),
                "source": "reddit",
                "title": post.get("title"),
                "text": post.get("selftext", ""),
                "created_at": post.get("created_utc").isoformat() if isinstance(post.get("created_utc"), datetime) else str(post.get("created_utc")),
                "upvotes": post.get("score", 0),
                "comments": post.get("num_comments", 0),
                "url": post.get("url"),
                "subreddit": post.get("subreddit"),
                "sentiment": {
                    "compound": sentiment.get("compound", 0),
                    "label": sentiment.get("label", "neutral")
                }
            })
        
        return jsonify({"posts": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==========================
# STOCK DETAIL ENDPOINTS
# ==========================

@app.route("/api/stock/<symbol>/impact-timeline")
def get_impact_timeline(symbol):
    """Get impact timeline for influencer posts"""
    try:
        time_window = request.args.get("timeWindow", "1h")
        
        # Mock data - in production, would calculate from historical data
        mock_events = [
            {
                "influencer": "Elon Musk",
                "platform": "twitter",
                "time": datetime.utcnow().isoformat(),
                "post": "Just bought more $" + symbol,
                "priceBefore": 148.50,
                "priceAfter": 151.20,
                "impact": 1.82
            }
        ]
        
        return jsonify({"events": mock_events})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/stock/<symbol>/topics")
def get_stock_topics(symbol):
    """Get topic clusters for a stock"""
    try:
        time_range = request.args.get("timeRange", "24h")
        
        # Mock data - in production, would use LDA
        mock_topics = [
            {"id": 1, "name": "Earnings & Financials", "weight": 0.35, "posts": 45},
            {"id": 2, "name": "Product Launches", "weight": 0.28, "posts": 32}
        ]
        
        return jsonify({"topics": mock_topics})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/stock/<symbol>/correlation")
def get_correlation(symbol):
    """Get correlation analysis between sentiment and price"""
    try:
        period = request.args.get("period", "30d")
        
        # Mock data - in production, would calculate correlation
        mock_correlation = {
            "lags": ["-24h", "-12h", "-6h", "-3h", "-1h", "0", "+1h", "+3h", "+6h", "+12h", "+24h"],
            "correlations": [-0.2, 0.1, 0.3, 0.5, 0.65, 0.72, 0.68, 0.55, 0.4, 0.2, 0.1],
            "maxCorrelation": 0.72,
            "maxLag": "+1h",
            "interpretation": "Sentiment leads price by 1-2 hours"
        }
        
        return jsonify(mock_correlation)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/stock/<symbol>/validation")
def get_stock_validation(symbol):
    """Get validation results for stock sentiment"""
    try:
        symbol_upper = symbol.upper()
        
        # ดึงข้อมูลจาก database
        stock_data = db.stock_data.find_one({"symbol": symbol_upper})
        if not stock_data:
            return jsonify({"error": "Stock data not found"}), 404
        
        # ดึง validation results
        validation = stock_data.get('validation', {})
        overall_sentiment = stock_data.get('overallSentiment', {})
        
        if not validation:
            return jsonify({
                "message": "No validation data available",
                "symbol": symbol_upper
            }), 404
        
        # สรุปผล
        yahoo_validation = validation.get('yahoo', {})
        reddit_validation = validation.get('reddit', {})
        
        confidences = []
        if yahoo_validation:
            confidences.append(yahoo_validation.get('confidence', 0))
        if reddit_validation and reddit_validation.get('is_valid', False):
            confidences.append(reddit_validation.get('confidence', 0) * 0.5)
        
        overall_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        recommendation = 'high_confidence' if overall_confidence > 0.7 else \
                        ('medium_confidence' if overall_confidence > 0.4 else 'low_confidence')
        
        return jsonify({
            "symbol": symbol_upper,
            "yahoo": yahoo_validation,
            "reddit": reddit_validation,
            "overall_confidence": round(overall_confidence, 3),
            "recommendation": recommendation,
            "overall_sentiment": {
                "compound": overall_sentiment.get('compound', 0),
                "label": overall_sentiment.get('label', 'neutral'),
                "confidence": overall_sentiment.get('confidence', 0)
            }
        })
    except Exception as e:
        print(f"❌ Error getting validation: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/api/stock/<symbol>/pressure-score")
def get_pressure_score(symbol):
    """Calculate buy/sell pressure score from Yahoo Finance data"""
    try:
        symbol_upper = symbol.upper()
        
        # ใช้ StockInfoManager สำหรับ validation (ต้องใช้ข้อมูล real-time)
        from processors.stock_info_manager import StockInfoManager
        stock_manager = StockInfoManager()
        stock_info = stock_manager.get_stock_info_for_validation(symbol_upper)
        
        if not stock_info:
            return jsonify({"error": "Stock not found"}), 404
        
        # Get historical data for volume analysis
        hist_data = stock_fetcher.get_historical_data(symbol_upper, period="5d", interval="1d")
        
        # Calculate buy/sell pressure based on:
        # 1. Price change direction and magnitude
        # 2. Volume compared to average
        # 3. Sentiment from aggregated data
        
        current_price = stock_info.get('currentPrice', 0)
        previous_close = stock_info.get('previousClose', current_price)
        change = stock_info.get('change', 0)
        change_percent = stock_info.get('changePercent', 0)
        volume = stock_info.get('volume', 0)
        
        # Calculate average volume
        avg_volume = 0
        if hist_data and len(hist_data) > 0:
            volumes = [d.get('volume', 0) for d in hist_data if d.get('volume', 0) > 0]
            if volumes:
                avg_volume = sum(volumes) / len(volumes)
        
        # Get sentiment data
        days_back = int(request.args.get("days", 7))
        aggregated_data = data_aggregator.aggregate_stock_data(symbol_upper, days_back)
        overall_sentiment = aggregated_data.get('overallSentiment', {}).get('compound', 0)
        
        # Calculate buy pressure (0-100)
        # Factors:
        # 1. Price change (positive = buy pressure, negative = sell pressure)
        # 2. Volume (higher than average = stronger pressure)
        # 3. Sentiment (positive = buy pressure, negative = sell pressure)
        
        price_factor = max(0, min(100, 50 + (change_percent * 2)))  # -25% to +25% maps to 0-100
        volume_factor = 50  # Base
        if avg_volume > 0:
            volume_ratio = volume / avg_volume
            if volume_ratio > 1.5:  # High volume
                volume_factor = min(100, 50 + (volume_ratio - 1.5) * 20)
            elif volume_ratio < 0.5:  # Low volume
                volume_factor = max(0, 50 - (0.5 - volume_ratio) * 20)
        
        sentiment_factor = max(0, min(100, 50 + (overall_sentiment * 10)))  # -5 to +5 maps to 0-100
        
        # Weighted average
        buy_pressure = (price_factor * 0.4 + volume_factor * 0.3 + sentiment_factor * 0.3)
        buy_pressure = max(0, min(100, buy_pressure))
        sell_pressure = 100 - buy_pressure
        
        return jsonify({
            "buyPressure": round(buy_pressure, 2),
            "sellPressure": round(sell_pressure, 2),
            "score": round(buy_pressure, 2),
            "factors": {
                "priceFactor": round(price_factor, 2),
                "volumeFactor": round(volume_factor, 2),
                "sentimentFactor": round(sentiment_factor, 2),
                "volumeRatio": round(volume / avg_volume, 2) if avg_volume > 0 else 0,
                "changePercent": round(change_percent, 2),
                "overallSentiment": round(overall_sentiment, 3)
            }
        })
    except Exception as e:
        print(f"❌ Error calculating pressure score: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/stock/<symbol>/news")
def get_stock_news(symbol):
    """Get news from database (ดึงจาก database แทน real-time API)"""
    try:
        symbol_upper = symbol.upper()
        
        # 1. ดึงข่าวจาก database ก่อน (ใช้ collection post_yahoo)
        from utils.post_normalizer import get_collection_name
        news_articles = []
        collection_name = get_collection_name('yahoo')
        if db is not None and hasattr(db, collection_name) and getattr(db, collection_name) is not None:
            post_collection = getattr(db, collection_name)
            # ดึงข่าวล่าสุด 50 ข่าว
            news_cursor = post_collection.find(
                {"symbol": symbol_upper}
            ).sort("created_utc", -1).limit(50)
            news_articles = list(news_cursor)
        
        # 2. ถ้าไม่มีข่าวใน database ให้ดึงจาก stock data
        if not news_articles:
            stock_data = batch_processor.get_stock_from_database(symbol_upper)
            if stock_data and stock_data.get('newsData'):
                news_articles = stock_data.get('newsData', {}).get('articles', [])
        
        # 3. ถ้ายังไม่มี ให้ดึงจาก Yahoo Finance real-time (fallback)
        if not news_articles:
            print(f"⚠️ No news in database for {symbol_upper}, fetching from Yahoo Finance...")
            try:
                ticker = yf.Ticker(symbol_upper)
                news_list = ticker.news
                
                for news_item in news_list[:20]:  # Limit to 20 most recent
                    title = news_item.get('title', '')
                    summary = news_item.get('summary', '')
                    text = f"{title} {summary}"
                    
                    # Analyze sentiment
                    sentiment_result = sentiment_analyzer.analyze(text)
                    
                    # Determine if news is positive or negative
                    sentiment_score = sentiment_result.get('compound', 0)
                    if sentiment_score > 0.1:
                        sentiment_label = 'positive'
                    elif sentiment_score < -0.1:
                        sentiment_label = 'negative'
                    else:
                        sentiment_label = 'neutral'
                    
                    news_articles.append({
                        "title": title,
                        "description": summary,
                        "url": news_item.get('link', ''),
                        "source": news_item.get('publisher', 'Yahoo Finance'),
                        "publishedAt": news_item.get('providerPublishTime', 0),
                        "sentiment": {
                            "compound": sentiment_score,
                            "label": sentiment_label,
                            "positive": sentiment_result.get('positive', 0),
                            "negative": sentiment_result.get('negative', 0),
                            "neutral": sentiment_result.get('neutral', 0)
                        },
                        "impact": "high" if abs(sentiment_score) > 0.5 else "medium" if abs(sentiment_score) > 0.2 else "low"
                    })
            except Exception as e_yahoo:
                print(f"⚠️ Error fetching from Yahoo Finance: {e_yahoo}")
        
        # 4. แปลงรูปแบบข่าวให้ตรงกับ frontend
        analyzed_news = []
        for article in news_articles:
            # ถ้าเป็นข่าวจาก database
            if isinstance(article, dict) and 'title' in article:
                analyzed_news.append({
                    "title": article.get('title', ''),
                    "summary": article.get('description', article.get('summary', '')),
                    "link": article.get('url', ''),
                    "publisher": article.get('source', article.get('publisher', 'Yahoo Finance')),
                    "publishedAt": article.get('publishedAt', article.get('providerPublishTime', 0)),
                    "sentiment": article.get('sentiment', {
                        "compound": 0,
                        "label": "neutral",
                        "positive": 0,
                        "negative": 0,
                        "neutral": 1
                    }),
                    "impact": article.get('impact', 'medium')
                })
        
        # 5. Sort by published date (newest first)
        analyzed_news.sort(key=lambda x: x.get('publishedAt', 0), reverse=True)
        
        print(f"✅ Returning {len(analyzed_news)} news articles for {symbol_upper} from database")
        
        return jsonify({
            "symbol": symbol_upper,
            "news": analyzed_news,
            "total": len(analyzed_news),
            "positiveCount": sum(1 for n in analyzed_news if n.get('sentiment', {}).get('label') == 'positive'),
            "negativeCount": sum(1 for n in analyzed_news if n.get('sentiment', {}).get('label') == 'negative'),
            "neutralCount": sum(1 for n in analyzed_news if n.get('sentiment', {}).get('label') == 'neutral'),
            "source": "database" if news_articles else "yahoo_finance"
        })
    except Exception as e:
        print(f"❌ Error fetching news: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# ==========================
# ALERTS ENDPOINTS
# ==========================

@app.route("/api/alerts", methods=["GET"])
def get_alerts():
    """Get all alert rules"""
    try:
        alerts = list(db.alerts.find({}))
        for alert in alerts:
            alert["_id"] = str(alert["_id"])
        return jsonify({"alerts": alerts})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/alerts", methods=["POST"])
def create_alert():
    """Create a new alert rule"""
    try:
        data = request.json
        alert_rule = {
            "type": data.get("type"),
            "tickers": data.get("tickers", []),
            "threshold": data.get("threshold"),
            "sensitivity": data.get("sensitivity", "medium"),
            "deliveryMethods": data.get("deliveryMethods", []),
            "throttle": data.get("throttle", {}),
            "escalation": data.get("escalation", {}),
            "enabled": True,
            "createdAt": datetime.utcnow().isoformat()
        }
        
        result = db.alerts.insert_one(alert_rule)
        alert_rule["_id"] = str(result.inserted_id)
        return jsonify(alert_rule), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/alerts/<alert_id>", methods=["PUT"])
def update_alert(alert_id):
    """Update an alert rule"""
    try:
        data = request.json
        db.alerts.update_one(
            {"_id": alert_id},
            {"$set": data}
        )
        return jsonify({"message": "Alert updated"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/alerts/<alert_id>", methods=["DELETE"])
def delete_alert(alert_id):
    """Delete an alert rule"""
    try:
        db.alerts.delete_one({"_id": alert_id})
        return jsonify({"message": "Alert deleted"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/alerts/<alert_id>/acknowledge", methods=["POST"])
def acknowledge_alert(alert_id):
    """Acknowledge an alert"""
    try:
        db.alerts.update_one(
            {"_id": alert_id},
            {"$set": {"acknowledged": True, "acknowledgedAt": datetime.utcnow().isoformat()}}
        )
        return jsonify({"message": "Alert acknowledged"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/alerts/history")
def get_alert_history():
    """Get alert history"""
    try:
        filter_type = request.args.get("filter", "all")
        query = {}
        if filter_type == "acknowledged":
            query["acknowledged"] = True
        elif filter_type == "unacknowledged":
            query["acknowledged"] = {"$ne": True}
        
        history = list(db.alerts.find(query).sort("createdAt", -1).limit(100))
        for item in history:
            item["_id"] = str(item["_id"])
        return jsonify({"history": history})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==========================
# WATCHLIST ENDPOINTS
# ==========================

@app.route("/api/watchlist", methods=["GET"])
def get_watchlist():
    """Get user watchlist"""
    try:
        watchlist = db.watchlist.find_one({"userId": "default"})  # In production, use actual user ID
        if not watchlist:
            return jsonify({"tickers": []})
        return jsonify({"tickers": watchlist.get("tickers", [])})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/watchlist", methods=["POST"])
def add_to_watchlist():
    """Add ticker to watchlist"""
    try:
        data = request.json
        ticker = data.get("ticker", "").upper()
        
        db.watchlist.update_one(
            {"userId": "default"},
            {"$addToSet": {"tickers": ticker}},
            upsert=True
        )
        return jsonify({"message": f"Added {ticker} to watchlist"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/watchlist/<ticker>", methods=["DELETE"])
def remove_from_watchlist(ticker):
    """Remove ticker from watchlist"""
    try:
        db.watchlist.update_one(
            {"userId": "default"},
            {"$pull": {"tickers": ticker.upper()}}
        )
        return jsonify({"message": f"Removed {ticker} from watchlist"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==========================
# INFLUENCER ENDPOINTS
# ==========================

@app.route("/api/influencers", methods=["GET"])
def get_influencers():
    """Get all influencers"""
    try:
        filter_type = request.args.get("filter", "all")
        query = {}
        if filter_type == "followed":
            query["followed"] = True
        elif filter_type == "detected":
            query["detected"] = True
        elif filter_type == "suggested":
            query["suggested"] = True
        
        influencers = list(db.influencers.find(query))
        for inf in influencers:
            inf["_id"] = str(inf["_id"])
        return jsonify({"influencers": influencers})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/influencers/<influencer_id>/follow", methods=["POST"])
def follow_influencer(influencer_id):
    """Follow an influencer"""
    try:
        db.influencers.update_one(
            {"_id": influencer_id},
            {"$set": {"followed": True}}
        )
        return jsonify({"message": "Influencer followed"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/influencers/<influencer_id>/follow", methods=["DELETE"])
def unfollow_influencer(influencer_id):
    """Unfollow an influencer"""
    try:
        db.influencers.update_one(
            {"_id": influencer_id},
            {"$set": {"followed": False}}
        )
        return jsonify({"message": "Influencer unfollowed"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/influencers/<influencer_id>/timeline")
def get_influencer_timeline(influencer_id):
    """Get influencer timeline"""
    try:
        # Mock data - in production, would fetch from database
        timeline = [
            {
                "time": datetime.utcnow().isoformat(),
                "post": "Just bought more $AAPL",
                "impact": 1.82,
                "ticker": "AAPL"
            }
        ]
        return jsonify({"timeline": timeline})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==========================
# EXPORT ENDPOINTS
# ==========================

@app.route("/api/export/csv")
def export_csv():
    """Export data as CSV"""
    try:
        ticker = request.args.get("ticker")
        # In production, would generate CSV
        return jsonify({"message": "CSV export not yet implemented"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/export/excel")
def export_excel():
    """Export data as Excel"""
    try:
        ticker = request.args.get("ticker")
        # In production, would generate Excel
        return jsonify({"message": "Excel export not yet implemented"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==========================
# SETTINGS ENDPOINTS
# ==========================

@app.route("/api/settings", methods=["GET"])
def get_settings():
    """Get user settings"""
    try:
        userId = request.args.get("userId", "default")  # In production, use actual user ID
        settings = db.settings.find_one({"userId": userId})
        
        if settings:
            settings["_id"] = str(settings["_id"])
            # Don't return sensitive data in GET request
            if "apiKeys" in settings:
                # Only return if keys exist, but mask them
                settings["apiKeys"] = {
                    "newsApi": "***" if settings["apiKeys"].get("newsApi") else "",
                    "twitterToken": "***" if settings["apiKeys"].get("twitterToken") else ""
                }
            if "notifications" in settings:
                settings["notifications"] = {
                    "telegramToken": "***" if settings["notifications"].get("telegramToken") else "",
                    "lineToken": "***" if settings["notifications"].get("lineToken") else "",
                    "email": settings["notifications"].get("email", "")
                }
            return jsonify({"settings": settings})
        else:
            # Return default settings
            return jsonify({
                "settings": {
                    "userId": userId,
                    "theme": "dark",
                    "timezone": "UTC",
                    "defaultTimeRange": "24h",
                    "apiKeys": {"newsApi": "", "twitterToken": ""},
                    "notifications": {"telegramToken": "", "lineToken": "", "email": ""}
                }
            })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/settings", methods=["PUT"])
def update_settings():
    """Update user settings"""
    try:
        userId = request.args.get("userId", "default")
        data = request.json
        
        # Prepare update document
        update_doc = {
            "userId": userId,
            "updatedAt": datetime.utcnow().isoformat()
        }
        
        # Update theme, timezone, defaultTimeRange
        if "theme" in data:
            update_doc["theme"] = data["theme"]
        if "timezone" in data:
            update_doc["timezone"] = data["timezone"]
        if "defaultTimeRange" in data:
            update_doc["defaultTimeRange"] = data["defaultTimeRange"]
        
        # Update API keys (only if provided and not masked)
        if "apiKeys" in data:
            existing = db.settings.find_one({"userId": userId})
            api_keys = existing.get("apiKeys", {}) if existing else {}
            
            if data["apiKeys"].get("newsApi") and data["apiKeys"]["newsApi"] != "***":
                api_keys["newsApi"] = data["apiKeys"]["newsApi"]
            if data["apiKeys"].get("twitterToken") and data["apiKeys"]["twitterToken"] != "***":
                api_keys["twitterToken"] = data["apiKeys"]["twitterToken"]
            
            update_doc["apiKeys"] = api_keys
        
        # Update notification settings
        if "notifications" in data:
            existing = db.settings.find_one({"userId": userId})
            notifications = existing.get("notifications", {}) if existing else {}
            
            if data["notifications"].get("telegramToken") and data["notifications"]["telegramToken"] != "***":
                notifications["telegramToken"] = data["notifications"]["telegramToken"]
            if data["notifications"].get("lineToken") and data["notifications"]["lineToken"] != "***":
                notifications["lineToken"] = data["notifications"]["lineToken"]
            if data["notifications"].get("email"):
                notifications["email"] = data["notifications"]["email"]
            
            update_doc["notifications"] = notifications
        
        # Upsert settings
        db.settings.update_one(
            {"userId": userId},
            {"$set": update_doc},
            upsert=True
        )
        
        return jsonify({"message": "Settings updated successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==========================
# Run App
# ==========================
# ==========================
# Auto-fetch Scheduler (Background Thread)
# ==========================
POPULAR_TICKERS = ['AAPL', 'TSLA', 'NVDA', 'MSFT', 'AMZN', 'GOOGL', 'META', 'AMD', 'NFLX', 'SPY']

def fetch_stock_posts_background():
    """Fetch posts for popular stock tickers (runs in background)"""
    try:
        print(f"\n🔄 [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Auto-fetching posts for trending tickers...")
        
        total_fetched = 0
        for ticker in POPULAR_TICKERS:
            try:
                print(f"📊 Fetching posts for ${ticker}...")
                posts = fetch_posts(f"${ticker}", limit=20)
                total_fetched += len(posts) if posts else 0
                time.sleep(2)  # Rate limiting - wait 2 seconds between tickers
            except Exception as e:
                print(f"❌ Error fetching ${ticker}: {e}")
                continue
        
        print(f"✅ Auto-fetch completed: {total_fetched} total posts fetched")
        return total_fetched
    except Exception as e:
        print(f"❌ Error in background fetch: {e}")

def run_scheduler_background():
    """Run scheduler in background thread"""
    print("🚀 Starting background scheduler for auto-fetching posts...")
    print("📅 Schedule: Every 1 hour")
    
    # Schedule tasks
    schedule.every(1).hours.do(fetch_stock_posts_background)
    
    # Also run once immediately (after 30 seconds to let server start)
    time.sleep(30)
    fetch_stock_posts_background()
    
    # Run scheduler
    while True:
        try:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
        except Exception as e:
            print(f"❌ Error in scheduler: {e}")
            time.sleep(60)

# ============================================
# Batch Processing Endpoints
# ============================================

@app.route("/api/batch/process", methods=["POST"])
def batch_process_stocks():
    """
    ประมวลผลหุ้นแบบ batch (ดึงข้อมูลทั้งหมดมาครั้งเดียว)
    
    Body (JSON):
        {
            "symbols": ["AAPL", "TSLA", ...],  // Optional: ถ้าไม่ระบุจะดึงทั้งหมด
            "days_back": 7,  // Optional: จำนวนวันที่ดึงข่าวย้อนหลัง
            "batch_size": 100  // Optional: จำนวนหุ้นต่อ batch
        }
    """
    try:
        data = request.get_json() or {}
        symbols = data.get("symbols", [])
        days_back = data.get("days_back", 7)
        batch_size = data.get("batch_size", 100)
        
        # ถ้าไม่ระบุ symbols ให้ดึงทั้งหมด
        if not symbols:
            print("📋 Fetching all stock symbols...")
            all_symbols = stock_list_fetcher.get_all_valid_tickers(force_refresh=False)
            symbols = list(all_symbols) if all_symbols else []
        
        if not symbols:
            return jsonify({
                "success": False,
                "error": "No stock symbols found"
            }), 400
        
        print(f"🚀 Starting batch processing for {len(symbols)} stocks...")
        
        # ตั้งค่า batch processor
        batch_processor.days_back = days_back
        
        # รัน batch processing (async)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        results = loop.run_until_complete(
            batch_processor.process_all_stocks_async(symbols, batch_size=batch_size)
        )
        loop.close()
        
        return jsonify({
            "success": True,
            "processed": len(results),
            "total": len(symbols),
            "message": f"Successfully processed {len(results)}/{len(symbols)} stocks",
            "updatedAt": datetime.utcnow().isoformat()
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route("/api/batch/update", methods=["POST"])
def manual_update_stocks():
    """
    อัปเดตข้อมูลหุ้นด้วยตนเอง (ไม่ต้องรอ scheduled)
    
    Body (JSON):
        {
            "all_stocks": false  // true = อัปเดตทั้งหมด, false = อัปเดตเฉพาะหุ้นยอดนิยม
        }
    """
    try:
        data = request.get_json() or {}
        all_stocks = data.get("all_stocks", False)
        
        # รันการอัปเดต
        scheduled_updater.run_manual_update(all_stocks=all_stocks)
        
        return jsonify({
            "success": True,
            "message": "Update started",
            "all_stocks": all_stocks,
            "startedAt": datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route("/api/batch/status")
def batch_status():
    """ตรวจสอบสถานะ batch processing"""
    try:
        # นับจำนวนหุ้นใน database
        total_stocks = 0
        if db is not None and hasattr(db, 'stocks') and db.stocks is not None:
            total_stocks = db.stocks.count_documents({})
        
        # หาหุ้นที่อัปเดตล่าสุด
        latest_update = None
        if db is not None and hasattr(db, 'stocks') and db.stocks is not None:
            latest = db.stocks.find_one(sort=[("fetchedAt", -1)])
            if latest:
                latest_update_value = latest.get("fetchedAt")
                # แปลง datetime เป็น ISO format string ถ้าเป็น datetime object
                if isinstance(latest_update_value, datetime):
                    latest_update = latest_update_value.isoformat()
                elif isinstance(latest_update_value, str):
                    latest_update = latest_update_value
                else:
                    latest_update = str(latest_update_value) if latest_update_value else None
        
        # ตรวจสอบ scheduled_updater attributes
        scheduler_running = False
        update_interval_hours = 0.5  # ✅ default value: 30 นาที (0.5 ชั่วโมง)
        next_update_info = None
        try:
            if hasattr(scheduled_updater, 'is_running'):
                scheduler_running = scheduled_updater.is_running
            if hasattr(scheduled_updater, 'update_interval_hours'):
                update_interval_hours = scheduled_updater.update_interval_hours
            # ✅ ดึงข้อมูลเวลาที่จะอัปเดตครั้งถัดไป
            if hasattr(scheduled_updater, 'get_next_update_time'):
                next_update_info = scheduled_updater.get_next_update_time()
        except Exception as e:
            print(f"⚠️ Error getting scheduler status: {e}")
        
        return jsonify({
            "total_stocks": total_stocks,
            "latest_update": latest_update,
            "scheduler_running": scheduler_running,
            "update_interval_hours": update_interval_hours,
            "next_update": next_update_info  # ✅ เพิ่มข้อมูลเวลาที่จะอัปเดตครั้งถัดไป
        })
    except Exception as e:
        import traceback
        print(f"❌ Error in batch_status: {e}")
        traceback.print_exc()
        return jsonify({
            "error": str(e),
            "message": "Error checking batch status"
        }), 500

@app.route("/api/batch/fetch-news", methods=["POST"])
def batch_fetch_news():
    """
    ดึงข่าวจากหุ้นทั้งหมดที่มีใน database
    ใช้รายชื่อหุ้นจาก db.stock_tickers หรือ db.stocks
    
    Body (JSON):
        {
            "batch_size": 50,  // Optional: จำนวนหุ้นต่อ batch
            "max_news_per_stock": 100,  // Optional: จำนวนข่าวสูงสุดต่อหุ้น
            "force_refresh": false  // Optional: ดึงใหม่แม้จะมีข่าวอยู่แล้ว
        }
    """
    try:
        data = request.get_json() or {}
        batch_size = data.get("batch_size", 50)
        max_news_per_stock = data.get("max_news_per_stock", 100)
        force_refresh = data.get("force_refresh", False)
        
        print(f"📰 Starting news fetching for all stocks in database...")
        
        # ดึงรายชื่อหุ้นจาก database
        symbols = []
        
        # วิธีที่ 1: ดึงจาก db.stock_tickers
        if db is not None and hasattr(db, 'stock_tickers') and db.stock_tickers is not None:
            ticker_docs = db.stock_tickers.find({"isActive": True})
            symbols = [doc["ticker"] for doc in ticker_docs if doc.get("ticker")]
            print(f"  ✅ Found {len(symbols)} stocks from db.stock_tickers")
        
        # วิธีที่ 2: ถ้าไม่มีใน stock_tickers ให้ดึงจาก stock_list_fetcher
        if not symbols:
            print(f"  📋 Fetching from stock_list_fetcher...")
            all_symbols = stock_list_fetcher.get_all_valid_tickers(force_refresh=False)
            symbols = list(all_symbols) if all_symbols else []
            print(f"  ✅ Found {len(symbols)} stocks from stock_list_fetcher")
        
        # วิธีที่ 3: ดึงจาก db.stocks (หุ้นที่มีข้อมูลอยู่แล้ว)
        if not symbols and db is not None and hasattr(db, 'stocks') and db.stocks is not None:
            stock_docs = db.stocks.find({}, {"symbol": 1})
            symbols = [doc["symbol"] for doc in stock_docs if doc.get("symbol")]
            symbols = list(set(symbols))  # Remove duplicates
            print(f"  ✅ Found {len(symbols)} stocks from db.stocks")
        
        if not symbols:
            return jsonify({
                "success": False,
                "error": "No stock symbols found in database",
                "message": "Please ensure stock tickers are loaded in database first"
            }), 400
        
        print(f"🚀 Starting news fetching for {len(symbols)} stocks...")
        print(f"   Batch size: {batch_size}")
        print(f"   Max news per stock: {max_news_per_stock}")
        print(f"   Force refresh: {force_refresh}")
        
        # ตั้งค่า batch processor
        batch_processor.days_back = 7
        
        # ถ้า force_refresh = False ให้ skip หุ้นที่มีข่าวอยู่แล้ว
        if not force_refresh:
            print(f"  ⏭️  Skipping stocks that already have news...")
            symbols_to_process = []
            for symbol in symbols:
                symbol_upper = symbol.upper()
                from utils.post_normalizer import get_collection_name
                collection_name = get_collection_name('yahoo')
                if db is not None and hasattr(db, collection_name) and getattr(db, collection_name) is not None:
                    post_collection = getattr(db, collection_name)
                    news_count = post_collection.count_documents({"symbol": symbol_upper})
                    if news_count == 0:
                        symbols_to_process.append(symbol)
                    else:
                        print(f"    ⏭️  Skipping {symbol_upper} (already has {news_count} news)")
            symbols = symbols_to_process
            print(f"  ✅ {len(symbols)} stocks need news fetching")
        
        if not symbols:
            return jsonify({
                "success": True,
                "message": "All stocks already have news in database",
                "total_stocks": len(symbols),
                "processed": 0
            })
        
        # รัน batch processing (async) - ดึงเฉพาะข่าว
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        results = loop.run_until_complete(
            batch_processor.process_all_stocks_async(symbols, batch_size=batch_size)
        )
        loop.close()
        
        # นับจำนวนข่าวที่ดึงมา (ใช้ collection post_yahoo)
        from utils.post_normalizer import get_collection_name
        total_news = 0
        collection_name = get_collection_name('yahoo')
        if db is not None and hasattr(db, collection_name) and getattr(db, collection_name) is not None:
            post_collection = getattr(db, collection_name)
            total_news = post_collection.count_documents({})
        
        return jsonify({
            "success": True,
            "processed": len(results),
            "total": len(symbols),
            "total_news_in_db": total_news,
            "message": f"Successfully fetched news for {len(results)}/{len(symbols)} stocks",
            "updatedAt": datetime.utcnow().isoformat()
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route("/api/news-summary")
def get_news_summary():
    """
    สรุปข้อมูลข่าวใน database:
    - จำนวนหุ้นที่มีข่าว
    - จำนวนข่าวต่อหุ้น
    - จำนวนข่าวทั้งหมด
    """
    try:
        from utils.post_normalizer import get_collection_name
        collection_name = get_collection_name('yahoo')
        if db is None or not hasattr(db, collection_name) or getattr(db, collection_name) is None:
            return jsonify({
                "error": "Database not available",
                "message": "Database connection not available"
            }), 500
        
        post_collection = getattr(db, collection_name)
        
        # นับจำนวนข่าวทั้งหมด
        total_news = post_collection.count_documents({})
        
        # นับจำนวนหุ้นที่มีข่าว (distinct symbols)
        distinct_symbols = post_collection.distinct("symbol")
        total_stocks = len(distinct_symbols)
        
        # นับจำนวนข่าวต่อหุ้น
        news_per_stock = []
        for symbol in distinct_symbols:
            count = post_collection.count_documents({"symbol": symbol})
            news_per_stock.append({
                "symbol": symbol,
                "count": count
            })
        
        # เรียงตามจำนวนข่าว (มากไปน้อย)
        news_per_stock.sort(key=lambda x: x["count"], reverse=True)
        
        # สรุปสถิติ
        if news_per_stock:
            max_news = max(item["count"] for item in news_per_stock)
            min_news = min(item["count"] for item in news_per_stock)
            avg_news = sum(item["count"] for item in news_per_stock) / len(news_per_stock)
        else:
            max_news = 0
            min_news = 0
            avg_news = 0
        
        # Top 10 หุ้นที่มีข่าวมากที่สุด
        top_10_stocks = news_per_stock[:10]
        
        return jsonify({
            "summary": {
                "total_news": total_news,
                "total_stocks_with_news": total_stocks,
                "average_news_per_stock": round(avg_news, 2),
                "max_news_per_stock": max_news,
                "min_news_per_stock": min_news
            },
            "top_10_stocks": top_10_stocks,
            "all_stocks": news_per_stock,
            "fetchedAt": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        import traceback
        print(f"❌ Error in news-summary: {e}")
        print(traceback.format_exc())
        return jsonify({
            "error": str(e),
            "message": f"Error fetching news summary: {str(e)}"
        }), 500

if __name__ == "__main__":
    print("✅ MongoDB connected successfully!")
    # Initialize database collections
    if db is not None:
        initialize_collections(db)
    
    # ปิด background scheduler เพราะ scheduled_updater จัดการทุกอย่างแล้ว
    # เพื่อหลีกเลี่ยงการทำงานซ้ำกัน
    # scheduler_thread = threading.Thread(target=run_scheduler_background, daemon=True)
    # scheduler_thread.start()
    # print("✅ Background scheduler started (auto-fetch every 1 hour)")
    
    # ✅ Start scheduled updater (อัปเดตข้อมูลหุ้นทุก 30 นาที)
    # scheduled_updater จะจัดการการดึงข้อมูลทั้งหมด (Reddit, News, etc.)
    # ตรวจสอบว่ามีข้อมูลใน database หรือยัง - ถ้ามีแล้วจะไม่รัน initial update
    from database.db_config import db
    run_initial = True
    if db is not None and hasattr(db, 'stocks') and db.stocks is not None:
        stock_count = db.stocks.count_documents({})
        if stock_count > 100:  # ถ้ามีข้อมูลมากกว่า 100 หุ้น → ไม่รัน initial update
            run_initial = False
            print("✅ มีข้อมูลใน database แล้ว - ข้าม initial update")
            print("   💡 ใช้ /api/batch/update เพื่ออัปเดตข้อมูลด้วยตนเอง")
    
    # ✅ Start Reddit bulk scheduler (ดึง Reddit ทุก 45 วินาที)
    reddit_bulk_scheduler.start()
    print("✅ Reddit bulk scheduler started (fetches Reddit every 45 seconds)")
    
    scheduled_updater.start(run_initial_update=run_initial)
    print("✅ Scheduled updater started (updates Yahoo Finance every 30 minutes)")
    
    print("🚀 Flask API running on http://127.0.0.1:5000")
    print("💡 Reddit bulk scheduler: ดึง Reddit ทุก 45 วินาที")
    print("💡 Scheduled updater: อัปเดต Yahoo Finance ทุก 30 นาที (เฉพาะหุ้นที่เก่า)")
    print("💡 Batch processor is ready - use /api/batch/process to process all stocks")
    print("💡 Use /api/batch/fetch-news to fetch news for all stocks")
    print("")
    print("="*70)
    print("✅ ระบบทำงานต่อเนื่องใน background")
    print("   - Reddit: ดึงข้อมูลทุก 45 วินาที (ทำงานต่อเนื่อง)")
    print("   - Yahoo Finance: อัปเดตทุก 30 นาที (ทำงานต่อเนื่อง)")
    print("   - ข้อมูลจะถูกโหลดเข้ามาใน database อัตโนมัติแม้ไม่มีผู้ใช้ใช้งาน")
    print("="*70)
    print("")
    # ✅ ใช้ threaded=True เพื่อให้ Flask รองรับ multiple requests
    # ✅ ใช้ use_reloader=False เพื่อป้องกันการ restart เมื่อโค้ดไม่เปลี่ยน
    app.run(debug=True, threaded=True, use_reloader=False)
