import time
import os
import shutil
import smtplib
import ssl
from email.message import EmailMessage
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# ----------------------------
# CONFIGURATION
# ----------------------------
WATCH_FOLDER = r"C:\Users\Tumsa\Desktop\project_database\reddit-hashtag-analytics\backend\data\row"
PROCESSED_FOLDER = r"C:\Users\Tumsa\Desktop\project_database\reddit-hashtag-analytics\backend\data\process"
EMAIL_SENDER = "tumsanupong@gmail.com"
EMAIL_PASSWORD = "qyrb xgqr qdnk eowx"  # Gmail App Password
EMAIL_RECEIVER = "tumsanupong@gmail.com"

# ----------------------------
# FUNCTION TO SEND EMAIL
# ----------------------------
def send_email_with_attachment(file_path):
    # รอให้ไฟล์เสร็จสมบูรณ์ (ถ้ามี backend กำลังเขียนไฟล์)
    time.sleep(1)

    filename = os.path.basename(file_path)
    msg = EmailMessage()
    msg["Subject"] = f"New File Detected: {filename}"
    msg["From"] = EMAIL_SENDER
    msg["To"] = EMAIL_RECEIVER
    msg.set_content(f"A new file has been added: {filename}. File is attached.")

    # กำหนด MIME type ตามนามสกุล
    if file_path.endswith(".csv"):
        maintype, subtype = "text", "csv"
    elif file_path.endswith(".xlsx"):
        maintype, subtype = "application", "vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        maintype, subtype = "application", "octet-stream"

    # แนบไฟล์
    with open(file_path, "rb") as f:
        file_data = f.read()
        msg.add_attachment(file_data, maintype=maintype, subtype=subtype, filename=filename)

    # ส่งอีเมล
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as smtp:
        smtp.login(EMAIL_SENDER, EMAIL_PASSWORD)
        smtp.send_message(msg)

    print(f"📨 send {filename} to {EMAIL_RECEIVER} success")

    # ------------------------
    # ย้ายไฟล์ไป folder process
    # ------------------------
    if not os.path.exists(PROCESSED_FOLDER):
        os.makedirs(PROCESSED_FOLDER)  # สร้าง folder ถ้ายังไม่มี

    dest_path = os.path.join(PROCESSED_FOLDER, filename)
    shutil.move(file_path, dest_path)
    print(f"📂 move file {filename} to {PROCESSED_FOLDER} success")

# ----------------------------
# WATCHER CLASS
# ----------------------------
class Watcher(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
        if event.src_path.endswith(".csv") or event.src_path.endswith(".xlsx"):
            print(f"📁 new file: {event.src_path}")
            send_email_with_attachment(event.src_path)

# ----------------------------
# MAIN
# ----------------------------
if __name__ == "__main__":
    # ตรวจสอบโฟลเดอร์ก่อน
    if not os.path.exists(WATCH_FOLDER):
        print(f"❌ ERROR: Folder does not exist → {WATCH_FOLDER}")
        exit()

    print(f"👀 looking for file: {WATCH_FOLDER}")

    event_handler = Watcher()
    observer = Observer()
    observer.schedule(event_handler, WATCH_FOLDER, recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("🛑 Stopped watching folder.")

    observer.join()
