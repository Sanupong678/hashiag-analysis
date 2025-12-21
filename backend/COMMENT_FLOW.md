# 📊 กระบวนการดึงและใช้งาน Comments หลังจากวิเคราะห์ Sentiment

## 🔄 Flow หลังจากดึง Comments และวิเคราะห์ Sentiment

### 1. 📥 **การดึง Comments** (`fetch_comments_for_post`)
- ดึง comments จาก Reddit post (สูงสุด 100 comments/post)
- เก็บข้อมูล: `id`, `body`, `score`, `author`, `created_utc`
- **ยังไม่วิเคราะห์ sentiment** (`sentiment: None`)

### 2. 🧠 **การวิเคราะห์ Sentiment** (`save_to_database`)
- วิเคราะห์ sentiment **ตอนบันทึกลง database** (ไม่ใช่ตอนดึง)
- Extract ticker symbols จาก comment body
- สร้าง `normalized_comment` document:

```python
normalized_comment = {
    "id": "abc123",
    "post_id": "post_xyz",
    "body": "This stock is going to the moon! 🚀",
    "score": 100,
    "author": "trader123",
    "created_utc": datetime(...),
    "sentiment": {
        "compound": 0.75,  # ← วิเคราะห์แล้ว
        "pos": 0.65,
        "neu": 0.35,
        "neg": 0.0
    },
    "symbols": ["AAPL", "TSLA"],  # ← extract แล้ว
    "platform": "reddit",
    "fetched_at": datetime.utcnow()
}
```

### 3. 💾 **บันทึกลง Database**

**Comments → `comment_reddit` collection** (แยกจาก `post_reddit`)
- Bulk insert: `comment_collection.insert_many(normalized_comments)`
- มี indexes สำหรับ query: `post_id`, `symbols`, `created_utc`, `author`

**Post → `post_reddit` collection**
- เก็บแค่ `comments_count` (ไม่เก็บ comments array)

---

## 📍 **สถานะปัจจุบัน: ข้อมูล Comments อยู่ที่ไหน?**

### ✅ **ถูกบันทึกใน Database แล้ว**
- Collection: `comment_reddit`
- มีข้อมูล: `body`, `sentiment`, `symbols`, `author`, `score`
- มี indexes สำหรับ query

### ⚠️ **ยังไม่มีการใช้งานต่อ**
- **ยังไม่มี API endpoint** ที่ดึง comments จาก database
- Frontend แสดงแค่ `num_comments` (จำนวน) ไม่ได้แสดงเนื้อหาหรือ sentiment

---

## 🎯 **การใช้งาน Comments ที่ควรมี**

### 1. **แสดง Comments ในหน้า Stock Detail**
```
/api/stock/<symbol>/comments
- ดึง comments ที่มี ticker = symbol
- แสดง sentiment, author, score
```

### 2. **แสดง Comments ของ Post**
```
/api/post/<post_id>/comments
- ดึง comments ของ post หนึ่งๆ
- เรียงตาม score หรือ created_utc
```

### 3. **Aggregate Sentiment จาก Comments**
```
/api/stock/<symbol>/sentiment/comments
- คำนวณ average sentiment จาก comments
- รวมกับ post sentiment เพื่อให้ข้อมูลครบถ้วน
```

### 4. **Comment Analytics**
```
/api/stock/<symbol>/comment-analytics
- Top comments (by score)
- Sentiment distribution
- Most active commenters
```

---

## 📊 **ข้อมูลที่พร้อมใช้งาน**

จาก `comment_reddit` collection สามารถ query:

1. **Comments ตาม Ticker**
   ```python
   db.comment_reddit.find({"symbols": "AAPL"})
   ```

2. **Comments ของ Post**
   ```python
   db.comment_reddit.find({"post_id": "post_id"})
   ```

3. **Comments โดย Author**
   ```python
   db.comment_reddit.find({"author": "username"})
   ```

4. **Aggregate Sentiment**
   ```python
   db.comment_reddit.aggregate([
       {"$match": {"symbols": "AAPL"}},
       {"$group": {
           "_id": None,
           "avg_sentiment": {"$avg": "$sentiment.compound"}
       }}
   ])
   ```

---

## 🚀 **ขั้นตอนถัดไป (แนะนำ)**

1. **สร้าง API Endpoints** สำหรับดึง comments
2. **Aggregate Sentiment** จาก comments เพื่อแสดงใน dashboard
3. **แสดง Comments** ใน frontend (stock detail page)
4. **Comment Analytics** - แสดงสถิติ comments (top comments, sentiment distribution)
