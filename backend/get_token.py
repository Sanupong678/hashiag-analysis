import praw

reddit = praw.Reddit(
    client_id="HLncp-eMiPh74P02LC7K8w",
    client_secret="pjByukUePZb8eN8v5CZEK40Al0RBoQ",
    redirect_uri="http://localhost:8080",
    user_agent="reddit data collector by u/Interesting-Oven-917"
)

# 1. สร้าง URL สำหรับอนุมัติสิทธิ์
url = reddit.auth.url(scopes=["identity", "read"], state="teststate", duration="permanent")
print("🔗 เปิดลิงก์นี้ในเบราว์เซอร์เพื่ออนุญาตสิทธิ์:\n", url)
