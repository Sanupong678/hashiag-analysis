# สถานะการเชื่อม Reddit API

## ✅ **มีการเชื่อม Reddit API แล้ว!**

### 📍 **ไฟล์ที่เกี่ยวข้อง:**

1. **`backend/fetch_reddit.py`** - ไฟล์หลักที่เชื่อม Reddit API
   - ใช้ PRAW library
   - โหลด credentials จาก `.env` file
   - Function `fetch_posts()` สำหรับดึงข้อมูล

2. **`backend/reddit_config.py`** - Config file (optional)
3. **`backend/data_aggregator.py`** - ใช้ `fetch_posts()` ใน line 61

---

## 🔍 **ตรวจสอบสถานะปัจจุบัน:**

### ✅ **สิ่งที่ทำแล้ว:**
- ✅ Import PRAW library
- ✅ สร้าง Reddit instance
- ✅ โหลด credentials จาก `.env`
- ✅ Function `fetch_posts()` พร้อมใช้งาน
- ✅ Error handling พื้นฐาน
- ✅ บันทึกข้อมูลลง MongoDB

### ⚠️ **สิ่งที่ต้องตรวจสอบ/ปรับปรุง:**

1. **ยังไม่มี `.env` file** (ต้องสร้าง)
2. **Rate limiting** - ยังไม่มีการจัดการ
3. **Comments** - ยังไม่ดึง comments
4. **Error handling** - ควรปรับปรุงให้ดีขึ้น
5. **Retry logic** - ยังไม่มี

---

## 📝 **ขั้นตอนการตั้งค่า Reddit API:**

### Step 1: สร้าง Reddit App
1. ไปที่ https://www.reddit.com/prefs/apps
2. คลิก "create another app..." หรือ "create app"
3. ตั้งชื่อ app (เช่น "Stock Sentiment Dashboard")
4. เลือก "script" type
5. ใส่ redirect URI: `http://localhost:8080`
6. คลิก "create app"
7. **บันทึก:**
   - **Client ID** (ใต้ชื่อ app)
   - **Secret** (ในช่อง "secret")

### Step 2: สร้าง `.env` file
สร้างไฟล์ `.env` ในโฟลเดอร์ `reddit-hashtag-analytics/`:

```env
# Reddit API Configuration
REDDIT_CLIENT_ID=your_client_id_here
REDDIT_CLIENT_SECRET=your_client_secret_here
USER_AGENT=StockSentimentDashboard/1.0 by YourUsername
```

### Step 3: Test การเชื่อม
รันคำสั่ง:
```bash
cd backend
python test_reddit.py
```

---

## 🔧 **การปรับปรุงที่แนะนำ:**

### 1. เพิ่ม Rate Limiting Handling
### 2. เพิ่มการดึง Comments
### 3. ปรับปรุง Error Handling
### 4. เพิ่ม Retry Logic

