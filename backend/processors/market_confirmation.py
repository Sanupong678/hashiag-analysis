"""
Market Confirmation Module
ตรวจสอบความถูกต้องของ sentiment ด้วยพฤติกรรมตลาดจริง
"""
from typing import Dict, Optional
from datetime import datetime, timedelta
import math

class MarketConfirmation:
    """
    ตรวจสอบ sentiment ด้วย market data:
    - Price change
    - Volume change
    - Bid/Ask imbalance
    - VWAP deviation (optional)
    """
    
    def __init__(self):
        pass
    
    def calculate_confirmation_score(
        self,
        sentiment: float,
        price_change: float,
        volume_change: float,
        bid_ask_imbalance: Optional[float] = None,
        average_volume: Optional[float] = None,
        current_volume: Optional[float] = None
    ) -> Dict:
        """
        คำนวณ confirmation score
        
        Args:
            sentiment: Raw sentiment score (-1 to 1)
            price_change: Price change percentage
            volume_change: Volume change percentage (vs average)
            bid_ask_imbalance: (ask - bid) / bid (optional)
            average_volume: Average volume (optional)
            current_volume: Current volume (optional)
            
        Returns:
            Dictionary with confirmation metrics
        """
        # 1. Price-Sentiment Alignment
        sentiment_sign = 1 if sentiment > 0 else -1 if sentiment < 0 else 0
        price_sign = 1 if price_change > 0 else -1 if price_change < 0 else 0
        
        price_alignment = 0.0
        if sentiment_sign != 0 and price_sign != 0:
            if sentiment_sign == price_sign:
                # ตรงกัน: sentiment บวก + ราคาขึ้น = ดี
                price_alignment = min(1.0, abs(price_change) / 5.0)  # Normalize to 0-1
            else:
                # ไม่ตรงกัน: sentiment บวก แต่ราคาลง = ไม่ดี
                price_alignment = -min(1.0, abs(price_change) / 5.0)
        
        # 2. Volume Confirmation
        volume_confirmation = 0.0
        if volume_change is not None:
            # Volume spike = confirmation ที่แข็งแกร่ง
            if abs(volume_change) > 50:  # Volume เพิ่ม > 50%
                volume_confirmation = 0.3
            elif abs(volume_change) > 20:  # Volume เพิ่ม > 20%
                volume_confirmation = 0.15
            elif abs(volume_change) < -20:  # Volume ลด > 20% = ไม่ confirm
                volume_confirmation = -0.1
        
        # 3. Bid/Ask Imbalance
        bid_ask_confirmation = 0.0
        if bid_ask_imbalance is not None:
            # bid_ask_imbalance > 0 = มีแรงซื้อมากกว่าแรงขาย
            if sentiment > 0 and bid_ask_imbalance > 0:
                bid_ask_confirmation = min(0.2, abs(bid_ask_imbalance) * 10)
            elif sentiment < 0 and bid_ask_imbalance < 0:
                bid_ask_confirmation = min(0.2, abs(bid_ask_imbalance) * 10)
            elif sentiment != 0 and bid_ask_imbalance != 0:
                # ไม่ตรงกัน = ลด confidence
                bid_ask_confirmation = -min(0.15, abs(bid_ask_imbalance) * 10)
        
        # 4. Velocity (ความเร็วของการเปลี่ยนแปลง)
        velocity = 0.0
        if abs(price_change) > 2:  # ราคาเปลี่ยน > 2%
            velocity = 0.1
        if abs(price_change) > 5:  # ราคาเปลี่ยน > 5%
            velocity = 0.2
        
        # รวม confirmation score
        confirmation_score = (
            price_alignment * 0.5 +      # 50% weight
            volume_confirmation * 0.3 +   # 30% weight
            bid_ask_confirmation * 0.15 + # 15% weight
            velocity * 0.05               # 5% weight
        )
        
        # Normalize to -1 to 1
        confirmation_score = max(-1.0, min(1.0, confirmation_score))
        
        # คำนวณ confidence
        confidence = self._calculate_confidence(
            abs(sentiment),
            abs(confirmation_score),
            abs(price_change),
            abs(volume_change) if volume_change else 0
        )
        
        # กำหนด status
        status = self._determine_status(sentiment, confirmation_score, confidence)
        
        return {
            "raw_sentiment": sentiment,
            "price_alignment": price_alignment,
            "volume_confirmation": volume_confirmation,
            "bid_ask_confirmation": bid_ask_confirmation,
            "velocity": velocity,
            "market_confirmation": confirmation_score,
            "confidence": confidence,
            "status": status
        }
    
    def _calculate_confidence(
        self,
        sentiment_magnitude: float,
        confirmation_magnitude: float,
        price_change_magnitude: float,
        volume_change_magnitude: float
    ) -> float:
        """
        คำนวณ confidence score (0-1)
        
        Confidence สูงเมื่อ:
        - Sentiment ชัดเจน (magnitude สูง)
        - Market confirm (confirmation สูง)
        - Price change ชัดเจน
        - Volume spike
        """
        # Base confidence จาก sentiment magnitude
        base_confidence = min(0.5, sentiment_magnitude)
        
        # เพิ่ม confidence จาก confirmation
        confirmation_boost = confirmation_magnitude * 0.3
        
        # เพิ่ม confidence จาก price change
        price_boost = min(0.15, price_change_magnitude / 10.0)
        
        # เพิ่ม confidence จาก volume spike
        volume_boost = min(0.05, volume_change_magnitude / 100.0)
        
        confidence = base_confidence + confirmation_boost + price_boost + volume_boost
        
        # Normalize to 0-1
        return max(0.0, min(1.0, confidence))
    
    def _determine_status(self, sentiment: float, confirmation: float, confidence: float) -> str:
        """
        กำหนด status ของ sentiment
        
        Returns:
            Status string
        """
        if abs(sentiment) < 0.1:
            return "neutral"
        
        sentiment_positive = sentiment > 0
        confirmation_positive = confirmation > 0
        
        if sentiment_positive and confirmation_positive:
            if confidence > 0.7:
                return "positive_confirmed"
            elif confidence > 0.4:
                return "positive_partially_confirmed"
            else:
                return "positive_unconfirmed"
        elif sentiment_positive and not confirmation_positive:
            return "positive_but_unconfirmed"
        elif not sentiment_positive and confirmation_positive:
            return "negative_confirmed"
        elif not sentiment_positive and not confirmation_positive:
            if confidence > 0.7:
                return "negative_confirmed"
            elif confidence > 0.4:
                return "negative_partially_confirmed"
            else:
                return "negative_unconfirmed"
        
        return "neutral"
