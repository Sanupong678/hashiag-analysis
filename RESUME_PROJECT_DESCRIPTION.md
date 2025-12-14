# รายละเอียดโปรเจกต์สำหรับ Resume

## ชื่อโปรเจกต์ (Project Name)

**Multi-Source Stock Sentiment Analysis Dashboard**
หรือ
**Real-Time Stock Market Sentiment Analytics Platform**

---

## รายละเอียดเชิงวิชาการ (Academic Description)

**Multi-Source Stock Sentiment Analysis Dashboard** - พัฒนาระบบวิเคราะห์ความรู้สึก (Sentiment Analysis) สำหรับตลาดหุ้นโดยการรวบรวมข้อมูลจากหลายแหล่ง ได้แก่ Reddit, News API, Google Trends, และข้อมูลราคาหุ้นแบบเรียลไทม์ โดยใช้ VADER Sentiment Analyzer ที่ปรับปรุงให้เหมาะสมกับคำศัพท์ทางการเงิน และคำนวณคะแนนความรู้สึกแบบถ่วงน้ำหนักจากหลายแหล่งข้อมูล เพื่อให้ได้ผลลัพธ์ที่แม่นยำมากขึ้น ระบบใช้สถาปัตยกรรม RESTful API ด้วย Flask framework บน Python และจัดเก็บข้อมูลใน MongoDB พร้อมพัฒนาเว็บแดชบอร์ดด้วย JavaScript สำหรับแสดงผลข้อมูลแบบเรียลไทม์ กราฟเปรียบเทียบราคาหุ้นกับความรู้สึก และระบบแจ้งเตือนเมื่อมีการเปลี่ยนแปลงความรู้สึกอย่างมีนัยสำคัญ

---

## รายละเอียดแบบภาษาไทย (Bullet Points)

**Multi-Source Stock Sentiment Analysis Dashboard**

- พัฒนาระบบวิเคราะห์เชิงคาดการณ์ที่รวบรวมข้อมูล sentiment จากหลายแหล่ง (Reddit, News API, Google Trends) โดยใช้อัลกอริทึมคำนวณคะแนน sentiment แบบถ่วงน้ำหนักเพื่อคาดการณ์การเคลื่อนไหวของราคาหุ้นในอนาคตและทำนายว่าหุ้นจะขึ้นหรือลงตามแนวโน้ม sentiment ของตลาด

- สร้างระบบจำแนก sentiment โดยใช้ VADER Sentiment Analyzer ที่ปรับปรุงให้เหมาะสมกับคำศัพท์ทางการเงิน เพื่อจำแนก sentiment เป็นบวก ลบ หรือกลาง พร้อมพัฒนาการรวม sentiment จากหลายแหล่งด้วยการคำนวณแบบถ่วงน้ำหนักเพื่อวิเคราะห์แรงขับเคลื่อนของตลาดและสร้างข้อมูลเชิงคาดการณ์

- ออกแบบและพัฒนาฐานข้อมูล MongoDB พร้อมสร้าง indexes และ aggregation pipelines เพื่อจัดเก็บและ query ข้อมูลทางการเงินจากหลายแหล่งอย่างมีประสิทธิภาพสำหรับการวิเคราะห์ sentiment แบบเรียลไทม์และการคาดการณ์

- วิเคราะห์เนื้อหาจาก YouTube และ X (Twitter) จากผู้ทรงอิทธิพลเพื่อระบุแนวโน้มตลาดและคาดการณ์ว่าหุ้นประเภทไหนจะได้รับผลกระทบมากที่สุด ช่วยในการตัดสินใจลงทุนเชิงรุกตาม sentiment และอิทธิพลจากผู้ทรงอิทธิพล

---

## รายละเอียดแบบภาษาอังกฤษ (English Version - Bullet Points)

**Multi-Source Stock Sentiment Analysis Dashboard**

- Developed predictive analytics system that aggregates sentiment data from multiple sources (Reddit, News API, Google Trends) using weighted sentiment scoring algorithms to forecast future stock price movements and predict whether stocks will rise or fall based on market sentiment trends

- Built sentiment classification engine using enhanced VADER Sentiment Analyzer to classify sentiment as positive, negative, or neutral, implementing multi-source sentiment aggregation with weighted calculations to analyze market driving forces and generate predictive insights

- Designed and implemented MongoDB database schema with optimized indexes and aggregation pipelines to efficiently store and query multi-source financial data for real-time sentiment analysis and prediction

- Analyzed content from YouTube and X (Twitter) influencers to identify market trends and predict which stock categories will be most impacted, enabling proactive investment decision-making based on influencer sentiment and market influence

---

## เทคโนโลยีที่ใช้ (Technologies Used)

- **Backend**: Python, Flask, MongoDB
- **Frontend**: JavaScript (ES6+), HTML5, CSS3, Chart.js
- **APIs**: Reddit API, News API, Google Trends (PyTrends), yfinance
- **NLP**: VADER Sentiment Analysis, NLTK
- **Data Processing**: Pandas, NumPy

