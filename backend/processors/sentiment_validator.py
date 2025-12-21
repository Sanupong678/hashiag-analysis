"""
Sentiment Validator - ตรวจสอบความสอดคล้องระหว่าง Sentiment กับแรงซื้อ/ขาย
เพื่อกรองข้อมูลที่น่าสงสัย (bot, fake news, market manipulation)
"""
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
import math

class SentimentValidator:
    """
    ตรวจสอบความน่าเชื่อถือของ Sentiment โดยเปรียบเทียบกับแรงซื้อ/ขายจริง
    
    Logic:
    1. Yahoo Finance News: เชื่อถือได้สูง (ข่าวจากบริษัท)
    2. Reddit: อาจมีการปั่นตลาด, bot, กุเรื่อง
    3. ตรวจสอบความสอดคล้องระหว่าง sentiment กับแรงซื้อ/ขาย
    4. ถ้าไม่สอดคล้อง = อาจเป็น bot/manipulation
    """
    
    def __init__(self):
        pass
    
    def calculate_buy_sell_pressure(self, stock_info: Dict) -> Dict:
        """
        คำนวณแรงซื้อ/ขายจากข้อมูลหุ้น
        
        Args:
            stock_info: ข้อมูลหุ้นจาก Yahoo Finance
        
        Returns:
            {
                'buy_pressure': float (0-100),
                'sell_pressure': float (0-100),
                'volume_ratio': float (volume / avg_volume),
                'price_change': float (percent),
                'direction': str ('buy' or 'sell')
            }
        """
        if not stock_info:
            return {
                'buy_pressure': 50.0,
                'sell_pressure': 50.0,
                'volume_ratio': 1.0,
                'price_change': 0.0,
                'direction': 'neutral'
            }
        
        price_change = stock_info.get('changePercent', 0)
        volume = stock_info.get('volume', 0)
        avg_volume = stock_info.get('averageVolume', volume)  # ถ้าไม่มีใช้ volume ปัจจุบัน
        
        # ดึงข้อมูล bid/ask
        bid = stock_info.get('bid')
        ask = stock_info.get('ask')
        bid_size = stock_info.get('bidSize', 0)
        ask_size = stock_info.get('askSize', 0)
        current_price = stock_info.get('currentPrice', 0)
        
        # คำนวณ volume ratio
        if avg_volume > 0:
            volume_ratio = volume / avg_volume
        else:
            volume_ratio = 1.0
        
        # คำนวณแรงซื้อ/ขายจาก price change และ volume
        # Price change: บวก = แรงซื้อ, ลบ = แรงขาย
        price_factor = 50 + (price_change * 2)  # -5% = 40, +5% = 60
        
        # Volume: สูงกว่า average = แรงซื้อ/ขายมากขึ้น
        volume_factor = 50
        if volume_ratio > 1.5:  # Volume สูงมาก
            volume_factor = min(100, 50 + (volume_ratio - 1.5) * 20)
        elif volume_ratio < 0.5:  # Volume ต่ำมาก
            volume_factor = max(0, 50 - (0.5 - volume_ratio) * 20)
        
        # คำนวณ bid/ask pressure (ถ้ามีข้อมูล)
        bid_ask_factor = 50  # Default neutral
        if bid and ask and current_price > 0:
            # ถ้า bid_size > ask_size = มีแรงซื้อมากกว่า
            # ถ้า ask_size > bid_size = มีแรงขายมากกว่า
            total_size = bid_size + ask_size
            if total_size > 0:
                bid_ratio = bid_size / total_size
                ask_ratio = ask_size / total_size
                
                # คำนวณจาก bid/ask ratio
                # bid_ratio สูง = แรงซื้อมาก, ask_ratio สูง = แรงขายมาก
                bid_ask_factor = 50 + ((bid_ratio - ask_ratio) * 50)  # 0-100
                
                # ปรับตาม spread (spread แคบ = มีความต้องการซื้อ/ขายจริง)
                spread = stock_info.get('spread', 0)
                spread_percent = stock_info.get('spreadPercent', 0)
                if spread_percent > 0 and spread_percent < 1.0:  # Spread แคบ = มีความต้องการจริง
                    # Spread แคบ = confidence สูง
                    pass  # ใช้ bid_ask_factor ตามปกติ
                elif spread_percent > 2.0:  # Spread กว้าง = ไม่มีความต้องการชัดเจน
                    # ลดน้ำหนัก bid/ask factor
                    bid_ask_factor = 50 + (bid_ask_factor - 50) * 0.5
        
        # รวมกัน (price 40%, volume 30%, bid/ask 30%)
        buy_pressure = (price_factor * 0.4 + volume_factor * 0.3 + bid_ask_factor * 0.3)
        sell_pressure = 100 - buy_pressure
        
        # กำหนดทิศทาง (ใช้ทั้ง price change, volume, และ bid/ask)
        if (price_change > 1.0 and volume_ratio > 1.2) or (bid_ask_factor > 60):
            direction = 'buy'
        elif (price_change < -1.0 and volume_ratio > 1.2) or (bid_ask_factor < 40):
            direction = 'sell'
        else:
            direction = 'neutral'
        
        return {
            'buy_pressure': max(0, min(100, buy_pressure)),
            'sell_pressure': max(0, min(100, sell_pressure)),
            'volume_ratio': volume_ratio,
            'price_change': price_change,
            'direction': direction,
            'bid': bid,
            'ask': ask,
            'bid_size': bid_size,
            'ask_size': ask_size,
            'bid_ask_factor': bid_ask_factor
        }
    
    def validate_sentiment(self, 
                          sentiment: float, 
                          source: str, 
                          stock_info: Dict,
                          pressure_data: Optional[Dict] = None) -> Dict:
        """
        ตรวจสอบความสอดคล้องระหว่าง Sentiment กับแรงซื้อ/ขาย
        
        Args:
            sentiment: Sentiment score (-5.0 ถึง +5.0)
            source: 'yahoo_finance' หรือ 'reddit'
            stock_info: ข้อมูลหุ้น
            pressure_data: ข้อมูลแรงซื้อ/ขาย (ถ้าไม่มีจะคำนวณใหม่)
        
        Returns:
            {
                'is_valid': bool,
                'confidence': float (0-1.0),
                'alignment_score': float (-1.0 ถึง 1.0),  # -1 = ไม่สอดคล้อง, +1 = สอดคล้องมาก
                'reason': str,
                'pressure_data': dict,
                'risk_level': str ('low', 'medium', 'high')
            }
        """
        if not pressure_data:
            pressure_data = self.calculate_buy_sell_pressure(stock_info)
        
        # แปลง sentiment (-5.0 ถึง +5.0) เป็นทิศทาง (0-100)
        # Sentiment บวก = แรงซื้อ, Sentiment ลบ = แรงขาย
        sentiment_pressure = 50 + (sentiment * 10)  # -5.0 = 0, +5.0 = 100
        
        # เปรียบเทียบ sentiment กับแรงซื้อ/ขายจริง
        actual_pressure = pressure_data['buy_pressure']
        pressure_diff = abs(sentiment_pressure - actual_pressure)
        
        # คำนวณ alignment score (-1.0 ถึง +1.0)
        # ถ้า sentiment กับ pressure อยู่ในทิศทางเดียวกัน = สอดคล้อง
        sentiment_direction = 'buy' if sentiment > 0.1 else ('sell' if sentiment < -0.1 else 'neutral')
        actual_direction = pressure_data['direction']
        
        # Alignment score
        if sentiment_direction == actual_direction:
            # สอดคล้องกัน - คำนวณจากความใกล้เคียง
            alignment_score = 1.0 - (pressure_diff / 100)  # 0-1.0
        elif sentiment_direction == 'neutral' or actual_direction == 'neutral':
            # กลางๆ = alignment ปานกลาง
            alignment_score = 0.5 - (pressure_diff / 200)  # 0-0.5
        else:
            # ไม่สอดคล้องกัน (ทิศทางตรงข้าม)
            alignment_score = -1.0 + (pressure_diff / 100)  # -1.0 ถึง 0
        
        # Confidence score (0-1.0)
        # Yahoo Finance: เชื่อถือได้สูงกว่า
        base_confidence = 0.8 if source == 'yahoo_finance' else 0.5
        
        # ปรับ confidence ตาม alignment
        if alignment_score > 0.7:
            # สอดคล้องมาก = confidence สูง
            confidence = min(1.0, base_confidence + 0.2)
            is_valid = True
            reason = f"Sentiment สอดคล้องกับแรงซื้อ/ขาย ({alignment_score:.2f})"
            risk_level = 'low'
        elif alignment_score > 0.3:
            # สอดคล้องปานกลาง
            confidence = base_confidence
            is_valid = True
            reason = f"Sentiment สอดคล้องปานกลางกับแรงซื้อ/ขาย ({alignment_score:.2f})"
            risk_level = 'medium'
        elif alignment_score > -0.3:
            # ไม่ค่อยสอดคล้อง
            if source == 'reddit':
                # Reddit + ไม่สอดคล้อง = อาจเป็น bot/manipulation
                confidence = max(0.2, base_confidence - 0.4)
                is_valid = False
                reason = f"⚠️ Reddit sentiment ไม่สอดคล้องกับแรงซื้อ/ขาย - อาจเป็น bot/manipulation ({alignment_score:.2f})"
                risk_level = 'high'
            else:
                # Yahoo Finance ยังเชื่อถือได้ แต่ confidence ต่ำ
                confidence = max(0.4, base_confidence - 0.2)
                is_valid = True
                reason = f"Yahoo Finance sentiment ไม่ค่อยสอดคล้องกับแรงซื้อ/ขาย ({alignment_score:.2f})"
                risk_level = 'medium'
        else:
            # ไม่สอดคล้องเลย
            if source == 'reddit':
                confidence = 0.1
                is_valid = False
                reason = f"❌ Reddit sentiment ไม่สอดคล้องเลย - น่าจะเป็น bot/manipulation ({alignment_score:.2f})"
                risk_level = 'high'
            else:
                confidence = 0.3
                is_valid = True  # Yahoo Finance ยังแสดง แต่ confidence ต่ำมาก
                reason = f"⚠️ Yahoo Finance sentiment ไม่สอดคล้องเลย ({alignment_score:.2f})"
                risk_level = 'high'
        
        return {
            'is_valid': is_valid,
            'confidence': confidence,
            'alignment_score': alignment_score,
            'reason': reason,
            'pressure_data': pressure_data,
            'risk_level': risk_level,
            'sentiment_pressure': sentiment_pressure,
            'actual_pressure': actual_pressure,
            'pressure_diff': pressure_diff,
            'source': source,
            'validated_at': datetime.utcnow().isoformat()
        }
    
    def validate_multiple_sources(self, 
                                  yahoo_sentiment: Optional[float],
                                  reddit_sentiment: Optional[float],
                                  stock_info: Dict) -> Dict:
        """
        ตรวจสอบ sentiment จากหลายแหล่งพร้อมกัน
        
        Args:
            yahoo_sentiment: Sentiment จาก Yahoo Finance
            reddit_sentiment: Sentiment จาก Reddit
            stock_info: ข้อมูลหุ้น
        
        Returns:
            {
                'yahoo_validation': dict,
                'reddit_validation': dict,
                'overall_confidence': float,
                'recommendation': str
            }
        """
        pressure_data = self.calculate_buy_sell_pressure(stock_info)
        
        results = {
            'yahoo_validation': None,
            'reddit_validation': None,
            'pressure_data': pressure_data
        }
        
        # Validate Yahoo Finance
        if yahoo_sentiment is not None:
            results['yahoo_validation'] = self.validate_sentiment(
                yahoo_sentiment,
                'yahoo_finance',
                stock_info,
                pressure_data
            )
        
        # Validate Reddit
        if reddit_sentiment is not None:
            results['reddit_validation'] = self.validate_sentiment(
                reddit_sentiment,
                'reddit',
                stock_info,
                pressure_data
            )
        
        # คำนวณ overall confidence
        confidences = []
        if results['yahoo_validation']:
            confidences.append(results['yahoo_validation']['confidence'])
        if results['reddit_validation'] and results['reddit_validation']['is_valid']:
            # Reddit มีน้ำหนักน้อยกว่า
            confidences.append(results['reddit_validation']['confidence'] * 0.5)
        
        if confidences:
            results['overall_confidence'] = sum(confidences) / len(confidences) if confidences else 0.5
        else:
            results['overall_confidence'] = 0.0
        
        # สรุป recommendation
        if results['overall_confidence'] > 0.7:
            results['recommendation'] = 'high_confidence'
        elif results['overall_confidence'] > 0.4:
            results['recommendation'] = 'medium_confidence'
        else:
            results['recommendation'] = 'low_confidence'
        
        return results
