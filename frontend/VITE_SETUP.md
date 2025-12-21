# 🔧 Vite Setup สำหรับ Frontend

## 📋 ปัญหาที่พบ

เมื่อเปิด `http://localhost:5173/` ไม่แสดงอะไรเลย เพราะ:
- Vite ต้องการ `index.html` ที่ root ของ frontend folder
- เราเพิ่งย้าย HTML files ไปยัง `html/` folder
- Vite ไม่สามารถหา `index.html` ได้

## ✅ วิธีแก้ไข

### 1. **Copy `index.html` กลับไปที่ root**
   - ✅ Copy `html/index.html` → `index.html` (ที่ root)

### 2. **แก้ไข paths ใน `index.html` ที่ root**
   - ✅ CSS: `../public/css/` → `/public/css/`
   - ✅ JS: `../public/js/` → `/public/js/`
   - ✅ HTML links: `index.html` → `/html/index.html`

### 3. **แก้ไข `vite.config.ts`**
   - ✅ ตั้งค่า `publicDir: 'public'`
   - ✅ ตั้งค่า `server.open: '/'`

## 📁 โครงสร้างปัจจุบัน

```
frontend/
├── index.html          # Entry point สำหรับ Vite (copy จาก html/index.html)
├── html/               # HTML files อื่นๆ
│   ├── alerts.html
│   ├── compare.html
│   └── ...
├── public/             # Static assets
│   ├── css/
│   └── js/
└── vite.config.ts
```

## 🚀 การใช้งาน

1. **Start Vite dev server:**
   ```bash
   npm run dev
   ```

2. **เปิดเบราว์เซอร์:**
   - `http://localhost:5173/` → แสดง `index.html` (home page)
   - `http://localhost:5173/html/alerts.html` → แสดง alerts page
   - `http://localhost:5173/html/compare.html` → แสดง compare page
   - และอื่นๆ

## ⚠️ หมายเหตุ

- `index.html` ที่ root เป็น entry point สำหรับ Vite
- HTML files อื่นๆ อยู่ใน `html/` folder
- Paths ใช้ absolute paths (`/public/css/`, `/public/js/`)
- Navigation links ใช้ absolute paths (`/html/index.html`)

