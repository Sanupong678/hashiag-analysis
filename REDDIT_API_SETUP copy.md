# คู่มือการตั้งค่า Reddit API

## ✅ **สถานะ: มีการเชื่อม Reddit API แล้ว!**

### 📍 **ไฟล์ที่เกี่ยวข้อง:**
- **`backend/fetch_reddit.py`** - ไฟล์หลักที่เชื่อม Reddit API

---

## 🔧 **สิ่งที่ต้องทำ:**

### 1. สร้าง `.env` file (ถ้ายังไม่มี)

สร้างไฟล์ `.env` ในโฟลเดอร์ `reddit-hashtag-analytics/`:

```env
# Reddit API Configuration
REDDIT_CLIENT_ID=your_client_id_here
REDDIT_CLIENT_SECRET=your_client_secret_here
USER_AGENT=StockSentimentDashboard/1.0 by YourUsername
```

### 2. วิธีได้ Reddit API Credentials:

1. ไปที่ https://www.reddit.com/prefs/apps
2. Login ด้วย Reddit account
3. Scroll ลงไปคลิก **"create another app..."** หรือ **"create app"**
4. กรอกข้อมูล:
   - **Name**: Stock Sentiment Dashboard (หรือชื่อที่ต้องการ)
   - **Type**: เลือก **"script"**
   - **Description**: (optional)
   - **About URL**: (optional)
   - **Redirect URI**: `http://localhost:8080`
5. คลิก **"create app"**
6. **บันทึกข้อมูล:**
   - **Client ID**: ตัวเลข/ตัวอักษรใต้ชื่อ app (เช่น `HLncp-eMiPh74P02LC7K8w`)
   - **Secret**: คลิก "edit" แล้วจะเห็น "secret" (เช่น `pjByukUePZb8eN8v5CZEK40Al0RBoQ`)

### 3. ใส่ Credentials ใน `.env`:

```env
REDDIT_CLIENT_ID=HLncp-eMiPh74P02LC7K8w
REDDIT_CLIENT_SECRET=pjByukUePZb8eN8v5CZEK40Al0RBoQ
USER_AGENT=StockSentimentDashboard/1.0 by YourUsername
```

**หมายเหตุ:** 
- แทน `YourUsername` ด้วย Reddit username ของคุณ
- USER_AGENT ควรมีรูปแบบ: `AppName/Version by Username`

### 4. Test การเชื่อม:

```bash
cd backend
python test_reddit.py
```

หรือทดสอบผ่าน API:
```bash
# Start Flask server
python app.py

# ใน browser หรือ Postman
GET http://localhost:5000/api/hashtags?keyword=AAPL
```

---

## 📝 **การใช้งาน:**

### ใน Code:

```python
from fetch_reddit import fetch_posts

# ดึง posts สำหรับ keyword
posts = fetch_posts("AAPL", limit=50)

# ดึง comments สำหรับ post
from fetch_reddit import fetch_comments
comments = fetch_comments("post_id_here", limit=20)
```

### ใน API Endpoint:

Reddit API ถูกเรียกใช้ใน:
- `GET /api/hashtags?keyword=AAPL` - เรียก `fetch_posts()`
- `GET /api/stock/<symbol>` - เรียกผ่าน `data_aggregator.py`

---

## ⚠️ **Rate Limiting:**

Reddit API มี rate limit:
- **60 requests per minute** สำหรับ read-only access
- ถ้าเกินจะได้ error 429

**คำแนะนำ:**
- ใช้ delay ระหว่าง requests
- Cache ข้อมูลที่ดึงมาแล้ว
- ใช้ try-except เพื่อ handle rate limit errors

---

## 🔍 **ตรวจสอบว่าเชื่อมสำเร็จหรือไม่:**

### วิธีที่ 1: ดู Console Logs
เมื่อรัน Flask server จะเห็น:
```
🔍 Loading Reddit credentials:
CLIENT_ID: your_client_id
CLIENT_SECRET: your_client_secret
USER_AGENT: your_user_agent
```

### วิธีที่ 2: Test API
```bash
curl http://localhost:5000/api/hashtags?keyword=AAPL
```

### วิธีที่ 3: ดู Database
ตรวจสอบว่า posts ถูกบันทึกลง MongoDB หรือไม่

---

## ❌ **ปัญหาที่อาจเจอ:**

### 1. "Invalid credentials"
- ตรวจสอบ CLIENT_ID และ CLIENT_SECRET ใน `.env`
- ตรวจสอบว่า USER_AGENT ถูกต้อง

### 2. "Rate limit exceeded"
- รอ 1 นาทีแล้วลองใหม่
- ลดจำนวน requests

### 3. "No posts found"
- ลอง keyword อื่น
- ตรวจสอบว่า Reddit มี posts เกี่ยวกับ keyword นั้น

---

## ✅ **สรุป:**

**Reddit API ถูกเชื่อมแล้ว!** 

**สิ่งที่ต้องทำ:**
1. ✅ สร้าง `.env` file (ถ้ายังไม่มี)
2. ✅ ใส่ Reddit API credentials
3. ✅ Test การเชื่อม

**ไฟล์ที่ต้องแก้ไข:**
- ไม่ต้องแก้ไข (เชื่อมแล้ว)
- แค่ต้องมี `.env` file พร้อม credentials

