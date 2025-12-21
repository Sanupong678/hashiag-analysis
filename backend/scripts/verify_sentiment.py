"""
Script สำหรับตรวจสอบประสิทธิภาพของระบบ Sentiment Analysis
"""
import sys
import os
from pathlib import Path

# ตั้งค่า encoding สำหรับ Windows terminal
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# เพิ่ม path ของ backend เข้าไปใน sys.path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from database.db_config import db
from datetime import datetime, timedelta
from utils.post_normalizer import get_collection_name
from processors.sentiment_analyzer import SentimentAnalyzer

def verify_sentiment_accuracy(symbol: str):
    """
    ตรวจสอบความแม่นยำของ sentiment สำหรับหุ้น
    
    Args:
        symbol: Stock symbol (เช่น AAPL, TSLA)
    """
    symbol_upper = symbol.upper()
    
    print(f"\n{'='*70}")
    print(f"📊 Sentiment Verification for {symbol_upper}")
    print(f"{'='*70}")
    
    # 1. ตรวจสอบจำนวนข่าว
    collection = get_collection_name('yahoo')
    news_count = 0
    latest_news = None
    age_hours = None
    
    if db is not None and hasattr(db, collection) and getattr(db, collection) is not None:
        post_collection = getattr(db, collection)
        news_count = post_collection.count_documents({"symbol": symbol_upper})
        
        # 2. ตรวจสอบวันที่ข่าวล่าสุด
        if news_count > 0:
            latest_news = post_collection.find_one(
                {"symbol": symbol_upper},
                sort=[("publishedAt", -1), ("created_utc", -1), ("publish_date", -1)]
            )
            
            if latest_news:
                # หาวันที่ข่าวล่าสุด
                latest_date = None
                for date_field in ['publishedAt', 'created_utc', 'publish_date', 'providerPublishTime']:
                    if date_field in latest_news and latest_news[date_field]:
                        try:
                            date_value = latest_news[date_field]
                            if isinstance(date_value, str):
                                if 'T' in date_value:
                                    latest_date = datetime.fromisoformat(date_value.replace('Z', '+00:00'))
                                else:
                                    try:
                                        latest_date = datetime.fromtimestamp(float(date_value))
                                    except:
                                        continue
                            elif isinstance(date_value, (int, float)):
                                latest_date = datetime.fromtimestamp(date_value)
                            
                            if latest_date:
                                if isinstance(latest_date, str):
                                    latest_date = datetime.fromisoformat(latest_date.replace('Z', '+00:00'))
                                break
                        except:
                            continue
                
                if latest_date:
                    if isinstance(latest_date, str):
                        latest_date = datetime.fromisoformat(latest_date.replace('Z', '+00:00'))
                    age_hours = (datetime.utcnow() - latest_date.replace(tzinfo=None)).total_seconds() / 3600
    
    # 3. ตรวจสอบ sentiment จาก database
    stock_data = None
    overall = {}
    news_sentiment = {}
    reddit_sentiment = {}
    
    if db is not None and hasattr(db, 'stock_data') and db.stock_data is not None:
        stock_data = db.stock_data.find_one({"symbol": symbol_upper})
        
        if stock_data:
            overall = stock_data.get('overallSentiment', {})
            news_sentiment = stock_data.get('newsData', {}).get('sentiment', {})
            reddit_sentiment = stock_data.get('redditData', {}).get('sentiment', {})
    
    # 4. ตรวจสอบ time-weighted
    is_time_weighted = news_sentiment.get('time_weighted', False)
    avg_age = news_sentiment.get('avg_age_hours', 0)
    max_age = news_sentiment.get('max_age_hours', 168)
    recent_override = news_sentiment.get('recent_positive_override', False)
    
    # 5. ตรวจสอบราคาหุ้น
    price_info = {}
    if stock_data:
        stock_info = stock_data.get('stockInfo', {})
        if stock_info:
            price_info = {
                'current_price': stock_info.get('currentPrice', 0),
                'change': stock_info.get('change', 0),
                'change_percent': stock_info.get('changePercent', 0)
            }
    
    # 6. แสดงผล
    print(f"\n📰 News Information:")
    print(f"   Count: {news_count} articles")
    if age_hours is not None:
        print(f"   Latest News Age: {age_hours:.1f} hours ({age_hours/24:.1f} days)")
        if latest_news:
            print(f"   Latest Title: {latest_news.get('title', 'N/A')[:60]}...")
    else:
        print(f"   Latest News Age: N/A")
    
    print(f"\n🧠 Sentiment Analysis:")
    print(f"   Overall Sentiment: {overall.get('compound', 0):.3f} ({overall.get('label', 'N/A')})")
    print(f"   Confidence: {overall.get('confidence', 0):.2f}")
    
    if news_sentiment:
        print(f"\n   News Sentiment:")
        print(f"      Compound: {news_sentiment.get('compound', 0):.3f}")
        print(f"      Label: {news_sentiment.get('label', 'N/A')}")
        print(f"      Time-Weighted: {is_time_weighted}")
        if avg_age > 0:
            print(f"      Average Age: {avg_age:.1f} hours")
        if max_age:
            print(f"      Max Age: {max_age} hours (7 days)")
        if recent_override:
            print(f"      Recent Positive Override: ✅ Enabled")
    
    if reddit_sentiment:
        print(f"\n   Reddit Sentiment:")
        print(f"      Compound: {reddit_sentiment.get('compound', 0):.3f}")
        print(f"      Label: {reddit_sentiment.get('label', 'N/A')}")
    
    if price_info and price_info.get('current_price', 0) > 0:
        print(f"\n📈 Stock Price:")
        print(f"   Current Price: ${price_info['current_price']:.2f}")
        print(f"   Change: {price_info['change']:+.2f} ({price_info['change_percent']:+.2f}%)")
    
    # 7. ตรวจสอบปัญหา
    issues = []
    warnings = []
    
    if news_count == 0:
        issues.append("❌ ไม่มีข่าวใน database")
    elif news_count < 10:
        warnings.append(f"⚠️  มีข่าวน้อย ({news_count} ข่าว)")
    
    if age_hours and age_hours > 48:
        issues.append(f"❌ ข่าวเก่าเกินไป ({age_hours:.1f} ชั่วโมง / {age_hours/24:.1f} วัน)")
    elif age_hours and age_hours > 24:
        warnings.append(f"⚠️  ข่าวค่อนข้างเก่า ({age_hours:.1f} ชั่วโมง)")
    
    if not is_time_weighted and news_sentiment:
        warnings.append("⚠️  ไม่ได้ใช้ time-weighted sentiment")
    
    if not overall:
        issues.append("❌ ไม่มี overall sentiment")
    
    # ตรวจสอบความสอดคล้องระหว่าง sentiment กับราคา
    if price_info and overall:
        sentiment = overall.get('compound', 0)
        price_change = price_info.get('change_percent', 0)
        
        if sentiment > 0.1 and price_change < -2:
            warnings.append(f"⚠️  Sentiment บวก ({sentiment:.3f}) แต่ราคาตก ({price_change:.2f}%)")
        elif sentiment < -0.1 and price_change > 2:
            warnings.append(f"⚠️  Sentiment ลบ ({sentiment:.3f}) แต่ราคาขึ้น ({price_change:.2f}%)")
    
    # 8. สรุปผล
    if issues:
        print(f"\n❌ Issues Found:")
        for issue in issues:
            print(f"   {issue}")
    
    if warnings:
        print(f"\n⚠️  Warnings:")
        for warning in warnings:
            print(f"   {warning}")
    
    if not issues and not warnings:
        print(f"\n✅ All checks passed! System is working correctly.")
    
    # 9. แสดงตัวอย่างข่าวล่าสุด
    if latest_news and news_count > 0:
        print(f"\n📋 Sample Latest News:")
        sample_news = list(post_collection.find(
            {"symbol": symbol_upper}
        ).sort("publishedAt", -1).limit(3))
        
        analyzer = SentimentAnalyzer()
        for i, news in enumerate(sample_news, 1):
            text = f"{news.get('title', '')} {news.get('summary', '')}"
            sentiment = analyzer.analyze(text)
            pub_date = news.get('publishedAt', 'N/A')
            if isinstance(pub_date, (int, float)):
                pub_date = datetime.fromtimestamp(pub_date).isoformat()
            
            print(f"\n   {i}. {news.get('title', 'N/A')[:60]}...")
            print(f"      Date: {pub_date}")
            print(f"      Sentiment: {sentiment['compound']:.3f} ({sentiment['label']})")
    
    return {
        'symbol': symbol_upper,
        'news_count': news_count,
        'latest_age_hours': age_hours,
        'sentiment': overall.get('compound', 0),
        'sentiment_label': overall.get('label', 'N/A'),
        'is_time_weighted': is_time_weighted,
        'issues': issues,
        'warnings': warnings,
        'status': 'ok' if not issues else 'error'
    }

def verify_multiple_stocks(symbols: list):
    """ตรวจสอบหลายหุ้นพร้อมกัน"""
    results = []
    for symbol in symbols:
        try:
            result = verify_sentiment_accuracy(symbol)
            results.append(result)
        except Exception as e:
            print(f"\n❌ Error verifying {symbol}: {e}")
            results.append({
                'symbol': symbol.upper(),
                'status': 'error',
                'error': str(e)
            })
    
    # สรุปผล
    print(f"\n{'='*70}")
    print(f"📊 Summary")
    print(f"{'='*70}")
    
    ok_count = sum(1 for r in results if r.get('status') == 'ok')
    error_count = sum(1 for r in results if r.get('status') == 'error')
    
    print(f"✅ Passed: {ok_count}/{len(results)}")
    print(f"❌ Failed: {error_count}/{len(results)}")
    
    if error_count > 0:
        print(f"\n❌ Stocks with issues:")
        for r in results:
            if r.get('status') == 'error':
                print(f"   - {r['symbol']}: {r.get('error', 'Unknown error')}")
    
    return results

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='ตรวจสอบประสิทธิภาพของระบบ Sentiment Analysis')
    parser.add_argument('symbols', nargs='*', default=['AAPL'],
                       help='Stock symbols to verify (default: AAPL)')
    parser.add_argument('--all-popular', action='store_true',
                       help='Verify all popular stocks (AAPL, TSLA, MSFT, GOOGL, AMZN)')
    
    args = parser.parse_args()
    
    if args.all_popular:
        symbols = ['AAPL', 'TSLA', 'MSFT', 'GOOGL', 'AMZN']
    else:
        symbols = args.symbols
    
    if len(symbols) == 1:
        verify_sentiment_accuracy(symbols[0])
    else:
        verify_multiple_stocks(symbols)
