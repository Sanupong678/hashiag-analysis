"""
Reddit Bulk Processor - ดึง Reddit แบบ bulk (time-based)
แทนการดึง per-stock เพื่อให้เร็วขึ้นมาก
"""
import asyncio
import asyncpraw
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
from database.db_config import db
from typing import List, Dict, Optional, Set
from processors.sentiment_analyzer import SentimentAnalyzer
from utils.post_normalizer import normalize_post, get_collection_name, get_comment_collection_name
import re
import hashlib
import time

# โหลด .env
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

class RedditBulkProcessor:
    """
    ดึง Reddit posts แบบ bulk (time-based)
    - ดึง posts ใหม่ทุก 45 วินาที (ตาม reddit_bulk_scheduler)
    - Extract symbols จาก posts
    - วิเคราะห์ sentiment ครั้งเดียวต่อ post
    """
    
    def __init__(self):
        self.sentiment_analyzer = SentimentAnalyzer()
        # ✅ ลด subreddits เป็น 60 ตัว (เลือกที่ popular และ active มากที่สุด)
        # เรียงตามความ popular และความเกี่ยวข้องกับหุ้น/การลงทุน
        self.subreddits = [
            # Tier 1: Most Popular Stock/Investing (1-25) - ถูกพูดถึงมากที่สุด
            'wallstreetbets',      # 20M+ members - Most popular
            'stocks',              # 9M+ members
            'StockMarket',         # 3.9M+ members
            'Daytrading',          # 4.9M+ members
            'pennystocks',         # 2.1M+ members
            'investing',           # 2M+ members
            'CryptoCurrency',      # 6M+ members
            'Bitcoin',             # 4M+ members
            'options',             # 1.5M+ members
            'ethereum',            # 2M+ members
            'dogecoin',            # 2M+ members
            'personalfinance',     # 15M+ members
            'financialindependence', # 1M+ members
            'RobinHood',           # 948K+ members
            'dividends',           # 400K+ members
            'algotrading',         # 200K+ members
            'ValueInvesting',      # 200K+ members
            'trading',             # 200K+ members
            'Bogleheads',          # 200K+ members
            'SecurityAnalysis',    # 150K+ members
            'investments',         # 150K+ members
            'Stock_Picks',         # 100K+ members
            'StockMarketChat',     # 80K+ members
            'SPACs',               # 70K+ members
            'weedstocks',          # 60K+ members
            
            # Tier 2: Trading & Real Estate (26-40)
            'realestateinvesting', # 200K+ members
            'realestate',          # 1M+ members
            'swingtrading',        # 40K+ members
            'Forex',               # 100K+ members
            'fatFIRE',             # 100K+ members
            'leanFIRE',            # 100K+ members
            'REBubble',            # 100K+ members
            'etfs',                # 30K+ members
            'indexfunds',          # 50K+ members
            'gold',                # 50K+ members
            'landlord',            # 50K+ members
            'FIREyFemmes',         # 50K+ members
            'forex',               # 50K+ members
            'bonds',               # 30K+ members
            'silver',              # 30K+ members
            
            # Tier 3: Technology & AI Stocks (41-55)
            'technology',          # 1M+ members
            'MachineLearning',     # 2M+ members
            'programming',         # 3M+ members
            'datascience',         # 1M+ members
            'tech',                # 500K+ members
            'artificialintelligence', # 200K+ members
            'cybersecurity',       # 100K+ members
            'artificial',          # 100K+ members
            'intel',              # 50K+ members
            'semiconductors',      # 50K+ members
            'AMD_Stock',           # 30K+ members
            'NVIDIAClub',          # 20K+ members
            'cloudcomputing',      # 20K+ members
            'chipstocks',          # 10K+ members
            
            # Tier 4: Sector-Specific & Crypto (56-60)
            'teslamotors',         # 1M+ members
            'tesla',               # 500K+ members
            'teslainvestorsclub',  # 200K+ members
            'electricvehicles',    # 200K+ members
            'automotive',          # 200K+ members
            'cardano',             # 500K+ members
            'ethtrader',           # 200K+ members
            'solana',              # 200K+ members
            'NFT',                 # 200K+ members
            'cryptomarkets'        # 100K+ members
        ]
        
        # ✅ ตรวจสอบและลบ duplicates
        self.subreddits = list(dict.fromkeys(self.subreddits))  # เก็บลำดับเดิมแต่ลบ duplicates
        self.last_fetched_at = None
        # ✅ ไม่ใช้ processed_post_ids ใน memory (จะตรวจสอบจาก database แทน)
        # self.processed_post_ids: Set[str] = set()
        
        # Ticker ignore list (false positives)
        self.ignore_tickers = {
            'USD', 'GDP', 'CEO', 'IPO', 'ETF', 'SEC', 'IRS', 'FDA', 
            'AI', 'IT', 'TV', 'PC', 'USA', 'ON', 'ALL', 'FOR', 'THE',
            'AND', 'OR', 'IS', 'AT', 'TO', 'IN', 'OF', 'AS', 'BE'
        }
    
    async def get_reddit_instance(self):
        """สร้าง Async Reddit instance"""
        return asyncpraw.Reddit(
            client_id=os.getenv("REDDIT_CLIENT_ID"),
            client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
            user_agent=os.getenv("USER_AGENT")
        )
    
    def extract_tickers(self, text: str, valid_tickers: Set[str]) -> Set[str]:
        """
        Extract stock tickers จากข้อความ
        
        รองรับ:
        - $AAPL
        - AAPL (standalone)
        - AAPL, MSFT, TSLA (comma-separated)
        
        Args:
            text: ข้อความที่ต้องการ extract
            valid_tickers: Set ของ ticker symbols ที่ถูกต้อง
            
        Returns:
            Set ของ ticker symbols ที่พบ
        """
        if not text or not valid_tickers or len(valid_tickers) == 0:
            return set()
        
        tickers = set()
        text_upper = text.upper()
        
        # Pattern 1: $SYMBOL (สำคัญที่สุด - ใช้บ่อยที่สุด)
        dollar_pattern = re.compile(r'\$([A-Z]{1,5})\b')
        dollar_matches = dollar_pattern.findall(text_upper)
        for ticker in dollar_matches:
            if ticker in valid_tickers and ticker not in self.ignore_tickers:
                tickers.add(ticker)
        
        # Pattern 2: Standalone ticker (ต้องมี context)
        # หา ticker ที่อยู่หลังคำสำคัญ เช่น "buy AAPL", "AAPL stock"
        standalone_pattern = re.compile(
            r'\b(buy|sell|hold|trade|stock|shares?|ticker|symbol|NYSE|NASDAQ)\s+([A-Z]{1,5})\b',
            re.IGNORECASE
        )
        standalone_matches = standalone_pattern.findall(text_upper)
        for _, ticker in standalone_matches:
            if ticker in valid_tickers and ticker not in self.ignore_tickers:
                tickers.add(ticker)
        
        # Pattern 2b: Standalone ticker ที่อยู่หน้าคำสำคัญ เช่น "AAPL is", "TSLA to"
        standalone_before_pattern = re.compile(
            r'\b([A-Z]{1,5})\s+(is|to|will|can|should|going|up|down|buy|sell|hold|stock|shares?|ticker|symbol)\b',
            re.IGNORECASE
        )
        standalone_before_matches = standalone_before_pattern.findall(text_upper)
        for ticker, _ in standalone_before_matches:
            if ticker in valid_tickers and ticker not in self.ignore_tickers:
                tickers.add(ticker)
        
        # Pattern 3: Ticker ใน parentheses หรือ brackets
        bracket_pattern = re.compile(r'[\(\[]([A-Z]{1,5})[\)\]]')
        bracket_matches = bracket_pattern.findall(text_upper)
        for ticker in bracket_matches:
            if ticker in valid_tickers and ticker not in self.ignore_tickers:
                tickers.add(ticker)
        
        # Pattern 4: Ticker ที่อยู่หลัง "ticker:" หรือ "symbol:"
        colon_pattern = re.compile(r'(?:ticker|symbol):\s*([A-Z]{1,5})\b', re.IGNORECASE)
        colon_matches = colon_pattern.findall(text_upper)
        for ticker in colon_matches:
            if ticker in valid_tickers and ticker not in self.ignore_tickers:
                tickers.add(ticker)
        
        # Pattern 5: Ticker ที่อยู่ระหว่าง spaces หรือ punctuation (เช่น "I like AAPL", "AAPL, MSFT")
        # ต้องมี context ว่าเป็น ticker (เช่น อยู่หลังคำสำคัญ หรือมี comma/period)
        word_boundary_pattern = re.compile(r'\b([A-Z]{2,5})\b')
        word_matches = word_boundary_pattern.findall(text_upper)
        for ticker in word_matches:
            # ตรวจสอบว่าเป็น valid ticker และไม่ใช่ ignore list
            if ticker in valid_tickers and ticker not in self.ignore_tickers:
                # ตรวจสอบ context: ต้องมีคำสำคัญใกล้ๆ หรือมี punctuation
                ticker_pos = text_upper.find(ticker)
                if ticker_pos >= 0:
                    # ดู context รอบๆ ticker (50 ตัวอักษรก่อนและหลัง)
                    context_start = max(0, ticker_pos - 50)
                    context_end = min(len(text_upper), ticker_pos + len(ticker) + 50)
                    context = text_upper[context_start:context_end]
                    # ถ้ามีคำสำคัญใน context ให้เพิ่ม ticker
                    context_keywords = ['STOCK', 'SHARE', 'TICKER', 'SYMBOL', 'BUY', 'SELL', 'HOLD', 'TRADE', 
                                     'PRICE', 'MARKET', 'INVEST', 'PORTFOLIO', 'POSITION', 'CALL', 'PUT',
                                     'OPTION', 'DIVIDEND', 'EARNINGS', 'REVENUE', 'EPS', 'PE', 'RATIO']
                    if any(keyword in context for keyword in context_keywords):
                        tickers.add(ticker)
        
        return tickers
    
    async def fetch_new_posts_bulk(self, since: Optional[datetime] = None, limit_per_subreddit: int = 500, valid_tickers: Optional[Set[str]] = None) -> List[Dict]:
        """
        ดึง Reddit posts ใหม่แบบ bulk
        
        Args:
            since: วันที่เริ่มดึง (ถ้า None = ดึง 2 ชั่วโมงล่าสุด)
            limit_per_subreddit: จำนวน posts ต่อ subreddit (default: 500, แต่จะปรับตามช่วงเวลาที่ดึง)
            valid_tickers: Set of valid ticker symbols (สำหรับ extract symbols จาก comments)
            
        Returns:
            List of posts
        """
        if since is None:
            # ✅ เพิ่มเป็น 1 ชั่วโมง เพื่อดึง posts ได้มากขึ้น (แม้จะดึงทุก 30 วินาที)
            # เพราะ Reddit อาจจะไม่มี posts ใหม่ทุก 30 วินาที
            since = datetime.utcnow() - timedelta(hours=1)
        
        all_posts = []
        reddit = await self.get_reddit_instance()
        
        from utils.progress_bar import draw_progress_bar, reset_progress
        
        print(f"   🔍 กำลังดึง posts จาก {len(self.subreddits)} subreddits")
        print(f"   ⏰ ดึง posts ที่สร้างหลังจาก: {since.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Reset progress bar
        reset_progress()
        
        # ✅ ตัวนับสำหรับ comments progress bar
        total_comments_processed = 0
        comments_progress_shown = False  # ตรวจสอบว่าแสดง progress bar สำหรับ comments หรือยัง
        
        try:
            subreddit_idx = 0
            for subreddit_name in self.subreddits:
                subreddit_idx += 1
                # แสดง progress สำหรับ subreddits
                draw_progress_bar(subreddit_idx, len(self.subreddits), bar_length=50, prefix="กำลังโหลด post_reddit", show_total=True)
                try:
                    subreddit = await reddit.subreddit(subreddit_name)
                    
                    # ✅ ดึง posts ใหม่ (sort by new) - เพิ่ม limit
                    # ใช้ limit สูงเพื่อดึงได้มากขึ้น (Reddit API รองรับได้)
                    posts_count = 0
                    skipped_old = 0
                    async for submission in subreddit.new(limit=limit_per_subreddit):
                        try:
                            # ตรวจสอบวันที่
                            post_time = datetime.utcfromtimestamp(submission.created_utc)
                            if post_time < since:
                                skipped_old += 1
                                # ✅ ใช้ threshold แบบ dynamic:
                                # - ถ้าดึงย้อนหลังมาก (ระบบปิดไปนาน) → threshold สูง (100)
                                # - ถ้าดึงแค่ 2 ชั่วโมงล่าสุด → threshold ต่ำ (20)
                                time_range = datetime.utcnow() - since
                                threshold = 100 if time_range > timedelta(hours=4) else 20
                                if skipped_old >= threshold:
                                    break
                                continue
                            
                            # ✅ Reset skipped_old counter เมื่อเจอ post ใหม่
                            skipped_old = 0
                            
                            # ✅ ไม่ตรวจสอบ processed_post_ids ใน memory (จะตรวจสอบจาก database แทน)
                            # เพราะ processed_post_ids ใน memory อาจจะใหญ่เกินไป
                            # ตรวจสอบจาก database แทน (จะทำใน save_to_database)
                            
                            posts_count += 1
                            
                            # ✅ ดึง comments สำหรับ post นี้ (สำคัญมาก!)
                            # Comments ที่เป็น positive มากๆ สามารถขับเคลื่อนราคาได้ แม้จะเป็นข่าวร้าย
                            # ดึง comments มากสุด 100 ตัว (ลดลงเพื่อหลีกเลี่ยง rate limit)
                            # ✅ เพิ่ม delay 0.5 วินาทีระหว่างการดึง comments แต่ละ post เพื่อหลีกเลี่ยง rate limit
                            await asyncio.sleep(0.5)
                            comments = await self.fetch_comments_for_post(submission, max_comments=100)
                            
                            # ✅ บันทึก comments ลง database ทันที (ไม่ต้องรอจนถึง save_to_database)
                            comments_saved = False
                            if comments:
                                try:
                                    # บันทึก comments
                                    await self.save_comments_immediately(
                                        submission.id, 
                                        comments, 
                                        valid_tickers, 
                                        source='reddit',
                                        show_progress=False
                                    )
                                    comments_saved = True
                                    # ✅ อัปเดต progress bar สำหรับ comments
                                    total_comments_processed += len(comments)
                                    
                                    # ✅ แสดง progress bar สำหรับ comments (ถ้ามี comments มากกว่า 50)
                                    if total_comments_processed > 50 and not comments_progress_shown:
                                        comments_progress_shown = True
                                        reset_progress()  # Reset progress bar สำหรับ comments
                                        print()  # ขึ้นบรรทัดใหม่
                                    
                                    if comments_progress_shown:
                                        # ประมาณ total comments จาก posts ที่ดึงมาแล้ว + comments ที่เหลือ
                                        estimated_total = sum(p.get('comments_fetched', 0) for p in all_posts) + len(comments)
                                        if estimated_total > 0:
                                            draw_progress_bar(
                                                total_comments_processed, 
                                                estimated_total, 
                                                bar_length=50, 
                                                prefix="กำลังโหลด comment", 
                                                show_total=True
                                            )
                                except Exception:
                                    # ถ้าบันทึกไม่ได้ก็ไม่เป็นไร ยังเก็บไว้ใน post['comments'] เพื่อบันทึกทีหลัง
                                    pass
                            
                            post = {
                                "id": submission.id,
                                "title": submission.title,
                                "selftext": getattr(submission, 'selftext', '') or '',
                                "score": submission.score or 0,
                                "num_comments": submission.num_comments or 0,
                                "created_utc": post_time,
                                "subreddit": str(submission.subreddit),
                                "url": submission.url,
                                "author": str(submission.author) if submission.author else "[deleted]",
                                "upvote_ratio": getattr(submission, 'upvote_ratio', 0),
                                "is_self": submission.is_self,
                                "over_18": getattr(submission, 'over_18', False),
                                "fetched_at": datetime.utcnow(),
                                "comments": comments if not comments_saved else [],  # ✅ เก็บ comments เฉพาะถ้ายังไม่ได้บันทึก (ประหยัด memory)
                                "comments_fetched": len(comments),  # จำนวน comments ที่ดึงได้
                                "comments_saved": comments_saved  # ระบุว่า comments ถูกบันทึกไปแล้วหรือยัง
                            }
                            
                            all_posts.append(post)
                            # ✅ ไม่เก็บใน memory (จะตรวจสอบจาก database แทน)
                            # self.processed_post_ids.add(submission.id)
                            
                            # ✅ จำกัดจำนวน posts ต่อ subreddit แบบ dynamic:
                            # - ถ้าดึงย้อนหลังมาก (ระบบปิดไปนาน) → limit สูง (2000)
                            # - ถ้าดึงแค่ 2 ชั่วโมงล่าสุด → limit ต่ำ (500)
                            time_range = datetime.utcnow() - since
                            max_posts = 2000 if time_range > timedelta(hours=4) else 500
                            if posts_count >= max_posts:
                                break
                            
                        except Exception:
                            continue
                            
                except Exception:
                    continue
            
        finally:
            await reddit.close()
        
        # ✅ นับจำนวน comments ที่ดึงได้ทั้งหมด
        total_comments = sum(post.get('comments_fetched', 0) for post in all_posts)
        
        # ✅ แสดง progress bar เสร็จสิ้นสำหรับ posts
        draw_progress_bar(len(self.subreddits), len(self.subreddits), bar_length=50, prefix="กำลังโหลด post_reddit", show_total=True)
        
        # ✅ แสดง progress bar เสร็จสิ้นสำหรับ comments (ถ้ามี comments และแสดง progress bar แล้ว)
        if total_comments > 0 and comments_progress_shown:
            # แสดง progress bar เสร็จสิ้น
            draw_progress_bar(total_comments, total_comments, bar_length=50, prefix="กำลังโหลด comment", show_total=True)
        
        if len(all_posts) == 0:
            print(f"   💡 Tip: อาจจะไม่มี posts ใหม่ในช่วงเวลาที่กำหนด หรือ Reddit API rate limit")
        
        return all_posts
    
    async def fetch_comments_for_post(self, submission, max_comments: int = 100) -> List[Dict]:
        """
        ดึง comments จาก Reddit post (ไม่วิเคราะห์ sentiment ตอนดึง - จะวิเคราะห์ทีหลัง)
        
        Args:
            submission: Reddit submission object
            max_comments: จำนวน comments สูงสุดที่ดึง (default: 100)
            
        Returns:
            List of comments (ยังไม่วิเคราะห์ sentiment)
        """
        comments = []
        try:
            # ✅ ต้อง load submission ก่อนเข้าถึง comments
            await submission.load()
            
            # ✅ ดึง comments (asyncpraw ต้องใช้ await)
            comments_forest = await submission.comments()
            
            # ✅ Replace MoreComments instances (limit=None = ดึงทั้งหมด)
            await comments_forest.replace_more(limit=None)
            
            # ✅ Get flattened list of comments
            # ใน asyncpraw, .list() คืนค่าเป็น list object ธรรมดา ไม่ใช่ awaitable
            # ใช้ list() โดยไม่ await
            all_comments = comments_forest.list()
            
            comment_count = 0
            for comment in all_comments:
                if comment_count >= max_comments:
                    break
                
                # ข้าม deleted/removed comments
                if not hasattr(comment, 'body') or comment.body in ['[deleted]', '[removed]']:
                    continue
                
                # ✅ ดึงข้อมูล comment โดยไม่วิเคราะห์ sentiment (จะวิเคราะห์ทีหลัง)
                comment_text = comment.body or ''
                if not comment_text.strip():
                    continue
                
                # ✅ ไม่วิเคราะห์ sentiment ตอนนี้ - จะวิเคราะห์ตอนบันทึกลง database
                comment_data = {
                    "id": comment.id,
                    "body": comment_text,  # เก็บเนื้อหาไว้
                    "score": comment.score or 0,
                    "author": str(comment.author) if comment.author else "[deleted]",
                    "created_utc": datetime.utcfromtimestamp(comment.created_utc) if hasattr(comment, 'created_utc') else datetime.utcnow(),
                    "sentiment": None,  # จะวิเคราะห์ทีหลัง
                    "is_submitter": comment.is_submitter if hasattr(comment, 'is_submitter') else False,
                    "parent_id": str(comment.parent_id) if hasattr(comment, 'parent_id') else None
                }
                
                comments.append(comment_data)
                comment_count += 1
                
        except Exception as e:
            # ถ้าเกิด error ในการดึง comments → ข้าม (ไม่ให้กระทบการดึง posts)
            error_msg = str(e)
            # ✅ ตรวจสอบว่าเป็น rate limit error หรือไม่
            if "429" in error_msg or "rate limit" in error_msg.lower():
                print(f"   ⚠️  Rate limit hit for post {submission.id if hasattr(submission, 'id') else 'unknown'}: skipping comments")
            else:
                print(f"   ⚠️  Error fetching comments for post {submission.id if hasattr(submission, 'id') else 'unknown'}: {error_msg}")
        
        return comments
    
    async def save_comments_immediately(self, post_id: str, comments: List[Dict], valid_tickers: Optional[Set[str]] = None, source: str = 'reddit', show_progress: bool = False):
        """
        บันทึก comments ลง database ทันทีหลังจากดึงเสร็จ (ไม่ต้องรอจนถึง save_to_database)
        
        Args:
            post_id: Post ID
            comments: List of comments ที่ดึงมาจาก Reddit
            valid_tickers: Set of valid ticker symbols
            source: Source platform ('reddit', 'yahoo', 'x', 'youtube', etc.)
            show_progress: แสดง progress bar หรือไม่ (default: False เพื่อไม่ให้แสดงมากเกินไป)
        """
        if not comments:
            return
        
        if db is None:
            return
        
        from utils.post_normalizer import get_comment_collection_name
        from utils.progress_bar import draw_progress_bar
        comment_collection_name = get_comment_collection_name(source)
        
        # ✅ สร้าง comment collection ถ้ายังไม่มี
        if comment_collection_name not in db.list_collection_names():
            try:
                db.create_collection(comment_collection_name)
                db[comment_collection_name].create_index("id", unique=True)
                db[comment_collection_name].create_index("post_id")
                db[comment_collection_name].create_index("created_utc")
                db[comment_collection_name].create_index("author")
                db[comment_collection_name].create_index("symbols")
                db[comment_collection_name].create_index([("post_id", 1), ("created_utc", -1)])
            except Exception as e:
                return
        
        comment_collection = getattr(db, comment_collection_name)
        if comment_collection is None:
            return
        
        # ✅ ตรวจสอบ comment IDs ที่มีอยู่แล้ว
        try:
            recent_comments = list(comment_collection.find(
                {"post_id": post_id},
                {"id": 1},
                limit=1000
            ))
            existing_comment_ids = {c.get("id") for c in recent_comments if c.get("id")}
        except Exception:
            existing_comment_ids = set()
        
        # ✅ เตรียม normalized comments
        normalized_comments = []
        skipped_count = 0
        total_comments = len(comments)
        
        # แสดง progress bar ถ้า show_progress = True
        if show_progress and total_comments > 10:
            draw_progress_bar(0, total_comments, bar_length=50, prefix="กำลังโหลด comment", show_total=True)
        
        for idx, comment in enumerate(comments):
            # อัปเดต progress bar
            if show_progress and total_comments > 10:
                draw_progress_bar(idx, total_comments, bar_length=50, prefix="กำลังโหลด comment", show_total=True)
            
            comment_id = comment.get('id')
            if not comment_id:
                skipped_count += 1
                continue
            if comment_id in existing_comment_ids:
                skipped_count += 1
                continue
            
            # Extract symbols จาก comment body
            comment_body = comment.get('body', '') or ''
            
            # Extract symbols
            if valid_tickers and comment_body.strip():
                comment_symbols = self.extract_tickers(comment_body, valid_tickers)
            else:
                # ถ้าไม่มี valid_tickers หรือ body ว่าง → extract แบบง่าย
                if comment_body.strip():
                    dollar_pattern = re.compile(r'\$([A-Z]{1,5})\b')
                    comment_symbols = set(dollar_pattern.findall(comment_body.upper()))
                else:
                    comment_symbols = set()
            
            # ✅ วิเคราะห์ sentiment
            comment_sentiment = {}
            if comment_body.strip():
                try:
                    comment_sentiment = self.sentiment_analyzer.analyze(comment_body)
                except Exception:
                    comment_sentiment = {"compound": 0.0, "pos": 0.0, "neu": 1.0, "neg": 0.0}
            else:
                # ถ้า body ว่าง → neutral sentiment
                comment_sentiment = {"compound": 0.0, "pos": 0.0, "neu": 1.0, "neg": 0.0}
            
            normalized_comment = {
                "id": comment_id,
                "post_id": post_id,
                "body": comment_body,
                "score": comment.get('score', 0),
                "author": comment.get('author', '[deleted]'),
                "created_utc": comment.get('created_utc'),
                "sentiment": comment_sentiment,
                "is_submitter": comment.get('is_submitter', False),
                "parent_id": comment.get('parent_id'),
                "fetched_at": datetime.utcnow(),
                "symbols": list(comment_symbols) if comment_symbols else [],
                "platform": source
            }
            normalized_comments.append(normalized_comment)
            existing_comment_ids.add(comment_id)  # ป้องกัน duplicates
        
        # ✅ Bulk insert comments
        if normalized_comments:
            try:
                comment_collection.insert_many(normalized_comments, ordered=False)
            except Exception:
                # ถ้า insert_many ล้มเหลว → insert ทีละตัว
                saved_count = 0
                for comment in normalized_comments:
                    try:
                        comment_collection.update_one(
                            {"id": comment['id']},
                            {"$set": comment},
                            upsert=True
                        )
                        saved_count += 1
                    except Exception:
                        continue
    
    def calculate_combined_sentiment(self, post_sentiment: Dict, comments: List[Dict]) -> Dict:
        """
        คำนวณ sentiment รวมจาก post + comments (weighted by upvotes)
        
        Args:
            post_sentiment: Sentiment ของ post
            comments: List of comments with sentiment
            
        Returns:
            Combined sentiment dictionary
        """
        if not comments:
            return post_sentiment
        
        # คำนวณ weighted average โดยใช้ upvotes เป็น weight
        # Post มี weight = 1.0 (base weight)
        # Comments มี weight = log(score + 1) เพื่อลด impact ของ comments ที่มี upvotes สูงมาก
        
        import math
        
        # Post weight
        post_weight = 1.0
        post_compound = post_sentiment.get('compound', 0.0)
        
        # Comments weights และ sentiments
        total_weight = post_weight
        weighted_compound = post_compound * post_weight
        
        comment_sentiments = []
        for comment in comments:
            comment_sentiment = comment.get('sentiment', {})
            comment_compound = comment_sentiment.get('compound', 0.0)
            comment_score = comment.get('score', 0)
            
            # ✅ ตรวจสอบว่า comment_score + 1 > 0 เพื่อป้องกัน math domain error
            # ถ้า comment_score เป็นค่าลบมาก (เช่น -10) → comment_score + 1 อาจเป็น 0 หรือค่าลบ
            score_for_log = max(1, comment_score + 1)  # รับประกันว่า >= 1
            
            # Weight = log(score + 1) + 0.1 (เพื่อให้ comments ที่มี upvotes สูงมีน้ำหนักมากกว่า)
            # แต่ไม่ให้มากเกินไป (log scale)
            comment_weight = math.log(score_for_log) + 0.1
            
            weighted_compound += comment_compound * comment_weight
            total_weight += comment_weight
            
            comment_sentiments.append(comment_compound)
        
        # คำนวณ average
        if total_weight > 0:
            combined_compound = weighted_compound / total_weight
        else:
            combined_compound = post_compound
        
        # คำนวณ positive/negative/neutral จาก combined compound
        if combined_compound >= 0.05:
            label = "positive"
            positive = min(1.0, combined_compound)
            negative = 0.0
        elif combined_compound <= -0.05:
            label = "negative"
            positive = 0.0
            negative = min(1.0, abs(combined_compound))
        else:
            label = "neutral"
            positive = 0.0
            negative = 0.0
        
        neutral = 1.0 - positive - negative
        
        return {
            "compound": combined_compound,
            "positive": positive,
            "negative": negative,
            "neutral": neutral,
            "label": label,
            "post_sentiment": post_sentiment,  # เก็บ original post sentiment
            "comments_count": len(comments),
            "comments_avg_sentiment": sum(comment_sentiments) / len(comment_sentiments) if comment_sentiments else 0.0
        }
    
    def analyze_post_sentiment(self, post: Dict) -> Dict:
        """
        วิเคราะห์ sentiment ต่อ post (ครั้งเดียว)
        
        Args:
            post: Post dictionary
            
        Returns:
            Sentiment dictionary
        """
        text = f"{post.get('title', '')} {post.get('selftext', '')}".strip()
        if not text:
            return {
                "compound": 0.0,
                "positive": 0.0,
                "negative": 0.0,
                "neutral": 1.0,
                "label": "neutral"
            }
        
        # วิเคราะห์ sentiment (ครั้งเดียว)
        sentiment = self.sentiment_analyzer.analyze(text)
        
        return sentiment
    
    async def process_bulk_posts(self, posts: List[Dict], valid_tickers: Set[str]) -> Dict[str, List[Dict]]:
        """
        Process posts แบบ bulk:
        1. Extract tickers
        2. วิเคราะห์ sentiment (ครั้งเดียวต่อ post)
        3. Group by symbol
        
        Args:
            posts: List of posts
            valid_tickers: Set of valid ticker symbols
            
        Returns:
            Dictionary {symbol: [posts]}
        """
        symbol_posts = {}  # {symbol: [posts]}
        processed_posts = []  # สำหรับบันทึกลง database
        
        posts_without_tickers = 0
        for post in posts:
            # Extract tickers (รวม comments ด้วย - comments อาจมี tickers!)
            text = f"{post.get('title', '')} {post.get('selftext', '')}"
            # ✅ เพิ่ม comments text เพื่อ extract tickers จาก comments ด้วย
            comments = post.get('comments', [])
            if comments:
                comments_text = ' '.join([c.get('body', '') for c in comments])
                text += ' ' + comments_text
            symbols = self.extract_tickers(text, valid_tickers)
            
            # ✅ Debug: แสดงตัวอย่าง extraction (เฉพาะ 3 ตัวแรก)
            if posts_without_tickers < 3 and not symbols:
                sample_text = text[:150]
                print(f"   🔍 Debug post #{posts_without_tickers + 1} (ไม่มี ticker): {sample_text}...")
            
            if not symbols:
                posts_without_tickers += 1
                continue  # ข้าม post ที่ไม่มี ticker
            
            # วิเคราะห์ sentiment ของ post
            post_sentiment = self.analyze_post_sentiment(post)
            
            # ✅ ใช้ post sentiment ธรรมดา (ไม่รวม comments เพราะ comments ยังไม่วิเคราะห์ sentiment)
            # Comments จะถูกวิเคราะห์ sentiment ตอนบันทึกลง database
            # และสามารถคำนวณ combined sentiment ทีหลังได้
            post['sentiment'] = post_sentiment
            post['post_sentiment'] = post_sentiment  # เก็บ original post sentiment ไว้ด้วย
            
            # Group by symbol
            for symbol in symbols:
                if symbol not in symbol_posts:
                    symbol_posts[symbol] = []
                symbol_posts[symbol].append(post)
            
            # เก็บ post สำหรับบันทึกลง database
            processed_posts.append({
                **post,
                "symbols": list(symbols),
                "sentiment": post.get('sentiment')  # ใช้ combined sentiment (post + comments)
            })
        
        # ✅ Debug: แสดงจำนวน posts ที่ไม่มี ticker และสถิติ comments
        if posts_without_tickers > 0:
            print(f"   ⚠️  Posts ที่ไม่มี ticker: {posts_without_tickers}/{len(posts)}")
        
        # ✅ สถิติ comments
        total_comments_in_posts = sum(len(post.get('comments', [])) for post in processed_posts)
        posts_with_comments = sum(1 for post in processed_posts if post.get('comments'))
        if total_comments_in_posts > 0:
            print(f"   💬 Comments: {total_comments_in_posts} comments จาก {posts_with_comments} posts (รวม sentiment จาก comments แล้ว!)")
        
        return {
            "symbol_posts": symbol_posts,
            "processed_posts": processed_posts
        }
    
    async def save_to_database(self, processed_posts: List[Dict], valid_tickers: Optional[Set[str]] = None, source: str = 'reddit'):
        """
        บันทึก posts และ comments ลง database แบบ bulk
        Comments จะถูกเก็บแยกใน comment collection ตาม platform (comment_reddit, comment_yahoo, etc.)
        
        Args:
            processed_posts: List of processed posts
            valid_tickers: Set of valid ticker symbols (สำหรับ extract symbols จาก comments)
            source: Source platform ('reddit', 'yahoo', 'x', 'youtube', etc.)
        """
        if not processed_posts:
            return
        
        collection_name = get_collection_name(source)
        comment_collection_name = get_comment_collection_name(source)
        
        if db is None:
            return
        
        if not hasattr(db, collection_name):
            return
        
        post_collection = getattr(db, collection_name)
        comment_collection = None
        
        # ✅ สร้าง comment collection ถ้ายังไม่มี
        if comment_collection_name not in db.list_collection_names():
            try:
                db.create_collection(comment_collection_name)
                print(f"   ✅ Created {comment_collection_name} collection")
                # Create indexes
                db[comment_collection_name].create_index("id", unique=True)
                db[comment_collection_name].create_index("post_id")
                db[comment_collection_name].create_index("created_utc")
                db[comment_collection_name].create_index("author")
                db[comment_collection_name].create_index("symbols")
                db[comment_collection_name].create_index([("post_id", 1), ("created_utc", -1)])
                print(f"   ✅ Created indexes for {comment_collection_name} collection")
            except Exception as e:
                print(f"   ⚠️  Error creating comment collection: {e}")
                import traceback
                traceback.print_exc()
        
        # ✅ ใช้ list_collection_names() แทน hasattr() เพื่อตรวจสอบ collection
        if comment_collection_name in db.list_collection_names():
            comment_collection = getattr(db, comment_collection_name)
        else:
            print(f"   ⚠️  {comment_collection_name} collection not found, comments will not be saved")
            comment_collection = None
        
        # Normalize และ prepare posts
        normalized_posts = []
        normalized_comments = []
        
        # ✅ ใช้ distinct แบบมี limit เพื่อให้เร็วขึ้น (ตรวจสอบเฉพาะ 10000 posts ล่าสุด)
        try:
            recent_posts = list(post_collection.find(
                {},
                {"id": 1},
                sort=[("created_utc", -1)],
                limit=10000
            ))
            existing_post_ids = {p.get("id") for p in recent_posts if p.get("id")}
        except Exception:
            existing_post_ids = set(post_collection.distinct("id"))
        
        # ✅ ตรวจสอบ comment IDs ที่มีอยู่แล้ว (เพื่อหลีกเลี่ยง duplicates)
        existing_comment_ids = set()
        if comment_collection:
            try:
                recent_comments = list(comment_collection.find(
                    {},
                    {"id": 1},
                    sort=[("created_utc", -1)],
                    limit=50000  # ตรวจสอบ 50k comments ล่าสุด
                ))
                existing_comment_ids = {c.get("id") for c in recent_comments if c.get("id")}
            except Exception:
                pass
        
        for post in processed_posts:
            post_id = post['id']
            
            # ✅ ตรวจสอบว่า comments ถูกบันทึกไปแล้วหรือยัง
            comments_saved = post.get('comments_saved', False)
            comments = post.get('comments', [])
            comments_count = post.get('comments_fetched', len(comments))
            
            # ✅ ถ้า comments ถูกบันทึกไปแล้ว → ข้าม (ประหยัดเวลาและ resources)
            if not comments_saved and comments:
                # ✅ Extract symbols และวิเคราะห์ sentiment จาก comments (กรณีที่ยังไม่ได้บันทึก)
                # ✅ Debug: ตรวจสอบว่า comments มีข้อมูลหรือไม่
                if len(normalized_comments) < 3:
                    print(f"   🔍 Debug: Post {post_id} มี {comments_count} comments (ยังไม่ได้บันทึก)")
                
                # ✅ บันทึก comments เฉพาะกรณีที่ยังไม่ได้บันทึก
                for comment in comments:
                    comment_id = comment.get('id')
                    if not comment_id or comment_id in existing_comment_ids:
                        continue
                    
                    # Extract symbols จาก comment body
                    comment_body = comment.get('body', '')
                    if valid_tickers:
                        comment_symbols = self.extract_tickers(comment_body, valid_tickers)
                    else:
                        # ถ้าไม่มี valid_tickers → extract แบบง่าย (หา $SYMBOL pattern)
                        dollar_pattern = re.compile(r'\$([A-Z]{1,5})\b')
                        comment_symbols = set(dollar_pattern.findall(comment_body.upper()))
                    
                    # ✅ วิเคราะห์ sentiment ตอนบันทึกลง database (ไม่ใช่ตอนดึง)
                    comment_sentiment = {}
                    if comment_body.strip():
                        comment_sentiment = self.sentiment_analyzer.analyze(comment_body)
                    
                    normalized_comment = {
                        "id": comment_id,
                        "post_id": post_id,
                        "body": comment_body,  # เก็บเนื้อหาไว้
                        "score": comment.get('score', 0),
                        "author": comment.get('author', '[deleted]'),
                        "created_utc": comment.get('created_utc'),
                        "sentiment": comment_sentiment,  # วิเคราะห์ตอนบันทึก
                        "is_submitter": comment.get('is_submitter', False),
                        "parent_id": comment.get('parent_id'),
                        "fetched_at": datetime.utcnow(),
                        "symbols": list(comment_symbols) if comment_symbols else [],
                        "platform": source  # เพิ่ม platform เพื่อระบุ source
                    }
                    normalized_comments.append(normalized_comment)
                    existing_comment_ids.add(comment_id)  # ป้องกัน duplicates ในรอบเดียวกัน
                
                # ✅ Debug: แสดงจำนวน comments ที่เตรียมไว้แล้ว
                if len(normalized_comments) > 0 and len(normalized_comments) % 100 == 0:
                    print(f"   🔍 Debug: เตรียม {len(normalized_comments)} comments แล้ว...")
            
            # ✅ ตรวจสอบว่ามี post อยู่แล้วหรือยัง
            if post_id in existing_post_ids:
                continue
            
            # Normalize post (ไม่เก็บ comments array)
            first_symbol = post.get('symbols', [])[0] if post.get('symbols') else ''
            normalized = normalize_post(post, 'reddit', first_symbol)
            
            # ✅ เอา comments array ออก และเก็บแค่ comments_count
            if 'comments' in normalized:
                del normalized['comments']
            normalized['comments_count'] = comments_count  # เก็บแค่จำนวน
            normalized['comments_fetched'] = comments_count  # สำหรับ backward compatibility
            
            # เพิ่ม symbols array
            normalized['symbols'] = post.get('symbols', [])
            if first_symbol:
                normalized['keyword'] = first_symbol
            
            # เพิ่ม sentiment
            normalized['sentiment'] = post.get('sentiment', {})
            normalized_posts.append(normalized)
        
        # ✅ Bulk insert posts
        if normalized_posts:
            try:
                post_collection.insert_many(normalized_posts, ordered=False)
            except Exception:
                # ถ้า insert_many ล้มเหลว → insert ทีละตัว
                saved_posts = 0
                for post in normalized_posts:
                    try:
                        post_collection.update_one(
                            {"id": post['id']},
                            {"$set": post},
                            upsert=True
                        )
                        saved_posts += 1
                    except Exception:
                        continue
        
        # ✅ Bulk insert comments
        # ✅ ตรวจสอบว่า collection ถูกสร้างหรือไม่
        if comment_collection_name not in db.list_collection_names():
            try:
                db.create_collection(comment_collection_name)
                db[comment_collection_name].create_index("id", unique=True)
                db[comment_collection_name].create_index("post_id")
                db[comment_collection_name].create_index("created_utc")
                db[comment_collection_name].create_index("author")
                db[comment_collection_name].create_index("symbols")
                db[comment_collection_name].create_index([("post_id", 1), ("created_utc", -1)])
                comment_collection = getattr(db, comment_collection_name)
            except Exception:
                comment_collection = None
        
        if normalized_comments and comment_collection:
            try:
                comment_collection.insert_many(normalized_comments, ordered=False)
            except Exception:
                # ถ้า insert_many ล้มเหลว → insert ทีละตัว
                saved_comments = 0
                for comment in normalized_comments:
                    try:
                        comment_collection.update_one(
                            {"id": comment['id']},
                            {"$set": comment},
                            upsert=True
                        )
                        saved_comments += 1
                    except Exception:
                        continue
    
    async def run_bulk_fetch(self, valid_tickers: Optional[Set[str]] = None) -> Dict:
        """
        รัน bulk fetch process
        
        Args:
            valid_tickers: Set of valid ticker symbols (ถ้า None จะดึงจาก database)
            
        Returns:
            Dictionary with results
        """
        # ดึง valid tickers
        if valid_tickers is None:
            from utils.stock_list_fetcher import stock_list_fetcher
            all_tickers = stock_list_fetcher.get_all_valid_tickers(force_refresh=False)
            valid_tickers = {t.upper() for t in all_tickers}
        
        # ดึง last_fetched_at จาก database
        collection_name = get_collection_name('reddit')
        if db is not None and hasattr(db, collection_name):
            post_collection = getattr(db, collection_name)
            latest_post = post_collection.find_one(sort=[("created_utc", -1)])
            if latest_post:
                latest_date = latest_post.get('created_utc')
                if isinstance(latest_date, str):
                    self.last_fetched_at = datetime.fromisoformat(latest_date.replace('Z', '+00:00'))
                elif isinstance(latest_date, datetime):
                    self.last_fetched_at = latest_date
                else:
                    # ✅ ถ้า latest_date ไม่ใช่ string หรือ datetime ให้ดึงย้อนหลัง 2 ชั่วโมง
                    self.last_fetched_at = datetime.utcnow() - timedelta(hours=2)
            else:
                # ✅ ถ้ายังไม่มี posts ใน database ให้ดึงย้อนหลัง 2 ชั่วโมง (ไม่ใช่ 7 วัน)
                # เพราะดึงทุก 30 วินาทีแล้ว ไม่ต้องดึงย้อนหลังมาก
                self.last_fetched_at = datetime.utcnow() - timedelta(hours=2)
        else:
            # ✅ ถ้ายังไม่มี database ให้ดึงย้อนหลัง 2 ชั่วโมง (ไม่ใช่ 7 วัน)
            self.last_fetched_at = datetime.utcnow() - timedelta(hours=2)
        
        # ✅ ดึง posts ใหม่ - ตรวจสอบว่า last_fetched_at เก่าแค่ไหน
        # ถ้าเก่าเกิน 2 ชั่วโมง (ระบบปิดไป) → ดึงย้อนหลังให้ครอบคลุมช่วงที่ปิดไป
        # ถ้าไม่เก่า (ดึงทุก 30 วินาที) → ดึงแค่ posts ที่ใหม่กว่า last_fetched_at
        now = datetime.utcnow()
        if self.last_fetched_at:
            # ตรวจสอบว่า last_fetched_at เก่าแค่ไหน
            time_since_last_fetch = now - self.last_fetched_at
            
            if time_since_last_fetch > timedelta(hours=2):
                # ✅ ระบบปิดไปนานกว่า 2 ชั่วโมง → ดึงย้อนหลังให้ครอบคลุมช่วงที่ปิดไป
                # ดึงจาก last_fetched_at (เพิ่ม buffer 5 นาทีเพื่อไม่พลาด)
                since_time = self.last_fetched_at - timedelta(minutes=5)
                print(f"   ⚠️  ระบบปิดไป {int(time_since_last_fetch.total_seconds() / 3600)} ชั่วโมง → ดึงย้อนหลังจาก {since_time.strftime('%Y-%m-%d %H:%M:%S')}")
            else:
                # ✅ ระบบทำงานปกติ (ดึงทุก 30 วินาที) → ดึงแค่ posts ที่ใหม่กว่า last_fetched_at
                since_time = self.last_fetched_at - timedelta(minutes=5)
        else:
            # ✅ ครั้งแรก (ยังไม่มี last_fetched_at) → ดึงย้อนหลัง 2 ชั่วโมง
            since_time = now - timedelta(hours=2)
        posts = await self.fetch_new_posts_bulk(since=since_time, valid_tickers=valid_tickers)
        
        if not posts:
            return {
                "posts_fetched": 0,
                "posts_processed": 0,
                "symbols_found": 0,
                "posts_saved": 0
            }
        
        # ✅ Debug: แสดงข้อมูล valid_tickers
        print(f"   🔍 Valid tickers count: {len(valid_tickers)}")
        if len(valid_tickers) == 0:
            print(f"   ⚠️  WARNING: No valid tickers found! Posts will not be saved.")
        
        # Process posts
        result = await self.process_bulk_posts(posts, valid_tickers)
        symbol_posts = result["symbol_posts"]
        processed_posts = result["processed_posts"]
        
        # ✅ Debug: แสดงตัวอย่าง posts ที่ไม่มี ticker (แสดงทุกครั้งที่มี posts แต่ไม่มี ticker)
        if len(posts) > 0:
            if len(processed_posts) == 0:
                print(f"   ⚠️  Posts ที่ดึงได้แต่ไม่มี ticker: {len(posts)} posts")
                # แสดงตัวอย่าง posts หลายตัว (ไม่ใช่แค่ตัวแรก)
                for i, sample_post in enumerate(posts[:5]):  # แสดง 5 ตัวแรก
                    sample_text = f"{sample_post.get('title', '')} {sample_post.get('selftext', '')}"[:300]
                    print(f"   📝 ตัวอย่าง post #{i+1}: {sample_text}...")
                    # ลอง extract tickers แบบ debug
                    debug_symbols = self.extract_tickers(sample_text, valid_tickers)
                    print(f"   🔍 Tickers ที่ extract ได้: {debug_symbols}")
                if len(valid_tickers) > 0:
                    # แสดงตัวอย่าง valid tickers
                    sample_tickers = list(valid_tickers)[:20]  # เพิ่มเป็น 20 ตัว
                    print(f"   📋 ตัวอย่าง valid tickers (20 ตัวแรก): {sample_tickers}")
            else:
                # ✅ แสดงตัวอย่าง posts ที่มี ticker (เพื่อยืนยันว่าทำงาน)
                print(f"   ✅ Posts ที่มี ticker: {len(processed_posts)}/{len(posts)}")
                if len(processed_posts) > 0:
                    sample_processed = processed_posts[0]
                    sample_symbols = sample_processed.get('symbols', [])
                    sample_title = sample_processed.get('title', '')[:100]
                    print(f"   📝 ตัวอย่าง post ที่มี ticker: {sample_title}... → Symbols: {sample_symbols}")
        
        # ✅ Debug: ตรวจสอบ comments ก่อนบันทึก
        total_comments_in_processed = sum(len(post.get('comments', [])) for post in processed_posts)
        print(f"   🔍 Debug: processed_posts = {len(processed_posts)}, total comments in posts = {total_comments_in_processed}")
        
        # บันทึกลง database (ใช้ source='reddit' สำหรับ Reddit bulk processor)
        await self.save_to_database(processed_posts, valid_tickers, source='reddit')
        
        # ✅ นับจำนวน comments ที่บันทึกได้
        from utils.post_normalizer import get_comment_collection_name
        comment_collection_name = get_comment_collection_name('reddit')
        total_comments_saved = 0
        if db is not None and comment_collection_name in db.list_collection_names():
            comment_collection = getattr(db, comment_collection_name)
            if comment_collection:
                # นับ comments ที่บันทึกในรอบนี้ (ประมาณจาก posts ที่บันทึก)
                try:
                    # นับ comments จาก posts ที่เพิ่งบันทึก (ใช้ post_id จาก processed_posts)
                    post_ids = [p.get('id') for p in processed_posts if p.get('id')]
                    if post_ids:
                        total_comments_saved = comment_collection.count_documents({"post_id": {"$in": post_ids}})
                except Exception:
                    pass
        
        # ✅ แสดงสรุปข้อมูลที่ดึงมา
        print(f"\n📊 สรุปข้อมูลที่ดึงมา:")
        print(f"   📝 Reddit Posts: {len(processed_posts):,} posts")
        print(f"   💬 Comments: {total_comments_saved:,} comments")
        print(f"   🏷️  Symbols: {len(symbol_posts):,} symbols")
        
        return {
            "posts_fetched": len(posts),
            "posts_processed": len(processed_posts),
            "symbols_found": len(symbol_posts),
            "posts_saved": len(processed_posts),
            "comments_saved": total_comments_saved,
            "symbol_posts": symbol_posts
        }
