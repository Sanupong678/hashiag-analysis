// Internationalization (i18n) System
// Supports Thai and English language switching

const i18n = {
  currentLang: localStorage.getItem('language') || 'en',
  
  translations: {
    en: {
      // Navigation
      'nav.home': 'Home (Overview)',
      'nav.watchlist': 'Watchlist / My Tickers',
      'nav.compare': 'Compare',
      'nav.stockDetail': 'Stock Detail',
      'nav.influencer': 'Influencer Tracker',
      'nav.alerts': 'Alerts & Escalation',
      'nav.dataExplorer': 'Data Explorer / Raw Feed',
      'nav.settings': 'Settings',
      
      // Common
      'common.refresh': 'Refresh',
      'common.loading': 'Loading...',
      'common.error': 'Error',
      'common.success': 'Success',
      'common.apply': 'Apply',
      'common.reset': 'Reset',
      'common.cancel': 'Cancel',
      'common.save': 'Save',
      'common.delete': 'Delete',
      'common.edit': 'Edit',
      'common.close': 'Close',
      'common.search': 'Search',
      'common.filter': 'Filter',
      'common.filters': 'Filters',
      'common.all': 'All',
      'common.yes': 'Yes',
      'common.no': 'No',
      
      // Dashboard
      'dashboard.title': 'Stock Sentiment Dashboard',
      'dashboard.totalMentions': 'Total Mentions',
      'dashboard.avgSentiment': 'Avg Sentiment Score',
      'dashboard.spikeEvents': 'Spike Events (24h)',
      'dashboard.activeAlerts': 'Active Alerts',
      'dashboard.viewAll': 'View All',
      'dashboard.last24h': 'Last 24h',
      
      // Widgets
      'widget.marketSentimentHeatmap': 'Market Sentiment Heatmap',
      'widget.trendingStockTickers': 'Trending Stock Tickers',
      'widget.topInfluencers': 'Top Influencers Feed',
      'widget.mentionsVolume': 'Mentions Volume',
      'widget.priceSentimentDivergence': 'Price vs Sentiment Divergence',
      'widget.rawFeed': 'Raw Feed',
      'widget.eventAnalysis': 'Event Analysis & Stock Recommendations',
      
      // Event Analysis
      'eventAnalysis.analyze': 'Analyze Events',
      'eventAnalysis.clickToAnalyze': 'Click "Analyze Events" to analyze news from YouTube and get stock recommendations',
      'eventAnalysis.loading': 'Analyzing events from YouTube videos...',
      'eventAnalysis.buyRecommendations': 'Buy Recommendations',
      'eventAnalysis.sellRecommendations': 'Sell Recommendations',
      'eventAnalysis.detectedEvents': 'Detected Events',
      'eventAnalysis.confidence': 'Confidence',
      'eventAnalysis.mentions': 'Mentions',
      'eventAnalysis.reasons': 'Reasons',
      'eventAnalysis.sentiment': 'Sentiment',
      'eventAnalysis.score': 'Score',
      'eventAnalysis.noRecommendations': 'No recommendations available',
      'eventAnalysis.error': 'Error analyzing events',
      
      // Trending Tickers
      'trending.autoUpdating': 'Auto-updating every 10m',
      'trending.sortBy': 'Sort by:',
      'trending.sortMentions': 'Most Mentions',
      'trending.sortPositive': 'Best Sentiment (Positive)',
      'trending.sortNegative': 'Worst Sentiment (Negative)',
      'trending.sortAbs': 'Strongest Sentiment (Any)',
      'trending.priceRange': 'Price Range:',
      'trending.priceAll': 'All Prices (Default)',
      'trending.price0to5': '$0 - $5',
      'trending.price5to10': '$5 - $10',
      'trending.price10to25': '$10 - $25',
      'trending.price25to50': '$25 - $50',
      'trending.price50to100': '$50 - $100',
      'trending.price100to500': '$100 - $500',
      'trending.price500plus': '$500+',
      'trending.fetchingPrices': 'Fetching stock prices...',
      'trending.noPriceData': 'Price data not available',
      'trending.realtime': 'Real-time',
      'trending.fetchNewPosts': 'Fetch New Posts',
      'trending.allSources': 'All Sources',
      'trending.sourceReddit': 'Reddit',
      'trending.sourceNews': 'News',
      'trending.sourceTwitter': 'Twitter',
      'trending.sourceYoutube': 'YouTube',
      'trending.timeRange1h': 'Last 1 Hour',
      'trending.timeRange6h': 'Last 6 Hours',
      'trending.timeRange24h': 'Last 24 Hours',
      'trending.timeRange7d': 'Last 7 Days',
      'trending.timeRange30d': 'Last 30 Days',
      'trending.postsVeryFast': '25 posts/sub (Very Fast)',
      'trending.postsFast': '50 posts/sub (Fast)',
      'trending.postsBalanced': '100 posts/sub (Balanced - Max)',
      
      // Heatmap
      'heatmap.viewTicker': 'By Ticker',
      'heatmap.viewSector': 'By Sector',
      'heatmap.viewCountry': 'By Country',
      'heatmap.top10': 'Top 10',
      'heatmap.top20': 'Top 20',
      'heatmap.top50': 'Top 50',
      
      // Influencers
      'influencer.timeWindow1h': 'Last 1 hour',
      'influencer.timeWindow6h': 'Last 6 hours',
      'influencer.timeWindow24h': 'Last 24 hours',
      
      // Divergence
      'divergence.threshold': 'Threshold',
      
      // Raw Feed
      'rawFeed.removeDuplicates': 'Remove Duplicates',
      'rawFeed.cleanData': 'Clean Data',
      'rawFeed.collapse': 'Collapse',
      'rawFeed.expand': 'Expand',
      
      // Global Filters
      'filters.globalFilters': 'Global Filters',
      'filters.timeRange': 'Time Range',
      'filters.last5min': 'Last 5 minutes',
      'filters.last15min': 'Last 15 minutes',
      'filters.last1hour': 'Last 1 hour',
      'filters.last6hours': 'Last 6 hours',
      'filters.last24hours': 'Last 24 hours',
      'filters.last7days': 'Last 7 days',
      'filters.last30days': 'Last 30 days',
      'filters.customRange': 'Custom Range',
      'filters.dataSources': 'Data Sources',
      'filters.sourceReddit': 'Reddit',
      'filters.sourceNews': 'News (GDELT/NewsAPI)',
      'filters.sourceTrends': 'Google Trends',
      'filters.sourceTwitter': 'Twitter/X',
      'filters.sourceYoutube': 'YouTube',
      'filters.marketExchange': 'Market/Exchange',
      'filters.allMarkets': 'All Markets',
      'filters.marketUS': 'US',
      'filters.marketTH': 'TH',
      'filters.marketEU': 'EU',
      'filters.marketGlobal': 'Global',
      'filters.sector': 'Sector',
      'filters.allSectors': 'All Sectors',
      'filters.sectorTech': 'Technology',
      'filters.sectorFinancial': 'Financial',
      'filters.sectorEnergy': 'Energy',
      'filters.sectorConsumer': 'Consumer',
      'filters.sectorHealthcare': 'Healthcare',
      'filters.sectorCrypto': 'Crypto',
      'filters.sentimentType': 'Sentiment Type',
      'filters.sentimentAll': 'All',
      'filters.sentimentPositive': 'Positive',
      'filters.sentimentNeutral': 'Neutral',
      'filters.sentimentNegative': 'Negative',
      'filters.sentimentRange': 'Score Range',
      'filters.mentionType': 'Mention Type',
      'filters.mentionPosts': 'Posts',
      'filters.mentionComments': 'Comments',
      'filters.mentionHeadlines': 'Headlines',
      'filters.mentionTweets': 'Tweets',
      'filters.mentionTranscripts': 'Video Transcripts',
      'filters.language': 'Language',
      'filters.allLanguages': 'All Languages',
      'filters.languageEn': 'English',
      'filters.languageTh': 'Thai',
      'filters.minEngagement': 'Min Engagement',
      'filters.minUpvotes': 'Upvotes ≥',
      'filters.minComments': 'Comments ≥',
      'filters.minShares': 'Shares ≥',
      'filters.timeDecay': 'Time Decay',
      'filters.decayOff': 'Off',
      'filters.decayExponential': 'Exponential (alpha)',
      'filters.decayLinear': 'Linear (window)',
      'filters.weightingMode': 'Weighting Mode',
      'filters.weightingDefault': 'Default (upvotes+comments)',
      'filters.weightingEngagement': 'Engagement-only',
      'filters.weightingEqual': 'Equal-weight',
      'filters.alertMode': 'Alert Mode',
      'filters.applyFilters': 'Apply Filters',
      'filters.resetFilters': 'Reset',
      
      // Alerts
      'alerts.title': 'Alerts',
      'alerts.noAlerts': 'No alerts',
      
      // Sentiment
      'sentiment.positive': 'Positive',
      'sentiment.negative': 'Negative',
      'sentiment.neutral': 'Neutral',
      
      // Language
      'lang.english': 'English',
      'lang.thai': 'ไทย',
      'lang.switch': 'Switch Language',
      
      // Messages
      'msg.loadingDashboard': 'Loading dashboard data...',
      'msg.errorLoadingDashboard': 'Error loading dashboard data',
      'msg.noDataAvailable': 'No data available',
      'msg.noTickersAvailable': 'No tickers available',
      'msg.noInfluencersFound': 'No influencers found',
      'msg.noSparklineData': 'No sparkline data available',
      'msg.noDivergenceDetected': 'No divergence detected',
      'msg.noPostsFound': 'No posts found',
      'msg.failedLoadTrending': 'Failed to load trending tickers. Check API connection and database.',
      'msg.noDataToClean': 'No data to clean',
      'msg.removingDuplicates': 'Removing duplicates...',
      'msg.cleaningData': 'Cleaning data...',
      'msg.addingToWatchlist': 'Adding {ticker} to watchlist...',
      'msg.removedDuplicates': 'Removed {count} duplicate posts',
      'msg.cleanedData': 'Cleaned data: removed {count} posts',
      'msg.updated': 'Updated',
      'msg.realtime': 'Real-time',
      'msg.fetchingNewPosts': 'Fetching new posts from Reddit...',
      'msg.fetchedNewPosts': 'Fetched {count} new posts! Refreshing trending tickers...',
      'msg.errorFetchingPosts': 'Error: {error}',
      'msg.failedFetchPosts': 'Failed to fetch new posts. Check API connection.',
      'msg.addedToWatchlist': 'Added {ticker} to watchlist',
      'msg.addedToWatchlistOffline': 'Added {ticker} to watchlist (offline mode)',
      'msg.settingAlert': 'Setting alert for {ticker}'
    },
    
    th: {
      // Navigation
      'nav.home': 'หน้าแรก (ภาพรวม)',
      'nav.watchlist': 'รายการติดตาม / หุ้นของฉัน',
      'nav.compare': 'เปรียบเทียบ',
      'nav.stockDetail': 'รายละเอียดหุ้น',
      'nav.influencer': 'ติดตามผู้มีอิทธิพล',
      'nav.alerts': 'การแจ้งเตือน',
      'nav.dataExplorer': 'สำรวจข้อมูล / ฟีดดิบ',
      'nav.settings': 'การตั้งค่า',
      
      // Common
      'common.refresh': 'รีเฟรช',
      'common.loading': 'กำลังโหลด...',
      'common.error': 'เกิดข้อผิดพลาด',
      'common.success': 'สำเร็จ',
      'common.apply': 'ใช้',
      'common.reset': 'รีเซ็ต',
      'common.cancel': 'ยกเลิก',
      'common.save': 'บันทึก',
      'common.delete': 'ลบ',
      'common.edit': 'แก้ไข',
      'common.close': 'ปิด',
      'common.search': 'ค้นหา',
      'common.filter': 'กรอง',
      'common.filters': 'ตัวกรอง',
      'common.all': 'ทั้งหมด',
      'common.yes': 'ใช่',
      'common.no': 'ไม่',
      
      // Dashboard
      'dashboard.title': 'แดชบอร์ดความรู้สึกหุ้น',
      'dashboard.totalMentions': 'จำนวนการกล่าวถึงทั้งหมด',
      'dashboard.avgSentiment': 'คะแนนความรู้สึกเฉลี่ย',
      'dashboard.spikeEvents': 'เหตุการณ์เพิ่มขึ้น (24 ชม.)',
      'dashboard.activeAlerts': 'การแจ้งเตือนที่เปิดใช้งาน',
      'dashboard.viewAll': 'ดูทั้งหมด',
      'dashboard.last24h': '24 ชม. ที่แล้ว',
      
      // Widgets
      'widget.marketSentimentHeatmap': 'แผนที่ความร้อนความรู้สึกตลาด',
      'widget.trendingStockTickers': 'หุ้นที่กำลังเป็นที่นิยม',
      'widget.topInfluencers': 'ฟีดผู้มีอิทธิพล',
      'widget.mentionsVolume': 'ปริมาณการกล่าวถึง',
      'widget.priceSentimentDivergence': 'ความแตกต่างราคา vs ความรู้สึก',
      'widget.rawFeed': 'ฟีดดิบ',
      'widget.eventAnalysis': 'วิเคราะห์เหตุการณ์และคำแนะนำหุ้น',
      
      // Event Analysis
      'eventAnalysis.analyze': 'วิเคราะห์เหตุการณ์',
      'eventAnalysis.clickToAnalyze': 'คลิก "วิเคราะห์เหตุการณ์" เพื่อวิเคราะห์ข่าวจาก YouTube และรับคำแนะนำหุ้น',
      'eventAnalysis.loading': 'กำลังวิเคราะห์เหตุการณ์จากวิดีโอ YouTube...',
      'eventAnalysis.buyRecommendations': 'คำแนะนำซื้อ',
      'eventAnalysis.sellRecommendations': 'คำแนะนำขาย',
      'eventAnalysis.detectedEvents': 'เหตุการณ์ที่ตรวจจับได้',
      'eventAnalysis.confidence': 'ความมั่นใจ',
      'eventAnalysis.mentions': 'การกล่าวถึง',
      'eventAnalysis.reasons': 'เหตุผล',
      'eventAnalysis.sentiment': 'ความรู้สึก',
      'eventAnalysis.score': 'คะแนน',
      'eventAnalysis.noRecommendations': 'ไม่มีคำแนะนำ',
      'eventAnalysis.error': 'เกิดข้อผิดพลาดในการวิเคราะห์เหตุการณ์',
      
      // Trending Tickers
      'trending.autoUpdating': 'อัปเดตอัตโนมัติทุก 10 นาที',
      'trending.sortBy': 'เรียงตาม:',
      'trending.sortMentions': 'กล่าวถึงมากที่สุด',
      'trending.sortPositive': 'ความรู้สึกดีที่สุด (บวก)',
      'trending.sortNegative': 'ความรู้สึกแย่ที่สุด (ลบ)',
      'trending.sortAbs': 'ความรู้สึกแรงที่สุด (ใดๆ)',
      'trending.realtime': 'เรียลไทม์',
      'trending.fetchNewPosts': 'ดึงโพสต์ใหม่',
      'trending.allSources': 'ทุกแหล่ง',
      'trending.sourceReddit': 'Reddit',
      'trending.sourceNews': 'ข่าว',
      'trending.sourceTwitter': 'Twitter',
      'trending.sourceYoutube': 'YouTube',
      'trending.priceRange': 'ช่วงราคา:',
      'trending.priceAll': 'ทุกราคา (ค่าเริ่มต้น)',
      'trending.price0to5': '$0 - $5',
      'trending.price5to10': '$5 - $10',
      'trending.price10to25': '$10 - $25',
      'trending.price25to50': '$25 - $50',
      'trending.price50to100': '$50 - $100',
      'trending.price100to500': '$100 - $500',
      'trending.price500plus': '$500+',
      'trending.fetchingPrices': 'กำลังดึงราคาหุ้น...',
      'trending.noPriceData': 'ไม่มีข้อมูลราคา',
      'trending.timeRange1h': '1 ชั่วโมงที่แล้ว',
      'trending.timeRange6h': '6 ชั่วโมงที่แล้ว',
      'trending.timeRange24h': '24 ชั่วโมงที่แล้ว',
      'trending.timeRange7d': '7 วันที่แล้ว',
      'trending.timeRange30d': '30 วันที่แล้ว',
      'trending.postsVeryFast': '25 โพสต์/ซับ (เร็วมาก)',
      'trending.postsFast': '50 โพสต์/ซับ (เร็ว)',
      'trending.postsBalanced': '100 โพสต์/ซับ (สมดุล - สูงสุด)',
      
      // Heatmap
      'heatmap.viewTicker': 'ตามหุ้น',
      'heatmap.viewSector': 'ตามภาค',
      'heatmap.viewCountry': 'ตามประเทศ',
      'heatmap.top10': '10 อันดับแรก',
      'heatmap.top20': '20 อันดับแรก',
      'heatmap.top50': '50 อันดับแรก',
      
      // Influencers
      'influencer.timeWindow1h': '1 ชั่วโมงที่แล้ว',
      'influencer.timeWindow6h': '6 ชั่วโมงที่แล้ว',
      'influencer.timeWindow24h': '24 ชั่วโมงที่แล้ว',
      
      // Divergence
      'divergence.threshold': 'เกณฑ์',
      
      // Raw Feed
      'rawFeed.removeDuplicates': 'ลบรายการซ้ำ',
      'rawFeed.cleanData': 'ทำความสะอาดข้อมูล',
      'rawFeed.collapse': 'ย่อ',
      'rawFeed.expand': 'ขยาย',
      
      // Global Filters
      'filters.globalFilters': 'ตัวกรองทั่วไป',
      'filters.timeRange': 'ช่วงเวลา',
      'filters.last5min': '5 นาทีที่แล้ว',
      'filters.last15min': '15 นาทีที่แล้ว',
      'filters.last1hour': '1 ชั่วโมงที่แล้ว',
      'filters.last6hours': '6 ชั่วโมงที่แล้ว',
      'filters.last24hours': '24 ชั่วโมงที่แล้ว',
      'filters.last7days': '7 วันที่แล้ว',
      'filters.last30days': '30 วันที่แล้ว',
      'filters.customRange': 'ช่วงกำหนดเอง',
      'filters.dataSources': 'แหล่งข้อมูล',
      'filters.sourceReddit': 'Reddit',
      'filters.sourceNews': 'ข่าว (GDELT/NewsAPI)',
      'filters.sourceTrends': 'Google Trends',
      'filters.sourceTwitter': 'Twitter/X',
      'filters.sourceYoutube': 'YouTube',
      'filters.marketExchange': 'ตลาด/ตลาดหลักทรัพย์',
      'filters.allMarkets': 'ทุกตลาด',
      'filters.marketUS': 'สหรัฐ',
      'filters.marketTH': 'ไทย',
      'filters.marketEU': 'ยุโรป',
      'filters.marketGlobal': 'ทั่วโลก',
      'filters.sector': 'ภาค',
      'filters.allSectors': 'ทุกภาค',
      'filters.sectorTech': 'เทคโนโลยี',
      'filters.sectorFinancial': 'การเงิน',
      'filters.sectorEnergy': 'พลังงาน',
      'filters.sectorConsumer': 'ผู้บริโภค',
      'filters.sectorHealthcare': 'สุขภาพ',
      'filters.sectorCrypto': 'คริปโต',
      'filters.sentimentType': 'ประเภทความรู้สึก',
      'filters.sentimentAll': 'ทั้งหมด',
      'filters.sentimentPositive': 'บวก',
      'filters.sentimentNeutral': 'กลาง',
      'filters.sentimentNegative': 'ลบ',
      'filters.sentimentRange': 'ช่วงคะแนน',
      'filters.mentionType': 'ประเภทการกล่าวถึง',
      'filters.mentionPosts': 'โพสต์',
      'filters.mentionComments': 'ความคิดเห็น',
      'filters.mentionHeadlines': 'หัวข้อข่าว',
      'filters.mentionTweets': 'ทวีต',
      'filters.mentionTranscripts': 'คำบรรยายวิดีโอ',
      'filters.language': 'ภาษา',
      'filters.allLanguages': 'ทุกภาษา',
      'filters.languageEn': 'อังกฤษ',
      'filters.languageTh': 'ไทย',
      'filters.minEngagement': 'การมีส่วนร่วมขั้นต่ำ',
      'filters.minUpvotes': 'อัปโหวต ≥',
      'filters.minComments': 'ความคิดเห็น ≥',
      'filters.minShares': 'แชร์ ≥',
      'filters.timeDecay': 'การลดลงตามเวลา',
      'filters.decayOff': 'ปิด',
      'filters.decayExponential': 'เอกซ์โพเนนเชียล (alpha)',
      'filters.decayLinear': 'เชิงเส้น (window)',
      'filters.weightingMode': 'โหมดการถ่วงน้ำหนัก',
      'filters.weightingDefault': 'ค่าเริ่มต้น (อัปโหวต+ความคิดเห็น)',
      'filters.weightingEngagement': 'การมีส่วนร่วมเท่านั้น',
      'filters.weightingEqual': 'น้ำหนักเท่ากัน',
      'filters.alertMode': 'โหมดการแจ้งเตือน',
      'filters.applyFilters': 'ใช้ตัวกรอง',
      'filters.resetFilters': 'รีเซ็ต',
      
      // Alerts
      'alerts.title': 'การแจ้งเตือน',
      'alerts.noAlerts': 'ไม่มีการแจ้งเตือน',
      
      // Sentiment
      'sentiment.positive': 'บวก',
      'sentiment.negative': 'ลบ',
      'sentiment.neutral': 'กลาง',
      
      // Language
      'lang.english': 'English',
      'lang.thai': 'ไทย',
      'lang.switch': 'สลับภาษา',
      
      // Messages
      'msg.loadingDashboard': 'กำลังโหลดข้อมูลแดชบอร์ด...',
      'msg.errorLoadingDashboard': 'เกิดข้อผิดพลาดในการโหลดข้อมูลแดชบอร์ด',
      'msg.noDataAvailable': 'ไม่มีข้อมูล',
      'msg.noTickersAvailable': 'ไม่มีหุ้นที่พร้อมใช้งาน',
      'msg.noInfluencersFound': 'ไม่พบผู้มีอิทธิพล',
      'msg.noSparklineData': 'ไม่มีข้อมูลสปาร์คไลน์',
      'msg.noDivergenceDetected': 'ไม่พบความแตกต่าง',
      'msg.noPostsFound': 'ไม่พบโพสต์',
      'msg.failedLoadTrending': 'โหลดหุ้นที่กำลังเป็นที่นิยมล้มเหลว ตรวจสอบการเชื่อมต่อ API และฐานข้อมูล',
      'msg.noDataToClean': 'ไม่มีข้อมูลให้ทำความสะอาด',
      'msg.removingDuplicates': 'กำลังลบรายการซ้ำ...',
      'msg.cleaningData': 'กำลังทำความสะอาดข้อมูล...',
      'msg.addingToWatchlist': 'กำลังเพิ่ม {ticker} ลงในรายการติดตาม...',
      'msg.removedDuplicates': 'ลบโพสต์ซ้ำ {count} รายการ',
      'msg.cleanedData': 'ทำความสะอาดข้อมูล: ลบโพสต์ {count} รายการ',
      'msg.updated': 'อัปเดต',
      'msg.realtime': 'เรียลไทม์',
      'msg.fetchingNewPosts': 'กำลังดึงโพสต์ใหม่จาก Reddit...',
      'msg.fetchedNewPosts': 'ดึงโพสต์ใหม่ {count} รายการ! กำลังรีเฟรชหุ้นที่กำลังเป็นที่นิยม...',
      'msg.errorFetchingPosts': 'เกิดข้อผิดพลาด: {error}',
      'msg.failedFetchPosts': 'ดึงโพสต์ใหม่ล้มเหลว ตรวจสอบการเชื่อมต่อ API',
      'msg.addedToWatchlist': 'เพิ่ม {ticker} ลงในรายการติดตามแล้ว',
      'msg.addedToWatchlistOffline': 'เพิ่ม {ticker} ลงในรายการติดตามแล้ว (โหมดออฟไลน์)',
      'msg.settingAlert': 'กำลังตั้งค่าการแจ้งเตือนสำหรับ {ticker}'
    }
  },
  
  // Get translation for a key
  t(key, params = {}) {
    const translation = this.translations[this.currentLang]?.[key] || key;
    
    // Replace parameters if provided
    if (Object.keys(params).length > 0) {
      return translation.replace(/\{(\w+)\}/g, (match, param) => {
        return params[param] || match;
      });
    }
    
    return translation;
  },
  
  // Set language
  setLanguage(lang) {
    if (this.translations[lang]) {
      this.currentLang = lang;
      localStorage.setItem('language', lang);
      document.documentElement.lang = lang;
      this.updatePage();
      return true;
    }
    return false;
  },
  
  // Get current language
  getLanguage() {
    return this.currentLang;
  },
  
  // Update all elements with data-i18n attribute
  updatePage() {
    // Update elements with data-i18n attribute
    document.querySelectorAll('[data-i18n]').forEach(el => {
      const key = el.getAttribute('data-i18n');
      const translation = this.t(key);
      
      // Handle different element types
      if (el.tagName === 'INPUT' && el.type === 'button' || el.tagName === 'BUTTON') {
        el.textContent = translation;
      } else if (el.tagName === 'INPUT' && (el.type === 'text' || el.type === 'search')) {
        el.placeholder = translation;
      } else if (el.tagName === 'INPUT' && el.type === 'submit') {
        el.value = translation;
      } else if (el.tagName === 'TITLE') {
        el.textContent = translation;
      } else if (el.hasAttribute('title')) {
        el.title = translation;
      } else {
        el.textContent = translation;
      }
    });
    
    // Update option elements
    document.querySelectorAll('option[data-i18n]').forEach(option => {
      const key = option.getAttribute('data-i18n');
      option.textContent = this.t(key);
    });
    
    // Update placeholder attributes
    document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
      const key = el.getAttribute('data-i18n-placeholder');
      el.placeholder = this.t(key);
    });
    
    // Update title attributes
    document.querySelectorAll('[data-i18n-title]').forEach(el => {
      const key = el.getAttribute('data-i18n-title');
      el.title = this.t(key);
    });
    
    // Trigger custom event for other scripts to update
    window.dispatchEvent(new CustomEvent('languageChanged', { 
      detail: { language: this.currentLang } 
    }));
  },
  
  // Initialize i18n system
  init() {
    // Set document language
    document.documentElement.lang = this.currentLang;
    
    // Update page on load
    this.updatePage();
    
    // Listen for language change events
    window.addEventListener('languageChanged', () => {
      this.updatePage();
    });
  }
};

// Initialize on load
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => i18n.init());
} else {
  i18n.init();
}

// Export for use in other scripts
window.i18n = i18n;

