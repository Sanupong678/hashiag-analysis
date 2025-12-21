"""
News API Integration Module
Fetches news articles related to stocks and financial topics
"""
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import requests
from typing import List, Dict, Optional

# __file__ = backend/fetchers/news_fetcher.py
# ต้องการ path = reddit-hashtag-analytics/.env (ขึ้นไป 2 ระดับ)
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

class NewsFetcher:
    def __init__(self):
        # Support both NEWS_API_KEY and NEW_API_KEY (for typo compatibility)
        self.api_key = os.getenv("NEWS_API_KEY") or os.getenv("NEW_API_KEY")
        self.base_url = "https://newsapi.org/v2"
        
        if not self.api_key:
            print("⚠️ NEWS_API_KEY not found in environment variables")
        else:
            print(f"✅ News API key loaded: {self.api_key[:10]}...")
        
    def fetch_news(self, query: str, days_back: int = 7, max_results: int = 50) -> List[Dict]:
        """
        Fetch news articles for a given query (stock symbol or keyword)
        
        Args:
            query: Stock symbol or keyword to search
            days_back: Number of days to look back
            max_results: Maximum number of articles to return
            
        Returns:
            List of news articles with title, description, source, publishedAt, url
        """
        if not self.api_key:
            print("⚠️ NEWS_API_KEY not found in environment variables")
            return []
        
        try:
            # Calculate date range
            to_date = datetime.now()
            from_date = to_date - timedelta(days=days_back)
            
            # Search in both everything endpoint and headlines
            articles = []
            
            # Search everything endpoint
            params = {
                'q': query,
                'apiKey': self.api_key,
                'language': 'en',
                'sortBy': 'publishedAt',
                'pageSize': min(max_results, 100),
                'from': from_date.strftime('%Y-%m-%d'),
                'to': to_date.strftime('%Y-%m-%d')
            }
            
            response = requests.get(f"{self.base_url}/everything", params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'ok':
                    for article in data.get('articles', []):
                        articles.append({
                            'title': article.get('title', ''),
                            'description': article.get('description', ''),
                            'source': article.get('source', {}).get('name', 'Unknown'),
                            'publishedAt': article.get('publishedAt', ''),
                            'url': article.get('url', ''),
                            'urlToImage': article.get('urlToImage', ''),
                            'query': query,
                            'fetchedAt': datetime.utcnow().isoformat()
                        })
            
            # Also search headlines for recent news
            if len(articles) < max_results:
                params_headlines = {
                    'q': query,
                    'apiKey': self.api_key,
                    'country': 'us',
                    'category': 'business',
                    'pageSize': min(max_results - len(articles), 100)
                }
                
                response_headlines = requests.get(f"{self.base_url}/top-headlines", params=params_headlines, timeout=10)
                
                if response_headlines.status_code == 200:
                    data_headlines = response_headlines.json()
                    if data_headlines.get('status') == 'ok':
                        for article in data_headlines.get('articles', []):
                            # Avoid duplicates
                            if not any(a['url'] == article.get('url', '') for a in articles):
                                articles.append({
                                    'title': article.get('title', ''),
                                    'description': article.get('description', ''),
                                    'source': article.get('source', {}).get('name', 'Unknown'),
                                    'publishedAt': article.get('publishedAt', ''),
                                    'url': article.get('url', ''),
                                    'urlToImage': article.get('urlToImage', ''),
                                    'query': query,
                                    'fetchedAt': datetime.utcnow().isoformat()
                                })
            
            return articles[:max_results]
            
        except Exception as e:
            print(f"❌ Error fetching news for '{query}': {e}")
            return []
    
    def fetch_stock_news(self, symbol: str, days_back: int = 7) -> List[Dict]:
        """Fetch news specifically for a stock symbol"""
        # Try both symbol and company name variations
        queries = [symbol, f"${symbol}", f"{symbol} stock"]
        all_articles = []
        
        for query in queries:
            articles = self.fetch_news(query, days_back, max_results=20)
            all_articles.extend(articles)
        
        # Remove duplicates based on URL
        seen_urls = set()
        unique_articles = []
        for article in all_articles:
            if article['url'] not in seen_urls:
                seen_urls.add(article['url'])
                unique_articles.append(article)
        
        return unique_articles

