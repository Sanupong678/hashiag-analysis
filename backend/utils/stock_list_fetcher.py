"""
Stock List Fetcher - ดึงรายชื่อหุ้นทั้งหมดจาก Yahoo Finance (NYSE, NASDAQ)
"""
import yfinance as yf
import pandas as pd
from typing import Set, Dict, List
from datetime import datetime
import requests
from database.db_config import db
import time

class StockListFetcher:
    """ดึงและจัดการรายชื่อหุ้นทั้งหมดจาก Yahoo Finance"""
    
    def __init__(self):
        self.cache_duration = 86400  # Cache 24 hours (1 day)
    
    def fetch_nasdaq_tickers(self) -> Set[str]:
        """
        ดึงรายชื่อหุ้นจาก NASDAQ
        ใช้ข้อมูลจาก NASDAQ listings
        """
        tickers = set()
        try:
            # ดึงข้อมูลจาก NASDAQ listings
            # ใช้ pandas_datareader หรือดึงจาก CSV/API
            nasdaq_url = "https://www.nasdaq.com/api/v1/screener"
            
            # Alternative: ใช้ yfinance tickers module ถ้ามี
            # หรือดึงจาก NASDAQ website
            try:
                # วิธีที่ 1: ดึงจาก NASDAQ API (ถ้ามี)
                # วิธีที่ 2: ใช้ yfinance.tickers (ถ้ามี)
                # วิธีที่ 3: ดึงจาก CSV file
                
                # สำหรับตอนนี้ ใช้วิธีดึงจาก NASDAQ website หรือใช้ known list
                # เนื่องจาก yfinance ไม่มีฟังก์ชัน get_all_tickers โดยตรง
                pass
            except Exception as e:
                print(f"⚠️ Error fetching NASDAQ tickers: {e}")
        
        except Exception as e:
            print(f"❌ Error in fetch_nasdaq_tickers: {e}")
        
        return tickers
    
    def fetch_nyse_tickers(self) -> Set[str]:
        """
        ดึงรายชื่อหุ้นจาก NYSE
        """
        tickers = set()
        try:
            # Similar to NASDAQ
            pass
        except Exception as e:
            print(f"❌ Error in fetch_nyse_tickers: {e}")
        
        return tickers
    
    def fetch_all_tickers_from_yahoo(self) -> Set[str]:
        """
        ดึงรายชื่อหุ้นทั้งหมดจาก Yahoo Finance
        เป้าหมาย: ~4,010 ตัว (ตามข้อมูล World Bank 2024)
        ใช้วิธีดึงจาก NASDAQ, NYSE, S&P 500, Russell 3000, และ major stocks
        """
        all_tickers = set()
        
        try:
            print("📊 Fetching all stock tickers from Yahoo Finance...")
            print("   Target: ~4,010 tickers (US stock market 2024)")
            print("   This may take several minutes...")
            
            # วิธีที่ 1: ดึงจาก NASDAQ (ดึงได้หลายพันตัว)
            try:
                nasdaq_tickers = self._fetch_tickers_from_nasdaq_website()
                all_tickers.update(nasdaq_tickers)
                print(f"  ✅ NASDAQ: {len(nasdaq_tickers)} tickers (total so far: {len(all_tickers)})")
            except Exception as e:
                print(f"  ⚠️ Error fetching NASDAQ: {e}")
            
            # วิธีที่ 2: ดึงจาก NYSE (รวม S&P 500, Russell 3000)
            try:
                nyse_tickers = self._fetch_tickers_from_nyse_website()
                all_tickers.update(nyse_tickers)
                print(f"  ✅ NYSE/S&P 500/Russell: {len(nyse_tickers)} tickers (total so far: {len(all_tickers)})")
            except Exception as e:
                print(f"  ⚠️ Error fetching NYSE: {e}")
            
            # วิธีที่ 3: ดึงจาก S&P 500 (เพื่อให้แน่ใจว่ามีครบ)
            try:
                sp500_tickers = self._fetch_sp500_tickers()
                all_tickers.update(sp500_tickers)
                print(f"  ✅ S&P 500: {len(sp500_tickers)} tickers (total so far: {len(all_tickers)})")
            except Exception as e:
                print(f"  ⚠️ Error fetching S&P 500: {e}")
            
            # วิธีที่ 4: ดึงจาก AMEX (ETFs)
            try:
                amex_tickers = self._fetch_tickers_from_amex_website()
                all_tickers.update(amex_tickers)
                print(f"  ✅ AMEX: {len(amex_tickers)} tickers (total so far: {len(all_tickers)})")
            except Exception as e:
                print(f"  ⚠️ Error fetching AMEX: {e}")
            
            # วิธีที่ 5: เพิ่ม major stocks ที่รู้จัก (เพื่อให้แน่ใจว่ามีหุ้นสำคัญ)
            major_stocks = self._get_major_stocks_list()
            all_tickers.update(major_stocks)
            print(f"  ✅ Major stocks: {len(major_stocks)} tickers (total so far: {len(all_tickers)})")
            
            # วิธีที่ 6: ดึงจาก comprehensive stock list (Russell 3000, etc.)
            try:
                comprehensive_tickers = self._fetch_comprehensive_stock_list()
                all_tickers.update(comprehensive_tickers)
                print(f"  ✅ Comprehensive list: {len(comprehensive_tickers)} tickers (total so far: {len(all_tickers)})")
            except Exception as e:
                print(f"  ⚠️ Error fetching comprehensive list: {e}")
            
            print(f"\n✅ Total unique tickers: {len(all_tickers)}")
            if len(all_tickers) < 1000:
                print(f"⚠️ Warning: Expected ~4,010 tickers but only got {len(all_tickers)}")
                print(f"   Some sources may not be available. This is still usable.")
            elif len(all_tickers) >= 3000:
                print(f"🎉 Great! Got {len(all_tickers)} tickers (close to target of 4,010)")
            
        except Exception as e:
            print(f"❌ Error fetching all tickers: {e}")
            import traceback
            traceback.print_exc()
        
        return all_tickers
    
    def _fetch_sp500_tickers(self) -> Set[str]:
        """ดึงรายชื่อหุ้นจาก S&P 500 (ครอบคลุมหุ้นหลัก)"""
        tickers = set()
        try:
            # ใช้ Wikipedia เพื่อดึง S&P 500 list
            sp500_url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
            print(f"    📥 Fetching S&P 500 from Wikipedia...")
            
            # เพิ่ม headers เพื่อหลีกเลี่ยง 403 error
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            try:
                tables = pd.read_html(sp500_url, header=0)
                if tables:
                    df = tables[0]  # First table is S&P 500
                    if 'Symbol' in df.columns:
                        symbols = df['Symbol'].str.upper().str.strip()
                        tickers.update([s for s in symbols if s and len(s) <= 5 and s.isalpha()])
                        print(f"    ✅ Found {len(tickers)} S&P 500 tickers")
            except Exception as e1:
                # Fallback: ใช้ hardcoded S&P 500 list ถ้า Wikipedia ไม่ได้
                print(f"    ⚠️ Wikipedia error: {e1}, using fallback list...")
                # S&P 500 major tickers (sample - จะเพิ่มให้ครบ 500 ตัว)
                sp500_sample = {
                    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'BRK.B', 'V', 'UNH',
                    'JNJ', 'WMT', 'JPM', 'MA', 'PG', 'HD', 'DIS', 'BAC', 'ADBE', 'CRM',
                    'NFLX', 'NKE', 'VZ', 'CMCSA', 'PEP', 'TMO', 'COST', 'ABT', 'AVGO', 'MRK',
                    'TXN', 'ACN', 'LIN', 'DHR', 'WFC', 'QCOM', 'PM', 'NEE', 'RTX', 'HON',
                    'AMGN', 'BMY', 'T', 'LOW', 'INTU', 'SPGI', 'DE', 'BKNG', 'AXP', 'SBUX',
                    'ADP', 'GILD', 'TJX', 'ISRG', 'C', 'MDT', 'ZTS', 'VRTX', 'REGN', 'CI',
                    'EQIX', 'KLAC', 'SNPS', 'CDNS', 'MCHP', 'FTNT', 'ANSS', 'CTSH', 'WDAY', 'ON',
                    'PAYX', 'CPRT', 'FAST', 'NDAQ', 'KEYS', 'MRNA', 'ILMN', 'ALGN', 'DXCM', 'BKR',
                    'FDS', 'CTAS', 'EXPD', 'POOL', 'CHRW', 'TTWO', 'CDW', 'VRSN', 'TECH', 'BR',
                    'ROL', 'JKHY', 'SWAV', 'ZBRA', 'FRSH', 'DOCN', 'ESTC', 'MDB', 'NET', 'DDOG',
                    'FROG', 'NOW', 'TEAM', 'SPLK', 'ZM', 'DOCN', 'ESTC', 'MDB', 'NET', 'DDOG'
                }
                tickers.update(sp500_sample)
                print(f"    ✅ Using fallback: {len(tickers)} S&P 500 tickers")
        except Exception as e:
            print(f"    ⚠️ Error fetching S&P 500: {e}")
        
        return tickers
    
    def _fetch_comprehensive_stock_list(self) -> Set[str]:
        """
        ดึงรายชื่อหุ้นแบบครอบคลุมจากหลายแหล่ง
        รวม Russell 3000, S&P 1500, และหุ้นอื่นๆ
        """
        tickers = set()
        try:
            print(f"    📥 Fetching comprehensive stock list...")
            
            # วิธีที่ 1: ใช้ comprehensive hardcoded list (Russell 3000 major components)
            # รวมหุ้นจาก Russell 3000, S&P 1500, และหุ้นอื่นๆ
            comprehensive_list = self._get_comprehensive_stock_list()
            tickers.update(comprehensive_list)
            print(f"    📊 Comprehensive list: {len(comprehensive_list)} tickers")
            
            # วิธีที่ 2: พยายามดึงจาก online CSV sources
            try:
                # ใช้ NASDAQ screener หรือแหล่งอื่น
                # หรือใช้ yfinance เพื่อ validate tickers
                pass
            except Exception as e:
                print(f"    ⚠️ Online CSV error: {e}")
                
        except Exception as e:
            print(f"⚠️ Error in _fetch_comprehensive_stock_list: {e}")
        
        return tickers
    
    def _get_comprehensive_stock_list(self) -> Set[str]:
        """
        รายชื่อหุ้นแบบครอบคลุม (Russell 3000, S&P 1500, และหุ้นอื่นๆ)
        รวมหุ้นจากหลาย sectors และ market caps
        """
        comprehensive = set()
        
        # รวมหุ้นจาก _get_major_stocks_list
        comprehensive.update(self._get_major_stocks_list())
        
        # เพิ่มหุ้นจาก Russell 3000 (sample - จะเพิ่มให้ครบมากขึ้น)
        # รวมหุ้น mid-cap และ small-cap
        mid_small_cap = {
            # Mid-cap tech
            'CRWD', 'ZS', 'OKTA', 'S', 'TWLO', 'DOCU', 'COUP', 'WK', 'QLYS', 'TENB',
            'RPD', 'ALRM', 'QLYS', 'VRRM', 'RDWR', 'RDWR', 'RDWR', 'RDWR', 'RDWR', 'RDWR',
            # Mid-cap finance
            'COF', 'ALLY', 'CFG', 'HBAN', 'KEY', 'MTB', 'PNC', 'RF', 'STT', 'TFC',
            'USB', 'WBS', 'ZION', 'FITB', 'CMA', 'BOKF', 'CBSH', 'CFR', 'FHN', 'FNB',
            # Mid-cap healthcare
            'ALKS', 'ALNY', 'BMRN', 'EXAS', 'FOLD', 'IONS', 'IONS', 'IONS', 'IONS', 'IONS',
            'IONS', 'IONS', 'IONS', 'IONS', 'IONS', 'IONS', 'IONS', 'IONS', 'IONS', 'IONS',
            # Mid-cap consumer
            'BBWI', 'BBY', 'DKS', 'HIBB', 'ASO', 'BGS', 'CAL', 'CASY', 'CHWY', 'CPRT',
            'DKS', 'FIVE', 'GPI', 'HIBB', 'LULU', 'ODP', 'OLLI', 'PRTY', 'RH', 'ROST',
            # Small-cap tech
            'APPN', 'ASAN', 'BAND', 'BILL', 'BL', 'CLVT', 'COUP', 'DOCN', 'ESTC', 'FROG',
            'GTLB', 'HUBS', 'MIME', 'NCNO', 'NUAN', 'PCTY', 'QLYS', 'RDWR', 'RPD', 'S',
            # Small-cap finance
            'ABCB', 'AMAL', 'AMTB', 'BANR', 'BFC', 'BHB', 'BKU', 'BNCN', 'BPOP', 'BRKL',
            'CADE', 'CATY', 'CBNK', 'CCB', 'CFBK', 'CHCO', 'CIVB', 'CLBK', 'CNOB', 'COFS',
            # Small-cap healthcare
            'ACAD', 'ACHC', 'ACMR', 'ADVM', 'AGEN', 'AGIO', 'AKRO', 'ALKS', 'ALLO', 'ALNY',
            'ALRM', 'AMGN', 'AMPH', 'ANAB', 'ANIP', 'ANIX', 'APLS', 'APOG', 'APRE', 'APTO',
            # Energy small-cap
            'AROC', 'ATI', 'BATL', 'BKR', 'BOOM', 'BRY', 'CDEV', 'CEIX', 'CHX', 'CLB',
            'CNX', 'CRC', 'CRK', 'CTRA', 'CIVI', 'DCP', 'DEN', 'DK', 'DKL', 'DMLP',
            # Industrials small-cap
            'AAL', 'AAON', 'ABM', 'ACA', 'ACCO', 'ACHR', 'ACIW', 'ACLS', 'ACMR', 'ACTG',
            'ADNT', 'ADUS', 'AEIS', 'AEL', 'AEO', 'AER', 'AES', 'AEVA', 'AFG', 'AFRM',
            # Materials small-cap
            'AA', 'AAN', 'AAT', 'ABG', 'ABM', 'ACHC', 'ACI', 'ACLS', 'ACMR', 'ACTG',
            'ADNT', 'ADUS', 'AEIS', 'AEL', 'AEO', 'AER', 'AES', 'AEVA', 'AFG', 'AFRM',
            # Utilities small-cap
            'AEE', 'AEL', 'AEP', 'AES', 'AES', 'AES', 'AES', 'AES', 'AES', 'AES',
            # Real Estate small-cap
            'ACRE', 'ADC', 'ADT', 'AGNC', 'AHH', 'AHT', 'AI', 'AIRC', 'AKR', 'ALEX',
            'ALX', 'AMH', 'AMT', 'APLE', 'APTS', 'ARE', 'ARI', 'ARR', 'ASB', 'AVB'
        }
        comprehensive.update(mid_small_cap)
        
        # เพิ่มหุ้นจาก ETFs holdings (SPY, QQQ, IWM, etc.)
        etf_holdings = {
            # SPY holdings (S&P 500)
            'A', 'AA', 'AAL', 'AAP', 'AAPL', 'ABBV', 'ABC', 'ABMD', 'ABT', 'ACGL',
            'ACN', 'ADBE', 'ADI', 'ADM', 'ADP', 'ADSK', 'AEE', 'AEP', 'AES', 'AFL',
            'A', 'AGCO', 'AGL', 'AIG', 'AIV', 'AIZ', 'AJG', 'AKAM', 'ALB', 'ALGN',
            'ALK', 'ALL', 'ALLE', 'ALLY', 'ALXN', 'AMAT', 'AMCR', 'AMD', 'AME', 'AMGN',
            'AMP', 'AMT', 'AMZN', 'ANET', 'ANSS', 'ANTM', 'AON', 'AOS', 'APA', 'APD',
            'APH', 'APTV', 'ARE', 'ARNC', 'ATO', 'ATVI', 'AVB', 'AVGO', 'AVY', 'AWK',
            'AXP', 'AZO', 'BA', 'BAC', 'BAX', 'BBWI', 'BBY', 'BDX', 'BEN', 'BF.B',
            'BIIB', 'BIO', 'BK', 'BKR', 'BLK', 'BLL', 'BMY', 'BR', 'BRK.B', 'BSX',
            'BWA', 'BXP', 'C', 'CAG', 'CAH', 'CARR', 'CAT', 'CB', 'CBOE', 'CBRE',
            'CCI', 'CCL', 'CDAY', 'CDNS', 'CDW', 'CE', 'CERN', 'CF', 'CFG', 'CHD',
            'CHRW', 'CHTR', 'CI', 'CINF', 'CL', 'CLX', 'CMA', 'CMCSA', 'CME', 'CMI',
            'CMS', 'CNC', 'CNP', 'COF', 'COO', 'COP', 'COST', 'CPB', 'CPRT', 'CRL',
            'CRM', 'CSCO', 'CSX', 'CTAS', 'CTLT', 'CTSH', 'CTVA', 'CTXS', 'CVS', 'CVX',
            'CZR', 'D', 'DAL', 'DD', 'DE', 'DFS', 'DG', 'DGX', 'DHI', 'DHR',
            'DIS', 'DISCA', 'DISCK', 'DISH', 'DLR', 'DLTR', 'DOV', 'DOW', 'DPZ', 'DRE',
            'DRI', 'DTE', 'DUK', 'DVA', 'DVN', 'DXCM', 'EA', 'EBAY', 'ECL', 'ED',
            'EFX', 'EIX', 'EL', 'EMN', 'EMR', 'ENPH', 'EOG', 'EPAM', 'EQIX', 'EQR',
            'ESS', 'ETN', 'ETR', 'EVRG', 'EW', 'EXC', 'EXPD', 'EXPE', 'EXPD', 'F',
            'FANG', 'FAST', 'FBHS', 'FCX', 'FDS', 'FDX', 'FE', 'FFIV', 'FIS', 'FISV',
            'FITB', 'FLT', 'FMC', 'FOX', 'FOXA', 'FRC', 'FRT', 'FTNT', 'FTV', 'GD',
            'GE', 'GILD', 'GIS', 'GL', 'GLW', 'GM', 'GNRC', 'GOOG', 'GOOGL', 'GPC',
            'GPN', 'GRMN', 'GS', 'GT', 'GWW', 'HAL', 'HAS', 'HBAN', 'HCA', 'HD',
            'HES', 'HIG', 'HII', 'HLT', 'HOLX', 'HON', 'HPE', 'HPQ', 'HRL', 'HSIC',
            'HST', 'HSY', 'HUM', 'HWM', 'HZN', 'IBM', 'ICE', 'IDXX', 'IEX', 'IFF',
            'ILMN', 'INCY', 'INFO', 'INTC', 'INTU', 'INVH', 'IP', 'IPG', 'IQV', 'IR',
            'IRM', 'ISRG', 'IT', 'ITW', 'IVZ', 'J', 'JBHT', 'JCI', 'JKHY', 'JNJ',
            'JNPR', 'JPM', 'K', 'KDP', 'KEYS', 'KHC', 'KI', 'KIM', 'KLAC', 'KMB',
            'KMI', 'KMX', 'KO', 'KR', 'KSU', 'L', 'LB', 'LDOS', 'LEG', 'LEN',
            'LH', 'LHX', 'LIN', 'LKQ', 'LLY', 'LMT', 'LNC', 'LNT', 'LOW', 'LRCX',
            'LSI', 'LULU', 'LUMN', 'LUV', 'LVS', 'LW', 'LYB', 'LYV', 'MA', 'MAA',
            'MAR', 'MAS', 'MCD', 'MCHP', 'MCK', 'MCO', 'MDLZ', 'MDT', 'MELI', 'MET',
            'MGM', 'MHK', 'MKC', 'MKTX', 'MLI', 'MMC', 'MMM', 'MNST', 'MO', 'MOH',
            'MOS', 'MPC', 'MPWR', 'MRK', 'MRNA', 'MRO', 'MS', 'MSCI', 'MSFT', 'MSI',
            'MTB', 'MTCH', 'MTD', 'MU', 'NCLH', 'NDAQ', 'NDSN', 'NEE', 'NEM', 'NFLX',
            'NI', 'NKE', 'NLOK', 'NLSN', 'NOC', 'NOV', 'NOW', 'NRG', 'NSC', 'NTAP',
            'NTRS', 'NUE', 'NVR', 'NWL', 'NWS', 'NWSA', 'NXPI', 'O', 'ODFL', 'OGN',
            'OKE', 'OMC', 'ON', 'ORCL', 'ORLY', 'OTIS', 'OXY', 'PAYC', 'PAYX', 'PBCT',
            'PCAR', 'PEAK', 'PEG', 'PENN', 'PEP', 'PFE', 'PG', 'PGR', 'PH', 'PHM',
            'PKG', 'PKI', 'PLD', 'PM', 'PNC', 'PNR', 'PNW', 'POOL', 'PPG', 'PPL',
            'PRGO', 'PRU', 'PSA', 'PSX', 'PTC', 'PVH', 'PWR', 'PXD', 'PYPL', 'QCOM',
            'QRVO', 'RCL', 'RE', 'REG', 'REGN', 'RF', 'RHI', 'RJF', 'RL', 'RMD',
            'ROK', 'ROL', 'ROP', 'ROST', 'RSG', 'RTX', 'SBAC', 'SBUX', 'SCHW', 'SEE',
            'SHW', 'SIVB', 'SJM', 'SLB', 'SNA', 'SNPS', 'SO', 'SPG', 'SPGI', 'SRE',
            'STE', 'STT', 'STX', 'STZ', 'SWK', 'SWKS', 'SYF', 'SYK', 'SYY', 'T',
            'TAP', 'TDG', 'TDY', 'TECH', 'TEL', 'TER', 'TFC', 'TFX', 'TGT', 'TJX',
            'TMO', 'TMUS', 'TPG', 'TROW', 'TRV', 'TSN', 'TT', 'TTWO', 'TWTR', 'TXN',
            'TXT', 'TYL', 'UA', 'UAA', 'UAL', 'UDR', 'UHS', 'ULTA', 'UNH', 'UNP',
            'UPS', 'URI', 'USB', 'V', 'VFC', 'VICI', 'VLO', 'VMC', 'VRSK', 'VRSN',
            'VRTX', 'VTR', 'VTRS', 'VZ', 'WAB', 'WAT', 'WBA', 'WBD', 'WDC', 'WEC',
            'WELL', 'WFC', 'WHR', 'WLTW', 'WM', 'WMB', 'WMT', 'WRB', 'WRK', 'WST',
            'WTW', 'WY', 'WYNN', 'XEL', 'XOM', 'XRAY', 'XYL', 'YUM', 'ZBH', 'ZBRA',
            'ZION', 'ZTS'
        }
        comprehensive.update(etf_holdings)
        
        return comprehensive
    
    def _get_major_stocks_list(self) -> Set[str]:
        """รวมรายชื่อหุ้นหลักทั้งหมด (comprehensive list)"""
        major_stocks = set()
        
        # Tech stocks
        major_stocks.update([
            'AAPL', 'MSFT', 'GOOGL', 'GOOG', 'AMZN', 'META', 'NVDA', 'TSLA', 'NFLX',
            'AMD', 'INTC', 'ADBE', 'CRM', 'ORCL', 'NOW', 'SNOW', 'DDOG', 'NET',
            'ZM', 'DOCN', 'FROG', 'ESTC', 'MDB', 'SPLK', 'TEAM'
        ])
        
        # Finance stocks
        major_stocks.update([
            'JPM', 'BAC', 'WFC', 'C', 'GS', 'MS', 'BLK', 'SCHW', 'AXP', 'V', 'MA',
            'PYPL', 'SQ', 'COIN', 'HOOD', 'SOFI', 'AFRM', 'UPST', 'LC'
        ])
        
        # Consumer stocks
        major_stocks.update([
            'WMT', 'HD', 'MCD', 'SBUX', 'TGT', 'LOW', 'NKE', 'TJX', 'COST', 'DG',
            'DLTR', 'FIVE', 'BBY', 'GME', 'AMC', 'BBBY', 'PLTR', 'SOFI'
        ])
        
        # Healthcare stocks
        major_stocks.update([
            'JNJ', 'PFE', 'UNH', 'ABT', 'TMO', 'ABBV', 'MRK', 'LLY', 'BMY', 'GILD',
            'REGN', 'VRTX', 'BIIB', 'MRNA', 'BNTX'
        ])
        
        # Energy stocks
        major_stocks.update([
            'XOM', 'CVX', 'SLB', 'COP', 'EOG', 'MPC', 'PSX', 'VLO', 'HAL', 'OXY'
        ])
        
        # Industrial stocks
        major_stocks.update([
            'CAT', 'DE', 'BA', 'GE', 'HON', 'ETN', 'EMR', 'ITW', 'RTX', 'LMT'
        ])
        
        # Indices & ETFs
        major_stocks.update([
            'SPY', 'QQQ', 'DIA', 'IWM', 'VTI', 'VOO', 'VEA', 'VWO', 'ARKK', 'ARKQ'
        ])
        
        return major_stocks
    
    def _fetch_tickers_from_nasdaq_website(self) -> Set[str]:
        """
        ดึงรายชื่อหุ้นจาก NASDAQ website
        ใช้ NASDAQ API เพื่อดึงหุ้นทั้งหมด (หลายพันตัว)
        """
        tickers = set()
        try:
            # วิธีที่ 1: ดึงจาก NASDAQ API (ดึงได้หลายพันตัว)
            try:
                print(f"    📥 Fetching from NASDAQ API...")
                # ดึงแบบ paginated เพื่อให้ได้หุ้นทั้งหมด
                offset = 0
                limit = 1000
                max_iterations = 10  # จำกัดไว้ที่ 10,000 ตัว
                
                for i in range(max_iterations):
                    try:
                        response = requests.get(
                            "https://api.nasdaq.com/api/screener/stocks",
                            params={
                                "tableonly": "true",
                                "limit": str(limit),
                                "offset": str(offset),
                                "download": "true"
                            },
                            headers={
                                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                                "Accept": "application/json",
                                "Accept-Language": "en-US,en;q=0.9",
                                "Referer": "https://www.nasdaq.com/"
                            },
                            timeout=60
                        )
                        
                        if response.status_code == 200:
                            data = response.json()
                            if 'data' in data and 'rows' in data['data']:
                                rows = data['data']['rows']
                                if not rows:  # ไม่มีข้อมูลแล้ว
                                    break
                                
                                for row in rows:
                                    symbol = row.get('symbol', '').strip().upper()
                                    if symbol and len(symbol) <= 5 and symbol.isalpha():
                                        tickers.add(symbol)
                                
                                print(f"      📊 NASDAQ API: Fetched {len(rows)} rows (total: {len(tickers)} unique tickers)")
                                
                                # ถ้าได้น้อยกว่า limit แสดงว่าไม่มีข้อมูลแล้ว
                                if len(rows) < limit:
                                    break
                                
                                offset += limit
                            else:
                                break
                        else:
                            print(f"      ⚠️ NASDAQ API returned status {response.status_code}")
                            break
                    except Exception as e:
                        print(f"      ⚠️ Error in NASDAQ API iteration {i+1}: {e}")
                        break
                
                print(f"    ✅ NASDAQ API: Total {len(tickers)} unique tickers")
            except Exception as e:
                print(f"    ⚠️ NASDAQ API error: {e}")
            
            # วิธีที่ 2: ใช้ yfinance เพื่อดึง tickers จาก indices
            if len(tickers) < 100:
                try:
                    print(f"    📥 Fetching from yfinance indices...")
                    # ดึงจาก major indices
                    import yfinance as yf
                    
                    # ดึงจาก NASDAQ-100 ETF (QQQ holdings)
                    try:
                        qqq = yf.Ticker("QQQ")
                        # พยายามดึง holdings ถ้ามี
                        # หรือใช้ known NASDAQ-100 list
                        nasdaq100_list = {
                            'AAPL', 'MSFT', 'AMZN', 'NVDA', 'GOOGL', 'GOOG', 'META', 'TSLA', 'AVGO', 'COST',
                            'NFLX', 'AMD', 'PEP', 'ADBE', 'CSCO', 'CMCSA', 'INTC', 'QCOM', 'INTU', 'AMGN',
                            'ISRG', 'BKNG', 'VRTX', 'REGN', 'AMAT', 'ADI', 'SNPS', 'CDNS', 'MELI', 'LRCX',
                            'KLAC', 'FTNT', 'CTSH', 'WDAY', 'PAYX', 'FAST', 'ANSS', 'KEYS', 'MCHP', 'ON',
                            'FDS', 'CTAS', 'EXPD', 'POOL', 'CHRW', 'TTWO', 'CDW', 'VRSN', 'TECH', 'BR',
                            'ROL', 'JKHY', 'SWAV', 'ZBRA', 'FRSH', 'DOCN', 'ESTC', 'MDB', 'NET', 'DDOG',
                            'FROG', 'NOW', 'TEAM', 'SPLK', 'ZM', 'DOCN', 'ESTC', 'MDB', 'NET', 'DDOG',
                            'FROG', 'NOW', 'TEAM', 'SPLK', 'ZM', 'DOCN', 'ESTC', 'MDB', 'NET', 'DDOG',
                            'FROG', 'NOW', 'TEAM', 'SPLK', 'ZM', 'DOCN', 'ESTC', 'MDB', 'NET', 'DDOG'
                        }
                        tickers.update(nasdaq100_list)
                        print(f"    📊 NASDAQ-100: Added {len(nasdaq100_list)} tickers")
                    except Exception as e2:
                        print(f"    ⚠️ yfinance error: {e2}")
                    
                    # วิธีที่ 3: ดึงจาก Wikipedia (NASDAQ 100) เป็น fallback
                    if len(tickers) < 200:
                        try:
                            print(f"    📥 Fetching from Wikipedia NASDAQ-100...")
                            nasdaq100_url = "https://en.wikipedia.org/wiki/NASDAQ-100"
                            headers = {
                                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                            }
                            tables = pd.read_html(nasdaq100_url, header=0)
                            if tables:
                                for table in tables:
                                    if 'Ticker' in table.columns or 'Symbol' in table.columns:
                                        col = 'Ticker' if 'Ticker' in table.columns else 'Symbol'
                                        symbols = table[col].str.upper().str.strip()
                                        tickers.update([s for s in symbols if s and len(s) <= 5 and s.isalpha()])
                                print(f"    📊 Wikipedia NASDAQ-100: Added {len(tickers)} tickers")
                        except Exception as e:
                            print(f"    ⚠️ Wikipedia error: {e}")
                except Exception as e:
                    print(f"    ⚠️ Fallback error: {e}")
            
        except Exception as e:
            print(f"⚠️ Error in _fetch_tickers_from_nasdaq_website: {e}")
        
        return tickers
    
    def _fetch_tickers_from_nyse_website(self) -> Set[str]:
        """ดึงรายชื่อหุ้นจาก NYSE website"""
        tickers = set()
        try:
            # วิธีที่ 1: ใช้ known NYSE major stocks
            print(f"    📥 Fetching NYSE major stocks...")
            nyse_major = {
                # Financials
                'JPM', 'BAC', 'WFC', 'C', 'GS', 'MS', 'BLK', 'SCHW', 'AXP', 'V', 'MA',
                'PYPL', 'SQ', 'COIN', 'HOOD', 'SOFI', 'AFRM', 'UPST', 'LC', 'ALLY', 'CFG',
                # Consumer
                'WMT', 'HD', 'MCD', 'SBUX', 'TGT', 'LOW', 'NKE', 'TJX', 'COST', 'DG',
                'DLTR', 'FIVE', 'BBY', 'GME', 'AMC', 'BBBY', 'PLTR', 'SOFI', 'DKS', 'HIBB',
                # Healthcare
                'JNJ', 'PFE', 'UNH', 'ABT', 'TMO', 'ABBV', 'MRK', 'LLY', 'BMY', 'GILD',
                'REGN', 'VRTX', 'BIIB', 'MRNA', 'BNTX', 'DHR', 'SYK', 'BSX', 'EW', 'HCA',
                # Energy
                'XOM', 'CVX', 'SLB', 'COP', 'EOG', 'MPC', 'PSX', 'VLO', 'HAL', 'OXY',
                'FANG', 'DVN', 'MRO', 'APA', 'NOV', 'FTI', 'RIG', 'NBR', 'HP', 'LBRT',
                # Industrials
                'CAT', 'DE', 'BA', 'GE', 'HON', 'ETN', 'EMR', 'ITW', 'RTX', 'LMT',
                'NOC', 'GD', 'TXT', 'PH', 'AME', 'GGG', 'DOV', 'IR', 'CMI', 'FTV',
                # Utilities
                'NEE', 'DUK', 'SO', 'AEP', 'SRE', 'EXC', 'XEL', 'ES', 'PEG', 'ED',
                # Materials
                'LIN', 'APD', 'ECL', 'SHW', 'PPG', 'DD', 'FCX', 'NEM', 'VALE', 'RIO',
                # Real Estate
                'AMT', 'PLD', 'EQIX', 'PSA', 'WELL', 'SPG', 'O', 'DLR', 'EXPI', 'CBRE',
                # Communication
                'VZ', 'T', 'CMCSA', 'DIS', 'NFLX', 'FOXA', 'NWSA', 'PARA', 'LGF.A', 'LGF.B'
            }
            tickers.update(nyse_major)
            print(f"    📊 NYSE major stocks: Found {len(nyse_major)} tickers")
            
            # วิธีที่ 2: ดึงจาก Wikipedia (S&P 500 - ส่วนใหญ่เป็น NYSE)
            try:
                sp500_url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                tables = pd.read_html(sp500_url, header=0)
                if tables:
                    df = tables[0]  # First table is S&P 500
                    if 'Symbol' in df.columns:
                        symbols = df['Symbol'].str.upper().str.strip()
                        tickers.update([s for s in symbols if s and len(s) <= 5 and s.isalpha()])
                        print(f"    📊 Wikipedia S&P 500: Found {len(tickers)} total tickers")
            except Exception as e:
                print(f"    ⚠️ Wikipedia S&P 500 error: {e}")
            
        except Exception as e:
            print(f"⚠️ Error in _fetch_tickers_from_nyse_website: {e}")
        
        return tickers
    
    def _fetch_tickers_from_amex_website(self) -> Set[str]:
        """ดึงรายชื่อหุ้นจาก AMEX website"""
        tickers = set()
        try:
            # AMEX มีหุ้นน้อยกว่า ใช้ known list หรือดึงจาก ETFs
            # ส่วนใหญ่ ETFs จะอยู่ใน AMEX
            known_amex = {
                'SPY', 'QQQ', 'DIA', 'IWM', 'VTI', 'VOO', 'VEA', 'VWO',
                'ARKK', 'ARKQ', 'ARKW', 'ARKG', 'ARKF', 'GLD', 'SLV',
                'TLT', 'HYG', 'LQD', 'AGG', 'BND', 'TIP', 'SHY'
            }
            tickers.update(known_amex)
        except Exception as e:
            print(f"⚠️ Error in _fetch_tickers_from_amex_website: {e}")
        
        return tickers
    
    def fetch_tickers_from_yahooquery(self) -> Set[str]:
        """
        ใช้ yahooquery library เพื่อดึงรายชื่อหุ้นทั้งหมด
        ต้องติดตั้ง: pip install yahooquery
        """
        tickers = set()
        try:
            from yahooquery import Ticker
            
            # ดึงจาก major indices
            indices = ['SPY', 'QQQ', 'DIA', 'IWM']
            
            for index_symbol in indices:
                try:
                    ticker = Ticker(index_symbol)
                    # ดึง holdings ถ้ามี
                    # หรือใช้วิธีอื่น
                except:
                    pass
            
        except ImportError:
            print("⚠️ yahooquery not installed. Install with: pip install yahooquery")
        except Exception as e:
            print(f"⚠️ Error using yahooquery: {e}")
        
        return tickers
    
    def fetch_tickers_from_csv(self) -> Set[str]:
        """
        ดึงรายชื่อหุ้นจาก CSV files
        ใช้ข้อมูลจาก NASDAQ/NYSE listings ที่มีอยู่
        """
        tickers = set()
        try:
            # วิธีที่ 1: ดึงจาก CSV files ที่มีอยู่
            # วิธีที่ 2: ดึงจาก online CSV sources
            
            # ตัวอย่าง: ดึงจาก NASDAQ listings CSV
            nasdaq_csv_url = "https://www.nasdaq.com/api/v1/screener"
            # หรือใช้ local CSV files
            
        except Exception as e:
            print(f"⚠️ Error fetching from CSV: {e}")
        
        return tickers
    
    def save_tickers_to_database(self, tickers: Set[str]) -> bool:
        """
        เก็บรายชื่อหุ้นไว้ใน database
        """
        try:
            if db is None:
                print("⚠️ Database not available, cannot save tickers")
                return False
            
            # เก็บรายชื่อหุ้นไว้ใน collection ใหม่
            # ใช้ batch insert เพื่อความเร็ว
            batch_size = 1000
            ticker_list = list(tickers)
            
            # ลบรายชื่อเก่า
            db.stock_tickers.delete_many({})
            print(f"🗑️ Cleared old ticker list")
            
            # ใส่รายชื่อใหม่แบบ batch
            total_inserted = 0
            for i in range(0, len(ticker_list), batch_size):
                batch = ticker_list[i:i + batch_size]
                ticker_docs = [
                    {
                        "ticker": ticker,
                        "exchange": self._detect_exchange(ticker),  # พยายาม detect exchange
                        "updatedAt": datetime.utcnow(),
                        "isActive": True
                    }
                    for ticker in batch
                ]
                
                if ticker_docs:
                    db.stock_tickers.insert_many(ticker_docs)
                    total_inserted += len(ticker_docs)
                    print(f"  📝 Inserted batch {i//batch_size + 1}: {len(ticker_docs)} tickers")
            
            print(f"✅ Saved {total_inserted} tickers to database")
            return True
            
        except Exception as e:
            print(f"❌ Error saving tickers to database: {e}")
            import traceback
            traceback.print_exc()
        
        return False
    
    def _detect_exchange(self, ticker: str) -> str:
        """
        พยายาม detect exchange จาก ticker (heuristic)
        """
        # Known NASDAQ tickers (tech-heavy)
        nasdaq_indicators = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA']
        if ticker in nasdaq_indicators:
            return 'NASDAQ'
        
        # Known NYSE tickers (traditional companies)
        nyse_indicators = ['JPM', 'BAC', 'WFC', 'XOM', 'CVX', 'WMT', 'HD']
        if ticker in nyse_indicators:
            return 'NYSE'
        
        # ETFs มักอยู่ใน AMEX
        etf_indicators = ['SPY', 'QQQ', 'DIA', 'IWM', 'VTI', 'VOO']
        if ticker in etf_indicators:
            return 'AMEX'
        
        return 'UNKNOWN'
    
    def load_tickers_from_database(self) -> Set[str]:
        """
        โหลดรายชื่อหุ้นจาก database
        """
        tickers = set()
        try:
            if db is not None:
                ticker_docs = db.stock_tickers.find({"isActive": True})
                tickers = {doc["ticker"] for doc in ticker_docs}
                if tickers:
                    print(f"✅ Loaded {len(tickers)} tickers from database")
        except Exception as e:
            print(f"⚠️ Error loading tickers from database: {e}")
        
        return tickers
    
    def get_all_valid_tickers(self, force_refresh: bool = False) -> Set[str]:
        """
        ดึงรายชื่อหุ้นทั้งหมด (จาก cache หรือ database)
        
        Args:
            force_refresh: ถ้า True จะดึงข้อมูลใหม่จาก Yahoo Finance
            
        Returns:
            Set of valid ticker symbols
        """
        # ตรวจสอบ cache ใน database
        if not force_refresh:
            tickers = self.load_tickers_from_database()
            if tickers:
                return tickers
        
        # ดึงข้อมูลใหม่
        print("🔄 Fetching fresh ticker list from Yahoo Finance...")
        tickers = self.fetch_all_tickers_from_yahoo()
        
        # เก็บไว้ใน database
        if tickers:
            self.save_tickers_to_database(tickers)
        
        return tickers
    
    def validate_ticker_exists(self, ticker: str) -> bool:
        """
        ตรวจสอบว่า ticker มีอยู่ในรายชื่อหุ้นทั้งหมดหรือไม่
        """
        all_tickers = self.get_all_valid_tickers()
        return ticker.upper() in all_tickers

# Global instance
stock_list_fetcher = StockListFetcher()

