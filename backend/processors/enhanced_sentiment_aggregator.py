"""
Enhanced Sentiment Aggregator
รวม sentiment จากหลาย sources พร้อม confidence และ market confirmation
"""
from typing import Dict, List, Optional
from datetime import datetime
from processors.sentiment_analyzer import SentimentAnalyzer
from processors.market_confirmation import MarketConfirmation
from database.db_config import db

class EnhancedSentimentAggregator:
    """
    รวม sentiment จากหลาย sources:
    - Yahoo Finance News
    - Reddit Posts
    - Market Confirmation
    
    Source Weight:
    - SEC/Filing: 1.0
    - Reuters: 0.9
    - Yahoo Finance: 0.7
    - Reddit (score สูง): 0.5
    - Reddit (score ต่ำ): 0.2
    """
    
    def __init__(self):
        self.sentiment_analyzer = SentimentAnalyzer()
        self.market_confirmation = MarketConfirmation()
        
        # Source weights
        self.source_weights = {
            'sec': 1.0,
            'filing': 1.0,
            'reuters': 0.9,
            'yahoo_finance': 0.7,
            'reddit_high': 0.5,  # Reddit score > 10
            'reddit_low': 0.2    # Reddit score <= 10
        }
    
    def get_source_weight(self, source: str, score: Optional[int] = None) -> float:
        """
        ได้ source weight
        
        Args:
            source: Source name
            score: Post score (สำหรับ Reddit)
            
        Returns:
            Weight value
        """
        source_lower = source.lower()
        
        if 'sec' in source_lower or 'filing' in source_lower:
            return self.source_weights['sec']
        elif 'reuters' in source_lower:
            return self.source_weights['reuters']
        elif 'yahoo' in source_lower or 'finance' in source_lower:
            return self.source_weights['yahoo_finance']
        elif 'reddit' in source_lower:
            if score and score > 10:
                return self.source_weights['reddit_high']
            else:
                return self.source_weights['reddit_low']
        
        return 0.5  # Default weight
    
    def aggregate_sentiment(
        self,
        news_items: List[Dict],
        reddit_items: List[Dict],
        stock_info: Dict,
        previous_sentiment: Optional[Dict] = None
    ) -> Dict:
        """
        รวม sentiment จากหลาย sources พร้อม market confirmation
        
        Args:
            news_items: List of news articles
            reddit_items: List of Reddit posts
            stock_info: Stock info (price, volume, bid/ask)
            previous_sentiment: Previous sentiment (for velocity calculation)
            
        Returns:
            Enhanced sentiment dictionary
        """
        # 1. คำนวณ raw sentiment จาก news
        news_sentiments = []
        news_weights = []
        news_count = 0
        
        for news in news_items:
            sentiment = news.get('sentiment', {})
            if sentiment and 'compound' in sentiment:
                source = news.get('source', 'yahoo_finance')
                weight = self.get_source_weight(source)
                news_sentiments.append(sentiment['compound'])
                news_weights.append(weight)
                news_count += 1
        
        # 2. คำนวณ raw sentiment จาก Reddit
        reddit_sentiments = []
        reddit_weights = []
        reddit_count = 0
        
        for post in reddit_items:
            sentiment = post.get('sentiment', {})
            if sentiment and 'compound' in sentiment:
                score = post.get('score', 0)
                weight = self.get_source_weight('reddit', score)
                reddit_sentiments.append(sentiment['compound'])
                reddit_weights.append(weight)
                reddit_count += 1
        
        # 3. คำนวณ weighted average
        all_sentiments = news_sentiments + reddit_sentiments
        all_weights = news_weights + reddit_weights
        
        if not all_sentiments:
            raw_sentiment = 0.0
        else:
            weighted_sum = sum(s * w for s, w in zip(all_sentiments, all_weights))
            weight_sum = sum(all_weights)
            raw_sentiment = weighted_sum / weight_sum if weight_sum > 0 else 0.0
        
        # 4. คำนวณ sentiment velocity (การเปลี่ยนแปลง)
        sentiment_velocity = 0.0
        if previous_sentiment:
            prev_raw = previous_sentiment.get('raw_sentiment', 0.0)
            sentiment_velocity = raw_sentiment - prev_raw
        
        # 5. Market Confirmation
        price_change = stock_info.get('changePercent', 0.0)
        volume = stock_info.get('volume', 0)
        average_volume = stock_info.get('averageVolume', volume)
        volume_change = ((volume - average_volume) / average_volume * 100) if average_volume > 0 else 0
        
        bid = stock_info.get('bid', 0)
        ask = stock_info.get('ask', 0)
        bid_ask_imbalance = None
        if bid > 0 and ask > 0:
            bid_ask_imbalance = (ask - bid) / bid
        
        confirmation_result = self.market_confirmation.calculate_confirmation_score(
            sentiment=raw_sentiment,
            price_change=price_change,
            volume_change=volume_change,
            bid_ask_imbalance=bid_ask_imbalance,
            average_volume=average_volume,
            current_volume=volume
        )
        
        # 6. สร้าง enhanced sentiment
        enhanced_sentiment = {
            "raw_sentiment": raw_sentiment,
            "news_count": news_count,
            "reddit_count": reddit_count,
            "sentiment_velocity": sentiment_velocity,
            "market_confirmation": confirmation_result["market_confirmation"],
            "confidence": confirmation_result["confidence"],
            "status": confirmation_result["status"],
            "price_alignment": confirmation_result["price_alignment"],
            "volume_confirmation": confirmation_result["volume_confirmation"],
            "bid_ask_confirmation": confirmation_result["bid_ask_confirmation"],
            "velocity": confirmation_result["velocity"],
            "fetchedAt": datetime.utcnow().isoformat()
        }
        
        return enhanced_sentiment
