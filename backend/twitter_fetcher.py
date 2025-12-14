"""
Twitter/X API Integration Module (Optional)
Tracks posts from key influencers and stock-related tweets
Note: Requires Twitter API v2 access (paid tier recommended)
"""
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import requests

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

class TwitterFetcher:
    def __init__(self):
        # Support multiple environment variable names for X/Twitter
        self.bearer_token = (
            os.getenv("TWITTER_BEARER_TOKEN") or 
            os.getenv("X_BEARER_TOKEN") or 
            os.getenv("X_API_KEY") or
            os.getenv("X_API_TOKEN")
        )
        self.base_url = "https://api.twitter.com/2"
        
        # Key influencers to track
        self.influencers = {
            "elonmusk": "Elon Musk",
            "realDonaldTrump": "Donald Trump",
            "WarrenBuffett": "Warren Buffett",
            "jimcramer": "Jim Cramer"
        }
        
        if not self.bearer_token:
            print("⚠️ TWITTER_BEARER_TOKEN/X_BEARER_TOKEN not found in environment variables")
            print("   Twitter/X API features will be disabled")
        else:
            print(f"✅ Twitter/X API token loaded: {self.bearer_token[:10]}...")
    
    def search_tweets(self, query: str, max_results: int = 50) -> List[Dict]:
        """
        Search for tweets containing a query
        
        Args:
            query: Search query (e.g., stock symbol, company name)
            max_results: Maximum number of tweets to return
            
        Returns:
            List of tweets with text, author, created_at, etc.
        """
        if not self.bearer_token:
            print("⚠️ TWITTER_BEARER_TOKEN not found in environment variables")
            return []
        
        try:
            headers = {
                "Authorization": f"Bearer {self.bearer_token}"
            }
            
            params = {
                "query": f"{query} -is:retweet lang:en",
                "max_results": min(max_results, 100),
                "tweet.fields": "created_at,author_id,public_metrics,text",
                "user.fields": "username,name",
                "expansions": "author_id"
            }
            
            response = requests.get(
                f"{self.base_url}/tweets/search/recent",
                headers=headers,
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                tweets = []
                
                # Map user IDs to usernames
                users = {}
                if "includes" in data and "users" in data["includes"]:
                    for user in data["includes"]["users"]:
                        users[user["id"]] = user
                
                for tweet in data.get("data", []):
                    author_id = tweet.get("author_id")
                    author = users.get(author_id, {})
                    
                    tweets.append({
                        "id": tweet.get("id"),
                        "text": tweet.get("text", ""),
                        "author": author.get("username", "unknown"),
                        "author_name": author.get("name", "Unknown"),
                        "created_at": tweet.get("created_at", ""),
                        "metrics": tweet.get("public_metrics", {}),
                        "query": query,
                        "fetchedAt": datetime.utcnow().isoformat()
                    })
                
                return tweets
            else:
                print(f"❌ Twitter API error: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            print(f"❌ Error fetching tweets for '{query}': {e}")
            return []
    
    def get_influencer_tweets(self, username: str, max_results: int = 20) -> List[Dict]:
        """
        Get recent tweets from a specific influencer
        
        Args:
            username: Twitter username (without @)
            max_results: Maximum number of tweets
            
        Returns:
            List of tweets from the influencer
        """
        if not self.bearer_token:
            return []
        
        try:
            headers = {
                "Authorization": f"Bearer {self.bearer_token}"
            }
            
            # First, get user ID
            user_response = requests.get(
                f"{self.base_url}/users/by/username/{username}",
                headers=headers,
                timeout=10
            )
            
            if user_response.status_code != 200:
                return []
            
            user_data = user_response.json()
            user_id = user_data.get("data", {}).get("id")
            
            if not user_id:
                return []
            
            # Get user's tweets
            params = {
                "max_results": min(max_results, 100),
                "tweet.fields": "created_at,public_metrics,text",
                "exclude": "retweets,replies"
            }
            
            tweets_response = requests.get(
                f"{self.base_url}/users/{user_id}/tweets",
                headers=headers,
                params=params,
                timeout=10
            )
            
            if tweets_response.status_code == 200:
                data = tweets_response.json()
                tweets = []
                
                for tweet in data.get("data", []):
                    tweets.append({
                        "id": tweet.get("id"),
                        "text": tweet.get("text", ""),
                        "author": username,
                        "created_at": tweet.get("created_at", ""),
                        "metrics": tweet.get("public_metrics", {}),
                        "fetchedAt": datetime.utcnow().isoformat()
                    })
                
                return tweets
            else:
                return []
                
        except Exception as e:
            print(f"❌ Error fetching influencer tweets for '{username}': {e}")
            return []
    
    def track_stock_mentions(self, symbol: str, max_results: int = 50) -> List[Dict]:
        """Track mentions of a stock symbol on Twitter"""
        queries = [symbol, f"${symbol}", f"{symbol} stock"]
        all_tweets = []
        
        for query in queries:
            tweets = self.search_tweets(query, max_results // len(queries))
            all_tweets.extend(tweets)
        
        # Remove duplicates
        seen_ids = set()
        unique_tweets = []
        for tweet in all_tweets:
            if tweet["id"] not in seen_ids:
                seen_ids.add(tweet["id"])
                unique_tweets.append(tweet)
        
        return unique_tweets[:max_results]
    
    def get_influencer_impact(self, symbol: str) -> Dict:
        """
        Check if any tracked influencers have mentioned the stock
        
        Returns:
            Dictionary with influencer mentions and impact analysis
        """
        impact_data = {
            "symbol": symbol,
            "influencer_mentions": [],
            "fetchedAt": datetime.utcnow().isoformat()
        }
        
        for username, name in self.influencers.items():
            tweets = self.get_influencer_tweets(username, max_results=50)
            
            # Check if any tweets mention the stock
            relevant_tweets = [
                tweet for tweet in tweets
                if symbol.upper() in tweet["text"].upper() or f"${symbol.upper()}" in tweet["text"]
            ]
            
            if relevant_tweets:
                impact_data["influencer_mentions"].append({
                    "influencer": name,
                    "username": username,
                    "tweets": relevant_tweets,
                    "count": len(relevant_tweets)
                })
        
        return impact_data

