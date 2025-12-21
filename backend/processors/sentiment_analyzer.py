"""
Sentiment Analysis Module
Uses VADER (Valence Aware Dictionary and sEntiment Reasoner) for financial sentiment analysis
"""
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from datetime import datetime, timedelta
import re
import math

class SentimentAnalyzer:
    def __init__(self):
        self.analyzer = SentimentIntensityAnalyzer()
        # Financial-specific words that might affect sentiment
        # เพิ่ม boosters เพื่อให้ sentiment สามารถเกิน ±1.0 ได้ (รองรับ -500% ถึง +500%)
        self.financial_boosters = {
            'bullish': 1.5,      # เพิ่มจาก 0.3
            'bearish': -1.5,     # เพิ่มจาก -0.3
            'rally': 1.0,        # เพิ่มจาก 0.2
            'crash': -2.0,       # เพิ่มจาก -0.4
            'surge': 1.0,        # เพิ่มจาก 0.2
            'plunge': -1.5,      # เพิ่มจาก -0.3
            'soar': 1.0,         # เพิ่มจาก 0.2
            'tumble': -1.5,      # เพิ่มจาก -0.3
            'breakout': 0.8,     # เพิ่มจาก 0.15
            'breakdown': -1.0,   # เพิ่มจาก -0.2
            'moon': 2.0,         # เพิ่มใหม่
            'rocket': 2.0,       # เพิ่มใหม่
            'dump': -2.0,        # เพิ่มใหม่
            'pump': 1.5,         # เพิ่มใหม่
            'yolo': 1.0,         # เพิ่มใหม่
            'hodl': 0.8,         # เพิ่มใหม่
            'to the moon': 2.5,  # เพิ่มใหม่
            'market crash': -3.0, # เพิ่มใหม่
            'bull market': 1.5,  # เพิ่มใหม่
            'bear market': -1.5  # เพิ่มใหม่
        }
    
    def analyze(self, text):
        """
        Analyze sentiment of text
        Returns: {
            'compound': float,  # Overall sentiment score (-5.0 to 5.0, supports -500% to +500%)
            'positive': float,
            'neutral': float,
            'negative': float,
            'label': str  # 'positive', 'negative', or 'neutral'
        }
        """
        if not text or not isinstance(text, str):
            return {
                'compound': 0.0,
                'positive': 0.0,
                'neutral': 1.0,
                'negative': 0.0,
                'label': 'neutral'
            }
        
        # Clean text
        text = re.sub(r'http\S+', '', text)  # Remove URLs
        text = re.sub(r'[^\w\s]', ' ', text)  # Remove special chars
        
        # Get base sentiment
        scores = self.analyzer.polarity_scores(text)
        
        # Boost for financial terms
        # อนุญาตให้ sentiment เกิน ±1.0 เพื่อรองรับ -500% ถึง +500%
        text_lower = text.lower()
        base_compound = scores['compound']
        
        for term, boost in self.financial_boosters.items():
            if term in text_lower:
                base_compound += boost
        
        # จำกัดที่ -5.0 ถึง +5.0 (รองรับ -500% ถึง +500%)
        scores['compound'] = max(-5.0, min(5.0, base_compound))
        
        # Determine label
        if scores['compound'] >= 0.05:
            label = 'positive'
        elif scores['compound'] <= -0.05:
            label = 'negative'
        else:
            label = 'neutral'
        
        scores['label'] = label
        return scores
    
    def analyze_batch(self, texts, use_time_weighting=False, items_with_dates=None, max_age_hours=168, recent_positive_override=True):
        """
        Analyze multiple texts and return aggregated sentiment
        
        Args:
            texts: List of text strings to analyze
            use_time_weighting: If True, apply time-based exponential decay weighting
            items_with_dates: List of dicts with 'text' and 'publishedAt' keys (required if use_time_weighting=True)
            max_age_hours: Maximum age in hours before excluding news (default: 168 = 7 days)
            recent_positive_override: If True, recent positive news reduces impact of older negative news (default: True)
        
        Returns:
            Aggregated sentiment dict with time-weighted scores if use_time_weighting=True
        """
        if not texts:
            return None
        
        # If time weighting is requested, use items_with_dates
        if use_time_weighting and items_with_dates:
            return self._analyze_batch_time_weighted(items_with_dates, max_age_hours=max_age_hours, recent_positive_override=recent_positive_override)
        
        # Original simple averaging (backward compatible)
        results = []
        for text in texts:
            try:
                result = self.analyze(text)
                if result and isinstance(result, dict):
                    results.append(result)
            except Exception as e:
                print(f"⚠️ Error analyzing text: {e}")
                continue
        
        if not results:
            return None
        
        # Aggregate - use .get() to safely access keys
        avg_compound = sum(r.get('compound', 0) for r in results) / len(results)
        avg_positive = sum(r.get('positive', 0) for r in results) / len(results)
        avg_neutral = sum(r.get('neutral', 0) for r in results) / len(results)
        avg_negative = sum(r.get('negative', 0) for r in results) / len(results)
        
        # Count labels
        label_counts = {'positive': 0, 'neutral': 0, 'negative': 0}
        for r in results:
            label = r.get('label', 'neutral')
            if label in label_counts:
                label_counts[label] += 1
        
        return {
            'compound': avg_compound,
            'positive': avg_positive,
            'neutral': avg_neutral,
            'negative': avg_negative,
            'label': 'positive' if avg_compound >= 0.05 else ('negative' if avg_compound <= -0.05 else 'neutral'),
            'counts': label_counts,
            'total': len(results)
        }
    
    def _analyze_batch_time_weighted(self, items_with_dates, half_life_hours=24, max_age_hours=168, recent_positive_override=True):
        """
        Analyze batch with time-based exponential decay weighting
        
        Args:
            items_with_dates: List of dicts with 'text' and 'publishedAt' keys
            half_life_hours: Hours for sentiment to decay to 50% (default: 24 hours)
                              ข่าวที่เก่ากว่า 24 ชั่วโมงจะมีน้ำหนัก 50%
                              ข่าวที่เก่ากว่า 48 ชั่วโมงจะมีน้ำหนัก 25%
                              ข่าวที่เก่ากว่า 72 ชั่วโมงจะมีน้ำหนัก 12.5%
            max_age_hours: Maximum age in hours before excluding news (default: 168 = 7 days)
                            ข่าวที่เก่ากว่า 7 วันจะถูกตัดออกทั้งหมด
            recent_positive_override: If True, recent positive news reduces impact of older negative news
                                      ถ้ามีข่าวบวกล่าสุด (24 ชม.) จะลดน้ำหนักข่าวลบเก่า (3+ วัน)
        
        Returns:
            Time-weighted aggregated sentiment
        """
        if not items_with_dates:
            return None
        
        now = datetime.utcnow()
        weighted_results = []
        total_weight = 0
        
        # ตรวจสอบว่ามีข่าวบวกล่าสุด (ภายใน 24 ชั่วโมง) หรือไม่
        recent_positive_news = False
        if recent_positive_override:
            for item in items_with_dates:
                published_at = item.get('publishedAt')
                if published_at:
                    try:
                        if isinstance(published_at, str):
                            if 'T' in published_at:
                                published_dt = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                            else:
                                try:
                                    published_dt = datetime.fromtimestamp(float(published_at))
                                except:
                                    continue
                        elif isinstance(published_at, (int, float)):
                            published_dt = datetime.fromtimestamp(published_at)
                        else:
                            continue
                        
                        age_hours = (now - published_dt.replace(tzinfo=None)).total_seconds() / 3600
                        if 0 <= age_hours <= 24:  # ข่าวล่าสุด 24 ชั่วโมง
                            text = item.get('text', '')
                            if text:
                                result = self.analyze(text)
                                if result and result.get('compound', 0) > 0.3:  # ข่าวบวกที่ชัดเจน
                                    recent_positive_news = True
                                    break
                    except:
                        continue
        
        for item in items_with_dates:
            text = item.get('text', '')
            if not text:
                continue
            
            # Parse publishedAt date
            published_at = item.get('publishedAt')
            if not published_at:
                # ถ้าไม่มีวันที่ ให้ใช้เวลาปัจจุบัน (น้ำหนักเต็ม)
                age_hours = 0
            else:
                try:
                    # Handle different date formats
                    if isinstance(published_at, str):
                        # Try ISO format first
                        if 'T' in published_at:
                            published_dt = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                        else:
                            # Try timestamp
                            try:
                                published_dt = datetime.fromtimestamp(float(published_at))
                            except:
                                published_dt = now
                    elif isinstance(published_at, (int, float)):
                        # Timestamp
                        published_dt = datetime.fromtimestamp(published_at)
                    else:
                        published_dt = now
                    
                    # Calculate age in hours
                    age_hours = (now - published_dt.replace(tzinfo=None)).total_seconds() / 3600
                    if age_hours < 0:
                        age_hours = 0  # Future dates = treat as now
                except Exception as e:
                    print(f"⚠️ Error parsing date {published_at}: {e}")
                    age_hours = 0
            
            # ตัดข่าวที่เก่ากว่า max_age_hours
            if age_hours > max_age_hours:
                continue  # ข้ามข่าวเก่าเกินไป
            
            # Calculate exponential decay weight
            # weight = 2^(-age_hours / half_life_hours)
            # ข่าวใหม่ (0 ชั่วโมง) = weight 1.0
            # ข่าวเก่า 24 ชั่วโมง = weight 0.5
            # ข่าวเก่า 48 ชั่วโมง = weight 0.25
            # ข่าวเก่า 72 ชั่วโมง = weight 0.125
            base_weight = math.pow(2, -age_hours / half_life_hours)
            
            # Analyze sentiment
            try:
                result = self.analyze(text)
                if result and isinstance(result, dict):
                    sentiment_compound = result.get('compound', 0)
                    
                    # ถ้ามีข่าวบวกล่าสุด และข่าวนี้เป็นข่าวลบเก่า (3+ วัน) ให้ลดน้ำหนักลงมาก
                    if recent_positive_override and recent_positive_news:
                        if age_hours >= 72 and sentiment_compound < -0.1:  # ข่าวลบเก่า 3+ วัน
                            # ลดน้ำหนักลงเหลือ 10% ของเดิม
                            weight = base_weight * 0.1
                        elif age_hours >= 48 and sentiment_compound < -0.1:  # ข่าวลบเก่า 2+ วัน
                            # ลดน้ำหนักลงเหลือ 30% ของเดิม
                            weight = base_weight * 0.3
                        else:
                            weight = base_weight
                    else:
                        weight = base_weight
                    
                    weighted_results.append({
                        'result': result,
                        'weight': weight,
                        'age_hours': age_hours
                    })
                    total_weight += weight
            except Exception as e:
                print(f"⚠️ Error analyzing text: {e}")
                continue
        
        if not weighted_results or total_weight == 0:
            return None
        
        # Calculate weighted averages
        weighted_compound = sum(r['result'].get('compound', 0) * r['weight'] for r in weighted_results) / total_weight
        weighted_positive = sum(r['result'].get('positive', 0) * r['weight'] for r in weighted_results) / total_weight
        weighted_neutral = sum(r['result'].get('neutral', 0) * r['weight'] for r in weighted_results) / total_weight
        weighted_negative = sum(r['result'].get('negative', 0) * r['weight'] for r in weighted_results) / total_weight
        
        # Count labels (weighted)
        label_counts = {'positive': 0, 'neutral': 0, 'negative': 0}
        for r in weighted_results:
            label = r['result'].get('label', 'neutral')
            if label in label_counts:
                label_counts[label] += r['weight']
        
        # Normalize label counts
        if total_weight > 0:
            for label in label_counts:
                label_counts[label] = label_counts[label] / total_weight * len(weighted_results)
        
        return {
            'compound': weighted_compound,
            'positive': weighted_positive,
            'neutral': weighted_neutral,
            'negative': weighted_negative,
            'label': 'positive' if weighted_compound >= 0.05 else ('negative' if weighted_compound <= -0.05 else 'neutral'),
            'counts': {k: int(round(v)) for k, v in label_counts.items()},
            'total': len(weighted_results),
            'time_weighted': True,
            'half_life_hours': half_life_hours,
            'max_age_hours': max_age_hours,
            'recent_positive_override': recent_positive_override,
            'avg_age_hours': sum(r['age_hours'] for r in weighted_results) / len(weighted_results) if weighted_results else 0
        }

