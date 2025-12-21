import os
import praw
from dotenv import load_dotenv

# __file__ = backend/config/reddit_config.py
# ต้องการ path = reddit-hashtag-analytics/.env (ขึ้นไป 2 ระดับ)
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
    user_agent=os.getenv("USER_AGENT")
)
