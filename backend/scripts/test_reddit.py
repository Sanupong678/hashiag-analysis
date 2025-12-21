import os
import praw
from dotenv import load_dotenv

# โหลด .env
# __file__ = backend/scripts/test_reddit.py
# ต้องการ path = reddit-hashtag-analytics/.env (ขึ้นไป 2 ระดับ)
env_path = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
load_dotenv(env_path)

# อ่านค่า credentials
client_id = os.getenv("REDDIT_CLIENT_ID")
client_secret = os.getenv("REDDIT_CLIENT_SECRET")
user_agent = os.getenv("USER_AGENT")

# ✅ เพิ่ม refresh token (เดี๋ยวเราจะได้จากขั้นตอน login)
refresh_token = os.getenv("REDDIT_REFRESH_TOKEN")

# สร้าง Reddit instance
reddit = praw.Reddit(
    client_id=client_id,
    client_secret=client_secret,
    refresh_token=refresh_token,
    user_agent=user_agent
)

print("✅ Authentication success! Logged in as:", reddit.user.me())

# ดึงโพสต์
subreddit = reddit.subreddit("technology")
print("\n🔍 แสดงโพสต์ล่าสุดจาก r/technology:\n")
for post in subreddit.hot(limit=5):
    print(f"📢 {post.title} ({post.score} upvotes)\n{post.url}\n")
