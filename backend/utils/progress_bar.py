"""
Progress Bar Utility สำหรับแสดงความคืบหน้า
พร้อมสี gradient และการแสดงเวลา
"""
import sys
import os
import time
from datetime import datetime, timedelta

# พยายามใช้ colorama สำหรับ Windows (ถ้ามี)
try:
    import colorama
    colorama.init(autoreset=True)
    USE_COLORAMA = True
except ImportError:
    USE_COLORAMA = False

# ANSI color codes สำหรับ Windows PowerShell
class Colors:
    """ANSI color codes"""
    RESET = '\033[0m'
    BOLD = '\033[1m'
    
    # สี gradient จากแดง → เหลือง → เขียว
    RED = '\033[91m'
    YELLOW = '\033[93m'
    GREEN = '\033[92m'
    CYAN = '\033[96m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'

# เก็บเวลาเริ่มต้นและเวลาอัปเดตล่าสุด
_progress_start_time = None
_progress_last_update = None
_progress_last_current = 0

def _enable_ansi_colors():
    """เปิดใช้งาน ANSI colors บน Windows"""
    if sys.platform == 'win32' and not USE_COLORAMA:
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            # Enable ANSI escape sequences
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
        except:
            pass

def _get_gradient_color(percent: float) -> str:
    """
    สร้างสี gradient ตามเปอร์เซ็นต์
    0-33%: แดง → เหลือง
    33-66%: เหลือง → เขียวอ่อน
    66-100%: เขียวอ่อน → เขียวเข้ม
    """
    if percent < 33:
        # แดง → เหลือง
        intensity = percent / 33
        return Colors.RED if intensity < 0.5 else Colors.YELLOW
    elif percent < 66:
        # เหลือง → เขียวอ่อน
        return Colors.YELLOW
    else:
        # เขียวอ่อน → เขียวเข้ม
        intensity = (percent - 66) / 34
        return Colors.GREEN

def _format_time(seconds: float) -> str:
    """แปลงวินาทีเป็นรูปแบบเวลา"""
    if seconds < 60:
        return f"{int(seconds)} วินาที"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        secs = int(seconds % 60)
        return f"{minutes} นาที {secs} วินาที"
    else:
        hours = int(seconds / 3600)
        minutes = int((seconds % 3600) / 60)
        return f"{hours} ชั่วโมง {minutes} นาที"

def draw_progress_bar(current: int, total: int, bar_length: int = 50, prefix: str = "กำลังโหลด", show_total: bool = True):
    """
    วาด progress bar พร้อมสี gradient และการแสดงเวลา
    
    Args:
        current: ค่าปัจจุบัน (จำนวนหุ้นที่ดึงได้)
        total: ค่าสูงสุด (จำนวนหุ้นทั้งหมด)
        bar_length: ความยาวของ progress bar (default: 50)
        prefix: ข้อความนำหน้า (default: "กำลังโหลด")
        show_total: แสดงจำนวนทั้งหมดหรือไม่ (default: True)
    """
    global _progress_start_time, _progress_last_update, _progress_last_current
    
    # เปิดใช้งาน ANSI colors
    _enable_ansi_colors()
    
    # เริ่มต้นเวลา
    now = time.time()
    is_first_call = _progress_start_time is None
    if is_first_call:
        _progress_start_time = now
        _progress_last_update = now
        _progress_last_current = current
    
    if total == 0:
        percent = 100.0
        filled = bar_length
    else:
        percent = min(100.0, (current / total) * 100)
        filled = int(bar_length * current / total)
    
    # คำนวณเวลา
    elapsed_time = now - _progress_start_time
    remaining = total - current
    
    # คำนวณ ETA (Estimated Time to Arrival)
    eta_seconds = None
    if current > 0 and remaining > 0:
        # คำนวณความเร็ว (หุ้นต่อวินาที)
        speed = current / elapsed_time if elapsed_time > 0 else 0
        if speed > 0:
            eta_seconds = remaining / speed
    
    # สร้าง progress bar พร้อมสี gradient
    bar_parts = []
    for i in range(bar_length):
        if i < filled:
            # คำนวณสีตามตำแหน่งใน progress bar
            pos_percent = (i / bar_length) * 100
            color = _get_gradient_color(pos_percent)
            bar_parts.append(f"{color}█{Colors.RESET}")
        else:
            bar_parts.append('░')
    
    bar = ''.join(bar_parts)
    
    # สีของเปอร์เซ็นต์ตามความคืบหน้า
    percent_color = _get_gradient_color(percent)
    
    # สร้างข้อความ
    if current == 0:
        time_info = " | กำลังเริ่มต้น..."
    else:
        time_info = f" | เวลาผ่านไป: {_format_time(elapsed_time)}"
        if eta_seconds and eta_seconds > 0:
            time_info += f" | คาดว่าจะเสร็จใน: {_format_time(eta_seconds)}"
    
    # ✅ แสดงผล (ใช้ \r เพื่อเขียนทับบรรทัดเดิม)
    # ถ้าเป็นครั้งแรก ให้ขึ้นบรรทัดใหม่ก่อน (เพื่อไม่ให้ถูกข้อความอื่นทับ)
    # หมายเหตุ: บรรทัดใหม่ถูกจัดการใน batch_data_processor แล้ว
    
    # สร้างข้อความ progress bar (ใช้ \r เพื่อเขียนทับบรรทัดเดิม)
    # ใช้ \r เพื่อกลับไปที่จุดเริ่มต้นของบรรทัด และลบข้อความเก่าด้วย \x1b[K (ANSI escape code)
    # บน Windows PowerShell อาจต้องใช้วิธีอื่น
    
    # ✅ ใช้ encoding ที่ปลอดภัยสำหรับ Windows
    try:
        # ตั้งค่า encoding สำหรับ Windows
        if sys.platform == 'win32':
            import io
            if hasattr(sys.stdout, 'buffer'):
                # ใช้ UTF-8 encoding
                sys.stdout.reconfigure(encoding='utf-8', errors='replace') if hasattr(sys.stdout, 'reconfigure') else None
    except:
        pass
    
    if show_total:
        message = f'\r{prefix}: [{bar}] {percent_color}{percent:.1f}%{Colors.RESET} (ดึงได้ {current:,} หุ้น จากทั้งหมด {total:,} หุ้น){time_info}'
    else:
        message = f'\r{prefix}: [{bar}] {percent_color}{percent:.1f}%{Colors.RESET} (ดึงได้ {current:,} หุ้น){time_info}'
    
    # ✅ ใช้ print() แทน sys.stdout.write เพื่อให้ทำงานได้ดีบน Windows PowerShell
    # ใช้ end='\r' เพื่อเขียนทับบรรทัดเดิม
    try:
        print(message, end='', flush=True)
    except (UnicodeEncodeError, OSError, AttributeError) as e:
        # ถ้า encoding ไม่รองรับ ให้ใช้ข้อความแบบง่าย (ไม่มีสี)
        try:
            # ใช้ block characters ที่ปลอดภัยกว่า
            simple_filled = '#' * filled
            simple_empty = '-' * (bar_length - filled)
            simple_bar = simple_filled + simple_empty
            simple_message = f'\r{prefix}: [{simple_bar}] {percent:.1f}% (ดึงได้ {current:,} หุ้น จากทั้งหมด {total:,} หุ้น){time_info}'
            print(simple_message, end='', flush=True)
        except Exception as e2:
            # ถ้ายังไม่ได้ ให้ใช้ข้อความแบบง่ายที่สุด
            simple_message = f'\r{prefix}: {percent:.1f}% ({current}/{total}){time_info}'
            print(simple_message, end='', flush=True)
    
    # อัปเดตเวลาล่าสุด
    _progress_last_update = now
    _progress_last_current = current
    
    # ถ้าเสร็จแล้วให้ขึ้นบรรทัดใหม่และรีเซ็ตเวลา
    if current >= total:
        print()  # ขึ้นบรรทัดใหม่
        _progress_start_time = None
        _progress_last_update = None
        _progress_last_current = 0

def reset_progress():
    """รีเซ็ต progress bar (ใช้เมื่อเริ่มงานใหม่)"""
    global _progress_start_time, _progress_last_update, _progress_last_current
    _progress_start_time = None
    _progress_last_update = None
    _progress_last_current = 0

