"""
Post Normalizer - สำหรับ normalize post structure ให้ทุก collection เหมือนกัน
"""
from datetime import datetime
from typing import Dict, Optional

def normalize_post(post: Dict, source: str, symbol: Optional[str] = None) -> Dict:
    """
    Normalize post structure ให้เหมือนกันทุก collection
    
    Args:
        post: Post dictionary จาก source ต่างๆ
        source: Source name (reddit, yahoo, x, youtube, news)
        symbol: Stock symbol (optional)
    
    Returns:
        Normalized post dictionary
    """
    # สร้าง id ถ้ายังไม่มี
    post_id = post.get('id') or post.get('uuid') or post.get('post_id') or post.get('_id')
    if isinstance(post_id, dict):
        post_id = str(post_id)
    
    # สร้าง title และ selftext
    title = post.get('title', '') or post.get('headline', '') or ''
    # ใช้ selftext, summary, description, content, หรือ full_content (จำกัด 500 ตัวอักษร)
    selftext = post.get('selftext', '') or post.get('summary', '') or post.get('description', '') or post.get('content', '') or ''
    # ถ้ายังไม่มี ให้ใช้ full_content (จำกัด 500 ตัวอักษรเพื่อไม่ให้ยาวเกินไป)
    if not selftext:
        full_content = post.get('full_content', '')
        if full_content:
            selftext = full_content[:500]  # ใช้แค่ 500 ตัวอักษรแรก
    
    # สร้าง created_utc
    created_utc = post.get('created_utc')
    if not created_utc:
        created_utc = post.get('publishedAt') or post.get('published_at') or post.get('created_at')
    if isinstance(created_utc, (int, float)):
        created_utc = datetime.fromtimestamp(created_utc).isoformat()
    elif isinstance(created_utc, datetime):
        created_utc = created_utc.isoformat()
    elif not created_utc:
        created_utc = datetime.utcnow().isoformat()
    
    # สร้าง subreddit (source name)
    subreddit = post.get('subreddit') or post.get('source') or post.get('publisher') or source
    
    # สร้าง keyword (symbol)
    keyword = post.get('keyword') or post.get('symbol') or symbol or ''
    
    # Normalized post structure
    normalized = {
        # Standard fields (เหมือน Reddit structure)
        'id': str(post_id) if post_id else '',
        'title': title,
        'selftext': selftext,
        'score': post.get('score', 0) or 0,
        'num_comments': post.get('num_comments', 0) or post.get('comment_count', 0) or 0,
        'created_utc': created_utc,
        'subreddit': subreddit,
        'keyword': keyword.upper() if keyword else '',
        'url': post.get('url', '') or post.get('link', '') or '',
        'author': post.get('author', '') or post.get('publisher', '') or source,
        'upvote_ratio': post.get('upvote_ratio', 0) or 0,
        'is_self': post.get('is_self', False),
        'over_18': post.get('over_18', False),
        'fetched_at': post.get('fetched_at') or datetime.utcnow().isoformat(),
        
        # Source specific fields (เก็บไว้เพื่อ backward compatibility)
        'source': source,
        'symbol': keyword.upper() if keyword else '',
    }
    
    # เพิ่ม source-specific fields
    if source == 'yahoo':
        normalized.update({
            'publishedAt': created_utc,
            'type': post.get('type', 'STORY'),
            'uuid': post.get('uuid', ''),
            'newsHash': post.get('newsHash', ''),
            # Article details (ถ้ามี - ดึงจาก URL)
            'full_content': post.get('full_content', ''),
            # 'images': post.get('images', []),  # ไม่ดึงรูปภาพเพื่อลดพื้นที่
            'tags': post.get('tags', []),
            'word_count': post.get('word_count', 0),
            'full_content': post.get('full_content', ''),
            'images': post.get('images', []),
            'tags': post.get('tags', []),
            'word_count': post.get('word_count', 0),
        })
    elif source == 'reddit':
        normalized.update({
            'ticker': keyword.upper() if keyword else '',
            # ✅ ไม่เก็บ comments array (เก็บแยกใน comment_reddit collection)
            # เก็บแค่ comments_count สำหรับ backward compatibility
            'comments_count': post.get('comments_count', 0) or post.get('comments_fetched', 0) or len(post.get('comments', [])),
            'comments_fetched': post.get('comments_fetched', 0) or len(post.get('comments', [])),  # จำนวน comments ที่ดึงได้
            'post_sentiment': post.get('post_sentiment'),  # Original post sentiment (ก่อนรวม comments)
        })
    elif source == 'x' or source == 'twitter':
        normalized.update({
            'tweet_id': post.get('tweet_id', ''),
            'retweet_count': post.get('retweet_count', 0),
            'like_count': post.get('like_count', 0),
        })
    elif source == 'youtube':
        normalized.update({
            'video_id': post.get('video_id', ''),
            'view_count': post.get('view_count', 0),
            'like_count': post.get('like_count', 0),
        })
    elif source == 'news':
        normalized.update({
            'publishedAt': created_utc,
            'newsHash': post.get('newsHash', ''),
        })
    
    return normalized

def get_collection_name(source: str) -> str:
    """
    获取 collection name ตาม source
    
    Args:
        source: Source name (reddit, yahoo, x, youtube, news)
    
    Returns:
        Collection name
    """
    collection_map = {
        'reddit': 'post_reddit',
        'yahoo': 'post_yahoo',
        'x': 'post_x',
        'twitter': 'post_x',
        'youtube': 'post_youtube',
        'news': 'post_news',
    }
    return collection_map.get(source.lower(), f'post_{source.lower()}')

def get_comment_collection_name(source: str) -> str:
    """
    Get comment collection name ตาม source
    
    Args:
        source: Source name (reddit, yahoo, x, youtube, news)
    
    Returns:
        Comment collection name
    """
    comment_collection_map = {
        'reddit': 'comment_reddit',
        'yahoo': 'comment_yahoo',
        'x': 'comment_x',
        'twitter': 'comment_x',
        'youtube': 'comment_youtube',
        'news': 'comment_news',
    }
    return comment_collection_map.get(source.lower(), f'comment_{source.lower()}')

