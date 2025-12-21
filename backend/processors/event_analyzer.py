"""
Event Analysis Module
วิเคราะห์เหตุการณ์สำคัญทางการเงินจากข่าว YouTube และแนะนำหุ้นที่เกี่ยวข้อง
"""
import re
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from processors.sentiment_analyzer import SentimentAnalyzer

class EventAnalyzer:
    def __init__(self):
        self.sentiment_analyzer = SentimentAnalyzer()
        
        # กำหนดเหตุการณ์สำคัญและหุ้นที่เกี่ยวข้อง
        self.event_stock_mapping = {
            # Federal Reserve / Interest Rates
            'fed_rate': {
                'keywords': ['federal reserve', 'fed', 'interest rate', 'rate hike', 'rate cut', 'monetary policy', 
                            'jerome powell', 'fomc', 'federal funds rate'],
                'affected_stocks': {
                    'positive': ['JPM', 'BAC', 'WFC', 'C', 'GS', 'MS'],  # Banks benefit from higher rates
                    'negative': ['XLF', 'SPY', 'QQQ'],  # Market indices may drop
                    'sectors': ['financial', 'banking']
                },
                'event_type': 'monetary_policy'
            },
            
            # Tax Policy
            'tax_policy': {
                'keywords': ['tax', 'taxation', 'tax cut', 'tax hike', 'corporate tax', 'capital gains tax', 
                            'tax reform', 'irs'],
                'affected_stocks': {
                    'positive': ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META'],  # Tech companies benefit from tax cuts
                    'negative': ['SPY'],  # Market may react negatively to tax hikes
                    'sectors': ['technology', 'consumer']
                },
                'event_type': 'fiscal_policy'
            },
            
            # Trump / Political Events
            'trump_news': {
                'keywords': ['trump', 'donald trump', 'president trump', 'trump administration', 'trump policy',
                           'trump trade', 'trump tariff'],
                'affected_stocks': {
                    'positive': ['XOM', 'CVX', 'SLB'],  # Energy sector
                    'negative': ['BABA', 'JD', 'PDD'],  # Chinese stocks
                    'sectors': ['energy', 'defense']
                },
                'event_type': 'political'
            },
            
            # Trade War / Tariffs
            'trade_war': {
                'keywords': ['trade war', 'tariff', 'china trade', 'trade dispute', 'trade agreement', 
                            'us china trade', 'import export'],
                'affected_stocks': {
                    'positive': ['CAT', 'DE', 'BA'],  # US manufacturing
                    'negative': ['BABA', 'JD', 'TSM', 'AAPL'],  # Companies with China exposure
                    'sectors': ['manufacturing', 'technology']
                },
                'event_type': 'trade_policy'
            },
            
            # Inflation / CPI
            'inflation': {
                'keywords': ['inflation', 'cpi', 'consumer price index', 'price increase', 'inflation rate',
                            'hyperinflation', 'deflation'],
                'affected_stocks': {
                    'positive': ['GLD', 'SLV', 'XLE'],  # Gold, commodities
                    'negative': ['T', 'TLT'],  # Bonds
                    'sectors': ['commodities', 'energy']
                },
                'event_type': 'economic_indicator'
            },
            
            # Employment / Jobs Report
            'jobs_report': {
                'keywords': ['jobs report', 'unemployment', 'non-farm payroll', 'employment', 'job market',
                            'labor market', 'wage growth'],
                'affected_stocks': {
                    'positive': ['SPY', 'QQQ', 'DIA'],  # Strong jobs = strong market
                    'negative': ['TLT'],  # Bonds may drop
                    'sectors': ['consumer', 'retail']
                },
                'event_type': 'economic_indicator'
            },
            
            # Earnings Season
            'earnings': {
                'keywords': ['earnings', 'earnings report', 'quarterly earnings', 'q1', 'q2', 'q3', 'q4',
                            'beat expectations', 'miss expectations', 'guidance'],
                'affected_stocks': {
                    'positive': ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META'],  # Tech earnings
                    'negative': [],
                    'sectors': ['technology', 'finance']
                },
                'event_type': 'corporate'
            },
            
            # Oil / Energy
            'oil_energy': {
                'keywords': ['oil price', 'crude oil', 'energy', 'opec', 'gas price', 'petroleum',
                            'energy crisis', 'oil production'],
                'affected_stocks': {
                    'positive': ['XOM', 'CVX', 'SLB', 'XLE'],  # Energy stocks
                    'negative': ['UAL', 'DAL', 'AAL'],  # Airlines
                    'sectors': ['energy', 'transportation']
                },
                'event_type': 'commodity'
            },
            
            # Tech Regulation
            'tech_regulation': {
                'keywords': ['tech regulation', 'antitrust', 'big tech', 'tech companies', 'regulation',
                            'fcc', 'ftc', 'sec tech'],
                'affected_stocks': {
                    'positive': [],
                    'negative': ['AAPL', 'GOOGL', 'META', 'AMZN', 'MSFT'],  # Big tech may be regulated
                    'sectors': ['technology']
                },
                'event_type': 'regulatory'
            },
            
            # Global Economy
            'global_economy': {
                'keywords': ['global economy', 'world economy', 'international trade', 'gdp', 'economic growth',
                            'recession', 'economic crisis', 'world market'],
                'affected_stocks': {
                    'positive': ['SPY', 'QQQ', 'DIA'],  # Broad market
                    'negative': [],
                    'sectors': ['all']
                },
                'event_type': 'macro_economic'
            }
        }
    
    def detect_events(self, text: str) -> List[Dict]:
        """
        ตรวจจับเหตุการณ์สำคัญจากข้อความ
        
        Args:
            text: ข้อความที่ต้องการวิเคราะห์
            
        Returns:
            List of detected events with confidence scores
        """
        text_lower = text.lower()
        detected_events = []
        
        for event_id, event_config in self.event_stock_mapping.items():
            keywords = event_config['keywords']
            matches = sum(1 for keyword in keywords if keyword in text_lower)
            
            if matches > 0:
                # คำนวณ confidence score
                confidence = min(matches / len(keywords) * 2, 1.0)  # Normalize to 0-1
                
                detected_events.append({
                    'event_id': event_id,
                    'event_type': event_config['event_type'],
                    'confidence': confidence,
                    'matched_keywords': [kw for kw in keywords if kw in text_lower],
                    'affected_stocks': event_config['affected_stocks']
                })
        
        # เรียงตาม confidence
        detected_events.sort(key=lambda x: x['confidence'], reverse=True)
        return detected_events
    
    def analyze_video(self, video: Dict, trending_tickers: List[Dict] = None) -> Dict:
        """
        วิเคราะห์วิดีโอ YouTube เพื่อหาเหตุการณ์และแนะนำหุ้น
        
        Args:
            video: ข้อมูลวิดีโอจาก YouTube API
            trending_tickers: List of trending tickers with sentiment (optional)
            
        Returns:
            Analysis result with events and stock recommendations
        """
        title = video.get('title', '')
        description = video.get('description', '')
        full_text = f"{title} {description}"
        
        # วิเคราะห์ sentiment
        sentiment = self.sentiment_analyzer.analyze(full_text)
        
        # ตรวจจับเหตุการณ์
        events = self.detect_events(full_text)
        
        # แนะนำหุ้นตามเหตุการณ์ + sentiment จาก trending tickers
        recommended_stocks = self.get_stock_recommendations(events, sentiment, trending_tickers)
        
        return {
            'video_id': video.get('id'),
            'title': title,
            'url': video.get('url'),
            'channel': video.get('channelTitle'),
            'published_at': video.get('publishedAt'),
            'sentiment': sentiment,
            'events': events,
            'recommended_stocks': recommended_stocks,
            'analysis_date': datetime.utcnow().isoformat()
        }
    
    def get_stock_recommendations(self, events: List[Dict], sentiment: Dict, trending_tickers: List[Dict] = None) -> Dict:
        """
        แนะนำหุ้นตามเหตุการณ์ที่ตรวจจับได้ + sentiment จาก trending tickers
        
        Args:
            events: List of detected events
            sentiment: Sentiment analysis result
            trending_tickers: List of trending tickers with sentiment (optional)
            
        Returns:
            Dictionary with buy/sell recommendations
        """
        buy_stocks = {}
        sell_stocks = {}
        watch_stocks = {}
        
        sentiment_score = sentiment.get('compound', 0)
        
        # 1. แนะนำหุ้นจาก event mapping (hardcoded rules)
        for event in events:
            event_id = event['event_id']
            confidence = event['confidence']
            affected = event['affected_stocks']
            
            # ถ้า sentiment เป็นบวก แนะนำหุ้น positive
            if sentiment_score > 0.1:
                for stock in affected.get('positive', []):
                    if stock not in buy_stocks:
                        buy_stocks[stock] = {
                            'reason': event_id,
                            'confidence': confidence,
                            'sentiment_score': sentiment_score,
                            'source': 'event_mapping'  # ระบุว่ามาจาก event mapping
                        }
                    else:
                        # เพิ่ม confidence ถ้ามีเหตุการณ์หลายเหตุการณ์
                        buy_stocks[stock]['confidence'] = min(
                            buy_stocks[stock]['confidence'] + confidence * 0.3, 1.0
                        )
                        buy_stocks[stock]['reasons'] = buy_stocks[stock].get('reasons', [event_id])
                        if event_id not in buy_stocks[stock]['reasons']:
                            buy_stocks[stock]['reasons'].append(event_id)
                
                # หุ้น negative อาจจะต้องระวัง
                for stock in affected.get('negative', []):
                    if stock not in sell_stocks:
                        sell_stocks[stock] = {
                            'reason': event_id,
                            'confidence': confidence,
                            'sentiment_score': sentiment_score,
                            'source': 'event_mapping'
                        }
            
            # ถ้า sentiment เป็นลบ แนะนำหุ้น negative (อาจจะ short หรือหลีกเลี่ยง)
            elif sentiment_score < -0.1:
                for stock in affected.get('negative', []):
                    if stock not in sell_stocks:
                        sell_stocks[stock] = {
                            'reason': event_id,
                            'confidence': confidence,
                            'sentiment_score': sentiment_score,
                            'source': 'event_mapping'
                        }
                
                # หุ้น positive อาจจะยังดี
                for stock in affected.get('positive', []):
                    if stock not in watch_stocks:
                        watch_stocks[stock] = {
                            'reason': event_id,
                            'confidence': confidence,
                            'sentiment_score': sentiment_score,
                            'note': 'Monitor - negative sentiment but historically positive',
                            'source': 'event_mapping'
                        }
        
        # 2. เพิ่มหุ้นจาก trending tickers ที่มี sentiment สูง (ถ้ามี)
        if trending_tickers:
            # เรียงตาม sentiment (สูงสุดก่อน)
            sorted_tickers = sorted(
                trending_tickers,
                key=lambda x: abs(x.get('avgSentiment', 0)),
                reverse=True
            )
            
            # หุ้นที่มี sentiment บวกสูง (> 0.3) → แนะนำซื้อ
            for ticker_data in sorted_tickers:
                ticker = ticker_data.get('ticker') or ticker_data.get('word', '')
                ticker_sentiment = ticker_data.get('avgSentiment', 0)
                mentions = ticker_data.get('count', 0) or ticker_data.get('mentions', 0)
                
                if not ticker or len(ticker) > 5:  # ข้าม ticker ที่ไม่ถูกต้อง
                    continue
                
                # ถ้า sentiment บวกสูง (> 0.3) และมี mentions มาก (> 5)
                if ticker_sentiment > 0.3 and mentions > 5:
                    if ticker not in buy_stocks:
                        buy_stocks[ticker] = {
                            'reason': 'high_positive_sentiment',
                            'confidence': min(0.7, (ticker_sentiment / 5.0) * 0.7 + (mentions / 100) * 0.3),
                            'sentiment_score': ticker_sentiment,
                            'mentions': mentions,
                            'source': 'trending_sentiment'  # ระบุว่ามาจาก sentiment จริง
                        }
                    else:
                        # ถ้ามีอยู่แล้ว (จาก event mapping) ให้เพิ่ม confidence
                        buy_stocks[ticker]['confidence'] = min(
                            buy_stocks[ticker]['confidence'] + 0.2, 1.0
                        )
                        buy_stocks[ticker]['source'] = 'both'  # มาจากทั้ง event และ sentiment
                        buy_stocks[ticker]['mentions'] = mentions
                
                # ถ้า sentiment ลบสูง (< -0.3) และมี mentions มาก (> 5)
                elif ticker_sentiment < -0.3 and mentions > 5:
                    if ticker not in sell_stocks:
                        sell_stocks[ticker] = {
                            'reason': 'high_negative_sentiment',
                            'confidence': min(0.7, (abs(ticker_sentiment) / 5.0) * 0.7 + (mentions / 100) * 0.3),
                            'sentiment_score': ticker_sentiment,
                            'mentions': mentions,
                            'source': 'trending_sentiment'
                        }
                    else:
                        sell_stocks[ticker]['confidence'] = min(
                            sell_stocks[ticker]['confidence'] + 0.2, 1.0
                        )
                        sell_stocks[ticker]['source'] = 'both'
                        sell_stocks[ticker]['mentions'] = mentions
        
        return {
            'buy': buy_stocks,
            'sell': sell_stocks,
            'watch': watch_stocks,
            'overall_sentiment': sentiment_score,
            'event_count': len(events),
            'trending_tickers_used': len(trending_tickers) if trending_tickers else 0
        }
    
    def analyze_multiple_videos(self, videos: List[Dict], trending_tickers: List[Dict] = None) -> Dict:
        """
        วิเคราะห์หลายวิดีโอพร้อมกันและสรุปผล
        
        Args:
            videos: List of video dictionaries
            trending_tickers: List of trending tickers with sentiment (optional)
            
        Returns:
            Aggregated analysis with overall recommendations
        """
        all_analyses = []
        all_buy_stocks = {}
        all_sell_stocks = {}
        all_watch_stocks = {}
        
        for video in videos:
            analysis = self.analyze_video(video, trending_tickers)
            all_analyses.append(analysis)
            
            # รวม stock recommendations
            recs = analysis['recommended_stocks']
            
            # รวม buy stocks
            for stock, info in recs['buy'].items():
                if stock not in all_buy_stocks:
                    all_buy_stocks[stock] = {
                        'count': 1,
                        'total_confidence': info['confidence'],
                        'reasons': [info.get('reason', 'unknown')],
                        'avg_sentiment': info['sentiment_score'],
                        'sources': [info.get('source', 'unknown')]
                    }
                else:
                    all_buy_stocks[stock]['count'] += 1
                    all_buy_stocks[stock]['total_confidence'] += info['confidence']
                    if info.get('reason') not in all_buy_stocks[stock]['reasons']:
                        all_buy_stocks[stock]['reasons'].append(info.get('reason', 'unknown'))
                    all_buy_stocks[stock]['avg_sentiment'] = (
                        all_buy_stocks[stock]['avg_sentiment'] + info['sentiment_score']
                    ) / 2
                    if info.get('source') not in all_buy_stocks[stock]['sources']:
                        all_buy_stocks[stock]['sources'].append(info.get('source', 'unknown'))
            
            # รวม sell stocks
            for stock, info in recs['sell'].items():
                if stock not in all_sell_stocks:
                    all_sell_stocks[stock] = {
                        'count': 1,
                        'total_confidence': info['confidence'],
                        'reasons': [info.get('reason', 'unknown')],
                        'avg_sentiment': info['sentiment_score'],
                        'sources': [info.get('source', 'unknown')]
                    }
                else:
                    all_sell_stocks[stock]['count'] += 1
                    all_sell_stocks[stock]['total_confidence'] += info['confidence']
                    if info.get('reason') not in all_sell_stocks[stock]['reasons']:
                        all_sell_stocks[stock]['reasons'].append(info.get('reason', 'unknown'))
                    all_sell_stocks[stock]['avg_sentiment'] = (
                        all_sell_stocks[stock]['avg_sentiment'] + info['sentiment_score']
                    ) / 2
                    if info.get('source') not in all_sell_stocks[stock]['sources']:
                        all_sell_stocks[stock]['sources'].append(info.get('source', 'unknown'))
        
        # คำนวณ final scores
        final_buy = {}
        for stock, data in all_buy_stocks.items():
            final_buy[stock] = {
                'confidence': min(data['total_confidence'] / data['count'], 1.0),
                'mention_count': data['count'],
                'reasons': list(set(data['reasons'])),
                'avg_sentiment': data['avg_sentiment'],
                'score': (data['total_confidence'] / data['count']) * data['count'] * (1 + abs(data['avg_sentiment']))
            }
        
        final_sell = {}
        for stock, data in all_sell_stocks.items():
            final_sell[stock] = {
                'confidence': min(data['total_confidence'] / data['count'], 1.0),
                'mention_count': data['count'],
                'reasons': list(set(data['reasons'])),
                'avg_sentiment': data['avg_sentiment'],
                'score': (data['total_confidence'] / data['count']) * data['count'] * (1 + abs(data['avg_sentiment']))
            }
        
        # เรียงตาม score
        sorted_buy = sorted(final_buy.items(), key=lambda x: x[1]['score'], reverse=True)
        sorted_sell = sorted(final_sell.items(), key=lambda x: x[1]['score'], reverse=True)
        
        return {
            'total_videos': len(videos),
            'analyses': all_analyses,
            'top_buy_recommendations': dict(sorted_buy[:20]),  # Top 20
            'top_sell_recommendations': dict(sorted_sell[:20]),  # Top 20
            'summary': {
                'total_events_detected': sum(len(a['events']) for a in all_analyses),
                'unique_events': len(set(e['event_id'] for a in all_analyses for e in a['events'])),
                'avg_sentiment': sum(a['sentiment']['compound'] for a in all_analyses) / len(all_analyses) if all_analyses else 0
            }
        }

