"""
Sentiment Analysis Module
Uses VADER (Valence Aware Dictionary and sEntiment Reasoner) for financial sentiment analysis
"""
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import re

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
    
    def analyze_batch(self, texts):
        """Analyze multiple texts and return aggregated sentiment"""
        if not texts:
            return None
        
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

