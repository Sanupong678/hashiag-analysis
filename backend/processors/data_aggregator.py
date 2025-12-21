"""
Data Aggregator Service
Combines data from all sources - Yahoo Finance เป็นหลัก (ฟรี, เร็ว, แม่นยำ)
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from database.db_config import db
from fetchers.fetch_reddit import fetch_posts
from processors.sentiment_analyzer import SentimentAnalyzer
from fetchers.news_fetcher import NewsFetcher
from fetchers.trends_fetcher import TrendsFetcher
from fetchers.stock_data import StockDataFetcher
from fetchers.youtube_fetcher import YouTubeFetcher
from fetchers.rapidapi_fetcher import RapidAPIFetcher
from fetchers.yahoo_finance_fetcher import YahooFinanceFetcher
from cache.redis_cache import cache  # เพิ่ม Redis cache
from processors.sentiment_validator import SentimentValidator
from processors.stock_info_manager import StockInfoManager

class DataAggregator:
    def __init__(self):
        self.sentiment_analyzer = SentimentAnalyzer()
        self.sentiment_validator = SentimentValidator()  # เพิ่ม validator
        self.stock_info_manager = StockInfoManager()  # เพิ่ม stock info manager
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
            'overallSentiment': None,
            'validation': {}  # เก็บ validation results
        }
        
        # 1. Fetch stock price data from Yahoo Finance (หลัก)
        # ใช้ Smart Caching - อัปเดตตามความเหมาะสม
        print(f"  📈 Fetching stock data from Yahoo Finance...")
        
        # สำหรับ validation ต้องใช้ข้อมูล real-time
        # แต่สำหรับการแสดงผลทั่วไป ใช้ cache ได้
        result['stockInfo'] = self.stock_info_manager.get_stock_info_smart(symbol_upper, force_refresh=False)
        
        if not result['stockInfo']:
            # Fallback to stock_fetcher
            result['stockInfo'] = self.stock_fetcher.get_stock_info(symbol_upper)
        
        # 2. Fetch news articles from Yahoo Finance (หลัก - ฟรี, เร็ว, แม่นยำ)
        # ตรวจสอบ cache ก่อน
        print(f"  📰 Fetching news from Yahoo Finance (primary source)...")
        try:
            # ตรวจสอบ cache ก่อน
            yahoo_news = None
            if cache:
                cached_news = cache.get_stock_news(symbol_upper)
                if cached_news:
                    print(f"    ✅ Using cached news for {symbol_upper}")
                    yahoo_news = cached_news
            
            # ถ้าไม่มีใน cache ให้ดึงใหม่ - เพิ่มเป็น 100 ข่าว
            if not yahoo_news:
                yahoo_news = self.yahoo_fetcher.get_stock_news(symbol_upper, max_results=100)
                if yahoo_news and cache:
                    cache.set_stock_news(symbol_upper, yahoo_news)
            
            if yahoo_news:
                # วิเคราะห์ sentiment จากข่าว Yahoo Finance (ใช้ time-weighted)
                # สร้าง items_with_dates สำหรับ time-weighted analysis
                items_with_dates = []
                for article in yahoo_news:
                    text = f"{article.get('title', '')} {article.get('summary', '')}"
                    if text.strip():
                        items_with_dates.append({
                            'text': text,
                            'publishedAt': article.get('publishedAt') or article.get('providerPublishTime') or article.get('publish_date')
                        })
                
                if items_with_dates:
                    # ตรวจสอบ cache sentiment ก่อน
                    sentiment_result = None
                    if cache:
                        cached_sentiment = cache.get_sentiment(symbol_upper)
                        if cached_sentiment:
                            print(f"    ✅ Using cached sentiment for {symbol_upper}")
                            sentiment_result = cached_sentiment
                    
                    # ถ้าไม่มีใน cache ให้วิเคราะห์ใหม่ (ใช้ time-weighted)
                    if not sentiment_result:
                        # ใช้ time-weighted analysis เพื่อให้ข่าวใหม่มีน้ำหนักมากกว่าข่าวเก่า
                        sentiment_result = self.sentiment_analyzer.analyze_batch(
                            texts=[item['text'] for item in items_with_dates],
                            use_time_weighting=True,
                            items_with_dates=items_with_dates
                        )
                        if sentiment_result:
                            print(f"    ⏰ Time-weighted sentiment: {sentiment_result.get('compound', 0):.3f} (avg age: {sentiment_result.get('avg_age_hours', 0):.1f}h)")
                        if sentiment_result and cache:
                            cache.set_sentiment(symbol_upper, sentiment_result)
                    
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
                        
                        # สร้าง items_with_dates สำหรับ time-weighted analysis
                        items_with_dates = []
                        for article in combined_news:
                            text = f"{article.get('title', '')} {article.get('description', '')}"
                            if text.strip():
                                items_with_dates.append({
                                    'text': text,
                                    'publishedAt': article.get('publishedAt') or article.get('publishedAt') or article.get('publish_date')
                                })
                        
                        if items_with_dates:
                            # ใช้ time-weighted analysis
                            sentiment_result = self.sentiment_analyzer.analyze_batch(
                                texts=[item['text'] for item in items_with_dates],
                                use_time_weighting=True,
                                items_with_dates=items_with_dates
                            )
                            if sentiment_result:
                                print(f"    ⏰ Time-weighted sentiment: {sentiment_result.get('compound', 0):.3f} (avg age: {sentiment_result.get('avg_age_hours', 0):.1f}h)")
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
            
            # Analyze sentiment for each post (ใช้ time-weighted)
            if reddit_posts:
                # สร้าง items_with_dates สำหรับ time-weighted analysis
                items_with_dates = []
                for post in reddit_posts:
                    text = f"{post.get('title', '')} {post.get('selftext', '')}"
                    if text.strip():
                        # Reddit posts อาจมี created_utc, publishedAt, หรือ created_at
                        published_at = post.get('publishedAt') or post.get('created_utc') or post.get('created_at')
                        items_with_dates.append({
                            'text': text,
                            'publishedAt': published_at
                        })
                
                if items_with_dates:
                    # ใช้ time-weighted analysis เพื่อให้ post ใหม่มีน้ำหนักมากกว่า
                    sentiment_result = self.sentiment_analyzer.analyze_batch(
                        texts=[item['text'] for item in items_with_dates],
                        use_time_weighting=True,
                        items_with_dates=items_with_dates
                    )
                    if sentiment_result:
                        print(f"    ⏰ Reddit time-weighted sentiment: {sentiment_result.get('compound', 0):.3f} (avg age: {sentiment_result.get('avg_age_hours', 0):.1f}h)")
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
            from fetchers.twitter_fetcher import TwitterFetcher
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
        
        # 8. Validate sentiment กับแรงซื้อ/ขาย
        # สำหรับ validation ต้องใช้ข้อมูล real-time เพื่อความแม่นยำ
        print(f"  🔍 Validating sentiment against buy/sell pressure...")
        
        # ดึงข้อมูลหุ้นแบบ real-time สำหรับ validation
        realtime_stock_info = self.stock_info_manager.get_stock_info_for_validation(symbol_upper)
        if not realtime_stock_info:
            realtime_stock_info = result['stockInfo'] or {}
        
        validation_results = {}
        
        # Validate Yahoo Finance sentiment
        yahoo_sentiment = None
        if result['newsData']['sentiment']:
            yahoo_sentiment = result['newsData']['sentiment']['compound']
            yahoo_validation = self.sentiment_validator.validate_sentiment(
                yahoo_sentiment,
                'yahoo_finance',
                realtime_stock_info  # ใช้ข้อมูล real-time
            )
            validation_results['yahoo'] = yahoo_validation
            print(f"    📰 Yahoo Finance: {'✅' if yahoo_validation['is_valid'] else '❌'} "
                  f"Confidence: {yahoo_validation['confidence']:.2f}, "
                  f"Alignment: {yahoo_validation['alignment_score']:.2f}")
            print(f"      {yahoo_validation['reason']}")
        
        # Validate Reddit sentiment
        reddit_sentiment = None
        if result['redditData']['sentiment']:
            reddit_sentiment = result['redditData']['sentiment']['compound']
            reddit_validation = self.sentiment_validator.validate_sentiment(
                reddit_sentiment,
                'reddit',
                realtime_stock_info  # ใช้ข้อมูล real-time
            )
            validation_results['reddit'] = reddit_validation
            print(f"    🔴 Reddit: {'✅' if reddit_validation['is_valid'] else '❌'} "
                  f"Confidence: {reddit_validation['confidence']:.2f}, "
                  f"Alignment: {reddit_validation['alignment_score']:.2f}")
            print(f"      {reddit_validation['reason']}")
        
        # 9. Calculate overall sentiment (weighted average) - ใช้เฉพาะข้อมูลที่ผ่าน validation
        print(f"  🧠 Calculating overall sentiment (only validated sources)...")
        sentiment_scores = []
        weights = []
        confidences = []
        
        # Yahoo Finance News - ใช้เฉพาะถ้าผ่าน validation
        if result['newsData']['sentiment'] and result['newsData'].get('source', '').startswith('yahoo'):
            yahoo_valid = validation_results.get('yahoo', {})
            if yahoo_valid.get('is_valid', True):  # Yahoo Finance ยังแสดงแม้ confidence ต่ำ
                sentiment_scores.append(result['newsData']['sentiment']['compound'])
                # ปรับน้ำหนักตาม confidence
                base_yahoo_weight = min(2.0, 1.0 + (result['newsData']['articleCount'] / 30) * 0.5)
                confidence_multiplier = yahoo_valid.get('confidence', 1.0)
                yahoo_weight = base_yahoo_weight * confidence_multiplier
                weights.append(yahoo_weight)
                confidences.append(yahoo_valid.get('confidence', 1.0))
                print(f"    ✅ Yahoo Finance news weight: {yahoo_weight:.2f} (confidence: {confidence_multiplier:.2f})")
            else:
                print(f"    ⚠️  Yahoo Finance sentiment ไม่ผ่าน validation - ข้าม")
        
        # Reddit - ใช้เฉพาะถ้าผ่าน validation
        if result['redditData']['sentiment']:
            reddit_valid = validation_results.get('reddit', {})
            if reddit_valid.get('is_valid', False):  # Reddit ต้องผ่าน validation เท่านั้น
                sentiment_scores.append(result['redditData']['sentiment']['compound'])
                base_reddit_weight = min(0.5, (result['redditData']['mentionCount'] / 100) * 0.3)
                confidence_multiplier = reddit_valid.get('confidence', 0.5)
                reddit_weight = base_reddit_weight * confidence_multiplier
                weights.append(reddit_weight)
                confidences.append(reddit_valid.get('confidence', 0.5))
                print(f"    ✅ Reddit weight: {reddit_weight:.2f} (confidence: {confidence_multiplier:.2f})")
            else:
                print(f"    ❌ Reddit sentiment ไม่ผ่าน validation - ข้าม (อาจเป็น bot/manipulation)")
        
        # Twitter - ยังไม่ validate (optional)
        if result['twitterData']['sentiment']:
            sentiment_scores.append(result['twitterData']['sentiment']['compound'])
            twitter_weight = min(0.5, (result['twitterData']['tweetCount'] / 50) * 0.3)
            weights.append(twitter_weight)
            print(f"    🐦 Twitter weight: {twitter_weight:.2f}")
        
        if sentiment_scores:
            total_weight = sum(weights) if weights else 1
            if total_weight > 0:
                overall_compound = sum(s * w for s, w in zip(sentiment_scores, weights)) / total_weight
            else:
                overall_compound = sum(sentiment_scores) / len(sentiment_scores)
            
            # คำนวณ overall confidence จาก validation results
            overall_confidence = sum(confidences) / len(confidences) if confidences else 0.5
            
            result['overallSentiment'] = {
                'compound': overall_compound,
                'label': 'positive' if overall_compound >= 0.05 else ('negative' if overall_compound <= -0.05 else 'neutral'),
                'confidence': min(1.0, overall_confidence),
                'validation': validation_results  # เก็บ validation results
            }
        
        # เก็บ validation results ใน result
        result['validation'] = validation_results
        
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

