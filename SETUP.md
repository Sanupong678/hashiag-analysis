# Setup Guide

## Quick Start

### 1. Install Dependencies

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Install Python packages
pip install -r requirements.txt
```

### 2. Configure Environment Variables

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your API keys:
   - **Reddit API** (Required): Get from https://www.reddit.com/prefs/apps
   - **MongoDB** (Required): Your MongoDB connection string
   - **News API** (Optional): Get from https://newsapi.org/
   - **Twitter API** (Optional): Get from https://developer.twitter.com/

### 3. Set Up MongoDB

#### Option A: MongoDB Atlas (Cloud - Recommended)
1. Create account at https://www.mongodb.com/cloud/atlas
2. Create a free cluster
3. Get connection string
4. Add to `.env` as `MONGO_URI`

#### Option B: Local MongoDB
1. Install MongoDB locally
2. Start MongoDB service
3. Use connection string: `mongodb://localhost:27017/`
4. Add to `.env` as `MONGO_URI`

### 4. Update Database Configuration

Edit `backend/db_config.py` if needed (or use environment variable).

### 5. Start the Backend Server

```bash
cd backend
python app.py
```

You should see:
```
✅ MongoDB connected successfully!
🚀 Flask API running on http://127.0.0.1:5000
```

### 6. Open the Frontend

1. Open `frontend/index.html` in your browser
   - Or use a local server:
   ```bash
   cd frontend
   python -m http.server 8000
   ```
2. Navigate to `http://localhost:8000`

## Testing the Setup

### Test Reddit API
```bash
cd backend
python -c "from fetch_reddit import fetch_posts; fetch_posts('AAPL', 10)"
```

### Test Stock Data
```bash
cd backend
python -c "from stock_data import StockDataFetcher; s = StockDataFetcher(); print(s.get_stock_info('AAPL'))"
```

### Test Full Aggregation
```bash
cd backend
python -c "from data_aggregator import DataAggregator; d = DataAggregator(); print(d.aggregate_stock_data('AAPL'))"
```

## Troubleshooting

### MongoDB Connection Issues
- Check your connection string format
- Verify network access (for Atlas)
- Check MongoDB service is running (for local)

### Reddit API Issues
- Verify credentials in `.env`
- Check rate limits (60 requests/minute)
- Ensure USER_AGENT is unique

### News API Issues
- Free tier: 500 requests/day
- Check API key is correct
- Verify you're not exceeding rate limits

### Frontend Not Loading Data
- Check backend is running on port 5000
- Check browser console for CORS errors
- Verify API endpoints are accessible

## Next Steps

1. Try analyzing a stock: Enter "AAPL" in the dashboard
2. Compare stocks: Go to Compare page and enter multiple symbols
3. Set up alerts: Check the alerts section for sentiment spikes
4. Customize: Modify thresholds and settings as needed

## API Rate Limits

- **Reddit**: 60 requests/minute
- **News API (Free)**: 500 requests/day
- **Google Trends**: ~1 request/second (be patient)
- **yfinance**: No official limit, but be respectful
- **Twitter**: Depends on your tier

## Support

If you encounter issues:
1. Check the README.md for detailed documentation
2. Verify all environment variables are set correctly
3. Check backend logs for error messages
4. Check browser console for frontend errors

