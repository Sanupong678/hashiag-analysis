"""
Google Trends Integration Module
Tracks search trends for stocks and financial topics using PyTrends
"""
from pytrends.request import TrendReq
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict
import time

class TrendsFetcher:
    def __init__(self):
        self.pytrends = TrendReq(hl='en-US', tz=360)
        self.request_delay = 1  # Delay between requests to avoid rate limiting
    
    def get_trends(self, keywords: List[str], timeframe: str = 'today 3-m') -> Dict:
        """
        Get Google Trends data for keywords
        
        Args:
            keywords: List of keywords (stock symbols, company names, etc.)
            timeframe: Time range (e.g., 'today 3-m', 'today 1-y', 'all')
            
        Returns:
            Dictionary with trend data
        """
        if not keywords:
            return {}
        
        try:
            # Build payload
            self.pytrends.build_payload(keywords, cat=0, timeframe=timeframe, geo='', gprop='')
            
            # Get interest over time
            interest_over_time = self.pytrends.interest_over_time()
            
            # Get related queries - convert DataFrame to dict
            related_queries = {}
            try:
                related_df_dict = self.pytrends.related_queries()
                # related_queries() returns a dict where keys are keywords and values are dicts with 'top' and 'rising' DataFrames
                if related_df_dict and isinstance(related_df_dict, dict):
                    for keyword in keywords:
                        related_dict = {'top': [], 'rising': []}
                        if keyword in related_df_dict:
                            keyword_data = related_df_dict[keyword]
                            if isinstance(keyword_data, dict):
                                for query_type in ['top', 'rising']:
                                    if query_type in keyword_data:
                                        df = keyword_data[query_type]
                                        if isinstance(df, pd.DataFrame) and not df.empty:
                                            # Convert DataFrame to list of dicts
                                            related_dict[query_type] = df.to_dict('records')
                                        elif df is None:
                                            related_dict[query_type] = []
                                        else:
                                            # If it's already a list or dict, use as is
                                            related_dict[query_type] = df if isinstance(df, (list, dict)) else []
                        related_queries[keyword] = related_dict
                        time.sleep(self.request_delay)  # Rate limiting
                else:
                    # If no data, initialize empty dicts for all keywords
                    for keyword in keywords:
                        related_queries[keyword] = {'top': [], 'rising': []}
            except Exception as e:
                print(f"⚠️ Error fetching related queries: {e}")
                import traceback
                traceback.print_exc()
                # Initialize empty dicts for all keywords on error
                for keyword in keywords:
                    related_queries[keyword] = {'top': [], 'rising': []}
            
            # Convert to dictionary format
            result = {
                'keywords': keywords,
                'timeframe': timeframe,
                'interest_over_time': [],
                'related_queries': related_queries,
                'fetchedAt': datetime.utcnow().isoformat()
            }
            
            if not interest_over_time.empty:
                for date, row in interest_over_time.iterrows():
                    data_point = {
                        'date': date.isoformat(),
                        'values': {}
                    }
                    for keyword in keywords:
                        if keyword in row:
                            data_point['values'][keyword] = int(row[keyword])
                    result['interest_over_time'].append(data_point)
            
            return result
            
        except Exception as e:
            print(f"❌ Error fetching trends for {keywords}: {e}")
            return {}
    
    def get_stock_trends(self, symbol: str, timeframe: str = 'today 3-m') -> Dict:
        """Get trends for a stock symbol (tries multiple query variations)"""
        queries = [symbol, f"${symbol}", f"{symbol} stock", f"{symbol} price"]
        return self.get_trends(queries[:1], timeframe)  # Limit to avoid rate limits
    
    def compare_trends(self, symbols: List[str], timeframe: str = 'today 3-m') -> Dict:
        """Compare trends for multiple stock symbols"""
        # Limit to 5 symbols to avoid rate limits
        symbols = symbols[:5]
        return self.get_trends(symbols, timeframe)

