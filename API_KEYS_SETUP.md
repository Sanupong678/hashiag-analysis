# คู่มือการตั้งค่า API Keys ใน .env

## 📝 **รูปแบบ .env file ที่ถูกต้อง:**

```env
# Reddit API
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_client_secret
USER_AGENT=StockSentimentDashboard/1.0 by YourUsername

# News API
NEWS_API_KEY=f47fa9d4efbf42b4a34c6574a020e4b7
# หรือใช้ชื่อนี้ (ถ้ามี typo)
NEW_API_KEY=f47fa9d4efbf42b4a34c6574a020e4b7

# X (Twitter) API - Line 16-17
X_BEARER_TOKEN=your_x_bearer_token
# หรือใช้ชื่ออื่นๆ ที่รองรับ:
TWITTER_BEARER_TOKEN=your_x_bearer_token
X_API_KEY=your_x_bearer_token
X_API_TOKEN=your_x_bearer_token

# RapidAPI - Line 14-15
X_RAPIDAPI_KEY=your_rapidapi_key
X_RAPIDAPI_HOST=yahoo-finance15.p.rapidapi.com
# หรือใช้ชื่ออื่น:
RAPIDAPI_KEY=your_rapidapi_key
RAPIDAPI_HOST=yahoo-finance15.p.rapidapi.com

# YouTube API
YOUTUBE_API_KEY=AIzaSyBpPLT6XchdqFoDrqN99MoMRN8AsT2ZXkU

# MongoDB
MONGO_URI=your_mongodb_connection_string
```

---

## ✅ **API Keys ที่คุณมี:**

### 1. **News API** ✅
```env
NEWS_API_KEY=f47fa9d4efbf42b4a34c6574a020e4b7
```
- **สถานะ**: เชื่อมแล้วใน `news_fetcher.py`
- **รองรับ**: ทั้ง `NEWS_API_KEY` และ `NEW_API_KEY` (สำหรับ typo)

### 2. **X (Twitter) API** ✅
```env
X_BEARER_TOKEN=your_token_here  # Line 16-17
```
- **สถานะ**: เชื่อมแล้วใน `twitter_fetcher.py`
- **รองรับ**: 
  - `X_BEARER_TOKEN`
  - `TWITTER_BEARER_TOKEN`
  - `X_API_KEY`
  - `X_API_TOKEN`

### 3. **RapidAPI** ✅
```env
X_RAPIDAPI_KEY=your_key_here     # Line 14
X_RAPIDAPI_HOST=your_host_here  # Line 15
```
- **สถานะ**: เชื่อมแล้วใน `rapidapi_fetcher.py`
- **รองรับ**: 
  - `X_RAPIDAPI_KEY` / `RAPIDAPI_KEY`
  - `X_RAPIDAPI_HOST` / `RAPIDAPI_HOST`
- **ใช้สำหรับ**: Yahoo Finance backup, หรือ APIs อื่นๆ ผ่าน RapidAPI

### 4. **YouTube API** ✅
```env
YOUTUBE_API_KEY=AIzaSyBpPLT6XchdqFoDrqN99MoMRN8AsT2ZXkU
```
- **สถานะ**: เชื่อมแล้วใน `youtube_fetcher.py`
- **ใช้สำหรับ**: ดึงวิดีโอเกี่ยวกับหุ้น

---

## 🔧 **ไฟล์ที่อัปเดตแล้ว:**

### 1. `backend/news_fetcher.py`
- ✅ อ่าน `NEWS_API_KEY` หรือ `NEW_API_KEY`
- ✅ Error handling
- ✅ Logging

### 2. `backend/twitter_fetcher.py`
- ✅ อ่าน `X_BEARER_TOKEN` หรือชื่ออื่นๆ
- ✅ Error handling
- ✅ Logging

### 3. `backend/youtube_fetcher.py` (ใหม่)
- ✅ อ่าน `YOUTUBE_API_KEY`
- ✅ Search videos
- ✅ Get video details

### 4. `backend/rapidapi_fetcher.py` (ใหม่)
- ✅ อ่าน `X_RAPIDAPI_KEY` และ `X_RAPIDAPI_HOST`
- ✅ Yahoo Finance backup
- ✅ Generic RapidAPI support

### 5. `backend/data_aggregator.py`
- ✅ เพิ่ม YouTube fetcher
- ✅ เพิ่ม RapidAPI fetcher
- ✅ ใช้ RapidAPI เป็น backup ถ้า yfinance ไม่ทำงาน

---

## 🧪 **วิธีทดสอบ:**

### Test News API:
```bash
cd backend
python -c "from news_fetcher import NewsFetcher; n = NewsFetcher(); print(n.fetch_news('AAPL', 7, 10))"
```

### Test Twitter/X API:
```bash
cd backend
python -c "from twitter_fetcher import TwitterFetcher; t = TwitterFetcher(); print(t.search_tweets('AAPL', 10))"
```

### Test YouTube API:
```bash
cd backend
python -c "from youtube_fetcher import YouTubeFetcher; y = YouTubeFetcher(); print(y.search_stock_videos('AAPL', 5))"
```

### Test RapidAPI:
```bash
cd backend
python -c "from rapidapi_fetcher import RapidAPIFetcher; r = RapidAPIFetcher(); print(r.fetch_stock_quote('AAPL'))"
```

---

## 📋 **Checklist:**

- [x] News API - เชื่อมแล้ว
- [x] X (Twitter) API - เชื่อมแล้ว
- [x] YouTube API - เชื่อมแล้ว
- [x] RapidAPI - เชื่อมแล้ว
- [x] Reddit API - เชื่อมแล้ว (มีอยู่แล้ว)
- [x] Google Trends - ไม่ต้อง API key (ใช้ PyTrends)
- [x] Yahoo Finance - ไม่ต้อง API key (ใช้ yfinance)

---

## ⚠️ **หมายเหตุ:**

1. **News API**: รองรับทั้ง `NEWS_API_KEY` และ `NEW_API_KEY` (สำหรับ typo)
2. **X/Twitter**: รองรับหลายชื่อ environment variable
3. **RapidAPI**: ใช้เป็น backup สำหรับ Yahoo Finance
4. **YouTube**: Optional - ใช้สำหรับดึงวิดีโอเกี่ยวกับหุ้น

---

## 🎯 **สรุป:**

**ทุก API keys ที่คุณมีถูกเชื่อมแล้ว!** ✅

- ✅ News API
- ✅ X (Twitter) API  
- ✅ YouTube API
- ✅ RapidAPI
- ✅ Reddit API (มีอยู่แล้ว)

**ระบบพร้อมใช้งาน!** 🚀

