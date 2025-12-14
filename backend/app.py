from flask import Flask, jsonify, request, Response
from db_config import db
from fetch_reddit import fetch_posts
from bson.json_util import dumps
from flask_cors import CORS
from dotenv import load_dotenv
import os
import random
import pandas as pd
from datetime import datetime, timedelta
from data_aggregator import DataAggregator
from stock_data import StockDataFetcher
from sentiment_analyzer import SentimentAnalyzer
from db_schema import initialize_collections
from cache_manager import cache
from ticker_validator import ticker_validator
from retry_handler import retry_on_failure
from stock_list_fetcher import stock_list_fetcher
import schedule
import threading
import time
import yfinance as yf

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
        if db:
            # Indexes for posts collection
            db.posts.create_index([("keyword", 1), ("created_utc", -1)])
            db.posts.create_index([("ticker", 1), ("sentiment", -1)])
            db.posts.create_index("created_utc")
            print("✅ Database indexes created successfully")
    except Exception as e:
        print(f"⚠️ Error creating indexes: {e}")

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
    posts = list(db.posts.find({"keyword": keyword}))
    return export_posts_to_excel(posts, keyword, output_dir)


# ==========================
# Route: Download Excel
# ==========================
@app.route("/api/download")
def download_data():
    keyword = request.args.get("keyword", "AI")
    posts_cursor = db.posts.find({"keyword": keyword})
    posts = list(posts_cursor)
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

    pipeline = [
        {"$match": {"keyword": keyword}},
        {"$group": {"_id": "$keyword", "count": {"$sum": 1}}}
    ]
    result = list(db.posts.aggregate(pipeline))
    posts = [serialize_doc(p) for p in db.posts.find({"keyword": keyword}).sort("score", -1).limit(10)]

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
    posts = list(db.posts.find().sort("created_utc", -1).limit(50))
    return dumps(posts)

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

        pipeline = [
            {"$match": {"keyword": kw}},
            {"$group": {"_id": "$created_utc", "count": {"$sum": 1}}},
            {"$sort": {"_id": 1}}
        ]
        counts = list(db.posts.aggregate(pipeline))
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
    """Get aggregated stock data (price, sentiment, news, trends)"""
    try:
        days_back = int(request.args.get("days", 7))
        data = data_aggregator.aggregate_stock_data(symbol.upper(), days_back)
        
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
    """Get current stock price and info"""
    try:
        info = stock_fetcher.get_stock_info(symbol.upper())
        if not info:
            return jsonify({"error": "Stock not found"}), 404
        return jsonify(info)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/stock/<symbol>/info")
def get_stock_info(symbol):
    """Get current stock price and info (alias for /price endpoint)"""
    try:
        info = stock_fetcher.get_stock_info(symbol.upper())
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
        if db:
            ticker_docs = db.stock_tickers.find({})
            for doc in ticker_docs:
                exchange = doc.get('exchange', 'UNKNOWN')
                exchange_counts[exchange] = exchange_counts.get(exchange, 0) + 1
        
        # Get last updated time
        last_updated = None
        if db:
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
        source = request.args.get("source", "yahoo")  # default เป็น yahoo (primary source)
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
        
        # Build query - handle both datetime objects and string timestamps
        # Try datetime first, then fallback to string comparison
        time_query = {"created_utc": {"$gte": cutoff}}
        
        if source != "all":
            time_query["source"] = source
        
        # Get posts from database with filter
        posts = list(db.posts.find(time_query).sort("created_utc", -1).limit(5000))
        
        # If no posts found, try with string comparison (in case created_utc is stored as string)
        if not posts:
            time_query_str = {"created_utc": {"$gte": cutoff.isoformat()}}
            if source != "all":
                time_query_str["source"] = source
            posts = list(db.posts.find(time_query_str).sort("created_utc", -1).limit(5000))
        
        # If no posts with time filter, try without time filter (for testing/development)
        # But only if we have no posts at all - this helps during development
        if not posts:
            print(f"⚠️ No posts found with time filter (cutoff: {cutoff.isoformat()}), trying without time filter...")
            query = {}
            if source != "all":
                query["source"] = source
            posts = list(db.posts.find(query).sort("created_utc", -1).limit(5000))
            if posts:
                print(f"✅ Found {len(posts)} posts without time filter (showing all available data)")
        
        if not posts:
            print(f"No posts found in database for source: {source}")
            return jsonify({
                "topics": [],
                "message": f"No posts found for source '{source}'. Make sure data has been fetched.",
                "source": source,
                "timeRange": time_range,
                "totalPosts": 0
            })
        
        # Extract stock tickers ($SYMBOL format) from all posts
        # Count ALL mentions (not just once per post) to reflect true trending
        ticker_freq = {}
        ticker_sources = {}  # Track which sources mention each ticker
        ticker_sentiment = {}  # Track average sentiment per ticker
        ticker_posts = {}  # Track unique posts mentioning each ticker
        
        # Regex pattern to match $SYMBOL format (1-5 uppercase letters after $)
        ticker_pattern = re.compile(r'\$([A-Z]{1,5})\b')
        
        for post in posts:
            # Combine all text fields
            text = f"{post.get('title', '')} {post.get('selftext', '')} {post.get('text', '')} {post.get('body', '')}"
            post_source = post.get('source', 'unknown')
            post_sentiment = post.get('sentiment', {}).get('compound', 0) if isinstance(post.get('sentiment'), dict) else post.get('sentiment_score', 0)
            post_id = str(post.get('_id', ''))
            
            # Find all stock tickers in the text (count ALL occurrences for trending)
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
        
        # Convert to list with additional metadata
        topics = []
        for ticker, count in ticker_freq.items():
            # Calculate average sentiment
            sentiments = ticker_sentiment.get(ticker, [])
            avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0
            
            # Get unique post count
            unique_post_count = len(ticker_posts.get(ticker, set()))
            
            topics.append({
                "word": ticker,  # Keep 'word' for compatibility
                "ticker": ticker,  # Add explicit ticker field
                "count": count,  # Total mentions (all occurrences)
                "mentions": count,  # Alias for count
                "uniquePosts": unique_post_count,  # Number of unique posts
                "sources": list(ticker_sources.get(ticker, set())),
                "sourceCount": len(ticker_sources.get(ticker, set())),
                "avgSentiment": round(avg_sentiment, 3)
            })
        
        # Sort by mention count (most mentioned first) - ALWAYS show highest mentions first
        topics.sort(key=lambda x: x["count"], reverse=True)
        
        # Log top 5 for debugging
        if topics:
            print(f"📊 Top 5 trending tickers: {[(t['ticker'], t['count']) for t in topics[:5]]}")
        
        result = {
            "topics": topics[:100],  # Top 100 (เพิ่มจาก 50 เพื่อให้หุ้นที่อยู่นอก 50 มีโอกาสเข้ามา)
            "source": source,
            "timeRange": time_range,
            "totalPosts": len(posts),
            "totalTickers": len(topics)
        }
        
        # If no tickers found, add helpful message
        if len(topics) == 0:
            result["message"] = f"No stock tickers ($SYMBOL) found. Analyzed {len(posts)} posts. Make sure posts contain stock tickers in $SYMBOL format."
        
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
    """Fetch new posts from Reddit for trending stock tickers"""
    try:
        # Get popular stock tickers to fetch
        popular_tickers = ["AAPL", "TSLA", "NVDA", "MSFT", "AMZN", "GOOGL", "META", "AMD", "NFLX", "SPY"]
        
        total_fetched = 0
        for ticker in popular_tickers:
            try:
                print(f"📊 Fetching posts for ${ticker}...")
                posts = fetch_posts(f"${ticker}", limit=20)
                total_fetched += len(posts) if posts else 0
            except Exception as e:
                print(f"⚠️ Error fetching posts for ${ticker}: {e}")
                continue
        
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
    ดึงข้อมูล real-time จากหลาย API sources (Reddit, News, Twitter, etc.)
    รวมข้อมูลจากทุก sources มา analyze ร่วมกัน
    วิเคราะห์ mentions และส่งกลับไปแสดงผลทันที
    """
    try:
        from fetch_reddit import reddit
        from sentiment_analyzer import SentimentAnalyzer
        from news_fetcher import NewsFetcher
        from twitter_fetcher import TwitterFetcher
        from youtube_fetcher import YouTubeFetcher
        import re
        
        # รองรับหลาย sources: all, yahoo, reddit, news, twitter, youtube
        source = request.args.get("source", "yahoo")  # default เป็น yahoo (primary source)
        subreddits = request.args.get("subreddits", "all,stocks,investing,StockMarket,wallstreetbets").split(",")
        
        # กำหนด limit - default เป็น 50 เพื่อความเร็ว
        requested_limit = int(request.args.get("limit", "50"))  # Default เป็น 50 สำหรับความเร็ว
        
        # จำกัดสูงสุดที่ 100 เพื่อป้องกัน timeout และ rate limit (ลดจาก 500)
        limit_per_subreddit = min(requested_limit, 100)
        
        # ถ้า request มากกว่า 100 ให้แจ้งเตือน
        if requested_limit > 100:
            print(f"⚠️ Requested limit {requested_limit} is too high. Capping at 100 to prevent timeout.")
        
        # แนะนำ limit ตามจำนวน subreddits
        # ถ้ามีหลาย subreddits ให้ลด limit ต่อ subreddit
        num_subreddits = len([s for s in subreddits if s.strip() and s.strip() != "all"])
        if num_subreddits == 0:  # ถ้าเป็น "all" จะดึง 6 subreddits
            num_subreddits = 6
        
        # ไม่ต้องลด limit - ใช้ parallel processing แทน
        
        sort_by = request.args.get("sort", "hot")  # hot, new, top
        
        print(f"🔄 Fetching real-time data from multiple sources")
        print(f"   Sources: {source}")
        print(f"   Subreddits: {subreddits}")
        print(f"   Limit per subreddit: {limit_per_subreddit} (requested: {requested_limit})")
        
        # เก็บ posts ทั้งหมดจากทุก sources
        all_posts = []
        ticker_freq = {}
        ticker_sources = {}
        ticker_sentiment = {}
        ticker_posts = {}
        ticker_details = {}  # เก็บรายละเอียด post ที่ mention ticker
        
        # Regex pattern สำหรับหา $SYMBOL
        ticker_pattern = re.compile(r'\$([A-Z]{1,5})\b')
        
        # False positives ที่ต้องกรอง
        false_positives = {'USD', 'GDP', 'CEO', 'IPO', 'ETF', 'SEC', 'IRS', 'FDA', 'AI', 'IT', 'TV', 'PC', 'USA', 'UK', 'EU'}
        
        # สร้าง sentiment analyzer และ fetchers
        sentiment_analyzer = SentimentAnalyzer()
        from yahoo_finance_fetcher import YahooFinanceFetcher
        yahoo_fetcher = YahooFinanceFetcher()
        news_fetcher = NewsFetcher()
        twitter_fetcher = TwitterFetcher()
        youtube_fetcher = YouTubeFetcher()
        
        # ใช้ concurrent processing เพื่อความเร็ว
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import time as time_module
        
        start_time = time_module.time()
        
        # ============================================
        # 0. ดึงข้อมูลจาก YAHOO FINANCE (Primary Source - ฟรี, เร็ว, แม่นยำ)
        # ============================================
        if source == "all" or source == "yahoo":
            print(f"  📈 Fetching from Yahoo Finance (primary source)...")
            try:
                # ดึงข้อมูลหุ้นยอดนิยมจาก indices
                popular_tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'AVGO', 'COST', 'NFLX',
                                 'AMD', 'PEP', 'ADBE', 'CSCO', 'CMCSA', 'INTC', 'QCOM', 'INTU', 'AMGN', 'ISRG',
                                 'BKNG', 'VRTX', 'REGN', 'AMAT', 'ADI', 'SNPS', 'CDNS', 'MELI', 'LRCX', 'KLAC']
                
                # ดึงข่าวและข้อมูลจาก Yahoo Finance
                # ใช้ parallel processing เพื่อความเร็ว แต่จำกัดจำนวนเพื่อหลีกเลี่ยง rate limit
                yahoo_news_count = 0
                
                # ลดจำนวน tickers และเพิ่ม delay เพื่อหลีกเลี่ยง rate limiting
                tickers_to_fetch = popular_tickers[:10]  # ลดจาก 20 เป็น 10
                
                def fetch_yahoo_news_for_ticker(ticker_symbol):
                    """Helper function to fetch news for a single ticker"""
                    try:
                        # เพิ่ม delay เล็กน้อยระหว่าง requests
                        time_module.sleep(0.1)  # 100ms delay
                        news = yahoo_fetcher.get_stock_news(ticker_symbol, max_results=10)
                        return ticker_symbol, news
                    except Exception as e:
                        print(f"  ⚠️ Error in fetch_yahoo_news_for_ticker({ticker_symbol}): {e}")
                        return ticker_symbol, []
                
                # ใช้ parallel processing แต่จำกัด workers เพื่อหลีกเลี่ยง rate limit
                with ThreadPoolExecutor(max_workers=3) as executor:
                    futures = {executor.submit(fetch_yahoo_news_for_ticker, ticker): ticker for ticker in tickers_to_fetch}
                    
                    for future in as_completed(futures, timeout=30):
                        ticker = futures[future]
                        try:
                            ticker_symbol, news = future.result(timeout=10)
                            if news:
                                yahoo_news_count += len(news)
                                
                                # วิเคราะห์ sentiment
                                texts = [f"{a.get('title', '')} {a.get('summary', '')}" for a in news if a.get('title') or a.get('summary')]
                                if texts:
                                    sentiments = [sentiment_analyzer.analyze(text) for text in texts]
                                    
                                    # สร้าง post data จากข่าว Yahoo Finance
                                    for idx, article in enumerate(news):
                                        sentiment = sentiments[idx] if idx < len(sentiments) else {"compound": 0, "label": "neutral"}
                                        
                                        # Handle publishedAt - อาจเป็น timestamp หรือ 0
                                        published_at = article.get('publishedAt', 0)
                                        if published_at == 0:
                                            published_at = time_module.time()
                                        elif isinstance(published_at, (int, float)) and published_at > 0:
                                            pass  # Already a timestamp
                                        else:
                                            published_at = time_module.time()
                                        
                                        post_data = {
                                            "id": article.get('uuid', f"yahoo_{len(all_posts)}"),
                                            "title": article.get('title', ''),
                                            "selftext": article.get('summary', ''),
                                            "score": 0,
                                            "num_comments": 0,
                                            "created_utc": datetime.fromtimestamp(published_at),
                                            "subreddit": article.get('source', 'Yahoo Finance'),
                                            "url": article.get('url', ''),
                                            "author": article.get('author', 'Yahoo Finance'),
                                            "sentiment": sentiment,
                                            "source": "yahoo"
                                        }
                                        all_posts.append(post_data)
                                        
                                        # หา tickers ในข่าว
                                        full_text = f"{article.get('title', '')} {article.get('summary', '')}".upper()
                                        tickers = ticker_pattern.findall(full_text)
                                        
                                        unique_tickers_in_post = set()
                                        
                                        for found_ticker in tickers:
                                            if found_ticker in false_positives:
                                                continue
                                            
                                            ticker_freq[found_ticker] = ticker_freq.get(found_ticker, 0) + 1
                                            
                                            if found_ticker not in ticker_details:
                                                ticker_details[found_ticker] = []
                                            
                                            if found_ticker not in unique_tickers_in_post:
                                                unique_tickers_in_post.add(found_ticker)
                                                ticker_details[found_ticker].append({
                                                    "post_id": post_data["id"],
                                                    "title": article.get('title', ''),
                                                    "subreddit": article.get('source', 'Yahoo Finance'),
                                                    "score": 0,
                                                    "url": article.get('url', ''),
                                                    "created_utc": post_data["created_utc"].isoformat() if hasattr(post_data["created_utc"], 'isoformat') else str(post_data["created_utc"])
                                                })
                                            
                                            if found_ticker not in ticker_sources:
                                                ticker_sources[found_ticker] = set()
                                            ticker_sources[found_ticker].add("yahoo")
                                            
                                            if found_ticker not in ticker_sentiment:
                                                ticker_sentiment[found_ticker] = []
                                            ticker_sentiment[found_ticker].append(sentiment.get('compound', 0))
                        except Exception as e:
                            print(f"  ⚠️ Error processing Yahoo Finance data for {ticker}: {e}")
                            continue
                
                print(f"  ✅ Yahoo Finance: {yahoo_news_count} news articles processed")
            except Exception as e:
                print(f"  ⚠️ Error fetching Yahoo Finance data: {e}")
                import traceback
                traceback.print_exc()
        
        # ============================================
        # 1. ดึงข้อมูลจาก REDDIT (Parallel Processing)
        # ============================================
        def fetch_reddit_subreddit(stock_sub, limit, sort):
            """Helper function to fetch from a single subreddit"""
            posts = []
            try:
                subreddit = reddit.subreddit(stock_sub)
                if sort == "hot":
                    submissions = list(subreddit.hot(limit=limit))  # Convert to list เพื่อให้เร็วขึ้น
                elif sort == "new":
                    submissions = list(subreddit.new(limit=limit))
                elif sort == "top":
                    submissions = list(subreddit.top(limit=limit, time_filter="day"))
                else:
                    submissions = list(subreddit.hot(limit=limit))
                
                # เก็บข้อมูล submissions ก่อน แล้ววิเคราะห์ sentiment แบบ batch (เร็วกว่า)
                submission_list = []
                texts = []
                
                for submission in submissions:
                    try:
                        text = f"{submission.title} {getattr(submission, 'selftext', '') or ''}"
                        texts.append(text)
                        submission_list.append({
                            "id": submission.id,
                            "title": submission.title,
                            "selftext": getattr(submission, 'selftext', '') or '',
                            "score": submission.score or 0,
                            "num_comments": submission.num_comments or 0,
                            "created_utc": datetime.utcfromtimestamp(submission.created_utc),
                            "subreddit": str(submission.subreddit),
                            "url": submission.url,
                            "author": str(submission.author) if submission.author else "[deleted]"
                        })
                    except Exception as e:
                        continue
                
                # วิเคราะห์ sentiment แบบ batch (เร็วกว่ามาก)
                if texts:
                    # ใช้ list comprehension แทน loop เพื่อความเร็ว
                    sentiments = [sentiment_analyzer.analyze(text) for text in texts]
                    
                    # รวมข้อมูล
                    for idx, sub_data in enumerate(submission_list):
                        if idx < len(sentiments):
                            sub_data["sentiment"] = sentiments[idx]
                            sub_data["source"] = "reddit"
                            posts.append(sub_data)
            except Exception as e:
                print(f"⚠️ Error fetching from r/{stock_sub}: {e}")
            return posts
        
        if source == "all" or source == "reddit":
            print(f"  🔴 Fetching from Reddit (parallel)...")
            reddit_posts_count = 0
            
            # กำหนด subreddits ที่จะดึง
            stock_subreddits = []
            for subreddit_name in subreddits:
                subreddit_name = subreddit_name.strip()
                if not subreddit_name or subreddit_name == "all":
                    stock_subreddits = ["stocks", "investing", "StockMarket", "wallstreetbets", "options", "SecurityAnalysis"]
                    break
                else:
                    stock_subreddits.append(subreddit_name)
            
            # ดึงข้อมูลแบบ parallel (พร้อมกันหลาย subreddits)
            # ลดจำนวน subreddits และ limit เพื่อให้สมดุลกับแหล่งอื่น
            max_subreddits = 4  # ลดจาก 6 เป็น 4 เพื่อให้สมดุลกับ News/Twitter/YouTube
            with ThreadPoolExecutor(max_workers=3) as executor:  # ลด threads เพื่อประหยัด resources
                futures = {
                    executor.submit(fetch_reddit_subreddit, stock_sub, limit_per_subreddit, sort_by): stock_sub 
                    for stock_sub in stock_subreddits[:max_subreddits]
                }
                
                # คำนวณ timeout ตาม limit (50 posts = 45s, 100 posts = 90s)
                timeout_seconds = max(45, (limit_per_subreddit / 50) * 45)
                individual_timeout = max(20, (limit_per_subreddit / 50) * 20)
                
                completed_count = 0
                total_futures = len(futures)
                
                try:
                    for future in as_completed(futures, timeout=timeout_seconds):
                        stock_sub = futures[future]
                        try:
                            posts = future.result(timeout=individual_timeout)
                            completed_count += 1
                            
                            # ประมวลผล posts แบบ batch เพื่อความเร็ว
                            for post_data in posts:
                                all_posts.append(post_data)
                                reddit_posts_count += 1
                            
                            # หา tickers จากทุก posts พร้อมกัน (เร็วกว่า)
                            texts_for_tickers = [f"{p['title']} {p['selftext']}".upper() for p in posts]
                            all_tickers_found = []
                            post_ticker_map = []  # map post index กับ tickers
                            
                            for text in texts_for_tickers:
                                tickers = ticker_pattern.findall(text)
                                filtered_tickers = [t for t in tickers if t not in false_positives]
                                all_tickers_found.extend(filtered_tickers)
                                post_ticker_map.append(filtered_tickers)
                            
                            # นับ mentions และเก็บข้อมูล (เร็วกว่าเพราะทำครั้งเดียว)
                            for idx, post_data in enumerate(posts):
                                unique_tickers_in_post = set(post_ticker_map[idx]) if idx < len(post_ticker_map) else set()
                                
                                for ticker in unique_tickers_in_post:
                                    # นับ mentions
                                    ticker_freq[ticker] = ticker_freq.get(ticker, 0) + 1
                                    
                                    # เก็บรายละเอียด post
                                    if ticker not in ticker_details:
                                        ticker_details[ticker] = []
                                    
                                    ticker_details[ticker].append({
                                        "post_id": post_data["id"],
                                        "title": post_data["title"],
                                        "subreddit": post_data["subreddit"],
                                        "score": post_data["score"],
                                        "url": post_data["url"],
                                        "created_utc": post_data["created_utc"].isoformat() if hasattr(post_data["created_utc"], 'isoformat') else str(post_data["created_utc"])
                                    })
                                    
                                    # Track sources
                                    if ticker not in ticker_sources:
                                        ticker_sources[ticker] = set()
                                    ticker_sources[ticker].add("reddit")
                                    
                                    # Track sentiment
                                    if ticker not in ticker_sentiment:
                                        ticker_sentiment[ticker] = []
                                    ticker_sentiment[ticker].append(post_data.get('sentiment', {}).get('compound', 0))
                        except Exception as e:
                            completed_count += 1
                            print(f"⚠️ Error processing r/{stock_sub}: {e}")
                            continue
                    
                    # แจ้งเตือนถ้ามี futures ที่ยังไม่เสร็จ
                    if completed_count < total_futures:
                        print(f"⚠️ Warning: Only {completed_count}/{total_futures} subreddits completed (timeout: {timeout_seconds}s)")
                        
                except TimeoutError:
                    print(f"⚠️ Timeout after {timeout_seconds}s: {completed_count}/{total_futures} subreddits completed")
                    print(f"   Consider reducing limit from {limit_per_subreddit} to 50 or less")
            
            print(f"  ✅ Reddit: {reddit_posts_count} posts processed")
        
        # ============================================
        # 2. ดึงข้อมูลจาก NEWS API (ลดจำนวนเพื่อความเร็ว)
        # ============================================
        if source == "all" or source == "news":
            print(f"  📰 Fetching from News API...")
            try:
                # เพิ่ม queries และ limit เพื่อให้สมดุลกับ Reddit
                news_queries = ["stock market", "stocks", "trading", "investing", "NASDAQ", "NYSE", 
                               "financial news", "market analysis", "stock price", "earnings"]
                news_articles = []
                
                # ดึงข้อมูลแบบ parallel เพื่อความเร็ว
                def fetch_news_query(query):
                    try:
                        return news_fetcher.fetch_news(query, days_back=1, max_results=30)  # เพิ่มจาก 20 เป็น 30
                    except:
                        return []
                
                with ThreadPoolExecutor(max_workers=4) as executor:  # เพิ่ม workers
                    futures = {executor.submit(fetch_news_query, query): query for query in news_queries}
                    for future in as_completed(futures, timeout=20):  # เพิ่ม timeout
                        try:
                            articles = future.result(timeout=5)
                            news_articles.extend(articles)
                            if len(news_articles) >= 100:  # เพิ่มจาก 50 เป็น 100
                                break
                        except:
                            continue
                
                # วิเคราะห์ sentiment แบบ batch (เร็วกว่า)
                news_texts = [f"{a.get('title', '')} {a.get('description', '')}" for a in news_articles[:50]]
                news_sentiments = [sentiment_analyzer.analyze(text) for text in news_texts]
                
                # วิเคราะห์และหา tickers จาก news
                for idx, article in enumerate(news_articles[:50]):
                    try:
                        sentiment = news_sentiments[idx] if idx < len(news_sentiments) else {"compound": 0, "label": "neutral"}
                        
                        post_data = {
                            "id": article.get('url', '').split('/')[-1] or f"news_{len(all_posts)}",
                            "title": article.get('title', ''),
                            "selftext": article.get('description', ''),
                            "score": 0,  # News ไม่มี score
                            "num_comments": 0,
                            "created_utc": datetime.fromisoformat(article.get('publishedAt', datetime.utcnow().isoformat()).replace('Z', '+00:00')),
                            "subreddit": article.get('source', 'news'),
                            "url": article.get('url', ''),
                            "author": article.get('source', 'Unknown'),
                            "sentiment": sentiment,
                            "source": "news"
                        }
                        all_posts.append(post_data)
                        
                        # หา tickers ใน news article
                        full_text = f"{article.get('title', '')} {article.get('description', '')}".upper()
                        tickers = ticker_pattern.findall(full_text)
                        
                        unique_tickers_in_post = set()
                        
                        for ticker in tickers:
                            if ticker in false_positives:
                                continue
                            
                            ticker_freq[ticker] = ticker_freq.get(ticker, 0) + 1
                            
                            if ticker not in ticker_details:
                                ticker_details[ticker] = []
                            
                            if ticker not in unique_tickers_in_post:
                                unique_tickers_in_post.add(ticker)
                                ticker_details[ticker].append({
                                    "post_id": post_data["id"],
                                    "title": article.get('title', ''),
                                    "subreddit": article.get('source', 'news'),
                                    "score": 0,
                                    "url": article.get('url', ''),
                                    "created_utc": post_data["created_utc"].isoformat() if hasattr(post_data["created_utc"], 'isoformat') else str(post_data["created_utc"])
                                })
                            
                            if ticker not in ticker_sources:
                                ticker_sources[ticker] = set()
                            ticker_sources[ticker].add("news")
                            
                            if ticker not in ticker_sentiment:
                                ticker_sentiment[ticker] = []
                            ticker_sentiment[ticker].append(sentiment.get('compound', 0))
                            
                    except Exception as e:
                        print(f"⚠️ Error processing news article: {e}")
                        continue
                
                print(f"  ✅ News: {len(news_articles)} articles processed")
            except Exception as e:
                print(f"  ⚠️ Error fetching news: {e}")
        
        # ============================================
        # 3. ดึงข้อมูลจาก TWITTER/X API
        # ============================================
        if source == "all" or source == "twitter":
            print(f"  🐦 Fetching from Twitter/X API...")
            try:
                if twitter_fetcher.bearer_token:
                    # เพิ่ม queries และ limit เพื่อให้สมดุลกับ Reddit
                    twitter_queries = ["$stock", "stock market", "trading", "investing", 
                                      "NASDAQ", "NYSE", "stock price", "earnings", "dividend"]
                    all_tweets = []
                    
                    # ดึงข้อมูลแบบ parallel เพื่อความเร็ว
                    def fetch_tweets_query(query):
                        try:
                            if twitter_fetcher.bearer_token:
                                return twitter_fetcher.search_tweets(query, max_results=40)  # เพิ่มจาก 25 เป็น 40
                            return []
                        except:
                            return []
                    
                    with ThreadPoolExecutor(max_workers=3) as executor:  # เพิ่ม workers
                        futures = {executor.submit(fetch_tweets_query, query): query for query in twitter_queries}
                        for future in as_completed(futures, timeout=20):  # เพิ่ม timeout
                            try:
                                tweets = future.result(timeout=5)
                                all_tweets.extend(tweets)
                                if len(all_tweets) >= 100:  # เพิ่มจาก 50 เป็น 100
                                    break
                            except:
                                continue
                    
                    # วิเคราะห์ sentiment แบบ batch (เร็วกว่า)
                    tweet_texts = [t.get('text', '') for t in all_tweets[:100]]  # เพิ่มจาก 50 เป็น 100
                    tweet_sentiments = [sentiment_analyzer.analyze(text) for text in tweet_texts]
                    
                    # วิเคราะห์และหา tickers จาก tweets
                    for idx, tweet in enumerate(all_tweets[:100]):  # เพิ่มจาก 50 เป็น 100
                        try:
                            text = tweet.get('text', '')
                            sentiment = tweet_sentiments[idx] if idx < len(tweet_sentiments) else {"compound": 0, "label": "neutral"}
                            
                            post_data = {
                                "id": tweet.get('id', f"tweet_{len(all_posts)}"),
                                "title": text[:100] + "..." if len(text) > 100 else text,
                                "selftext": text,
                                "score": tweet.get('metrics', {}).get('like_count', 0),
                                "num_comments": tweet.get('metrics', {}).get('reply_count', 0),
                                "created_utc": datetime.fromisoformat(tweet.get('created_at', datetime.utcnow().isoformat()).replace('Z', '+00:00')),
                                "subreddit": f"@{tweet.get('author', 'twitter')}",
                                "url": f"https://twitter.com/{tweet.get('author', 'unknown')}/status/{tweet.get('id', '')}",
                                "author": tweet.get('author', 'Unknown'),
                                "sentiment": sentiment,
                                "source": "twitter"
                            }
                            all_posts.append(post_data)
                            
                            # หา tickers ใน tweet
                            full_text = text.upper()
                            tickers = ticker_pattern.findall(full_text)
                            
                            unique_tickers_in_post = set()
                            
                            for ticker in tickers:
                                if ticker in false_positives:
                                    continue
                                
                                ticker_freq[ticker] = ticker_freq.get(ticker, 0) + 1
                                
                                if ticker not in ticker_details:
                                    ticker_details[ticker] = []
                                
                                if ticker not in unique_tickers_in_post:
                                    unique_tickers_in_post.add(ticker)
                                    ticker_details[ticker].append({
                                        "post_id": tweet.get('id', ''),
                                        "title": text[:100] + "..." if len(text) > 100 else text,
                                        "subreddit": f"@{tweet.get('author', 'twitter')}",
                                        "score": tweet.get('metrics', {}).get('like_count', 0),
                                        "url": f"https://twitter.com/{tweet.get('author', 'unknown')}/status/{tweet.get('id', '')}",
                                        "created_utc": post_data["created_utc"].isoformat() if hasattr(post_data["created_utc"], 'isoformat') else str(post_data["created_utc"])
                                    })
                                
                                if ticker not in ticker_sources:
                                    ticker_sources[ticker] = set()
                                ticker_sources[ticker].add("twitter")
                                
                                if ticker not in ticker_sentiment:
                                    ticker_sentiment[ticker] = []
                                ticker_sentiment[ticker].append(sentiment.get('compound', 0))
                                
                        except Exception as e:
                            print(f"⚠️ Error processing tweet: {e}")
                            continue
                    
                    print(f"  ✅ Twitter: {len(all_tweets)} tweets processed")
                else:
                    print(f"  ⚠️ Twitter API token not configured")
            except Exception as e:
                print(f"  ⚠️ Error fetching Twitter: {e}")
        
        # ============================================
        # 4. ดึงข้อมูลจาก YOUTUBE API (Parallel Processing)
        # ============================================
        if source == "all" or source == "youtube":
            print(f"  📺 Fetching from YouTube API...")
            try:
                if youtube_fetcher.api_key:
                    # เพิ่ม queries และ limit เพื่อให้สมดุลกับ Reddit
                    youtube_queries = ["stock market", "trading", "investing", "stocks analysis",
                                       "stock news", "market analysis", "financial news", "earnings report"]
                    all_youtube_videos = []
                    
                    # ดึงข้อมูลแบบ parallel เพื่อความเร็ว
                    def fetch_youtube_query(query):
                        try:
                            return youtube_fetcher.search_videos(query, max_results=20)  # เพิ่มจาก 10 เป็น 20
                        except:
                            return []
                    
                    with ThreadPoolExecutor(max_workers=3) as executor:  # เพิ่ม workers
                        futures = {executor.submit(fetch_youtube_query, query): query for query in youtube_queries[:8]}  # เพิ่มจาก 3 เป็น 8 queries
                        for future in as_completed(futures, timeout=20):  # เพิ่ม timeout
                            try:
                                videos = future.result(timeout=5)
                                all_youtube_videos.extend(videos)
                                if len(all_youtube_videos) >= 80:  # เพิ่มจาก 30 เป็น 80
                                    break
                            except:
                                continue
                    
                    # วิเคราะห์ sentiment แบบ batch (เร็วกว่า)
                    youtube_texts = [f"{v.get('title', '')} {v.get('description', '')}" for v in all_youtube_videos[:80]]  # เพิ่มจาก 30 เป็น 80
                    youtube_sentiments = [sentiment_analyzer.analyze(text) for text in youtube_texts]
                    
                    # วิเคราะห์และหา tickers จาก YouTube videos
                    for idx, video in enumerate(all_youtube_videos[:80]):  # เพิ่มจาก 30 เป็น 80
                        try:
                            sentiment = youtube_sentiments[idx] if idx < len(youtube_sentiments) else {"compound": 0, "label": "neutral"}
                            
                            post_data = {
                                "id": video.get('id', f"youtube_{len(all_posts)}"),
                                "title": video.get('title', ''),
                                "selftext": video.get('description', ''),
                                "score": 0,  # YouTube ไม่มี score แต่มี viewCount
                                "num_comments": 0,
                                "created_utc": datetime.fromisoformat(video.get('publishedAt', datetime.utcnow().isoformat()).replace('Z', '+00:00')),
                                "subreddit": video.get('channelTitle', 'youtube'),
                                "url": video.get('url', ''),
                                "author": video.get('channelTitle', 'Unknown'),
                                "sentiment": sentiment,
                                "source": "youtube"
                            }
                            all_posts.append(post_data)
                            
                            # หา tickers ใน video title และ description
                            full_text = f"{video.get('title', '')} {video.get('description', '')}".upper()
                            tickers = ticker_pattern.findall(full_text)
                            
                            unique_tickers_in_post = set()
                            
                            for ticker in tickers:
                                if ticker in false_positives:
                                    continue
                                
                                ticker_freq[ticker] = ticker_freq.get(ticker, 0) + 1
                                
                                if ticker not in ticker_details:
                                    ticker_details[ticker] = []
                                
                                if ticker not in unique_tickers_in_post:
                                    unique_tickers_in_post.add(ticker)
                                    ticker_details[ticker].append({
                                        "post_id": video.get('id', ''),
                                        "title": video.get('title', ''),
                                        "subreddit": video.get('channelTitle', 'youtube'),
                                        "score": 0,
                                        "url": video.get('url', ''),
                                        "created_utc": post_data["created_utc"].isoformat() if hasattr(post_data["created_utc"], 'isoformat') else str(post_data["created_utc"])
                                    })
                                
                                if ticker not in ticker_sources:
                                    ticker_sources[ticker] = set()
                                ticker_sources[ticker].add("youtube")
                                
                                if ticker not in ticker_sentiment:
                                    ticker_sentiment[ticker] = []
                                ticker_sentiment[ticker].append(sentiment.get('compound', 0))
                                
                        except Exception as e:
                            print(f"⚠️ Error processing YouTube video: {e}")
                            continue
                    
                    print(f"  ✅ YouTube: {len(all_youtube_videos)} videos processed")
                else:
                    print(f"  ⚠️ YouTube API key not configured")
            except Exception as e:
                print(f"  ⚠️ Error fetching YouTube: {e}")
        
        # ดึงราคาหุ้นสำหรับ top tickers (เพื่อใช้ในการกรองราคา)
        # เพิ่มจำนวนจาก 30 เป็น 100 เพื่อรองรับการกรองราคาได้ดีขึ้น
        print("💰 Fetching stock prices for top tickers...")
        ticker_prices = {}
        top_tickers = sorted(ticker_freq.items(), key=lambda x: x[1], reverse=True)[:100]  # Top 100 tickers (increased for better price filtering)
        
        # ดึงราคาแบบ parallel เพื่อความเร็ว
        from concurrent.futures import ThreadPoolExecutor, as_completed as futures_completed
        
        def fetch_ticker_price(ticker_symbol):
            """Helper function to fetch price for a single ticker"""
            try:
                stock_info = stock_fetcher.get_stock_info(ticker_symbol)
                if stock_info:
                    return ticker_symbol, stock_info.get('currentPrice', 0)
            except Exception as e:
                print(f"⚠️ Could not fetch price for {ticker_symbol}: {e}")
            return ticker_symbol, None
        
        # Fetch prices in parallel (max 10 concurrent requests - increased for faster fetching)
        with ThreadPoolExecutor(max_workers=10) as executor:
            price_futures = {
                executor.submit(fetch_ticker_price, ticker): ticker 
                for ticker, _ in top_tickers
            }
            
            # Increase timeout to 30 seconds for more tickers
            for future in futures_completed(price_futures, timeout=30):
                try:
                    ticker, price = future.result(timeout=5)
                    if price and price > 0:  # Only store valid prices
                        ticker_prices[ticker] = price
                except Exception as e:
                    continue
        
        print(f"✅ Fetched prices for {len(ticker_prices)} tickers")
        
        # สร้าง topics list - ใช้ list comprehension เพื่อความเร็ว
        topics = [
            {
                "ticker": ticker,
                "word": ticker,
                "count": count,
                "mentions": count,
                "uniquePosts": len(ticker_details.get(ticker, [])),
                "sources": list(ticker_sources.get(ticker, set())),
                "sourceCount": len(ticker_sources.get(ticker, set())),
                "avgSentiment": round(sum(ticker_sentiment.get(ticker, [])) / len(ticker_sentiment.get(ticker, [])) if ticker_sentiment.get(ticker, []) else 0, 3),
                "topPosts": sorted(ticker_details.get(ticker, []), key=lambda x: x.get('score', 0), reverse=True)[:5],
                "currentPrice": ticker_prices.get(ticker),  # เพิ่มราคาหุ้น
                "price": ticker_prices.get(ticker)  # alias สำหรับ compatibility
            }
            for ticker, count in ticker_freq.items()
        ]
        
        # เรียงตาม mentions
        topics.sort(key=lambda x: x["count"], reverse=True)
        
        # นับ posts จากแต่ละ source
        source_counts = {}
        for post in all_posts:
            post_source = post.get('source', 'unknown')
            source_counts[post_source] = source_counts.get(post_source, 0) + 1
        
        print(f"✅ Real-time analysis complete:")
        print(f"   Total posts: {len(all_posts)}")
        print(f"   Source breakdown: {source_counts}")
        print(f"   Total tickers found: {len(topics)}")
        if topics:
            top5 = [(t['ticker'], t['count'], t['sources']) for t in topics[:5]]
            print(f"📊 Top 5: {top5}")
        
        # ส่ง Top 100 มา (ไม่ใช่แค่ 50) เพื่อให้หุ้นที่อยู่นอก 50 มีโอกาสเข้ามาเมื่อมีการอัปเดต
        # Frontend จะเป็นคนตัดเป็น Top 50 เอง
        return jsonify({
            "topics": topics[:100],  # Top 100 (เพิ่มจาก 50 เพื่อให้หุ้นที่อยู่นอก 50 มีโอกาสเข้ามา)
            "totalPosts": len(all_posts),
            "totalTickers": len(topics),
            "source": f"realtime-{source}",
            "sourceBreakdown": source_counts,  # เพิ่ม breakdown ของแต่ละ source
            "fetchedAt": datetime.utcnow().isoformat(),
            "subreddits": subreddits if source == "all" or source == "reddit" else []
        })
        
    except Exception as e:
        import traceback
        print(f"❌ Error in trending-realtime: {e}")
        print(traceback.format_exc())
        return jsonify({
            "error": str(e),
            "topics": [],
            "message": f"Error fetching real-time data: {str(e)}"
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
        from youtube_fetcher import YouTubeFetcher
        from event_analyzer import EventAnalyzer
        
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
        
        # ดึงวิดีโอข่าวสำคัญ
        print("📺 Fetching news videos from YouTube...")
        videos = youtube_fetcher.search_news_videos(max_results=max_videos)
        
        if not videos:
            # ตรวจสอบว่าเป็นเพราะ API key หรือ quota
            error_details = {
                "error": "No videos found",
                "message": "Could not fetch videos from YouTube API",
                "possible_causes": [
                    "YouTube API key not configured or invalid",
                    "YouTube API quota exceeded",
                    "Network connectivity issues",
                    "YouTube API service temporarily unavailable"
                ],
                "suggestions": [
                    "Check YOUTUBE_API_KEY in .env file",
                    "Verify API key is valid and has quota remaining",
                    "Check YouTube API quota usage in Google Cloud Console",
                    "Try again later if quota was exceeded"
                ]
            }
            
            # ตรวจสอบว่า API key มีหรือไม่
            if not youtube_fetcher.api_key:
                error_details["error"] = "YouTube API key not configured"
                error_details["message"] = "Please add YOUTUBE_API_KEY to your .env file"
                return jsonify(error_details), 400
            
            return jsonify(error_details), 404
        
        print(f"✅ Found {len(videos)} videos")
        
        # ดึง trending tickers จาก real-time API เพื่อใช้ sentiment จริง
        print("📊 Fetching trending tickers with sentiment...")
        trending_tickers = []
        try:
            import urllib.request
            import json as json_module
            
            # ดึงข้อมูล trending tickers จาก real-time API (internal call)
            base_url = request.url_root.rstrip('/')
            trending_url = f"{base_url}/api/trending-realtime?source=all&limit=50&sort=hot"
            
            with urllib.request.urlopen(trending_url, timeout=15) as response:
                if response.status == 200:
                    trending_data = json_module.loads(response.read().decode())
                    trending_tickers = trending_data.get('topics', [])[:30]  # Top 30 tickers
                    print(f"✅ Loaded {len(trending_tickers)} trending tickers with sentiment")
                    if trending_tickers:
                        top3 = [(t.get('ticker') or t.get('word', 'N/A'), t.get('avgSentiment', 0)) for t in trending_tickers[:3]]
                        print(f"   Top 3 tickers: {top3}")
        except Exception as e:
            print(f"⚠️ Could not fetch trending tickers: {e}")
            print("   Will use event mapping only (no real sentiment data)")
        
        # วิเคราะห์เหตุการณ์และแนะนำหุ้น (รวม sentiment จาก trending tickers)
        print("🔬 Analyzing events and generating stock recommendations...")
        print(f"   Using {len(trending_tickers)} trending tickers with real sentiment")
        analysis_result = event_analyzer.analyze_multiple_videos(videos, trending_tickers)
        
        # จัดรูปแบบผลลัพธ์
        result = {
            "success": True,
            "analysis_date": datetime.utcnow().isoformat(),
            "total_videos_analyzed": len(videos),
            "summary": analysis_result['summary'],
            "top_buy_recommendations": [
                {
                    "ticker": ticker,
                    "confidence": round(data['confidence'], 3),
                    "mention_count": data['mention_count'],
                    "reasons": data['reasons'],
                    "avg_sentiment": round(data['avg_sentiment'], 3),
                    "score": round(data['score'], 2),
                    "source": data.get('source', 'unknown'),
                    "calculation": data.get('calculation', {})
                }
                for ticker, data in list(analysis_result['top_buy_recommendations'].items())[:15]
            ],
            "top_sell_recommendations": [
                {
                    "ticker": ticker,
                    "confidence": round(data['confidence'], 3),
                    "mention_count": data['mention_count'],
                    "reasons": data['reasons'],
                    "avg_sentiment": round(data['avg_sentiment'], 3),
                    "score": round(data['score'], 2),
                    "source": data.get('source', 'unknown'),
                    "calculation": data.get('calculation', {})
                }
                for ticker, data in list(analysis_result['top_sell_recommendations'].items())[:15]
            ],
            "detected_events": {}
        }
        
        # สรุปเหตุการณ์ที่ตรวจจับได้
        event_counts = {}
        for analysis in analysis_result['analyses']:
            for event in analysis['events']:
                event_id = event['event_id']
                if event_id not in event_counts:
                    event_counts[event_id] = {
                        'count': 0,
                        'event_type': event['event_type'],
                        'avg_confidence': 0
                    }
                event_counts[event_id]['count'] += 1
                event_counts[event_id]['avg_confidence'] += event['confidence']
        
        for event_id, data in event_counts.items():
            data['avg_confidence'] = round(data['avg_confidence'] / data['count'], 3)
        
        result['detected_events'] = event_counts
        
        # เพิ่มตัวอย่างวิดีโอที่วิเคราะห์
        result['sample_videos'] = [
            {
                "title": a['title'],
                "url": a['url'],
                "channel": a['channel'],
                "sentiment": round(a['sentiment']['compound'], 3),
                "events_detected": [e['event_id'] for e in a['events']]
            }
            for a in analysis_result['analyses'][:10]
        ]
        
        print(f"✅ Analysis complete:")
        print(f"   Events detected: {len(event_counts)}")
        print(f"   Buy recommendations: {len(result['top_buy_recommendations'])}")
        print(f"   Sell recommendations: {len(result['top_sell_recommendations'])}")
        
        return jsonify(result)
        
    except Exception as e:
        import traceback
        print(f"❌ Error in event-analysis: {e}")
        print(traceback.format_exc())
        return jsonify({
            "success": False,
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
        
        # Get posts from database
        posts = list(db.posts.find().sort("created_utc", -1).limit(limit))
        
        # Serialize and add sentiment
        from sentiment_analyzer import SentimentAnalyzer
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

@app.route("/api/stock/<symbol>/pressure-score")
def get_pressure_score(symbol):
    """Calculate buy/sell pressure score from Yahoo Finance data"""
    try:
        symbol_upper = symbol.upper()
        
        # Get stock info from Yahoo Finance
        stock_info = stock_fetcher.get_stock_info(symbol_upper)
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
    """Get news from Yahoo Finance for a stock"""
    try:
        symbol_upper = symbol.upper()
        
        # Use yfinance to get news
        ticker = yf.Ticker(symbol_upper)
        news_list = ticker.news
        
        # Analyze sentiment for each news
        analyzed_news = []
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
            
            analyzed_news.append({
                "title": title,
                "summary": summary,
                "link": news_item.get('link', ''),
                "publisher": news_item.get('publisher', ''),
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
        
        # Sort by sentiment impact (strongest first)
        analyzed_news.sort(key=lambda x: abs(x['sentiment']['compound']), reverse=True)
        
        return jsonify({
            "symbol": symbol_upper,
            "news": analyzed_news,
            "total": len(analyzed_news),
            "positiveCount": sum(1 for n in analyzed_news if n['sentiment']['label'] == 'positive'),
            "negativeCount": sum(1 for n in analyzed_news if n['sentiment']['label'] == 'negative'),
            "neutralCount": sum(1 for n in analyzed_news if n['sentiment']['label'] == 'neutral')
        })
    except Exception as e:
        print(f"❌ Error fetching news: {e}")
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

if __name__ == "__main__":
    print("✅ MongoDB connected successfully!")
    # Initialize database collections
    if db is not None:
        initialize_collections(db)
    
    # Start background scheduler in a separate thread
    scheduler_thread = threading.Thread(target=run_scheduler_background, daemon=True)
    scheduler_thread.start()
    print("✅ Background scheduler started (auto-fetch every 1 hour)")
    
    print("🚀 Flask API running on http://127.0.0.1:5000")
    print("💡 Scheduler is running in background - posts will be auto-fetched every hour")
    app.run(debug=True)
