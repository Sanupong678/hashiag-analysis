"""
Stock Info Manager - จัดการการดึงข้อมูลหุ้นแบบ Smart Caching
- ข้อมูลราคา (price, bid/ask): อัปเดตบ่อย (1-5 นาที)
- ข้อมูล volume: อัปเดตปานกลาง (15-30 นาที)
- ข้อมูลอื่นๆ: อัปเดตไม่บ่อย (1-2 ชั่วโมง)
"""
from datetime import datetime, timedelta
from typing import Dict, Optional
from fetchers.yahoo_finance_fetcher import YahooFinanceFetcher
from cache.redis_cache import cache

class StockInfoManager:
    """
    จัดการการดึงข้อมูลหุ้นแบบ Smart Caching
    แบ่งตามประเภทข้อมูลและความถี่ในการอัปเดต
    """
    
    def __init__(self):
        self.yahoo_fetcher = YahooFinanceFetcher()
        
        # Cache TTL (Time To Live) สำหรับแต่ละประเภทข้อมูล
        self.cache_ttl = {
            'price_data': 60,      # 1 นาที (ราคา, bid/ask เปลี่ยนแปลงบ่อย)
            'volume_data': 900,    # 15 นาที (volume เปลี่ยนแปลงปานกลาง)
            'static_data': 3600,   # 1 ชั่วโมง (sector, industry ไม่ค่อยเปลี่ยน)
            'full_data': 300       # 5 นาที (ข้อมูลทั้งหมด)
        }
    
    def get_stock_info_smart(self, symbol: str, force_refresh: bool = False) -> Optional[Dict]:
        """
        ดึงข้อมูลหุ้นแบบ Smart Caching
        
        Args:
            symbol: Stock symbol
            force_refresh: ถ้า True จะดึงใหม่เสมอ
        
        Returns:
            Dictionary with stock information
        """
        symbol_upper = symbol.upper()
        
        if force_refresh:
            # ดึงใหม่เสมอ
            return self._fetch_fresh_data(symbol_upper)
        
        # ตรวจสอบ cache
        if cache:
            cached_data = cache.get_stock_info(symbol_upper)
            if cached_data:
                # ตรวจสอบอายุของข้อมูล
                fetched_at_str = cached_data.get('fetchedAt')
                if fetched_at_str:
                    try:
                        fetched_at = datetime.fromisoformat(fetched_at_str.replace('Z', '+00:00'))
                        age_seconds = (datetime.utcnow() - fetched_at.replace(tzinfo=None)).total_seconds()
                        
                        # ถ้าข้อมูลยังใหม่ (น้อยกว่า 5 นาที) ใช้ cache
                        if age_seconds < self.cache_ttl['full_data']:
                            return cached_data
                    except:
                        pass
        
        # ดึงข้อมูลใหม่
        return self._fetch_fresh_data(symbol_upper)
    
    def get_stock_info_realtime(self, symbol: str) -> Optional[Dict]:
        """
        ดึงข้อมูลหุ้นแบบ Real-time (สำหรับการคำนวณ validation)
        
        Args:
            symbol: Stock symbol
        
        Returns:
            Dictionary with stock information (ดึงใหม่เสมอ)
        """
        return self._fetch_fresh_data(symbol.upper())
    
    def _fetch_fresh_data(self, symbol: str) -> Optional[Dict]:
        """ดึงข้อมูลใหม่จาก Yahoo Finance"""
        stock_info = self.yahoo_fetcher.get_stock_info(symbol)
        
        if stock_info and cache:
            # เก็บใน cache
            cache.set_stock_info(symbol, stock_info)
        
        return stock_info
    
    def get_stock_info_for_validation(self, symbol: str) -> Optional[Dict]:
        """
        ดึงข้อมูลหุ้นสำหรับการ validation
        ใช้ข้อมูล real-time เพื่อความแม่นยำ
        
        Args:
            symbol: Stock symbol
        
        Returns:
            Dictionary with stock information
        """
        # สำหรับ validation ต้องใช้ข้อมูล real-time
        # แต่ถ้ามี cache ที่ใหม่มาก (น้อยกว่า 1 นาที) ก็ใช้ได้
        if cache:
            cached_data = cache.get_stock_info(symbol.upper())
            if cached_data:
                fetched_at_str = cached_data.get('fetchedAt')
                if fetched_at_str:
                    try:
                        fetched_at = datetime.fromisoformat(fetched_at_str.replace('Z', '+00:00'))
                        age_seconds = (datetime.utcnow() - fetched_at.replace(tzinfo=None)).total_seconds()
                        
                        # ถ้าข้อมูลใหม่มาก (น้อยกว่า 1 นาที) ใช้ cache
                        if age_seconds < self.cache_ttl['price_data']:
                            return cached_data
                    except:
                        pass
        
        # ดึงใหม่
        return self._fetch_fresh_data(symbol.upper())
    
    def should_refresh_price_data(self, stock_info: Dict) -> bool:
        """
        ตรวจสอบว่าควรอัปเดตข้อมูลราคาหรือไม่
        
        Args:
            stock_info: ข้อมูลหุ้นที่มีอยู่
        
        Returns:
            True ถ้าควรอัปเดต
        """
        if not stock_info:
            return True
        
        fetched_at_str = stock_info.get('fetchedAt')
        if not fetched_at_str:
            return True
        
        try:
            fetched_at = datetime.fromisoformat(fetched_at_str.replace('Z', '+00:00'))
            age_seconds = (datetime.utcnow() - fetched_at.replace(tzinfo=None)).total_seconds()
            
            # อัปเดตถ้าเก่ากว่า 1 นาที
            return age_seconds >= self.cache_ttl['price_data']
        except:
            return True
    
    def should_refresh_volume_data(self, stock_info: Dict) -> bool:
        """
        ตรวจสอบว่าควรอัปเดตข้อมูล volume หรือไม่
        
        Args:
            stock_info: ข้อมูลหุ้นที่มีอยู่
        
        Returns:
            True ถ้าควรอัปเดต
        """
        if not stock_info:
            return True
        
        fetched_at_str = stock_info.get('fetchedAt')
        if not fetched_at_str:
            return True
        
        try:
            fetched_at = datetime.fromisoformat(fetched_at_str.replace('Z', '+00:00'))
            age_seconds = (datetime.utcnow() - fetched_at.replace(tzinfo=None)).total_seconds()
            
            # อัปเดตถ้าเก่ากว่า 15 นาที
            return age_seconds >= self.cache_ttl['volume_data']
        except:
            return True
