"""
YouTube API Integration Module
Fetches video transcripts and finance commentary from YouTube
"""
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import requests

# __file__ = backend/fetchers/youtube_fetcher.py
# ต้องการ path = reddit-hashtag-analytics/.env (ขึ้นไป 2 ระดับ)
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

class YouTubeFetcher:
    def __init__(self):
        self.api_key = os.getenv("YOUTUBE_API_KEY")
        self.base_url = "https://www.googleapis.com/youtube/v3"
        self.quota_exceeded = False  # Flag to track quota status
        
        if not self.api_key:
            print("⚠️ YOUTUBE_API_KEY not found in environment variables")
            print("   YouTube API features will be disabled")
        else:
            print(f"✅ YouTube API key loaded: {self.api_key[:10]}...")
    
    def search_videos(self, query: str, max_results: int = 10) -> List[Dict]:
        """
        Search for YouTube videos related to a query
        
        Args:
            query: Search query (e.g., stock symbol, company name)
            max_results: Maximum number of videos to return
            
        Returns:
            List of video dictionaries
        """
        if not self.api_key:
            print("⚠️ YouTube API key not configured")
            return []
        
        try:
            params = {
                'part': 'snippet',
                'q': query,
                'type': 'video',
                'maxResults': min(max_results, 50),
                'key': self.api_key,
                'order': 'relevance',
                'publishedAfter': (datetime.utcnow() - timedelta(days=7)).isoformat() + 'Z'
            }
            
            response = requests.get(f"{self.base_url}/search", params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                # ตรวจสอบ error จาก YouTube API
                if 'error' in data:
                    error = data['error']
                    error_message = error.get('message', 'Unknown error')
                    error_code = error.get('code', 'Unknown')
                    
                    # ตรวจสอบว่าเป็น quota exceeded หรือไม่
                    if error_code == 403 and 'quota' in error_message.lower():
                        self.quota_exceeded = True
                        print(f"❌ YouTube API quota exceeded!")
                        print(f"   Error: {error_message}")
                        print(f"   💡 Quota resets daily. Please try again tomorrow or upgrade your quota.")
                        return []
                    elif error_code == 403:
                        print(f"❌ YouTube API returned error: {error_code} - {error_message}")
                        print("   💡 This usually means:")
                        print("      - API key is invalid or expired")
                        print("      - API quota has been exceeded")
                        print("      - API key doesn't have required permissions")
                        return []
                    elif error_code == 400:
                        print(f"❌ YouTube API returned error: {error_code} - {error_message}")
                        print("   💡 This usually means invalid request parameters")
                        return []
                    elif error_code == 429:
                        self.quota_exceeded = True
                        print(f"❌ YouTube API quota exceeded (429)")
                        print(f"   Error: {error_message}")
                        print(f"   💡 Please wait or upgrade quota")
                        return []
                    else:
                        print(f"❌ YouTube API returned error: {error_code} - {error_message}")
                        return []
                
                videos = []
                
                for item in data.get('items', []):
                    snippet = item.get('snippet', {})
                    video_id = item.get('id', {}).get('videoId')
                    if not video_id:
                        continue
                    
                    videos.append({
                        'id': video_id,
                        'title': snippet.get('title', ''),
                        'description': snippet.get('description', ''),
                        'channelTitle': snippet.get('channelTitle', ''),
                        'publishedAt': snippet.get('publishedAt', ''),
                        'thumbnail': snippet.get('thumbnails', {}).get('default', {}).get('url', ''),
                        'url': f"https://www.youtube.com/watch?v={video_id}",
                        'query': query,
                        'fetchedAt': datetime.utcnow().isoformat()
                    })
                
                return videos
            else:
                error_text = response.text[:200]  # Limit error text length
                print(f"❌ YouTube API HTTP error: {response.status_code}")
                print(f"   Response: {error_text}")
                
                # Parse error if possible
                try:
                    error_data = response.json()
                    if 'error' in error_data:
                        error = error_data['error']
                        error_code = error.get('code', 'Unknown')
                        error_message = error.get('message', 'Unknown')
                        print(f"   Error message: {error_message}")
                        print(f"   Error code: {error_code}")
                        
                        # ตรวจสอบ quota exceeded
                        if error_code == 403 and 'quota' in error_message.lower():
                            self.quota_exceeded = True
                            print(f"   ⚠️ Quota exceeded - stopping further API calls")
                except:
                    pass
                
                return []
                
        except requests.exceptions.Timeout:
            print(f"❌ YouTube API request timeout for query '{query}'")
            return []
        except requests.exceptions.RequestException as e:
            print(f"❌ Network error fetching YouTube videos for '{query}': {e}")
            return []
        except Exception as e:
            print(f"❌ Unexpected error fetching YouTube videos for '{query}': {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def get_video_details(self, video_id: str) -> Optional[Dict]:
        """
        Get detailed information about a video
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            Video details dictionary
        """
        if not self.api_key:
            return None
        
        try:
            params = {
                'part': 'snippet,statistics,contentDetails',
                'id': video_id,
                'key': self.api_key
            }
            
            response = requests.get(f"{self.base_url}/videos", params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                items = data.get('items', [])
                if items:
                    item = items[0]
                    snippet = item.get('snippet', {})
                    stats = item.get('statistics', {})
                    
                    return {
                        'id': video_id,
                        'title': snippet.get('title', ''),
                        'description': snippet.get('description', ''),
                        'channelTitle': snippet.get('channelTitle', ''),
                        'publishedAt': snippet.get('publishedAt', ''),
                        'viewCount': int(stats.get('viewCount', 0)),
                        'likeCount': int(stats.get('likeCount', 0)),
                        'commentCount': int(stats.get('commentCount', 0)),
                        'duration': item.get('contentDetails', {}).get('duration', ''),
                        'url': f"https://www.youtube.com/watch?v={video_id}"
                    }
            return None
                
        except Exception as e:
            print(f"❌ Error fetching video details for {video_id}: {e}")
            return None
    
    def search_stock_videos(self, symbol: str, max_results: int = 10) -> List[Dict]:
        """Search for videos related to a stock symbol"""
        queries = [
            f"{symbol} stock",
            f"${symbol} analysis",
            f"{symbol} earnings",
            f"{symbol} news"
        ]
        
        all_videos = []
        for query in queries[:2]:  # Limit to avoid quota
            videos = self.search_videos(query, max_results // len(queries))
            all_videos.extend(videos)
        
        # Remove duplicates
        seen_ids = set()
        unique_videos = []
        for video in all_videos:
            if video['id'] and video['id'] not in seen_ids:
                seen_ids.add(video['id'])
                unique_videos.append(video)
        
        return unique_videos[:max_results]
    
    def search_finance_videos(self, max_results: int = 20) -> List[Dict]:
        """
        Search for general finance/stock market videos
        
        Args:
            max_results: Maximum number of videos to return
            
        Returns:
            List of video dictionaries
        """
        if not self.api_key:
            return []
        
        try:
            # Search queries for finance content
            queries = [
                "stock market",
                "trading",
                "investing",
                "stocks analysis",
                "market news"
            ]
            
            all_videos = []
            for query in queries[:3]:  # Limit to 3 queries to avoid quota
                videos = self.search_videos(query, max_results // len(queries))
                all_videos.extend(videos)
            
            # Remove duplicates by video ID
            seen_ids = set()
            unique_videos = []
            for video in all_videos:
                if video.get('id') and video['id'] not in seen_ids:
                    seen_ids.add(video['id'])
                    unique_videos.append(video)
            
            return unique_videos[:max_results]
            
        except Exception as e:
            print(f"❌ Error fetching finance videos: {e}")
            return []
    
    def search_news_videos(self, max_results: int = 50) -> List[Dict]:
        """
        ค้นหาวิดีโอข่าวสำคัญเกี่ยวกับตลาดหุ้น
        
        Args:
            max_results: จำนวนวิดีโอสูงสุดที่ต้องการ
            
        Returns:
            List of video dictionaries
        """
        if not self.api_key:
            print("⚠️ YouTube API key not configured - cannot fetch news videos")
            return []
        
        try:
            # คำค้นหาสำหรับข่าวสำคัญ (ลดจำนวนลงเพื่อประหยัด quota)
            news_queries = [
                # Federal Reserve / Interest Rates
                "federal reserve interest rate",
                "fed rate hike",
                "jerome powell",
                
                # Tax Policy
                "tax policy",
                "corporate tax",
                
                # Trump / Political
                "trump stock market",
                "trump policy",
                
                # Trade War
                "trade war",
                "tariff",
                
                # Economic Indicators
                "inflation cpi",
                "jobs report",
                
                # Global Economy
                "global economy",
                "world economy",
                
                # Market News
                "stock market news",
                "market analysis"
            ]
            
            all_videos = []
            seen_ids = set()
            successful_queries = 0
            failed_queries = 0
            quota_error_count = 0
            
            # ดึงวิดีโอจากแต่ละ query
            for query in news_queries:
                # หยุดทันทีถ้า quota หมดแล้ว
                if self.quota_exceeded:
                    print(f"⚠️ Stopping video search - quota exceeded detected")
                    break
                
                if len(all_videos) >= max_results:
                    break
                
                videos = self.search_videos(query, max_results=5)
                
                # ตรวจสอบว่าเป็น quota error หรือไม่
                if self.quota_exceeded:
                    quota_error_count += 1
                    if quota_error_count == 1:  # แสดงแค่ครั้งแรก
                        print(f"⚠️ YouTube API quota exceeded - stopping all queries")
                    break
                
                if videos:
                    successful_queries += 1
                    for video in videos:
                        video_id = video.get('id')
                        if video_id and video_id not in seen_ids:
                            seen_ids.add(video_id)
                            all_videos.append(video)
                else:
                    failed_queries += 1
            
            print(f"📊 News video search summary:")
            print(f"   Successful queries: {successful_queries}")
            print(f"   Failed queries: {failed_queries}")
            print(f"   Total unique videos: {len(all_videos)}")
            
            if self.quota_exceeded:
                print("⚠️ YouTube API quota exceeded!")
                print("   💡 Solutions:")
                print("      - Wait for daily quota reset (resets at midnight Pacific Time)")
                print("      - Request quota increase in Google Cloud Console")
                print("      - Use multiple API keys and rotate them")
            elif len(all_videos) == 0 and failed_queries > 0:
                print("⚠️ All queries failed. Possible issues:")
                print("   - YouTube API key invalid or expired")
                print("   - API quota exceeded")
                print("   - Network connectivity issues")
            
            return all_videos[:max_results]
            
        except Exception as e:
            print(f"❌ Error fetching news videos: {e}")
            import traceback
            traceback.print_exc()
            return []

