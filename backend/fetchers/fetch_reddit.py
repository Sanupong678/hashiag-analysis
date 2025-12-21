import praw
import os
from dotenv import load_dotenv
from datetime import datetime
from database.db_config import db

# ✅ โหลด .env จากโฟลเดอร์หลัก (นอก backend)
# __file__ = backend/fetchers/fetch_reddit.py
# ต้องการ path = reddit-hashtag-analytics/.env
# ดังนั้นต้องขึ้นไป 2 ระดับ: .. (fetchers -> backend), .. (backend -> root)
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

# ✅ ตรวจสอบค่าที่โหลดได้
print("🔍 Loading Reddit credentials:")
print("CLIENT_ID:", os.getenv("REDDIT_CLIENT_ID"))
print("CLIENT_SECRET:", os.getenv("REDDIT_CLIENT_SECRET"))
print("USER_AGENT:", os.getenv("USER_AGENT"))

# ✅ สร้าง Reddit instance
reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
    user_agent=os.getenv("USER_AGENT")
)

def fetch_posts(keyword="AI", limit=50):
    """
    Fetch Reddit posts for a given keyword
    
    Args:
        keyword: Search keyword (e.g., stock symbol)
        limit: Maximum number of posts to fetch
        
    Returns:
        List of post dictionaries
    """
    print(f"🚀 Fetching Reddit posts for keyword: {keyword}")
    posts = []
    
    # Check if Reddit instance is properly configured
    if not reddit:
        print("❌ Reddit instance not initialized. Check your .env file.")
        return posts
    
    try:
        # Rate limiting: Reddit allows 60 requests per minute
        # Using read-only mode (no authentication required for public data)
        
        # Search in all subreddits
        search_results = reddit.subreddit("all").search(keyword, limit=limit, sort='relevance', time_filter='all')
        
        for submission in search_results:
            try:
                post = {
                    "id": submission.id,
                    "title": submission.title,
                    "selftext": getattr(submission, 'selftext', '') or '',
                    "score": submission.score or 0,
                    "num_comments": submission.num_comments or 0,
                    "created_utc": datetime.utcfromtimestamp(submission.created_utc),
                    "subreddit": str(submission.subreddit),
                    "keyword": keyword,
                    "url": submission.url,
                    "author": str(submission.author) if submission.author else "[deleted]",
                    "upvote_ratio": getattr(submission, 'upvote_ratio', 0),
                    "is_self": submission.is_self,
                    "over_18": getattr(submission, 'over_18', False),
                    "fetched_at": datetime.utcnow()
                }
                posts.append(post)
            except Exception as e:
                print(f"⚠️ Error processing post {submission.id}: {e}")
                continue
                
    except Exception as e:
        error_msg = str(e)
        print(f"⚠️ Error fetching Reddit posts: {error_msg}")
        
        # Handle specific Reddit API errors
        if "429" in error_msg or "rate limit" in error_msg.lower():
            print("⏳ Rate limit exceeded. Please wait before trying again.")
        elif "403" in error_msg or "forbidden" in error_msg.lower():
            print("🔒 Access forbidden. Check your API credentials.")
        elif "401" in error_msg or "unauthorized" in error_msg.lower():
            print("🔑 Unauthorized. Check your CLIENT_ID and CLIENT_SECRET.")
        else:
            print(f"❌ Unknown error: {error_msg}")

    if posts:
        try:
            # ใช้ collection post_reddit แทน posts
            from utils.post_normalizer import get_collection_name, normalize_post
            
            collection_name = get_collection_name('reddit')
            if db is not None and hasattr(db, collection_name):
                post_collection = getattr(db, collection_name)
                
                # Normalize posts และเพิ่ม keyword
                normalized_posts = []
                for p in posts:
                    normalized = normalize_post(p, 'reddit', keyword)
                    normalized['keyword'] = keyword.upper()
                    normalized_posts.append(normalized)
                
                # Check for duplicates before inserting
                existing_ids = set(post_collection.distinct("id"))
                new_posts = [p for p in normalized_posts if p["id"] not in existing_ids]
                
                if new_posts:
                    post_collection.insert_many(new_posts)
                    print(f"✅ Inserted {len(new_posts)} new posts for '{keyword}' (skipped {len(normalized_posts) - len(new_posts)} duplicates)")
                else:
                    print(f"ℹ️ All {len(normalized_posts)} posts already exist in database")
            else:
                print(f"⚠️ Collection {collection_name} not available")
        except Exception as e:
            print(f"⚠️ Error inserting posts: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("⚠️ No posts found or fetch failed")

    return posts

def fetch_comments(post_id, limit=20):
    """
    Fetch comments for a specific Reddit post
    
    Args:
        post_id: Reddit post ID
        limit: Maximum number of comments to fetch
        
    Returns:
        List of comment dictionaries
    """
    comments = []
    try:
        submission = reddit.submission(id=post_id)
        submission.comments.replace_more(limit=0)  # Remove "more comments" placeholders
        
        for comment in submission.comments.list()[:limit]:
            if hasattr(comment, 'body') and comment.body != '[deleted]':
                comments.append({
                    "id": comment.id,
                    "post_id": post_id,
                    "body": comment.body,
                    "score": comment.score or 0,
                    "created_utc": datetime.utcfromtimestamp(comment.created_utc),
                    "author": str(comment.author) if comment.author else "[deleted]",
                    "is_submitter": comment.is_submitter
                })
    except Exception as e:
        print(f"⚠️ Error fetching comments for post {post_id}: {e}")
    
    return comments
