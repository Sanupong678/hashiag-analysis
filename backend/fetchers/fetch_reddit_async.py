"""
Async Reddit Fetcher - ใช้ Async PRAW แทน PRAW (sync)
แก้ปัญหา warning และ performance issues
"""
import asyncpraw
import os
from dotenv import load_dotenv
from datetime import datetime
from database.db_config import db
from typing import List, Dict, Optional

# ✅ โหลด .env จากโฟลเดอร์หลัก
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

# ✅ สร้าง Async Reddit instance (global แต่จะสร้างใหม่ในแต่ละ async function)
async def get_reddit_instance():
    """
    สร้าง Async Reddit instance
    """
    return asyncpraw.Reddit(
        client_id=os.getenv("REDDIT_CLIENT_ID"),
        client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
        user_agent=os.getenv("USER_AGENT")
    )

async def fetch_posts_async(keyword: str = "AI", limit: int = 50, timeout: float = 10.0) -> List[Dict]:
    """
    Fetch Reddit posts for a given keyword (Async version)
    
    Args:
        keyword: Search keyword (e.g., stock symbol)
        limit: Maximum number of posts to fetch
        timeout: Timeout in seconds (default: 10 seconds เพื่อไม่ให้ block นาน)
        
    Returns:
        List of post dictionaries
    """
    # Suppress all print statements - ให้แสดงแค่ progress bar
    posts = []
    
    try:
        import asyncio
        # ใช้ timeout เพื่อไม่ให้ Reddit API block นานเกินไป
        async def fetch_with_timeout():
        # สร้าง Async Reddit instance
        reddit = await get_reddit_instance()
        
            try:
        # Search in all subreddits (async)
        subreddit = await reddit.subreddit("all")
        search_results = subreddit.search(keyword, limit=limit, sort='relevance', time_filter='all')
        
        async for submission in search_results:
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
            except Exception:
                # Suppress error messages
                continue
            finally:
        # Close Reddit instance
        await reddit.close()
        
        # ใช้ timeout เพื่อไม่ให้ Reddit API block นานเกินไป
        try:
            await asyncio.wait_for(fetch_with_timeout(), timeout=timeout)
        except asyncio.TimeoutError:
            # ถ้า timeout ให้ return posts ที่ดึงมาได้แล้ว (ไม่ต้องรอให้หมด)
            pass
                
    except Exception:
        # Suppress all error messages - ไม่แสดง error เพื่อให้ progress bar ดูสะอาด
        pass

    if posts:
        try:
            # ใช้ collection post_reddit
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
                    # Suppress print - ไม่แสดง log
                # Suppress all other print statements
        except Exception:
            # Suppress error messages
            pass
    # Suppress "No posts found" message

    return posts

async def fetch_comments_async(post_id: str, limit: int = 20) -> List[Dict]:
    """
    Fetch comments for a specific Reddit post (Async version)
    
    Args:
        post_id: Reddit post ID
        limit: Maximum number of comments to fetch
        
    Returns:
        List of comment dictionaries
    """
    comments = []
    try:
        reddit = await get_reddit_instance()
        submission = await reddit.submission(id=post_id)
        await submission.comments.replace_more(limit=0)  # Remove "more comments" placeholders
        
        comment_list = submission.comments.list()[:limit]
        for comment in comment_list:
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
        
        await reddit.close()
    except Exception:
        # Suppress error messages
        pass
    
    return comments

