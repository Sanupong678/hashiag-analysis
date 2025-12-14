# Template สำหรับ .env file

## 📝 **รูปแบบที่ถูกต้อง:**

```env
# ============================================
# Reddit API Configuration
# ============================================
REDDIT_CLIENT_ID=your_reddit_client_id_here
REDDIT_CLIENT_SECRET=your_reddit_client_secret_here
USER_AGENT=StockSentimentDashboard/1.0 by YourUsername

# ============================================
# News API Configuration
# ============================================
NEWS_API_KEY=f47fa9d4efbf42b4a34c6574a020e4b7
# หรือใช้ชื่อนี้ (ถ้ามี typo)
NEW_API_KEY=f47fa9d4efbf42b4a34c6574a020e4b7

# ============================================
# X (Twitter) API Configuration - Line 16-17
# ============================================
X_BEARER_TOKEN=your_x_bearer_token_here
# หรือใช้ชื่ออื่นๆ ที่รองรับ:
# TWITTER_BEARER_TOKEN=your_x_bearer_token_here
# X_API_KEY=your_x_bearer_token_here
# X_API_TOKEN=your_x_bearer_token_here

# ============================================
# RapidAPI Configuration - Line 14-15
# ============================================
X_RAPIDAPI_KEY=your_rapidapi_key_here
X_RAPIDAPI_HOST=yahoo-finance15.p.rapidapi.com
# หรือใช้ชื่ออื่น:
# RAPIDAPI_KEY=your_rapidapi_key_here
# RAPIDAPI_HOST=yahoo-finance15.p.rapidapi.com

# ============================================
# YouTube API Configuration
# ============================================
YOUTUBE_API_KEY=AIzaSyBpPLT6XchdqFoDrqN99MoMRN8AsT2ZXkU

# ============================================
# MongoDB Configuration
# ============================================
MONGO_URI=your_mongodb_connection_string_here
```

---

## ✅ **API Keys ที่คุณมี (ตามที่บอก):**

### Line 14-15: RapidAPI
```env
X_RAPIDAPI_KEY=your_key
X_RAPIDAPI_HOST=your_host
```

### Line 16-17: X (Twitter)
```env
X_BEARER_TOKEN=your_token
```

### News API
```env
NEWS_API_KEY=f47fa9d4efbf42b4a34c6574a020e4b7
```

### YouTube API
```env
YOUTUBE_API_KEY=AIzaSyBpPLT6XchdqFoDrqN99MoMRN8AsT2ZXkU
```

---

## 🔧 **ไฟล์ที่อัปเดตแล้ว:**

1. ✅ `backend/news_fetcher.py` - อ่าน `NEWS_API_KEY` หรือ `NEW_API_KEY`
2. ✅ `backend/twitter_fetcher.py` - อ่าน `X_BEARER_TOKEN` หรือชื่ออื่นๆ
3. ✅ `backend/youtube_fetcher.py` - อ่าน `YOUTUBE_API_KEY` (ใหม่)
4. ✅ `backend/rapidapi_fetcher.py` - อ่าน `X_RAPIDAPI_KEY` และ `X_RAPIDAPI_HOST` (ใหม่)
5. ✅ `backend/data_aggregator.py` - รวม YouTube และ Twitter

---

## 🧪 **วิธีทดสอบ:**

### Test News API:
```bash
cd backend
python -c "from news_fetcher import NewsFetcher; n = NewsFetcher(); articles = n.fetch_news('AAPL', 7, 5); print(f'Found {len(articles)} articles')"
```

### Test Twitter/X API:
```bash
cd backend
python -c "from twitter_fetcher import TwitterFetcher; t = TwitterFetcher(); tweets = t.search_tweets('AAPL', 5); print(f'Found {len(tweets)} tweets')"
```

### Test YouTube API:
```bash
cd backend
python -c "from youtube_fetcher import YouTubeFetcher; y = YouTubeFetcher(); videos = y.search_stock_videos('AAPL', 5); print(f'Found {len(videos)} videos')"
```

### Test RapidAPI:
```bash
cd backend
python -c "from rapidapi_fetcher import RapidAPIFetcher; r = RapidAPIFetcher(); data = r.fetch_stock_quote('AAPL'); print('RapidAPI:', 'OK' if data else 'No data')"
```

### Test Full Aggregation:
```bash
cd backend
python -c "from data_aggregator import DataAggregator; d = DataAggregator(); result = d.aggregate_stock_data('AAPL'); print('Reddit:', result['redditData']['mentionCount']); print('News:', result['newsData']['articleCount']); print('Twitter:', result.get('twitterData', {}).get('tweetCount', 0)); print('YouTube:', result.get('youtubeData', {}).get('videoCount', 0))"
```

---

## ✅ **สรุป:**

**ทุก API keys ที่คุณมีถูกเชื่อมแล้ว!** ✅

- ✅ News API (`NEWS_API_KEY`)
- ✅ X (Twitter) API (`X_BEARER_TOKEN`)
- ✅ YouTube API (`YOUTUBE_API_KEY`)
- ✅ RapidAPI (`X_RAPIDAPI_KEY`, `X_RAPIDAPI_HOST`)
- ✅ Reddit API (มีอยู่แล้ว)

**ระบบพร้อมใช้งาน!** 🚀

