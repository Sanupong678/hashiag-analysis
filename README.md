# Stock Sentiment Dashboard

A comprehensive personal dashboard for monitoring stocks and market sentiment, aggregating data from multiple sources (Reddit API, News API, Google Trends, Stock Prices) and performing sentiment analysis to track market moods.

## Features

### 🎯 Core Features

- **Multi-Source Data Aggregation**
  - Reddit posts and comments about stocks
  - News articles from NewsAPI
  - Google Trends search data
  - Real-time stock price data (via yfinance)
  - Optional: Twitter/X API for influencer tracking

- **Sentiment Analysis**
  - VADER sentiment analyzer with financial-specific enhancements
  - Sentiment scoring for Reddit posts and news articles
  - Overall weighted sentiment score combining all sources
  - Visual sentiment indicators and charts

- **Stock Comparison**
  - Compare multiple stocks side-by-side
  - Price vs Sentiment vs Mentions visualization
  - Historical price data with sentiment overlay
  - Market cap, volume, and sector information

- **Real-Time Alerts**
  - Sentiment spike detection
  - Price change alerts
  - Customizable alert thresholds
  - 24-hour alert history

- **Advanced Visualizations**
  - Price vs Sentiment correlation charts
  - Mentions over time
  - Sentiment distribution
  - Multi-stock comparison charts

## Tech Stack

### Backend
- **Python 3.8+**
- **Flask** - REST API framework
- **MongoDB** - Database for storing aggregated data
- **VADER Sentiment** - Sentiment analysis
- **yfinance** - Stock price data
- **PyTrends** - Google Trends integration
- **NewsAPI** - News article fetching
- **PRAW** - Reddit API wrapper

### Frontend
- **HTML5/CSS3** - Modern responsive UI
- **JavaScript (ES6+)** - Client-side logic
- **Chart.js** - Data visualization
- **Vanilla JS** - No framework dependencies

## Installation

### Prerequisites

- Python 3.8 or higher
- MongoDB (local or MongoDB Atlas)
- Node.js (optional, for frontend development)

### Backend Setup

1. **Clone the repository**
   ```bash
   cd reddit-hashtag-analytics
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   
   Create a `.env` file in the root directory:
   ```env
   # Reddit API
   REDDIT_CLIENT_ID=your_reddit_client_id
   REDDIT_CLIENT_SECRET=your_reddit_client_secret
   USER_AGENT=your_app_name/1.0
   
   # MongoDB
   MONGO_URI=your_mongodb_connection_string
   
   # News API (optional but recommended)
   NEWS_API_KEY=your_newsapi_key
   
   # Twitter API (optional)
   TWITTER_BEARER_TOKEN=your_twitter_bearer_token
   ```

5. **Update MongoDB configuration**
   
   Edit `backend/db_config.py` with your MongoDB connection string.

6. **Run the Flask server**
   ```bash
   cd backend
   python app.py
   ```
   
   The API will be available at `http://localhost:5000`

### Frontend Setup

1. **Navigate to frontend directory**
   ```bash
   cd frontend
   ```

2. **Open `index.html` in a browser**
   
   Or use a local server:
   ```bash
   # Using Python
   python -m http.server 8000
   
   # Using Node.js
   npx serve
   ```

3. **Access the dashboard**
   
   Open `http://localhost:8000` (or your server port)

## API Endpoints

### Stock Data

- `GET /api/stock/<symbol>` - Get aggregated stock data
  - Query params: `days` (default: 7)
  - Returns: Stock info, sentiment, Reddit posts, news, trends

- `GET /api/stock/<symbol>/price` - Get current stock price
  - Returns: Current price, change, volume, market cap

- `GET /api/stock/<symbol>/history` - Get historical price data
  - Query params: `period` (1d, 1mo, 1y, etc.), `interval` (1d, 1h, etc.)

### Comparison

- `GET /api/stock/compare` - Compare multiple stocks
  - Query params: `symbols` (comma-separated), `days`
  - Returns: Comparison data for all symbols

### Alerts

- `GET /api/alerts` - Get sentiment alerts
  - Query params: `threshold` (default: 0.3), `hours` (default: 24)
  - Returns: List of alerts for sentiment spikes

### Dashboard

- `GET /api/dashboard` - Get dashboard summary
  - Returns: Recent stocks, statistics

## Usage Examples

### Analyzing a Stock

1. Open the dashboard in your browser
2. Enter a stock symbol (e.g., "AAPL", "TSLA", "NVDA")
3. Click "Analyze Stock" or press Enter
4. View:
   - Current stock price and change
   - Overall sentiment score
   - Reddit mentions and sentiment
   - News articles and sentiment
   - Price vs Sentiment chart
   - Top Reddit posts and news articles

### Comparing Stocks

1. Navigate to "Compare Stocks" page
2. Enter 2-3 stock symbols
3. Click "Compare Stocks"
4. View side-by-side comparison:
   - Price charts
   - Sentiment comparison
   - Mentions comparison
   - Summary table

### Setting Up Alerts

Alerts are automatically generated when:
- Sentiment score exceeds threshold (default: ±0.3)
- Significant price changes occur
- High mention volume detected

View alerts in the "Real-time Alerts" section on the dashboard.

## API Keys Setup

### Reddit API

1. Go to https://www.reddit.com/prefs/apps
2. Create a new application
3. Note your Client ID and Secret
4. Add to `.env` file

### News API

1. Sign up at https://newsapi.org/
2. Get your free API key (500 requests/day)
3. Add `NEWS_API_KEY` to `.env` file

### Google Trends

No API key required! PyTrends uses public Google Trends data.

### Twitter/X API (Optional)

1. Apply for Twitter API access at https://developer.twitter.com/
2. Create a new app and get Bearer Token
3. Add `TWITTER_BEARER_TOKEN` to `.env` file
4. Note: Paid tier recommended for production use

## Project Structure

```
reddit-hashtag-analytics/
├── backend/
│   ├── app.py                 # Flask API server
│   ├── db_config.py           # MongoDB configuration
│   ├── fetch_reddit.py        # Reddit API integration
│   ├── sentiment_analyzer.py  # Sentiment analysis module
│   ├── news_fetcher.py       # News API integration
│   ├── trends_fetcher.py     # Google Trends integration
│   ├── stock_data.py         # Stock price data (yfinance)
│   ├── data_aggregator.py    # Main data aggregation service
│   ├── twitter_fetcher.py    # Twitter API (optional)
│   └── data/                 # Data storage
├── frontend/
│   ├── index.html            # Main dashboard
│   ├── compare.html          # Stock comparison page
│   ├── data.html             # Data export page
│   └── public/
│       ├── css/
│       │   └── style.css     # Styling
│       └── js/
│           ├── app.js        # Main dashboard logic
│           └── compare.js    # Comparison logic
├── requirements.txt          # Python dependencies
└── README.md                # This file
```

## Database Schema

### Collections

- **posts** - Reddit posts
- **stock_data** - Aggregated stock data with sentiment
- **alerts** - Generated alerts (future feature)

### Stock Data Document Structure

```json
{
  "symbol": "AAPL",
  "fetchedAt": "2024-01-01T00:00:00",
  "stockInfo": {
    "symbol": "AAPL",
    "name": "Apple Inc.",
    "currentPrice": 150.00,
    "change": 2.50,
    "changePercent": 1.69,
    "volume": 50000000,
    "marketCap": 2500000000000,
    "sector": "Technology"
  },
  "redditData": {
    "posts": [...],
    "sentiment": {
      "compound": 0.25,
      "label": "positive"
    },
    "mentionCount": 150
  },
  "newsData": {
    "articles": [...],
    "sentiment": {...},
    "articleCount": 45
  },
  "overallSentiment": {
    "compound": 0.20,
    "label": "positive",
    "confidence": 0.85
  }
}
```

## Limitations & Future Enhancements

### Current Limitations

- News API free tier: 500 requests/day
- Google Trends: Rate limiting (1 request per second recommended)
- Twitter API: Requires paid tier for production use
- Real-time updates: Manual refresh required

### Planned Enhancements

- [ ] WebSocket support for real-time updates
- [ ] User authentication and watchlists
- [ ] Email/SMS alert notifications
- [ ] Historical sentiment analysis
- [ ] Machine learning sentiment models
- [ ] Portfolio tracking
- [ ] Export to PDF/Excel
- [ ] Mobile app version

## Contributing

This is a personal project, but suggestions and improvements are welcome!

## License

This project is for personal use and educational purposes.

## Acknowledgments

- **VADER Sentiment** - Financial sentiment analysis
- **yfinance** - Stock market data
- **PyTrends** - Google Trends integration
- **NewsAPI** - News article aggregation
- **Chart.js** - Beautiful data visualizations

## Support

For issues or questions:
1. Check the API documentation above
2. Verify your `.env` file is configured correctly
3. Check MongoDB connection
4. Review browser console for frontend errors
5. Check Flask server logs for backend errors

---

**Note**: This dashboard is designed for personal use and educational purposes. Always do your own research before making investment decisions. This tool provides sentiment analysis and data aggregation but should not be the sole basis for trading decisions.

