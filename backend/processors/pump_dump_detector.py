"""
Pump and Dump Detection Module
ตรวจจับการปั่นราคาหุ้น (pump and dump) เพื่อเพิ่มความแม่นยำของ sentiment analysis
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from database.db_config import db
import statistics

class PumpDumpDetector:
    """
    ตรวจจับการปั่นราคาหุ้น (pump and dump) โดยใช้หลาย signals:
    1. Volume spike analysis
    2. Engagement pattern analysis (bot detection)
    3. Price-sentiment divergence
    4. Time-based analysis
    5. Source credibility
    """
    
    def __init__(self):
        # Keywords ที่บ่งชี้การปั่นราคา
        self.pump_keywords = [
            'to the moon', 'rocket', 'moon', 'pump', 'yolo', 'hodl',
            'diamond hands', 'apes together strong', 'buy the dip',
            'this is the way', 'wen moon', 'wen lambo', 'stocks only go up'
        ]
        
        # Keywords ที่บ่งชี้การเทขาย
        self.dump_keywords = [
            'dump', 'sell', 'exit', 'take profit', 'paper hands',
            'get out', 'crash', 'tank', 'plunge', 'bear trap'
        ]
        
        # Suspicious patterns
        self.suspicious_patterns = [
            '🚀🚀🚀', '📈📈📈', '💎💎💎',  # Multiple emojis
            'BUY NOW', 'URGENT', 'DON\'T MISS',  # Urgency language
            'guaranteed', '100% sure', 'can\'t lose'  # Unrealistic promises
        ]
    
    def detect_pump_dump(self, symbol: str, posts: List[Dict], stock_info: Dict) -> Dict:
        """
        ตรวจจับการปั่นราคาหุ้น
        
        Args:
            symbol: Stock symbol
            posts: List of posts mentioning this stock
            stock_info: Stock information (price, volume, etc.)
            
        Returns:
            {
                "is_pump_dump": bool,
                "confidence": float (0-1),
                "signals": {
                    "volume_spike": bool,
                    "engagement_suspicious": bool,
                    "price_sentiment_divergence": bool,
                    "time_pattern": bool,
                    "source_credibility": bool
                },
                "risk_score": float (0-100),
                "recommendation": str
            }
        """
        if not posts or not stock_info:
            return {
                "is_pump_dump": False,
                "confidence": 0.0,
                "signals": {},
                "risk_score": 0,
                "recommendation": "Insufficient data"
            }
        
        signals = {}
        risk_factors = []
        
        # Signal 1: Volume Spike Analysis
        volume_signal = self._check_volume_spike(symbol, stock_info)
        signals["volume_spike"] = volume_signal["is_spike"]
        if volume_signal["is_spike"]:
            risk_factors.append(("volume_spike", volume_signal["confidence"]))
        
        # Signal 2: Engagement Pattern Analysis
        engagement_signal = self._check_engagement_patterns(posts)
        signals["engagement_suspicious"] = engagement_signal["is_suspicious"]
        if engagement_signal["is_suspicious"]:
            risk_factors.append(("engagement_suspicious", engagement_signal["confidence"]))
        
        # Signal 3: Price-Sentiment Divergence
        divergence_signal = self._check_price_sentiment_divergence(symbol, posts, stock_info)
        signals["price_sentiment_divergence"] = divergence_signal["has_divergence"]
        if divergence_signal["has_divergence"]:
            risk_factors.append(("price_sentiment_divergence", divergence_signal["confidence"]))
        
        # Signal 4: Time Pattern Analysis
        time_signal = self._check_time_patterns(posts)
        signals["time_pattern"] = time_signal["is_suspicious"]
        if time_signal["is_suspicious"]:
            risk_factors.append(("time_pattern", time_signal["confidence"]))
        
        # Signal 5: Source Credibility
        credibility_signal = self._check_source_credibility(posts)
        signals["source_credibility"] = credibility_signal["is_low"]
        if credibility_signal["is_low"]:
            risk_factors.append(("source_credibility", credibility_signal["confidence"]))
        
        # Signal 6: Keyword Analysis
        keyword_signal = self._check_pump_keywords(posts)
        signals["pump_keywords"] = keyword_signal["has_pump_keywords"]
        if keyword_signal["has_pump_keywords"]:
            risk_factors.append(("pump_keywords", keyword_signal["confidence"]))
        
        # คำนวณ risk score และ confidence
        risk_score = sum(conf * 20 for _, conf in risk_factors)  # Max 100
        confidence = len(risk_factors) / 6.0  # 0-1 based on number of signals
        
        # กำหนดว่าเป็น pump and dump หรือไม่
        is_pump_dump = len(risk_factors) >= 3 or risk_score >= 60
        
        # Generate recommendation
        recommendation = self._generate_recommendation(is_pump_dump, risk_score, signals)
        
        return {
            "is_pump_dump": is_pump_dump,
            "confidence": confidence,
            "signals": signals,
            "risk_score": min(100, risk_score),
            "recommendation": recommendation,
            "risk_factors": risk_factors
        }
    
    def _check_volume_spike(self, symbol: str, stock_info: Dict) -> Dict:
        """
        ตรวจสอบ volume spike (ปริมาณการซื้อขายเพิ่มขึ้นผิดปกติ)
        """
        try:
            current_volume = stock_info.get('volume', 0)
            avg_volume = stock_info.get('averageVolume', 0)
            
            if avg_volume > 0 and current_volume > 0:
                volume_ratio = current_volume / avg_volume
                
                # ถ้า volume เพิ่มขึ้นมากกว่า 3 เท่า → สงสัย
                if volume_ratio > 3.0:
                    confidence = min(1.0, (volume_ratio - 3.0) / 5.0)  # 3x = 0.0, 8x = 1.0
                    return {
                        "is_spike": True,
                        "confidence": confidence,
                        "volume_ratio": volume_ratio
                    }
            
            return {"is_spike": False, "confidence": 0.0}
        except Exception:
            return {"is_spike": False, "confidence": 0.0}
    
    def _check_engagement_patterns(self, posts: List[Dict]) -> Dict:
        """
        ตรวจสอบ engagement patterns ที่น่าสงสัย (bot activity)
        """
        if not posts:
            return {"is_suspicious": False, "confidence": 0.0}
        
        suspicious_count = 0
        total_posts = len(posts)
        
        # ตรวจสอบ patterns ที่น่าสงสัย
        for post in posts:
            text = f"{post.get('title', '')} {post.get('selftext', '')}".lower()
            
            # 1. Low engagement แต่ high mentions
            score = post.get('score', 0)
            comments = post.get('num_comments', 0)
            if score < 5 and comments < 3 and total_posts > 10:
                suspicious_count += 1
            
            # 2. Multiple suspicious keywords
            pump_count = sum(1 for keyword in self.pump_keywords if keyword in text)
            if pump_count >= 3:
                suspicious_count += 1
            
            # 3. Suspicious patterns
            if any(pattern.lower() in text for pattern in self.suspicious_patterns):
                suspicious_count += 1
        
        suspicious_ratio = suspicious_count / total_posts if total_posts > 0 else 0
        
        # ถ้ามากกว่า 30% ของ posts น่าสงสัย → สงสัย
        if suspicious_ratio > 0.3:
            confidence = min(1.0, (suspicious_ratio - 0.3) / 0.5)  # 0.3 = 0.0, 0.8 = 1.0
            return {
                "is_suspicious": True,
                "confidence": confidence,
                "suspicious_ratio": suspicious_ratio
            }
        
        return {"is_suspicious": False, "confidence": 0.0}
    
    def _check_price_sentiment_divergence(self, symbol: str, posts: List[Dict], stock_info: Dict) -> Dict:
        """
        ตรวจสอบ price-sentiment divergence
        (sentiment สูงแต่ราคาไม่ขึ้น หรือ sentiment ต่ำแต่ราคาขึ้น)
        """
        try:
            # คำนวณ average sentiment
            sentiments = []
            for post in posts:
                if post.get('sentiment'):
                    if isinstance(post.get('sentiment'), dict):
                        sentiments.append(post.get('sentiment', {}).get('compound', 0))
                    else:
                        sentiments.append(post.get('sentiment', 0))
            
            if not sentiments:
                return {"has_divergence": False, "confidence": 0.0}
            
            avg_sentiment = sum(sentiments) / len(sentiments)
            
            # ดึง price change
            price_change = stock_info.get('changePercent', 0) or stock_info.get('priceChangePercent', 0)
            
            # ตรวจสอบ divergence
            # ถ้า sentiment > 0.5 แต่ price change < 0 → divergence (pump)
            # ถ้า sentiment < -0.5 แต่ price change > 0 → divergence (dump)
            if avg_sentiment > 0.5 and price_change < -5:
                # Sentiment บวกมาก แต่ราคาตกมาก → อาจเป็น pump and dump
                confidence = min(1.0, (avg_sentiment - 0.5) * 2)  # 0.5 = 0.0, 1.0 = 1.0
                return {
                    "has_divergence": True,
                    "confidence": confidence,
                    "sentiment": avg_sentiment,
                    "price_change": price_change,
                    "type": "pump_dump"
                }
            elif avg_sentiment < -0.5 and price_change > 5:
                # Sentiment ลบมาก แต่ราคาขึ้นมาก → อาจเป็น manipulation
                confidence = min(1.0, (abs(avg_sentiment) - 0.5) * 2)
                return {
                    "has_divergence": True,
                    "confidence": confidence,
                    "sentiment": avg_sentiment,
                    "price_change": price_change,
                    "type": "manipulation"
                }
            
            return {"has_divergence": False, "confidence": 0.0}
        except Exception:
            return {"has_divergence": False, "confidence": 0.0}
    
    def _check_time_patterns(self, posts: List[Dict]) -> Dict:
        """
        ตรวจสอบ time patterns ที่น่าสงสัย
        (posts เกิดขึ้นพร้อมกันมากเกินไป = coordinated pump)
        """
        if len(posts) < 5:
            return {"is_suspicious": False, "confidence": 0.0}
        
        try:
            # แปลง created_utc เป็น datetime
            post_times = []
            for post in posts:
                created_utc = post.get('created_utc')
                if isinstance(created_utc, str):
                    post_times.append(datetime.fromisoformat(created_utc.replace('Z', '+00:00')))
                elif isinstance(created_utc, datetime):
                    post_times.append(created_utc)
            
            if len(post_times) < 5:
                return {"is_suspicious": False, "confidence": 0.0}
            
            # เรียงตามเวลา
            post_times.sort()
            
            # ตรวจสอบว่ามี posts เกิดขึ้นพร้อมกันมากเกินไปหรือไม่
            # (หลาย posts ในช่วงเวลา 1 ชั่วโมง = coordinated)
            time_windows = []
            for i, time in enumerate(post_times):
                # นับ posts ใน 1 ชั่วโมงถัดไป
                window_end = time + timedelta(hours=1)
                posts_in_window = sum(1 for t in post_times if time <= t <= window_end)
                time_windows.append(posts_in_window)
            
            max_posts_in_hour = max(time_windows) if time_windows else 0
            
            # ถ้ามี posts มากกว่า 20 ตัวใน 1 ชั่วโมง → สงสัย
            if max_posts_in_hour > 20:
                confidence = min(1.0, (max_posts_in_hour - 20) / 30)  # 20 = 0.0, 50 = 1.0
                return {
                    "is_suspicious": True,
                    "confidence": confidence,
                    "max_posts_in_hour": max_posts_in_hour
                }
            
            return {"is_suspicious": False, "confidence": 0.0}
        except Exception:
            return {"is_suspicious": False, "confidence": 0.0}
    
    def _check_source_credibility(self, posts: List[Dict]) -> Dict:
        """
        ตรวจสอบ source credibility
        (accounts ใหม่, low karma, suspicious usernames)
        """
        if not posts:
            return {"is_low": False, "confidence": 0.0}
        
        low_credibility_count = 0
        total_posts = len(posts)
        
        for post in posts:
            author = post.get('author', '').lower()
            
            # 1. New accounts (ชื่อแบบ auto-generated)
            if any(pattern in author for pattern in ['bot', 'auto', 'generated', 'user_']):
                low_credibility_count += 1
            
            # 2. Low engagement posts
            score = post.get('score', 0)
            if score < 2:
                low_credibility_count += 1
        
        low_credibility_ratio = low_credibility_count / total_posts if total_posts > 0 else 0
        
        # ถ้ามากกว่า 50% ของ posts มี credibility ต่ำ → สงสัย
        if low_credibility_ratio > 0.5:
            confidence = min(1.0, (low_credibility_ratio - 0.5) / 0.3)  # 0.5 = 0.0, 0.8 = 1.0
            return {
                "is_low": True,
                "confidence": confidence,
                "low_credibility_ratio": low_credibility_ratio
            }
        
        return {"is_low": False, "confidence": 0.0}
    
    def _check_pump_keywords(self, posts: List[Dict]) -> Dict:
        """
        ตรวจสอบ pump keywords ใน posts
        """
        if not posts:
            return {"has_pump_keywords": False, "confidence": 0.0}
        
        pump_keyword_count = 0
        total_posts = len(posts)
        
        for post in posts:
            text = f"{post.get('title', '')} {post.get('selftext', '')}".lower()
            
            # นับ pump keywords
            pump_count = sum(1 for keyword in self.pump_keywords if keyword in text)
            if pump_count >= 2:  # มี pump keywords อย่างน้อย 2 คำ
                pump_keyword_count += 1
        
        pump_ratio = pump_keyword_count / total_posts if total_posts > 0 else 0
        
        # ถ้ามากกว่า 20% ของ posts มี pump keywords → สงสัย
        if pump_ratio > 0.2:
            confidence = min(1.0, (pump_ratio - 0.2) / 0.5)  # 0.2 = 0.0, 0.7 = 1.0
            return {
                "has_pump_keywords": True,
                "confidence": confidence,
                "pump_ratio": pump_ratio
            }
        
        return {"has_pump_keywords": False, "confidence": 0.0}
    
    def _generate_recommendation(self, is_pump_dump: bool, risk_score: float, signals: Dict) -> str:
        """
        สร้างคำแนะนำตาม risk score
        """
        if is_pump_dump:
            if risk_score >= 80:
                return "⚠️ HIGH RISK: Strong pump and dump signals detected. Avoid or be very cautious."
            elif risk_score >= 60:
                return "⚠️ MODERATE RISK: Some pump and dump signals detected. Proceed with caution."
            else:
                return "⚠️ LOW RISK: Minor pump and dump signals detected. Monitor closely."
        else:
            return "✅ LOW RISK: No significant pump and dump signals detected."
    
    def calculate_trust_score(self, symbol: str, posts: List[Dict], stock_info: Dict) -> float:
        """
        คำนวณ trust score (0-100) สำหรับ sentiment
        Score สูง = น่าเชื่อถือ, Score ต่ำ = น่าสงสัย
        """
        detection_result = self.detect_pump_dump(symbol, posts, stock_info)
        
        # Trust score = 100 - risk_score
        trust_score = 100 - detection_result.get("risk_score", 0)
        
        return max(0, min(100, trust_score))
    
    def adjust_sentiment_by_trust(self, original_sentiment: float, trust_score: float) -> float:
        """
        ปรับ sentiment ตาม trust score
        ถ้า trust score ต่ำ → ลด sentiment (ไม่เชื่อถือ)
        """
        # ถ้า trust score < 50 → ลด sentiment ลง 50%
        if trust_score < 50:
            adjustment_factor = trust_score / 100.0  # 0-0.5
            adjusted_sentiment = original_sentiment * adjustment_factor
            return adjusted_sentiment
        
        # ถ้า trust score >= 50 → ใช้ sentiment เดิม
        return original_sentiment
