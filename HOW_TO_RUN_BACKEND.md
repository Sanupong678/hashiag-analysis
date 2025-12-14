# 🚀 คู่มือการรัน Backend Server

## ✅ **แก้ไข Errors แล้ว!**

แก้ไข duplicate routes แล้ว:
- ✅ `/api/alerts` - แก้แล้ว
- ✅ `/api/influencers` - แก้แล้ว

ตอนนี้สามารถรัน backend ได้แล้ว!

---

## 📋 **ขั้นตอนการรัน Backend**

### **วิธีที่ 1: รันด้วย Python โดยตรง (แนะนำ)**

```powershell
# 1. เปิด Terminal/PowerShell
cd C:\Users\Tumsa\Desktop\project_database\reddit-hashtag-analytics

# 2. Activate virtual environment
venv\Scripts\activate

# 3. ตรวจสอบ dependencies (ถ้ายังไม่ได้ติดตั้ง)
pip install -r requirements.txt

# 4. รัน Flask server
cd backend
python app.py
```

---

### **วิธีที่ 2: รันจากโฟลเดอร์ backend**

```powershell
# 1. เปิด Terminal/PowerShell
cd C:\Users\Tumsa\Desktop\project_database\reddit-hashtag-analytics

# 2. Activate virtual environment
venv\Scripts\activate

# 3. รัน Flask server
python backend\app.py
```

---

## ✅ **เมื่อรันสำเร็จจะเห็น:**

```
✅ MongoDB connected successfully!
🔍 Loading Reddit credentials:
CLIENT_ID: 85slaGXJqZDbr9klutX7Rw
CLIENT_SECRET: Bn01CIUXEYp_o8ecJ0PrIvIwbSRvRw
USER_AGENT: Tumsanupong
✅ News API key loaded: f47fa9d4ef...
✅ YouTube API key loaded: AIzaSyBpPL...
⚠️ RapidAPI credentials not found in environment variables
   RapidAPI features will be disabled
✅ Database collections initialized
🚀 Flask API running on http://127.0.0.1:5000
 * Running on http://127.0.0.1:5000
 * Debug mode: on
```

---

## 🧪 **ทดสอบ API**

เปิด browser หรือใช้ PowerShell:

```powershell
# ทดสอบ Dashboard API
Invoke-WebRequest -Uri "http://localhost:5000/api/dashboard" | Select-Object -ExpandProperty Content

# หรือเปิดใน browser:
# http://localhost:5000/api/dashboard
```

---

## ⚠️ **ถ้าเจอ Error**

### **1. ModuleNotFoundError (เช่น vaderSentiment)**

```powershell
# ติดตั้ง dependencies
pip install -r requirements.txt
```

### **2. MongoDB connection failed**

- ตรวจสอบ `MONGO_URI` ใน `.env` file
- ตรวจสอบว่า MongoDB ทำงานอยู่

### **3. Port 5000 already in use**

แก้ไขใน `backend/app.py`:
```python
app.run(debug=True, port=5001)  # เปลี่ยนเป็น port อื่น
```

---

## 📝 **สรุปคำสั่งทั้งหมด:**

```powershell
# 1. ไปที่โฟลเดอร์โปรเจค
cd C:\Users\Tumsa\Desktop\project_database\reddit-hashtag-analytics

# 2. Activate virtual environment
venv\Scripts\activate

# 3. ติดตั้ง dependencies (ถ้ายังไม่ได้ติดตั้ง)
pip install -r requirements.txt

# 4. รัน Flask server
cd backend
python app.py
```

**Backend จะรันที่ `http://localhost:5000`** 🎉

---

## 🔗 **API Endpoints ที่พร้อมใช้:**

- `GET /api/dashboard` - Dashboard summary
- `GET /api/stock/<symbol>` - Stock data
- `GET /api/stock/<symbol>/price` - Current price
- `GET /api/stock/compare` - Compare stocks
- `GET /api/alerts` - Get alert rules
- `POST /api/alerts` - Create alert rule
- `GET /api/watchlist` - Get watchlist
- `GET /api/influencers` - Get influencers
- และอื่นๆ...

ดูรายละเอียดเพิ่มเติมใน `backend/app.py`

