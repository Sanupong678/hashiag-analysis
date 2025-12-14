"""
Data Aggregator Service
Combines data from all sources - Yahoo Finance เป็นหลัก (ฟรี, เร็ว, แม่นยำ)
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from db_config import db
from fetch_reddit import fetch_posts
from sentiment_analyzer import SentimentAnalyzer
from news_fetcher import NewsFetcher
from trends_fetcher import TrendsFetcher
from stock_data import StockDataFetcher
from youtube_fetcher import YouTubeFetcher
from rapidapi_fetcher import RapidAPIFetcher
from yahoo_finance_fetcher import YahooFinanceFetcher

class DataAggregator:
    def __init__(self):
        self.sentiment_analyzer = SentimentAnalyzer()
        self.yahoo_fetcher = YahooFinanceFetcher()  # ใช้ Yahoo Finance เป็นหลัก
        self.news_fetcher = NewsFetcher()  # ใช้เป็น backup
        self.trends_fetcher = TrendsFetcher()
        self.stock_fetcher = StockDataFetcher()
        self.youtube_fetcher = YouTubeFetcher()
        self.rapidapi_fetcher = RapidAPIFetcher()
    
    def aggregate_stock_data(self, symbol: str, days_back: int = 7) -> Dict:
        """
        Aggregate all data sources for a stock symbol
        
        Returns:
            Complete aggregated data including:
            - Stock price info
            - Reddit posts with sentiment
            - News articles with sentiment
            - Google Trends data
            - Overall sentiment score
        """
        symbol_upper = symbol.upper()
        print(f"📊 Aggregating data for {symbol_upper}...")
        
        result = {
            'symbol': symbol_upper,
            'fetchedAt': datetime.utcnow().isoformat(),
            'stockInfo': None,
            'redditData': {
                'posts': [],
                'sentiment': None,
                'mentionCount': 0
            },
            'newsData': {
                'articles': [],
                'sentiment': None,
                'articleCount': 0
            },
            'trendsData': {},
            'twitterData': {
                'tweets': [],
                'sentiment': None,
                'tweetCount': 0
            },
            'youtubeData': {
                'videos': [],
                'videoCount': 0
            },
            'overallSentiment': None
        }
        
        # 1. Fetch stock price data from Yahoo Finance (หลัก)
        print(f"  📈 Fetching stock data from Yahoo Finance...")
        result['stockInfo'] = self.yahoo_fetcher.get_stock_info(symbol_upper)
        if not result['stockInfo']:
            # Fallback to stock_fetcher
            result['stockInfo'] = self.stock_fetcher.get_stock_info(symbol_upper)
        
        # 2. Fetch news articles from Yahoo Finance (หลัก - ฟรี, เร็ว, แม่นยำ)
        print(f"  📰 Fetching news from Yahoo Finance (primary source)...")
        try:
            # ดึงข่าวจาก Yahoo Finance เป็นหลัก
            yahoo_news = self.yahoo_fetcher.get_stock_news(symbol_upper, max_results=50)
            
            if yahoo_news:
                # วิเคราะห์ sentiment จากข่าว Yahoo Finance
                texts = [f"{a.get('title', '')} {a.get('summary', '')}" for a in yahoo_news if a.get('title') or a.get('summary')]
                if texts:
                    sentiment_result = self.sentiment_analyzer.analyze_batch(texts)
                    if sentiment_result:
                        result['newsData']['sentiment'] = sentiment_result
                    result['newsData']['articles'] = yahoo_news[:30]  # Top 30
                    result['newsData']['articleCount'] = len(yahoo_news)
                    result['newsData']['source'] = 'yahoo_finance'
                    print(f"  ✅ Fetched {len(yahoo_news)} news articles from Yahoo Finance")
            
            # ถ้า Yahoo Finance ไม่มีข่าวพอ ให้ใช้ News API เป็น backup
            if not yahoo_news or len(yahoo_news) < 10:
                print(f"  📰 Yahoo Finance has limited news, trying News API as backup...")
                try:
                    backup_news = self.news_fetcher.fetch_stock_news(symbol_upper, days_back)
                    if backup_news:
                        # รวมข่าวจาก News API เข้ากับ Yahoo Finance
                        if yahoo_news:
                            combined_news = yahoo_news + backup_news
                        else:
                            combined_news = backup_news
                        
                        texts = [f"{a.get('title', '')} {a.get('description', '')}" for a in combined_news if a.get('title') or a.get('description')]
                        if texts:
                            sentiment_result = self.sentiment_analyzer.analyze_batch(texts)
                            if sentiment_result:
                                result['newsData']['sentiment'] = sentiment_result
                            result['newsData']['articles'] = combined_news[:30]
                            result['newsData']['articleCount'] = len(combined_news)
                            result['newsData']['source'] = 'yahoo_finance+news_api'
                            print(f"  ✅ Combined {len(yahoo_news) if yahoo_news else 0} Yahoo Finance + {len(backup_news)} News API articles")
                except Exception as e2:
                    print(f"  ⚠️ Error fetching backup news: {e2}")
        except Exception as e:
            print(f"  ⚠️ Error fetching Yahoo Finance news: {e}")
            import traceback
            traceback.print_exc()
        
        # 3. Fetch Reddit posts (optional - ลดความสำคัญลง)
        print(f"  🔴 Fetching Reddit posts (optional)...")
        try:
            reddit_posts = fetch_posts(symbol_upper, limit=50)  # ลดจาก 100 เป็น 50
            # Also try with $ prefix
            if len(reddit_posts) < 25:
                try:
                    additional_posts = fetch_posts(f"${symbol_upper}", limit=25)  # ลดจาก 50 เป็น 25
                    reddit_posts.extend(additional_posts)
                except Exception as e:
                    print(f"  ⚠️ Error fetching Reddit posts with $ prefix: {e}")
            
            # Analyze sentiment for each post
            if reddit_posts:
                texts = [f"{p.get('title', '')} {p.get('selftext', '')}" for p in reddit_posts if p.get('title') or p.get('selftext')]
                if texts:
                    sentiment_result = self.sentiment_analyzer.analyze_batch(texts)
                    if sentiment_result:
                        result['redditData']['sentiment'] = sentiment_result
                    result['redditData']['posts'] = reddit_posts[:10]  # ลดจาก 20 เป็น 10
                    result['redditData']['mentionCount'] = len(reddit_posts)
        except Exception as e:
            print(f"  ⚠️ Error fetching Reddit data: {e}")
            import traceback
            traceback.print_exc()
        
        # 4. Fetch Google Trends
        print(f"  📊 Fetching Google Trends...")
        try:
            result['trendsData'] = self.trends_fetcher.get_stock_trends(symbol_upper)
        except Exception as e:
            print(f"  ⚠️ Error fetching trends data: {e}")
        
        # 5. Fetch YouTube videos (optional)
        print(f"  📺 Fetching YouTube videos...")
        try:
            youtube_videos = self.youtube_fetcher.search_stock_videos(symbol_upper, max_results=10)
            if youtube_videos:
                result['youtubeData'] = {
                    'videos': youtube_videos,
                    'videoCount': len(youtube_videos),
                    'fetchedAt': datetime.utcnow().isoformat()
                }
        except Exception as e:
            print(f"  ⚠️ Error fetching YouTube data: {e}")
        
        # 6. Fetch Twitter/X posts (optional)
        print(f"  🐦 Fetching Twitter/X posts...")
        try:
            from twitter_fetcher import TwitterFetcher
            twitter_fetcher = TwitterFetcher()
            if twitter_fetcher.bearer_token:
                twitter_tweets = twitter_fetcher.track_stock_mentions(symbol_upper, max_results=50)
                if twitter_tweets:
                    texts = [t.get('text', '') for t in twitter_tweets]
                    if texts:
                        result['twitterData']['sentiment'] = self.sentiment_analyzer.analyze_batch(texts)
                        result['twitterData']['tweets'] = twitter_tweets[:20]  # Top 20
                        result['twitterData']['tweetCount'] = len(twitter_tweets)
        except Exception as e:
            print(f"  ⚠️ Error fetching Twitter data: {e}")
        
        # 7. Try RapidAPI as backup for stock data (optional)
        if not result['stockInfo'] and self.rapidapi_fetcher.api_key:
            print(f"  🔄 Trying RapidAPI as backup...")
            try:
                rapidapi_data = self.rapidapi_fetcher.fetch_stock_quote(symbol_upper)
                if rapidapi_data:
                    result['stockInfo'] = rapidapi_data
            except Exception as e:
                print(f"  ⚠️ Error fetching from RapidAPI: {e}")
        
        # 8. Calculate overall sentiment (weighted average)
        # Yahoo Finance เป็นหลัก - มีน้ำหนักมากที่สุด
        print(f"  🧠 Calculating overall sentiment (Yahoo Finance weighted highest)...")
        sentiment_scores = []
        weights = []
        
        # Yahoo Finance News มีน้ำหนักสูงสุด (หลัก)
        if result['newsData']['sentiment'] and result['newsData'].get('source', '').startswith('yahoo'):
            sentiment_scores.append(result['newsData']['sentiment']['compound'])
            # Yahoo Finance มีน้ำหนักสูงสุด - ใช้ weight 1.5-2.0 เท่า
            yahoo_weight = min(2.0, 1.0 + (result['newsData']['articleCount'] / 30) * 0.5)
            weights.append(yahoo_weight)
            print(f"    ✅ Yahoo Finance news weight: {yahoo_weight:.2f}")
        
        # Reddit มีน้ำหนักต่ำสุด (optional)
        if result['redditData']['sentiment']:
            sentiment_scores.append(result['redditData']['sentiment']['compound'])
            # ลดน้ำหนัก Reddit ลงมาก - ใช้ weight 0.3-0.5 เท่า
            reddit_weight = min(0.5, (result['redditData']['mentionCount'] / 100) * 0.3)
            weights.append(reddit_weight)
            print(f"    🔴 Reddit weight: {reddit_weight:.2f}")
        
        # Twitter มีน้ำหนักต่ำ (optional)
        if result['twitterData']['sentiment']:
            sentiment_scores.append(result['twitterData']['sentiment']['compound'])
            # Twitter มีน้ำหนักต่ำ - ใช้ weight 0.3-0.5 เท่า
            twitter_weight = min(0.5, (result['twitterData']['tweetCount'] / 50) * 0.3)
            weights.append(twitter_weight)
            print(f"    🐦 Twitter weight: {twitter_weight:.2f}")
        
        if sentiment_scores:
            total_weight = sum(weights) if weights else 1
            if total_weight > 0:
                overall_compound = sum(s * w for s, w in zip(sentiment_scores, weights)) / total_weight
            else:
                overall_compound = sum(sentiment_scores) / len(sentiment_scores)
            
            result['overallSentiment'] = {
                'compound': overall_compound,
                'label': 'positive' if overall_compound >= 0.05 else ('negative' if overall_compound <= -0.05 else 'neutral'),
                'confidence': min(1.0, total_weight)
            }
        
        # Clean result before saving to database - convert any DataFrames to dicts
        cleaned_result = self._clean_for_mongodb(result)
        
        # Save to database
        try:
            db.stock_data.update_one(
                {'symbol': symbol_upper},
                {'$set': cleaned_result},
                upsert=True
            )
            print(f"  ✅ Saved to database")
        except Exception as e:
            print(f"  ⚠️ Error saving to database: {e}")
            import traceback
            traceback.print_exc()
        
        return cleaned_result
    
    def _clean_for_mongodb(self, data):
        """Recursively clean data structure to ensure MongoDB compatibility"""
        import pandas as pd
        
        if isinstance(data, dict):
            cleaned = {}
            for key, value in data.items():
                if isinstance(value, pd.DataFrame):
                    # Convert DataFrame to list of dicts
                    cleaned[key] = value.to_dict('records')
                elif isinstance(value, (list, tuple)):
                    cleaned[key] = [self._clean_for_mongodb(item) for item in value]
                elif isinstance(value, dict):
                    cleaned[key] = self._clean_for_mongodb(value)
                else:
                    cleaned[key] = value
            return cleaned
        elif isinstance(data, (list, tuple)):
            return [self._clean_for_mongodb(item) for item in data]
        elif isinstance(data, pd.DataFrame):
            return data.to_dict('records')
        else:
            return data
    
    def compare_stocks(self, symbols: List[str], days_back: int = 7) -> Dict:
        """Compare multiple stocks"""
        results = {}
        for symbol in symbols:
            results[symbol.upper()] = self.aggregate_stock_data(symbol, days_back)
        return results

