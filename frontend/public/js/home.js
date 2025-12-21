// Home/Overview Page Controller
const API_BASE_URL = 'http://localhost:5000/api';

let heatmapChart = null;
let sparklineCharts = {};
let rawFeedData = []; // Store raw feed data for filtering

// Load home page data
async function loadHomeData() {
  try {
    const loadingMsg = window.i18n?.t('msg.loadingDashboard') || 'Loading dashboard data...';
    showLoading(loadingMsg);
    
    // Load KPI summary
    await loadKPISummary();
    
    // Load heatmap
    await loadHeatmap();
    
    // Load trending topics
    await loadTrendingTopics();
    
    // Load influencers feed
    await loadInfluencersFeed();
    
    // Load sparklines
    await loadSparklines();
    
    // Load divergence panel
    await loadDivergencePanel();
    
    // Load raw feed
    await loadRawFeed();
    
    hideLoading();
  } catch (error) {
    console.error('Error loading home data:', error);
    const errorMsg = window.i18n?.t('msg.errorLoadingDashboard') || 'Error loading dashboard data';
    showNotification(errorMsg, 'error');
    hideLoading();
  }
}

async function refreshHomeData() {
  await loadHomeData();
}

// KPI Summary
async function loadKPISummary() {
  try {
    const filters = window.globalState?.filters || {};
    const timeRange = filters.timeRange || '24h';
    
    // Fetch dashboard summary from API
    const response = await fetch(`${API_BASE_URL}/dashboard?timeRange=${timeRange}`);
    
    if (!response.ok) {
      throw new Error('Failed to fetch dashboard summary');
    }
    
    const data = await response.json();
    const stats = data.stats || data;
    
    // Calculate total mentions from raw feed or aggregated data
    let totalMentions = stats.totalMentions || 0;
    if (!totalMentions && data.posts) {
      totalMentions = data.posts.length;
    }
    
    // Calculate average sentiment from all posts
    let avgSentiment = stats.avgSentiment || 0;
    if (!avgSentiment && data.posts && data.posts.length > 0) {
      const sentiments = data.posts
        .map(p => p.sentiment?.compound || p.sentiment_score || 0)
        .filter(s => s !== 0);
      if (sentiments.length > 0) {
        avgSentiment = sentiments.reduce((a, b) => a + b, 0) / sentiments.length;
      }
    }
    
    // Get spike events count
    let spikeEvents = stats.spikeEvents || 0;
    if (!spikeEvents && data.spikes) {
      spikeEvents = data.spikes.length;
    }
    
    // Get active alerts count
    let activeAlerts = stats.activeAlerts || 0;
    if (!activeAlerts) {
      try {
        const alertsResponse = await fetch(`${API_BASE_URL}/alerts`);
        if (alertsResponse.ok) {
          const alertsData = await alertsResponse.json();
          activeAlerts = (alertsData.alerts || []).filter(a => a.enabled !== false).length;
        }
      } catch (e) {
        console.error('Error fetching alerts:', e);
      }
    }
    
    // Update KPI cards
    if (document.getElementById('kpiTotalMentions')) {
      document.getElementById('kpiTotalMentions').textContent = formatNumber(totalMentions);
    }
    
    const mentionsChange = stats.mentionsChange || 0;
    const mentionsChangeEl = document.getElementById('kpiMentionsChange');
    if (mentionsChangeEl) {
      mentionsChangeEl.textContent = `${mentionsChange >= 0 ? '+' : ''}${mentionsChange.toFixed(1)}%`;
      mentionsChangeEl.className = `kpi-change ${mentionsChange >= 0 ? 'positive' : 'negative'}`;
    }
    
    if (document.getElementById('kpiAvgSentiment')) {
      document.getElementById('kpiAvgSentiment').textContent = avgSentiment.toFixed(2);
    }
    
    const sentimentChange = stats.sentimentChange || 0;
    const sentimentChangeEl = document.getElementById('kpiSentimentChange');
    if (sentimentChangeEl) {
      sentimentChangeEl.textContent = `${sentimentChange >= 0 ? '+' : ''}${sentimentChange.toFixed(2)}`;
      sentimentChangeEl.className = `kpi-change ${sentimentChange >= 0 ? 'positive' : 'negative'}`;
    }
    
    if (document.getElementById('kpiSpikeEvents')) {
      document.getElementById('kpiSpikeEvents').textContent = spikeEvents;
    }
    
    if (document.getElementById('kpiActiveAlerts')) {
      document.getElementById('kpiActiveAlerts').textContent = activeAlerts;
    }
    
  } catch (error) {
    console.error('Error loading KPI summary:', error);
    // Fallback to mock data
    if (document.getElementById('kpiTotalMentions')) {
      document.getElementById('kpiTotalMentions').textContent = '0';
    }
    if (document.getElementById('kpiAvgSentiment')) {
      document.getElementById('kpiAvgSentiment').textContent = '0.00';
    }
    if (document.getElementById('kpiSpikeEvents')) {
      document.getElementById('kpiSpikeEvents').textContent = '0';
    }
    if (document.getElementById('kpiActiveAlerts')) {
      document.getElementById('kpiActiveAlerts').textContent = '0';
    }
  }
}

// Market Sentiment Heatmap
async function loadHeatmap() {
  const container = document.getElementById('heatmapContainer');
  if (container) {
    showCardLoading(container.closest('.widget-card'));
  }
  
  try {
    const filters = window.globalState?.filters || {};
    const view = document.getElementById('heatmapView')?.value || 'ticker';
    const topN = parseInt(document.getElementById('heatmapTopN')?.value || '20');
    
    // Setup event listeners for heatmap controls
    const heatmapViewSelect = document.getElementById('heatmapView');
    const heatmapTopNSelect = document.getElementById('heatmapTopN');
    
    if (heatmapViewSelect && !heatmapViewSelect.hasAttribute('data-listener')) {
      heatmapViewSelect.setAttribute('data-listener', 'true');
      heatmapViewSelect.addEventListener('change', () => {
        showCardLoading(container?.closest('.widget-card'));
        loadHeatmap();
      });
    }
    
    if (heatmapTopNSelect && !heatmapTopNSelect.hasAttribute('data-listener')) {
      heatmapTopNSelect.setAttribute('data-listener', 'true');
      heatmapTopNSelect.addEventListener('change', () => {
        showCardLoading(container?.closest('.widget-card'));
        loadHeatmap();
      });
    }
    
    const response = await fetch(
      `${API_BASE_URL}/heatmap?view=${view}&topN=${topN}&timeRange=${filters.timeRange || '24h'}`
    );
    
    if (!response.ok) throw new Error('Failed to fetch heatmap data');
    
    const data = await response.json();
    renderHeatmap(data.items || data.heatmap || []);
    
    if (container) {
      hideCardLoading(container.closest('.widget-card'));
    }
  } catch (error) {
    console.error('Error loading heatmap:', error);
    // Fallback: render empty heatmap
    renderHeatmap([]);
    
    if (container) {
      hideCardLoading(container.closest('.widget-card'));
    }
  }
}

function renderHeatmap(items) {
  const container = document.getElementById('heatmapContainer');
  if (!container) return;
  
  container.innerHTML = '';
  
  if (items.length === 0) {
    const noDataMsg = window.i18n?.t('msg.noDataAvailable') || 'No data available';
    container.innerHTML = `<div class="loading">${noDataMsg}</div>`;
    return;
  }
  
  items.forEach(item => {
    const cell = document.createElement('div');
    cell.className = 'heatmap-cell';
    cell.style.cursor = 'pointer';
    
    // Calculate size based on mentions
    const maxMentions = Math.max(...items.map(i => i.mentions || i.count || 0));
    const mentions = item.mentions || item.count || 0;
    const sizePercent = maxMentions > 0 ? (mentions / maxMentions) * 100 : 50;
    
    // Calculate color based on sentiment
    const sentiment = item.sentiment || item.avgSentiment || 0;
    const color = getSentimentColor(sentiment);
    
    cell.style.background = color;
    cell.style.opacity = Math.max(0.4, Math.min(1, 0.4 + (sizePercent / 100) * 0.6));
    cell.style.minWidth = `${Math.max(80, 80 + (sizePercent / 100) * 40)}px`;
    cell.style.minHeight = `${Math.max(60, 60 + (sizePercent / 100) * 40)}px`;
    
    const label = item.ticker || item.sector || item.country || 'N/A';
    
    cell.innerHTML = `
      <div class="heatmap-ticker">${label}</div>
      <div class="heatmap-sentiment">${(sentiment * 100).toFixed(0)}%</div>
      <div class="heatmap-mentions">${formatNumber(mentions)}</div>
    `;
    
    // Tooltip
    cell.title = `${label}: ${mentions} mentions, ${(sentiment * 100).toFixed(1)}% sentiment`;
    
    // Click handler - navigate to stock detail or filter
    cell.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      
      if (item.ticker) {
        window.location.href = `stock-detail.html?symbol=${item.ticker}`;
      } else if (item.sector) {
        // Filter by sector
        if (window.globalState) {
          window.globalState.filters.sector = item.sector.toLowerCase();
          applyGlobalFilters();
        }
      }
    });
    
    // Hover effect
    cell.addEventListener('mouseenter', () => {
      cell.style.transform = 'scale(1.05)';
      cell.style.transition = 'transform 0.2s';
    });
    
    cell.addEventListener('mouseleave', () => {
      cell.style.transform = 'scale(1)';
    });
    
    container.appendChild(cell);
  });
}

function getSentimentColor(sentiment) {
  // Green for positive, red for negative, gray for neutral
  // รองรับ sentiment ตั้งแต่ -5.0 ถึง +5.0 (รองรับ -500% ถึง +500%)
  if (sentiment >= 0.05) {
    // Normalize intensity: sentiment 5.0 = opacity 1.0, sentiment 0.05 = opacity 0.3
    const intensity = Math.min(1.0, 0.3 + (Math.min(sentiment, 5.0) / 5.0) * 0.7);
    return `rgba(16, 185, 129, ${intensity})`;
  } else if (sentiment <= -0.05) {
    // Normalize intensity: sentiment -5.0 = opacity 1.0, sentiment -0.05 = opacity 0.3
    const intensity = Math.min(1.0, 0.3 + (Math.min(Math.abs(sentiment), 5.0) / 5.0) * 0.7);
    return `rgba(239, 68, 68, ${intensity})`;
  } else {
    return `rgba(107, 114, 128, 0.5)`;
  }
}

// Store current topics for filtering
let currentTopics = [];

// Function to fetch stock prices for trending tickers
async function fetchStockPricesForTickers(topics, forceFetch = false) {
  if (!topics || topics.length === 0) return;
  
  // Prevent fetching if already rendering or in search mode (unless forceFetch)
  if (!forceFetch && (isRenderingWordCloud || currentTickerSearch)) {
    console.log('⏳ Skipping price fetch - rendering in progress or in search mode');
    return;
  }
  
  // Get all tickers to fetch prices (increased from 30 to 100 to support price filtering)
  // This allows price filter to work properly for more stocks
  const topTickers = topics.slice(0, 100); // Increased limit for better price filtering
  const tickersToFetch = topTickers.map(t => t.ticker || t.word).filter(Boolean);
  
  if (tickersToFetch.length === 0) return;
  
  try {
    // Fetch prices in batches to avoid overwhelming the API
    const batchSize = 5;
    for (let i = 0; i < tickersToFetch.length; i += batchSize) {
      const batch = tickersToFetch.slice(i, i + batchSize);
      
      // ✅ Fetch prices for batch - ใช้ real-time เสมอเพื่อให้ได้ราคาล่าสุด
      const pricePromises = batch.map(async (ticker) => {
        try {
          // ✅ ใช้ realtime=true เสมอเพื่อให้ได้ราคาล่าสุด (ไม่ว่าจะเปิดหรือปิด real-time mode)
          const response = await fetch(`${API_BASE_URL}/stock/${ticker}/info?realtime=true`);
          if (response.ok) {
            const data = await response.json();
            return {
              ticker: ticker,
              price: data.currentPrice || 0,
              change: data.change || 0,
              changePercent: data.changePercent || 0
            };
          } else if (response.status === 404) {
            // Stock not found - skip silently (might be invalid ticker or index)
            console.log(`⚠️ Stock ${ticker} not found (404)`);
          }
        } catch (e) {
          console.log(`⚠️ Could not fetch price for ${ticker}:`, e);
        }
        return null;
      });
      
      const priceResults = await Promise.all(pricePromises);
      
      // Update topics with price data
      priceResults.forEach(priceData => {
        if (priceData) {
          const topic = topics.find(t => (t.ticker || t.word) === priceData.ticker);
          if (topic) {
            topic.currentPrice = priceData.price;
            topic.price = priceData.price;
            topic.priceChange = priceData.change;
            topic.priceChangePercent = priceData.changePercent;
          }
        }
      });
      
      // Small delay between batches to avoid rate limiting
      if (i + batchSize < tickersToFetch.length) {
        await new Promise(resolve => setTimeout(resolve, 200));
      }
    }
    
    console.log('✅ Fetched stock prices for', tickersToFetch.length, 'tickers');
    
    // ✅ อัปเดต currentTopics ด้วยข้อมูลราคาใหม่
    const updatedTopics = [...topics]; // สร้าง copy เพื่อไม่ให้ mutate original
    priceResults.forEach(priceData => {
      if (priceData) {
        const topic = updatedTopics.find(t => (t.ticker || t.word) === priceData.ticker);
        if (topic) {
          topic.currentPrice = priceData.price;
          topic.price = priceData.price;
          topic.priceChange = priceData.change;
          topic.priceChangePercent = priceData.changePercent;
        }
      }
    });
    
    // อัปเดต currentTopics
    currentTopics = updatedTopics;
    
    // ✅ Re-render word cloud with updated price data (จะแสดง price change percentage)
    // ใช้ skipPriceFetch=true เพื่อป้องกัน infinite loop
    console.log('🔄 Re-rendering word cloud with price data...');
    renderWordCloud(updatedTopics, skipPriceFetch=true);
    
  } catch (error) {
    console.error('❌ Error fetching stock prices:', error);
  }
}

// Trending Topics / Word Cloud
async function loadTrendingTopics() {
  const container = document.getElementById('wordcloudContainer');
  if (container) {
    showCardLoading(container.closest('.widget-card'));
  }
  
  try {
    const filters = window.globalState?.filters || {};
    const sourceSelect = document.getElementById('topicsSource');
    const timeRangeSelect = document.getElementById('topicsTimeRange');
    const realtimeToggle = document.getElementById('realtimeModeToggle');
    
    // ตรวจสอบว่าเปิด real-time mode หรือไม่
    const isRealtime = realtimeToggle?.checked || false;
    
    const source = sourceSelect?.value || 'all';
    const timeRange = timeRangeSelect?.value || filters.timeRange || '24h';
    
    // Add timestamp to prevent caching
    const timestamp = new Date().getTime();
    
    let response;
    let apiUrl;
    
    if (isRealtime) {
      // ใช้ real-time API (ดึงจากหลาย API sources)
      const limitSelect = document.getElementById('realtimeLimit');
      const limit = limitSelect?.value || '50';
      // ใช้ source จาก dropdown (all, reddit, news, twitter)
      const realtimeSource = source === 'all' ? 'all' : (source === 'reddit' ? 'reddit' : (source === 'news' ? 'news' : (source === 'twitter' ? 'twitter' : 'all')));
      console.log('🔄 Loading REAL-TIME trending tickers from multiple APIs at', new Date().toLocaleTimeString());
      console.log(`   Sources: ${realtimeSource}`);
      console.log(`   Limit: ${limit} posts per subreddit`);
      apiUrl = `${API_BASE_URL}/trending-realtime?source=${realtimeSource}&subreddits=all,stocks,investing,StockMarket,wallstreetbets&limit=${limit}&sort=hot&_t=${timestamp}`;
      response = await fetch(apiUrl);
    } else {
      // ใช้ database API (ดึงจาก database)
      console.log('🔄 Loading trending stock tickers from database for source:', source, 'timeRange:', timeRange, 'at', new Date().toLocaleTimeString());
      apiUrl = `${API_BASE_URL}/trending-topics?source=${source}&timeRange=${timeRange}&_t=${timestamp}`;
      response = await fetch(apiUrl);
    }
    
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Failed to fetch trending topics: ${response.status} - ${errorText}`);
    }
    
    const data = await response.json();
    
    // ✅ Debug: ตรวจสอบ sentiment ใน topics
    if (data.topics && data.topics.length > 0) {
      const sampleTopics = data.topics.slice(0, 5);
      console.log('🔍 Sample topics with sentiment:', sampleTopics.map(t => ({
        ticker: t.ticker,
        count: t.count,
        avgSentiment: t.avgSentiment,
        hasSentiment: t.avgSentiment !== undefined && t.avgSentiment !== null
      })));
    }
    
    if (isRealtime) {
      console.log('✅ Received REAL-TIME tickers:', data.topics?.length || 0, 'tickers from', data.source || 'multiple sources', 'totalPosts:', data.totalPosts || 0);
      if (data.sourceBreakdown) {
        console.log('📊 Source breakdown:', data.sourceBreakdown);
      }
      console.log('📅 Fetched at:', data.fetchedAt || 'N/A');
      
      // Don't fetch prices here - let renderWordCloud handle it to prevent infinite loops
      // Prices will be fetched after rendering if needed
    } else {
      console.log('✅ Received tickers:', data.topics?.length || 0, 'tickers from source:', source, 'totalPosts:', data.totalPosts || 0, 'totalTickers:', data.totalTickers || 0);
      if (data.totalPostsInDatabase !== undefined) {
        console.log('📊 Total posts in database:', data.totalPostsInDatabase);
      }
      if (data.message) {
        console.log('💡 Message:', data.message);
      }
      if (data.tip) {
        console.log('💡 Tip:', data.tip);
      }
      
      // Don't fetch prices here - let renderWordCloud handle it to prevent infinite loops
      // Prices will be fetched after rendering if needed
    }
    
    // Log top 3 for verification
    if (data.topics && data.topics.length > 0) {
      const top3 = data.topics.slice(0, 3).map(t => `$${t.ticker} (${t.count} mentions)`).join(', ');
      console.log('🏆 Top 3 trending:', top3);
    }
    
    let topics = data.topics || data.words || [];
    
    // ✅ Debug: ตรวจสอบข้อมูลที่ได้รับ
    if (!isRealtime) {
      console.log('📊 Database mode data:', {
        topicsCount: topics.length,
        totalPosts: data.totalPosts,
        totalTickers: data.totalTickers,
        source: source,
        timeRange: timeRange,
        message: data.message,
        tip: data.tip
      });
    }
    
    // NEVER use mock data - always show real data or empty state
    if (topics.length === 0) {
      if (data.totalPosts > 0) {
        console.log('⚠️ No stock tickers ($SYMBOL) extracted from', data.totalPosts, 'posts');
        console.log('💡 This might mean posts don\'t contain ticker symbols in $SYMBOL format');
        console.log('💡 Posts may not contain stock tickers in $SYMBOL format (e.g., $AAPL, $TSLA)');
      } else {
        console.log('⚠️ No posts found in database for the selected time range and source');
        console.log('💡 Try: 1) Expanding time range, 2) Selecting different source, 3) Fetching new data');
      }
    }
    
    // Get sort option and apply sorting
    const sortBy = document.getElementById('trendingSortBy')?.value || 'mentions';
    
    if (sortBy === 'sentiment-positive') {
      // Sort by sentiment (highest positive first)
      topics = topics.sort((a, b) => {
        const sentimentA = a.avgSentiment || 0;
        const sentimentB = b.avgSentiment || 0;
        return sentimentB - sentimentA; // Descending (positive first)
      });
    } else if (sortBy === 'sentiment-negative') {
      // Sort by sentiment (most negative first)
      topics = topics.sort((a, b) => {
        const sentimentA = a.avgSentiment || 0;
        const sentimentB = b.avgSentiment || 0;
        return sentimentA - sentimentB; // Ascending (negative first)
      });
    } else if (sortBy === 'sentiment-abs') {
      // Sort by absolute sentiment (strongest sentiment first, regardless of direction)
      topics = topics.sort((a, b) => {
        const sentimentA = Math.abs(a.avgSentiment || 0);
        const sentimentB = Math.abs(b.avgSentiment || 0);
        return sentimentB - sentimentA; // Descending (strongest first)
      });
    } else {
      // Default: Sort by mention count (most mentioned first)
      topics = topics.sort((a, b) => (b.count || b.mentions || 0) - (a.count || a.mentions || 0));
    }
    
    // Store current topics
    currentTopics = topics;
    
    // ✅ ตรวจสอบ price range filter - ถ้าไม่ใช่ "all" ให้ดึงราคาก่อน render
    const priceRangeFilter = document.getElementById('priceRangeFilter')?.value || 'all';
    const needsPriceFilter = priceRangeFilter !== 'all';
    
    // Only render if not in search mode
    if (!currentTickerSearch) {
      if (needsPriceFilter && topics.length > 0) {
        // ถ้าใช้ price filter ให้ดึงราคาก่อน render
        console.log(`💰 Price filter active (${priceRangeFilter}), fetching prices first...`);
        const tickersNeedingPrice = topics.filter(t => {
          const price = t.currentPrice || t.price || 0;
          return price === 0 || price === null || price === undefined;
        });
        
        if (tickersNeedingPrice.length > 0) {
          // แสดง loading message
          const container = document.getElementById('wordcloudContainer');
          if (container) {
            container.innerHTML = `
              <div style="padding: 2rem; text-align: center; color: #94a3b8;">
                <p>💰 Fetching prices for ${tickersNeedingPrice.length} tickers...</p>
                <p style="font-size: 0.875rem; margin-top: 0.5rem;">
                  Please wait while we fetch stock prices to apply price filter
                </p>
              </div>
            `;
          }
          
          // ดึงราคา (force fetch เพื่อให้ทำงานแม้จะกำลัง render)
          await fetchStockPricesForTickers(tickersNeedingPrice, forceFetch=true);
          
          // อัปเดต currentTopics ด้วยราคาใหม่
          topics.forEach(topic => {
            const updated = tickersNeedingPrice.find(t => (t.ticker || t.word) === (topic.ticker || topic.word));
            if (updated && updated.currentPrice) {
              topic.currentPrice = updated.currentPrice;
              topic.price = updated.price;
              topic.priceChange = updated.priceChange;
              topic.priceChangePercent = updated.priceChangePercent;
            }
          });
          currentTopics = topics;
        }
      }
      
      // Render word cloud with fetched data (will fetch prices after rendering if needed)
      renderWordCloud(topics);
    } else {
      console.log('🔍 In search mode, skipping trending topics render');
    }
    
    // Update indicator
    const indicator = document.getElementById('trendingUpdateIndicator');
    if (indicator) {
      const now = new Date();
      const updatedText = window.i18n?.t('msg.updated') || 'Updated';
      const realtimeText = window.i18n?.t('msg.realtime') || 'Real-time';
      const modeText = isRealtime ? ` [${realtimeText}]` : '';
      indicator.textContent = `(${updatedText}: ${now.toLocaleTimeString()}${modeText})`;
      indicator.style.color = '#10b981';
      setTimeout(() => {
        if (indicator) indicator.style.color = '#94a3b8';
      }, 2000);
    }

    
    
    if (container) {
      hideCardLoading(container.closest('.widget-card'));
    }
  } catch (error) {
    console.error('❌ Error loading trending topics:', error);
    
    // Show empty state instead of mock data
    currentTopics = [];
    renderWordCloud([]);
    
    if (container) {
      hideCardLoading(container.closest('.widget-card'));
    }
    
    const errorMsg = window.i18n?.t('msg.failedLoadTrending') || 'Failed to load trending tickers. Check API connection and database.';
    showNotification(errorMsg, 'error');
  }
}

// Generate mock trending stock tickers for fallback
function generateMockTrendingTopics(source = 'all') {
  // Mock stock tickers with $SYMBOL format
  const commonTickers = [
    { word: 'AAPL', ticker: 'AAPL', count: 245, mentions: 245, sources: ['reddit', 'news', 'twitter'], sourceCount: 3, avgSentiment: 0.35 },
    { word: 'TSLA', ticker: 'TSLA', count: 198, mentions: 198, sources: ['reddit', 'twitter'], sourceCount: 2, avgSentiment: -0.12 },
    { word: 'NVDA', ticker: 'NVDA', count: 187, mentions: 187, sources: ['reddit', 'news'], sourceCount: 2, avgSentiment: 0.58 },
    { word: 'MSFT', ticker: 'MSFT', count: 156, mentions: 156, sources: ['news', 'reddit'], sourceCount: 2, avgSentiment: 0.42 },
    { word: 'AMZN', ticker: 'AMZN', count: 134, mentions: 134, sources: ['reddit', 'news'], sourceCount: 2, avgSentiment: 0.28 },
    { word: 'GOOGL', ticker: 'GOOGL', count: 112, mentions: 112, sources: ['news'], sourceCount: 1, avgSentiment: 0.15 },
    { word: 'META', ticker: 'META', count: 98, mentions: 98, sources: ['reddit', 'twitter'], sourceCount: 2, avgSentiment: 0.22 },
    { word: 'AMD', ticker: 'AMD', count: 87, mentions: 87, sources: ['reddit'], sourceCount: 1, avgSentiment: 0.45 },
    { word: 'NFLX', ticker: 'NFLX', count: 76, mentions: 76, sources: ['news', 'reddit'], sourceCount: 2, avgSentiment: -0.08 },
    { word: 'SPY', ticker: 'SPY', count: 65, mentions: 65, sources: ['reddit', 'news'], sourceCount: 2, avgSentiment: 0.12 }
  ];
  
  const redditTickers = [
    { word: 'GME', ticker: 'GME', count: 320, mentions: 320, sources: ['reddit'], sourceCount: 1, avgSentiment: 0.65 },
    { word: 'AMC', ticker: 'AMC', count: 145, mentions: 145, sources: ['reddit'], sourceCount: 1, avgSentiment: 0.38 },
    { word: 'BBBY', ticker: 'BBBY', count: 89, mentions: 89, sources: ['reddit'], sourceCount: 1, avgSentiment: 0.25 },
    { word: 'PLTR', ticker: 'PLTR', count: 67, mentions: 67, sources: ['reddit'], sourceCount: 1, avgSentiment: 0.18 },
    { word: 'SOFI', ticker: 'SOFI', count: 54, mentions: 54, sources: ['reddit'], sourceCount: 1, avgSentiment: 0.12 }
  ];
  
  const newsTickers = [
    { word: 'JPM', ticker: 'JPM', count: 156, mentions: 156, sources: ['news'], sourceCount: 1, avgSentiment: 0.22 },
    { word: 'BAC', ticker: 'BAC', count: 134, mentions: 134, sources: ['news'], sourceCount: 1, avgSentiment: 0.18 },
    { word: 'WMT', ticker: 'WMT', count: 98, mentions: 98, sources: ['news'], sourceCount: 1, avgSentiment: 0.15 },
    { word: 'JNJ', ticker: 'JNJ', count: 87, mentions: 87, sources: ['news'], sourceCount: 1, avgSentiment: 0.12 },
    { word: 'PG', ticker: 'PG', count: 76, mentions: 76, sources: ['news'], sourceCount: 1, avgSentiment: 0.08 }
  ];
  
  if (source === 'reddit') {
    return [...commonTickers.slice(0, 5), ...redditTickers].sort((a, b) => b.count - a.count);
  } else if (source === 'news') {
    return [...commonTickers.slice(0, 5), ...newsTickers].sort((a, b) => b.count - a.count);
  } else {
    // Mix all tickers for 'all' source
    return [...commonTickers, ...redditTickers.slice(0, 3), ...newsTickers.slice(0, 3)]
      .sort((a, b) => b.count - a.count)
      .slice(0, 30);
  }
}

// Flag to prevent renderWordCloud from calling fetchStockPricesForTickers recursively
let isRenderingWordCloud = false;

function renderWordCloud(topics, skipPriceFetch = false) {
  const container = document.getElementById('wordcloudContainer');
  if (!container) return;
  
  // Prevent recursive calls
  if (isRenderingWordCloud && !skipPriceFetch) {
    console.log('⏳ renderWordCloud already in progress, skipping...');
    return;
  }
  
  isRenderingWordCloud = true;
  
  // Clear container completely
  container.innerHTML = '';
  
  if (!topics || topics.length === 0) {
    // Check if this is from a search (not just empty trending list)
    // If currentTickerSearch is set, the search function should handle its own error messages
    if (!currentTickerSearch) {
      container.innerHTML = `
        <div style="padding: 2rem; text-align: center; color: #94a3b8;">
          <p>No trending stock tickers found.</p>
          <p style="font-size: 0.875rem; margin-top: 0.5rem;">
            Make sure posts contain stock tickers in <strong>$SYMBOL</strong> format (e.g., $AAPL, $TSLA)
            <br>• Try changing the source filter
            <br>• Fetching more data from Reddit/News/Twitter
            <br>• Expanding the time range
            <br>• Use the search box above to find specific tickers
          </p>
        </div>
      `;
    }
    // If currentTickerSearch is set, don't show default message - let search function handle it
    isRenderingWordCloud = false;
    return;
  }
  
  // Get sort option and apply sorting
  const sortBy = document.getElementById('trendingSortBy')?.value || 'mentions';
  
  // Get price filter from dropdown
  const priceRangeFilter = document.getElementById('priceRangeFilter')?.value || 'all';
  let minPrice = 0;
  let maxPrice = Infinity;
  let priceFilterActive = false;
  
  // Parse price range from dropdown value
  if (priceRangeFilter !== 'all') {
    priceFilterActive = true;
    if (priceRangeFilter === '0-5') {
      minPrice = 0;
      maxPrice = 5;
    } else if (priceRangeFilter === '5-10') {
      minPrice = 5;
      maxPrice = 10;
    } else if (priceRangeFilter === '10-25') {
      minPrice = 10;
      maxPrice = 25;
    } else if (priceRangeFilter === '25-50') {
      minPrice = 25;
      maxPrice = 50;
    } else if (priceRangeFilter === '50-100') {
      minPrice = 50;
      maxPrice = 100;
    } else if (priceRangeFilter === '100-500') {
      minPrice = 100;
      maxPrice = 500;
    } else if (priceRangeFilter === '500+') {
      minPrice = 500;
      maxPrice = Infinity;
    }
  }
  
  let sortedTopics = [...topics];
  
  // Apply price filter if active
  if (priceFilterActive) {
    // Filter topics that have price data and are within range
    const topicsWithPrice = sortedTopics.filter(topic => {
      const tickerPrice = topic.currentPrice || topic.price || 0;
      // Only filter if price is available (not 0 or null)
      if (tickerPrice === 0 || tickerPrice === null || tickerPrice === undefined) {
        return false; // Hide tickers without price data when filtering
      }
      if (maxPrice === Infinity) {
        return tickerPrice >= minPrice;
      }
      return tickerPrice >= minPrice && tickerPrice <= maxPrice;
    });
    
    // Count tickers without price data
    const tickersWithoutPrice = sortedTopics.filter(t => {
      const price = t.currentPrice || t.price || 0;
      return price === 0 || price === null || price === undefined;
    });
    
    // If we have results with price, use them
    if (topicsWithPrice.length > 0) {
      sortedTopics = topicsWithPrice;
      console.log(`✅ Found ${topicsWithPrice.length} tickers in price range $${minPrice} - ${maxPrice === Infinity ? '∞' : '$' + maxPrice}`);
      if (tickersWithoutPrice.length > 0) {
        console.log(`   ⚠️ ${tickersWithoutPrice.length} tickers hidden (no price data yet)`);
      }
    } else {
      // No tickers in range
      if (tickersWithoutPrice.length > 0) {
        // มี tickers แต่ไม่มีราคา
        console.log(`⚠️ No tickers with price data in range $${minPrice} - ${maxPrice === Infinity ? '∞' : '$' + maxPrice}`);
        console.log(`💡 ${tickersWithoutPrice.length} tickers found but don't have price data yet. Prices are being fetched...`);
        
        // Show message to user
        const container = document.getElementById('wordcloudContainer');
        if (container) {
          container.innerHTML = `
            <div style="padding: 2rem; text-align: center; color: #94a3b8;">
              <p>⏳ Fetching prices for tickers...</p>
              <p style="font-size: 0.875rem; margin-top: 0.5rem;">
                Found ${tickersWithoutPrice.length} tickers but prices are still loading.
                <br>Please wait a moment and the filter will apply automatically.
                <br>Or try selecting "All Prices" to see all tickers.
              </p>
              <button onclick="document.getElementById('priceRangeFilter').value='all'; document.getElementById('priceRangeFilter').dispatchEvent(new Event('change'));" 
                      style="margin-top: 1rem; padding: 0.5rem 1rem; background: #3b82f6; color: white; border: none; border-radius: 4px; cursor: pointer;">
                Show All Prices
              </button>
            </div>
          `;
        }
        isRenderingWordCloud = false;
        return; // Don't render anything yet
      } else {
        // ไม่มี tickers ใน range นี้เลย
        console.log(`⚠️ No tickers found in price range $${minPrice} - ${maxPrice === Infinity ? '∞' : '$' + maxPrice}`);
        const container = document.getElementById('wordcloudContainer');
        if (container) {
          container.innerHTML = `
            <div style="padding: 2rem; text-align: center; color: #94a3b8;">
              <p>📊 No tickers found in price range $${minPrice} - ${maxPrice === Infinity ? '∞' : '$' + maxPrice}</p>
              <p style="font-size: 0.875rem; margin-top: 0.5rem;">
                Try selecting a different price range or "All Prices" to see all tickers.
              </p>
              <button onclick="document.getElementById('priceRangeFilter').value='all'; document.getElementById('priceRangeFilter').dispatchEvent(new Event('change'));" 
                      style="margin-top: 1rem; padding: 0.5rem 1rem; background: #3b82f6; color: white; border: none; border-radius: 4px; cursor: pointer;">
                Show All Prices
              </button>
            </div>
          `;
        }
        isRenderingWordCloud = false;
        return;
      }
    }
  }
  
  if (sortBy === 'sentiment-positive') {
    // Sort by sentiment (highest positive first)
    sortedTopics = sortedTopics.sort((a, b) => {
      const sentimentA = a.avgSentiment || 0;
      const sentimentB = b.avgSentiment || 0;
      return sentimentB - sentimentA; // Descending (positive first)
    });
  } else if (sortBy === 'sentiment-negative') {
    // Sort by sentiment (most negative first)
    sortedTopics = sortedTopics.sort((a, b) => {
      const sentimentA = a.avgSentiment || 0;
      const sentimentB = b.avgSentiment || 0;
      return sentimentA - sentimentB; // Ascending (negative first)
    });
  } else if (sortBy === 'sentiment-abs') {
    // Sort by absolute sentiment (strongest sentiment first)
    sortedTopics = sortedTopics.sort((a, b) => {
      const sentimentA = Math.abs(a.avgSentiment || 0);
      const sentimentB = Math.abs(b.avgSentiment || 0);
      return sentimentB - sentimentA; // Descending (strongest first)
    });
  } else {
    // Default: Sort by mention count (most mentioned FIRST)
    sortedTopics = sortedTopics.sort((a, b) => {
      const countA = a.count || a.mentions || a.frequency || 0;
      const countB = b.count || b.mentions || b.frequency || 0;
      return countB - countA; // Descending order - highest first
    });
  }
  
  // Take top 50
  sortedTopics = sortedTopics.slice(0, 50);
  
  // Log top 3 for verification
  if (sortedTopics.length > 0) {
    console.log('📊 Displaying top tickers:', sortedTopics.slice(0, 3).map(t => {
      const ticker = t.ticker || t.word || 'UNKNOWN';
      const count = t.count || t.mentions || 0;
      return `$${ticker} (${count})`;
    }).join(', '));
  }
  
  if (sortedTopics.length === 0) {
    const noTickersMsg = window.i18n?.t('msg.noTickersAvailable') || 'No tickers available';
    container.innerHTML = `<div class="loading" style="padding: 2rem; text-align: center; color: #94a3b8;">${noTickersMsg}</div>`;
    return;
  }
  
  const maxCount = Math.max(...sortedTopics.map(t => t.count || t.mentions || t.frequency || 0));
  
  sortedTopics.forEach((topic, index) => {
    const tag = document.createElement('span');
    tag.className = 'word-tag';
    tag.style.cursor = 'pointer';
    tag.style.display = 'inline-block';
    tag.style.margin = '0.25rem';
    tag.style.padding = '0.5rem 0.75rem';
    tag.style.borderRadius = '6px';
    tag.style.transition = 'all 0.2s';
    tag.style.userSelect = 'none';
    
    // Get ticker symbol
    const ticker = topic.ticker || topic.word || 'UNKNOWN';
    const count = topic.count || topic.mentions || topic.frequency || 0;
    const sources = topic.sources || [];
    const sourceCount = topic.sourceCount || sources.length || 1;
    // ✅ ใช้ adjustedSentiment (filtered pump/dump) ถ้ามี, ไม่งั้นใช้ avgSentiment
    const sentiment = topic.adjustedSentiment !== undefined ? topic.adjustedSentiment :
                     (topic.avgSentiment !== undefined ? topic.avgSentiment : 
                     (topic.avg_sentiment !== undefined ? topic.avg_sentiment : 0));
    
    // ✅ ตรวจสอบ trust score และ pump/dump status
    const trustScore = topic.trustScore !== undefined ? topic.trustScore : 100;
    const isPumpDump = topic.isPumpDump || false;
    const riskScore = topic.riskScore !== undefined ? topic.riskScore : 0;
    
    // ✅ Debug: แสดง sentiment ถ้าเป็น 0 (เฉพาะ 5 ตัวแรก)
    if (Object.keys(topics).indexOf(ticker) < 5 && sentiment === 0) {
      console.log(`⚠️  Ticker ${ticker} has sentiment = 0`, {
        avgSentiment: topic.avgSentiment,
        avg_sentiment: topic.avg_sentiment,
        topic: topic
      });
    }
    
    // Size based on mention frequency
    const size = 0.75 + (count / maxCount) * 1.25;
    tag.style.fontSize = `${size}rem`;
    tag.style.fontWeight = count > maxCount * 0.5 ? '600' : '400';
    
    // Color based on sentiment - รองรับ sentiment ตั้งแต่ -5.0 ถึง +5.0
    // ความเข้มของสีจะขึ้นอยู่กับค่าสัมบูรณ์ของ sentiment
    let sentimentColor, sentimentBg, sentimentIcon, sentimentText;
    const absSentiment = Math.abs(sentiment);
    
    if (sentiment > 0.1) {
      // Positive: ความเข้มขึ้นอยู่กับค่า sentiment (0.1-5.0)
      const intensity = Math.min(1.0, 0.3 + (Math.min(sentiment, 5.0) / 5.0) * 0.7);
      sentimentColor = '#10b981'; // Green for positive
      sentimentBg = `rgba(16, 185, 129, ${0.1 + intensity * 0.2})`; // Background intensity based on sentiment
      sentimentIcon = sentiment > 2.0 ? '🚀' : sentiment > 1.0 ? '📈📈' : '📈'; // Different icons for extreme sentiment
      sentimentText = sentiment > 2.0 ? 'Very Positive' : sentiment > 1.0 ? 'Strong Positive' : 'Positive';
    } else if (sentiment < -0.1) {
      // Negative: ความเข้มขึ้นอยู่กับค่าสัมบูรณ์ของ sentiment (0.1-5.0)
      const intensity = Math.min(1.0, 0.3 + (Math.min(absSentiment, 5.0) / 5.0) * 0.7);
      sentimentColor = '#ef4444'; // Red for negative
      sentimentBg = `rgba(239, 68, 68, ${0.1 + intensity * 0.2})`; // Background intensity based on sentiment
      sentimentIcon = sentiment < -2.0 ? '💥' : sentiment < -1.0 ? '📉📉' : '📉'; // Different icons for extreme sentiment
      sentimentText = sentiment < -2.0 ? 'Very Negative' : sentiment < -1.0 ? 'Strong Negative' : 'Negative';
    } else {
      sentimentColor = '#6b7280'; // Gray for neutral
      sentimentBg = 'rgba(107, 114, 128, 0.1)'; // Light gray background
      sentimentIcon = '➡️';
      sentimentText = 'Neutral';
    }
    
    // ✅ ถ้าเป็น pump/dump หรือ trust score ต่ำ → เปลี่ยนสี border เป็นแดง
    if (isPumpDump || trustScore < 50) {
      tag.style.borderColor = '#ef4444'; // Red border for pump/dump
      tag.style.borderWidth = '3px';
      tag.style.backgroundColor = 'rgba(239, 68, 68, 0.1)'; // Light red background
    } else {
      tag.style.borderColor = sentimentColor;
      tag.style.borderWidth = '2px';
      tag.style.backgroundColor = sentimentBg;
    }
    tag.style.borderStyle = 'solid';
    tag.style.color = sentimentColor;
    tag.style.fontWeight = '600';
    
    // Display ticker with $ prefix + sentiment indicator + price (if available)
    // แสดง sentiment percentage ตามค่าจริง ไม่จำกัดที่ 100%
    const sentimentPercent = (sentiment * 100).toFixed(1); // ใช้ 1 ทศนิยมเพื่อความแม่นยำ
    const tickerPrice = topic.currentPrice || topic.price || null;
    const priceDisplay = tickerPrice ? `$${tickerPrice.toFixed(2)}` : '';
    
    // ✅ แสดง price change percentage ถ้ามี (สำคัญกว่าสำหรับผู้ใช้)
    const priceChangePercent = topic.priceChangePercent !== undefined ? topic.priceChangePercent : null;
    const priceChangeDisplay = priceChangePercent !== null ? 
      `<span style="font-size: 0.7em; font-weight: 500; color: ${priceChangePercent >= 0 ? '#10b981' : '#ef4444'};">
        ${priceChangePercent >= 0 ? '+' : ''}${priceChangePercent.toFixed(2)}%
      </span>` : 
      `<span style="font-size: 0.7em; font-weight: 500; color: #94a3b8;">0.0%</span>`;
    
    // ✅ แสดง sentiment percentage (สำคัญ!)
    // ถ้า trust score ต่ำหรือเป็น pump/dump → แสดง warning
    let sentimentDisplayStyle = '';
    let sentimentWarning = '';
    
    if (isPumpDump || trustScore < 50) {
      // แสดง warning icon สำหรับ pump/dump
      sentimentDisplayStyle = 'border-left: 3px solid #ef4444; padding-left: 0.25rem;';
      sentimentWarning = `<span style="font-size: 0.6em; color: #ef4444; margin-left: 0.25rem;" title="⚠️ Pump/Dump Risk: ${riskScore}%">⚠️</span>`;
    }
    
    const sentimentDisplay = sentiment !== 0 ? 
      `<span style="font-size: 0.7em; font-weight: 500; color: ${sentimentColor}; margin-left: 0.25rem; ${sentimentDisplayStyle}">
        ${sentimentPercent > 0 ? '+' : ''}${sentimentPercent}%
      </span>${sentimentWarning}` : 
      `<span style="font-size: 0.7em; font-weight: 500; color: #94a3b8; margin-left: 0.25rem;">0.0%</span>`;
    
    tag.innerHTML = `
      <span style="display: flex; align-items: center; gap: 0.25rem; flex-wrap: wrap;">
        <span>$${ticker}</span>
        ${priceDisplay ? `<span style="font-size: 0.7em; color: #94a3b8;">${priceDisplay}</span>` : ''}
        <span style="font-size: 0.75em; opacity: 0.8;">${sentimentIcon}</span>
        ${sentimentDisplay}
        ${priceChangeDisplay}
      </span>
    `;
    
    // Tooltip with detailed info
    const tooltipSentimentPercent = (sentiment * 100).toFixed(1);
    const priceInfo = tickerPrice ? `\nPrice: $${tickerPrice.toFixed(2)}` : '\nPrice: Loading...';
    const priceChangeInfo = priceChangePercent !== null ? 
      `\nPrice Change: ${priceChangePercent >= 0 ? '+' : ''}${priceChangePercent.toFixed(2)}%` : 
      '\nPrice Change: Loading...';
    // ✅ เพิ่ม trust score และ pump/dump info ใน tooltip
    const trustInfo = trustScore < 100 ? `\nTrust Score: ${trustScore}%${isPumpDump ? ' (⚠️ Pump/Dump Risk)' : ''}` : '';
    const riskInfo = riskScore > 0 ? `\nRisk Score: ${riskScore}%` : '';
    const recommendation = topic.recommendation ? `\n💡 ${topic.recommendation}` : '';
    
    const tooltip = `$${ticker}: ${count} mentions${priceInfo}${priceChangeInfo}
${sourceCount} source${sourceCount > 1 ? 's' : ''}: ${sources.join(', ')}
Sentiment: ${sentimentText} (${tooltipSentimentPercent > 0 ? '+' : ''}${tooltipSentimentPercent}%)
Raw sentiment: ${sentiment.toFixed(3)}${trustInfo}${riskInfo}${recommendation}
Click to view stock details`;
    tag.title = tooltip;
    tag.dataset.ticker = ticker;
    tag.dataset.count = count;
    tag.dataset.sentiment = sentiment;
    
    // Click handler - navigate to stock detail page
    tag.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      
      const clickedTicker = tag.dataset.ticker;
      const count = tag.dataset.count;
      
      console.log('🔍 Clicked stock ticker:', clickedTicker, 'with', count, 'mentions');
      
      // Highlight selected ticker
      document.querySelectorAll('.word-tag').forEach(t => {
        t.classList.remove('selected');
        if (t !== tag) {
          t.style.backgroundColor = '';
          t.style.color = '';
        }
      });
      
      tag.classList.add('selected');
      tag.style.backgroundColor = '#3b82f6';
      tag.style.color = 'white';
      
      // Navigate to stock detail page
      window.location.href = `stock-detail.html?symbol=${clickedTicker}`;
    });
    
    // Hover effect
    tag.addEventListener('mouseenter', () => {
      if (!tag.classList.contains('selected')) {
        tag.style.backgroundColor = '#3b82f6';
        tag.style.color = 'white';
        tag.style.transform = 'scale(1.1)';
        tag.style.boxShadow = '0 4px 12px rgba(59, 130, 246, 0.4)';
      }
    });
    
    tag.addEventListener('mouseleave', () => {
      if (!tag.classList.contains('selected')) {
        tag.style.backgroundColor = '';
        tag.style.color = '';
        tag.style.transform = 'scale(1)';
        tag.style.boxShadow = '';
      }
    });
    
    container.appendChild(tag);
  });
  
  // Add click anywhere to deselect (but don't clear filter since we navigate away)
  container.addEventListener('click', (e) => {
    if (e.target === container) {
      document.querySelectorAll('.word-tag').forEach(t => {
        t.classList.remove('selected');
      });
    }
  });
  
  // Reset rendering flag after completion
  isRenderingWordCloud = false;
  
  // Only fetch prices if not in search mode and not skipped
  if (!skipPriceFetch && !currentTickerSearch) {
    // Fetch prices for tickers that don't have price data yet
    const tickersNeedingPrice = sortedTopics.filter(t => {
      const price = t.currentPrice || t.price || 0;
      return price === 0 || price === null || price === undefined;
    });
    
    if (tickersNeedingPrice.length > 0) {
      console.log(`💰 Fetching prices for ${tickersNeedingPrice.length} tickers without price data...`);
      // Use setTimeout to avoid blocking the render
      setTimeout(() => {
        fetchStockPricesForTickers(tickersNeedingPrice);
      }, 100);
    }
  }
}

// Top Influencers Feed
async function loadInfluencersFeed() {
  try {
    const filters = window.globalState?.filters || {};
    const timeWindow = document.getElementById('influencerTimeWindow')?.value || '24h';
    
    const response = await fetch(
      `${API_BASE}/influencers?timeWindow=${timeWindow}&timeRange=${filters.timeRange || '24h'}`
    );
    
    if (!response.ok) throw new Error('Failed to fetch influencers');
    
    const data = await response.json();
    renderInfluencersFeed(data.influencers || []);
    
  } catch (error) {
    console.error('Error loading influencers:', error);
    renderInfluencersFeed([]);
  }
}

function renderInfluencersFeed(influencers) {
  const container = document.getElementById('influencersFeed');
  container.innerHTML = '';
  
  if (influencers.length === 0) {
    const noInfluencersMsg = window.i18n?.t('msg.noInfluencersFound') || 'No influencers found';
    container.innerHTML = `<div class="loading">${noInfluencersMsg}</div>`;
    return;
  }
  
  influencers.forEach(influencer => {
    const item = document.createElement('div');
    item.className = 'influencer-item';
    
    item.innerHTML = `
      <div class="influencer-avatar">${influencer.name?.[0] || '👤'}</div>
      <div class="influencer-info">
        <div class="influencer-name">${influencer.name || 'Unknown'}</div>
        <div class="influencer-metrics">
          ${influencer.posts || 0} posts • ${(influencer.avgSentiment || 0).toFixed(2)} sentiment
        </div>
      </div>
      <div class="influencer-impact">
        <div class="impact-score">${(influencer.avgImpact || 0).toFixed(1)}%</div>
        <div style="font-size: 0.75rem; color: #94a3b8;">impact</div>
      </div>
    `;
    
    item.addEventListener('click', () => {
      window.location.href = `influencer.html?id=${influencer.id || influencer.handle}`;
    });
    
    container.appendChild(item);
  });
}

// Mentions Volume Sparklines
async function loadSparklines() {
  try {
    const filters = window.globalState?.filters || {};
    
    const response = await fetch(
      `${API_BASE}/sparklines?timeRange=${filters.timeRange || '24h'}`
    );
    
    if (!response.ok) throw new Error('Failed to fetch sparklines');
    
    const data = await response.json();
    renderSparklines(data.sparklines || []);
    
  } catch (error) {
    console.error('Error loading sparklines:', error);
    renderSparklines([]);
  }
}

function renderSparklines(sparklines) {
  const container = document.getElementById('sparklinesContainer');
  container.innerHTML = '';
  
  if (sparklines.length === 0) {
    const noSparklineMsg = window.i18n?.t('msg.noSparklineData') || 'No sparkline data available';
    container.innerHTML = `<div class="loading">${noSparklineMsg}</div>`;
    return;
  }
  
  sparklines.forEach(sparkline => {
    const item = document.createElement('div');
    item.className = 'sparkline-item';
    
    const canvas = document.createElement('canvas');
    canvas.className = 'sparkline-chart';
    canvas.width = 200;
    canvas.height = 40;
    
    item.innerHTML = `
      <div class="sparkline-header">
        <span class="sparkline-ticker">${sparkline.ticker}</span>
        <span class="sparkline-value">${sparkline.current || 0}</span>
      </div>
    `;
    
    item.appendChild(canvas);
    
    // Draw sparkline
    const ctx = canvas.getContext('2d');
    drawSparkline(ctx, sparkline.data || [], canvas.width, canvas.height);
    
    container.appendChild(item);
  });
}

function drawSparkline(ctx, data, width, height) {
  if (data.length === 0) return;
  
  ctx.strokeStyle = '#60a5fa';
  ctx.lineWidth = 2;
  ctx.beginPath();
  
  const max = Math.max(...data);
  const min = Math.min(...data);
  const range = max - min || 1;
  
  data.forEach((value, index) => {
    const x = (index / (data.length - 1)) * width;
    const y = height - ((value - min) / range) * height;
    
    if (index === 0) {
      ctx.moveTo(x, y);
    } else {
      ctx.lineTo(x, y);
    }
  });
  
  ctx.stroke();
}

// Price vs Sentiment Divergence Panel
async function loadDivergencePanel() {
  const container = document.getElementById('divergenceList');
  if (container) {
    showCardLoading(container.closest('.widget-card'));
  }
  
  try {
    const filters = window.globalState?.filters || {};
    const threshold = parseFloat(document.getElementById('divergenceThreshold')?.value || '0.2');
    
    // Setup event listener for threshold
    const thresholdInput = document.getElementById('divergenceThreshold');
    if (thresholdInput && !thresholdInput.hasAttribute('data-listener')) {
      thresholdInput.setAttribute('data-listener', 'true');
      thresholdInput.addEventListener('change', () => {
        showCardLoading(container?.closest('.widget-card'));
        loadDivergencePanel();
      });
    }
    
    const response = await fetch(
      `${API_BASE_URL}/divergence?threshold=${threshold}&timeRange=${filters.timeRange || '24h'}`
    );
    
    if (!response.ok) throw new Error('Failed to fetch divergence data');
    
    const data = await response.json();
    renderDivergenceList(data.items || data.divergences || []);
    
    if (container) {
      hideCardLoading(container.closest('.widget-card'));
    }
  } catch (error) {
    console.error('Error loading divergence:', error);
    renderDivergenceList([]);
    
    if (container) {
      hideCardLoading(container.closest('.widget-card'));
    }
  }
}

function renderDivergenceList(items) {
  const container = document.getElementById('divergenceList');
  if (!container) return;
  
  container.innerHTML = '';
  
  if (items.length === 0) {
    const noDivergenceMsg = window.i18n?.t('msg.noDivergenceDetected') || 'No divergence detected';
    container.innerHTML = `<div class="loading">${noDivergenceMsg}</div>`;
    return;
  }
  
  items.forEach(item => {
    const div = document.createElement('div');
    div.className = 'divergence-item';
    div.style.cursor = 'pointer';
    
    const ticker = item.ticker || item.symbol || 'N/A';
    const sentimentChange = item.sentimentChange || item.sentiment || 0;
    const priceChange = item.priceChange || item.price || 0;
    const divergence = Math.abs(sentimentChange - priceChange);
    
    div.innerHTML = `
      <div>
        <div class="divergence-ticker">${ticker}</div>
        <div class="divergence-metrics">
          <span class="${sentimentChange >= 0 ? 'positive' : 'negative'}">
            Sentiment: ${(sentimentChange * 100).toFixed(1)}%
          </span>
          <span class="${priceChange >= 0 ? 'positive' : 'negative'}">
            Price: ${(priceChange * 100).toFixed(1)}%
          </span>
          <span class="divergence-value">
            Divergence: ${(divergence * 100).toFixed(1)}%
          </span>
        </div>
      </div>
      <div class="divergence-actions">
        <button class="btn-small" onclick="event.stopPropagation(); addToWatchlist('${ticker}')">⭐ Watch</button>
        <button class="btn-small" onclick="event.stopPropagation(); setAlert('${ticker}')">🔔 Alert</button>
      </div>
    `;
    
    div.addEventListener('click', (e) => {
      if (!e.target.closest('.divergence-actions') && !e.target.closest('button')) {
        window.location.href = `stock-detail.html?symbol=${ticker}`;
      }
    });
    
    // Hover effect
    div.addEventListener('mouseenter', () => {
      div.style.backgroundColor = '#334155';
      div.style.transition = 'background-color 0.2s';
    });
    
    div.addEventListener('mouseleave', () => {
      div.style.backgroundColor = '';
    });
    
    container.appendChild(div);
  });
}

// Raw Feed
async function loadRawFeed() {
  const container = document.getElementById('rawFeedContainer');
  if (container) {
    showCardLoading(container.closest('.widget-card'));
  }
  
  try {
    const filters = window.globalState?.filters || {};
    const keyword = filters.keyword || '';
    
    let url = `${API_BASE_URL}/raw-feed?timeRange=${filters.timeRange || '24h'}&limit=100`;
    if (keyword) {
      url += `&q=${encodeURIComponent(keyword)}`;
    }
    
    const response = await fetch(url);
    
    if (!response.ok) throw new Error('Failed to fetch raw feed');
    
    const data = await response.json();
    const posts = data.posts || data.feed || [];
    
    // Store raw data for filtering
    rawFeedData = posts;
    
    renderRawFeed(posts);
    
    if (container) {
      hideCardLoading(container.closest('.widget-card'));
    }
  } catch (error) {
    console.error('Error loading raw feed:', error);
    renderRawFeed([]);
    
    if (container) {
      hideCardLoading(container.closest('.widget-card'));
    }
  }
}

// Filter raw feed by word
function filterRawFeedByWord(word) {
  const container = document.getElementById('rawFeedContainer');
  if (container) {
    showCardLoading(container.closest('.widget-card'));
  }
  
  // Use setTimeout to allow UI to update
  setTimeout(() => {
    if (!rawFeedData || rawFeedData.length === 0) {
      loadRawFeed();
      return;
    }
    
    const filtered = rawFeedData.filter(post => {
      const text = (post.text || post.title || post.content || '').toLowerCase();
      return text.includes(word.toLowerCase());
    });
    
    renderRawFeed(filtered);
    
    if (container) {
      hideCardLoading(container.closest('.widget-card'));
    }
  }, 100);
}

// Remove duplicates from raw feed
function removeDuplicates() {
  if (!rawFeedData || rawFeedData.length === 0) {
    const noDataMsg = window.i18n?.t('msg.noDataToClean') || 'No data to clean';
    showNotification(noDataMsg, 'warning');
    return;
  }
  
  const removingMsg = window.i18n?.t('msg.removingDuplicates') || 'Removing duplicates...';
  showLoading(removingMsg);
  
  // Use setTimeout to allow UI to update
  setTimeout(() => {
    const seen = new Set();
    const unique = [];
    
    rawFeedData.forEach(post => {
      // Create unique key from text and source
      const text = (post.text || post.title || post.content || '').substring(0, 100);
      const source = post.source || 'unknown';
      const key = `${source}_${text}`;
      
      if (!seen.has(key)) {
        seen.add(key);
        unique.push(post);
      }
    });
    
    const removed = rawFeedData.length - unique.length;
    rawFeedData = unique;
    
    renderRawFeed(unique);
    hideLoading();
    const removedMsg = window.i18n?.t('msg.removedDuplicates', { count: removed }) || `Removed ${removed} duplicate posts`;
    showNotification(removedMsg, 'success');
  }, 100);
}

// Clean data (remove duplicates and filter low quality)
function cleanRawFeed() {
  if (!rawFeedData || rawFeedData.length === 0) {
    const noDataMsg = window.i18n?.t('msg.noDataToClean') || 'No data to clean';
    showNotification(noDataMsg, 'warning');
    return;
  }
  
  const cleaningMsg = window.i18n?.t('msg.cleaningData') || 'Cleaning data...';
  showLoading(cleaningMsg);
  
  // Use setTimeout to allow UI to update
  setTimeout(() => {
    const cleaned = rawFeedData.filter(post => {
      // Remove posts with no text
      const text = post.text || post.title || post.content || '';
      if (text.length < 10) return false;
      
      // Remove posts with very negative sentiment (spam)
      const sentiment = post.sentiment?.compound || post.sentiment_score || 0;
      if (sentiment < -0.8) return false;
      
      return true;
    });
    
    // Remove duplicates
    const seen = new Set();
    const unique = [];
    
    cleaned.forEach(post => {
      const text = (post.text || post.title || post.content || '').substring(0, 100);
      const source = post.source || 'unknown';
      const key = `${source}_${text}`;
      
      if (!seen.has(key)) {
        seen.add(key);
        unique.push(post);
      }
    });
    
    const removed = rawFeedData.length - unique.length;
    rawFeedData = unique;
    
    renderRawFeed(unique);
    hideLoading();
    const cleanedMsg = window.i18n?.t('msg.cleanedData', { count: removed }) || `Cleaned data: removed ${removed} posts`;
    showNotification(cleanedMsg, 'success');
  }, 100);
}

function renderRawFeed(posts) {
  const container = document.getElementById('rawFeedContainer');
  container.innerHTML = '';
  
  if (posts.length === 0) {
    const noPostsMsg = window.i18n?.t('msg.noPostsFound') || 'No posts found';
    container.innerHTML = `<div class="loading">${noPostsMsg}</div>`;
    return;
  }
  
  posts.forEach(post => {
    const item = document.createElement('div');
    item.className = `raw-feed-item ${post.sentiment?.label || 'neutral'}`;
    
    const sourceIcon = getSourceIcon(post.source);
    const sentiment = post.sentiment || {};
    
    item.innerHTML = `
      <div class="feed-source-icon">${sourceIcon}</div>
      <div class="feed-content">
        <div class="feed-header">
          <span class="feed-time">${formatTime(post.created_at || post.publishedAt)}</span>
          <span class="sentiment-badge ${sentiment.label || 'neutral'}">${sentiment.label || 'neutral'}</span>
        </div>
        <div class="feed-text">${post.title || post.text || 'No content'}</div>
        <div class="feed-engagement">
          <span>👍 ${post.upvotes || post.score || 0}</span>
          <span>💬 ${post.comments || post.num_comments || 0}</span>
          ${post.url ? `<a href="${post.url}" target="_blank">🔗 Link</a>` : ''}
        </div>
      </div>
    `;
    
    container.appendChild(item);
  });
}

function getSourceIcon(source) {
  const icons = {
    'reddit': '🔴',
    'news': '📰',
    'twitter': '🐦',
    'youtube': '📺',
    'trends': '📊'
  };
  return icons[source?.toLowerCase()] || '📄';
}

function formatTime(timeString) {
  if (!timeString) return 'Unknown';
  const date = new Date(timeString);
  const now = new Date();
  const diff = now - date;
  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(minutes / 60);
  
  if (minutes < 1) return 'Just now';
  if (minutes < 60) return `${minutes}m ago`;
  if (hours < 24) return `${hours}h ago`;
  return date.toLocaleDateString();
}

function formatNumber(num) {
  if (num >= 1e9) return `${(num / 1e9).toFixed(1)}B`;
  if (num >= 1e6) return `${(num / 1e6).toFixed(1)}M`;
  if (num >= 1e3) return `${(num / 1e3).toFixed(1)}K`;
  return num.toString();
}

// Helper functions
async function addToWatchlist(ticker) {
  const addingMsg = window.i18n?.t('msg.addingToWatchlist', { ticker }) || `Adding ${ticker} to watchlist...`;
  showLoading(addingMsg);
  
  try {
    const response = await fetch(`${API_BASE_URL}/watchlist`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ ticker: ticker })
    });
    
    if (response.ok) {
      const addedMsg = window.i18n?.t('msg.addedToWatchlist', { ticker }) || `Added ${ticker} to watchlist`;
      showNotification(addedMsg, 'success');
    } else {
      throw new Error('Failed to add to watchlist');
    }
    hideLoading();
  } catch (error) {
    console.error('Error adding to watchlist:', error);
    const offlineMsg = window.i18n?.t('msg.addedToWatchlistOffline', { ticker }) || `Added ${ticker} to watchlist (offline mode)`;
    showNotification(offlineMsg, 'warning');
    hideLoading();
  }
}

function setAlert(ticker) {
  const alertMsg = window.i18n?.t('msg.settingAlert', { ticker }) || `Setting alert for ${ticker}`;
  showNotification(alertMsg, 'info');
  window.location.href = `alerts.html?ticker=${ticker}`;
}

function showNotification(message, type = 'info') {
  if (typeof window.showNotification === 'function') {
    window.showNotification(message, type);
  } else {
    alert(message);
  }
}

// Apply global filters
function applyGlobalFilters() {
  if (window.globalState) {
    // Save filters to localStorage
    localStorage.setItem('globalFilters', JSON.stringify(window.globalState.filters));
    
    // Reload all data with new filters
    loadHomeData();
  }
}

// ✅ Load and update next update time
let nextUpdateInterval = null;

async function loadNextUpdateTime() {
  try {
    const response = await fetch(`${API_BASE_URL}/batch/status`);
    if (!response.ok) return;
    
    const data = await response.json();
    const nextUpdate = data.next_update;
    
    if (nextUpdate && nextUpdate.formatted) {
      const displayEl = document.getElementById('nextUpdateDisplay');
      const textEl = document.getElementById('nextUpdateText');
      
      if (displayEl && textEl) {
        displayEl.style.display = 'flex';
        
        // ✅ แสดงเวลาที่เหลือ (ใช้ remaining_seconds เพื่อความแม่นยำ)
        const remainingSeconds = nextUpdate.remaining_seconds || 0;
        const remainingMinutes = nextUpdate.remaining_minutes || 0;
        const remainingHours = nextUpdate.remaining_hours || 0;
        
        // ✅ Format ข้อความให้ชัดเจน (ใช้ remaining_seconds เพื่อความแม่นยำ)
        let timeText = '';
        if (remainingHours > 0) {
          const mins = remainingMinutes % 60;
          if (mins > 0) {
            timeText = `${remainingHours} ชั่วโมง ${mins} นาที`;
          } else {
            timeText = `${remainingHours} ชั่วโมง`;
          }
        } else if (remainingMinutes > 0) {
          const secs = remainingSeconds % 60;
          if (secs > 0 && remainingMinutes < 5) {
            // แสดงวินาทีเมื่อเหลือน้อยกว่า 5 นาที
            timeText = `${remainingMinutes} นาที ${secs} วินาที`;
          } else {
            timeText = `${remainingMinutes} นาที`;
          }
        } else if (remainingSeconds > 0) {
          timeText = `${remainingSeconds} วินาที`;
        } else {
          // ถ้า remaining_seconds เป็น 0 หรือ null → กำลังอัปเดต
          timeText = 'กำลังอัปเดต...';
        }
        
        textEl.textContent = `อีก ${timeText} จะอัปเดต (Yahoo Finance)`;
        
        // ✅ เปลี่ยนสีตามเวลาที่เหลือ (ใช้ remaining_seconds เพื่อความแม่นยำ)
        if (remainingSeconds === null || remainingSeconds === undefined || remainingSeconds <= 0) {
          textEl.style.color = '#3b82f6'; // น้ำเงิน - กำลังอัปเดต
        } else if (remainingSeconds <= 60) {
          textEl.style.color = '#ef4444'; // แดง - ใกล้ถึงเวลา (≤ 1 นาที)
        } else if (remainingMinutes < 5) {
          textEl.style.color = '#f59e0b'; // ส้ม - ใกล้ถึงเวลา (< 5 นาที)
        } else if (remainingMinutes < 15) {
          textEl.style.color = '#fbbf24'; // เหลือง - ใกล้ถึงเวลา (< 15 นาที)
        } else {
          textEl.style.color = '#10b981'; // เขียว - ยังเหลือเวลาอีกเยอะ
        }
      }
    } else {
      // ถ้าไม่มีข้อมูล ให้ซ่อน
      const displayEl = document.getElementById('nextUpdateDisplay');
      if (displayEl) {
        displayEl.style.display = 'none';
      }
    }
  } catch (error) {
    console.error('Error loading next update time:', error);
    // ซ่อน display ถ้ามี error
    const displayEl = document.getElementById('nextUpdateDisplay');
    if (displayEl) {
      displayEl.style.display = 'none';
    }
  }
}

// ✅ Update next update time every minute
function startNextUpdateTimer() {
  // โหลดครั้งแรกทันที
  loadNextUpdateTime();
  
  // ✅ อัปเดตทุก 10 วินาที (แทน 1 นาที) เพื่อให้เห็นการลดลงของเวลา
  if (nextUpdateInterval) {
    clearInterval(nextUpdateInterval);
  }
  nextUpdateInterval = setInterval(loadNextUpdateTime, 10000); // 10 seconds - อัปเดตบ่อยขึ้น
}

// ✅ Stop timer when page unloads
function stopNextUpdateTimer() {
  if (nextUpdateInterval) {
    clearInterval(nextUpdateInterval);
    nextUpdateInterval = null;
  }
}

// Initialize when page loads
if (document.getElementById('pageHome')) {
  document.addEventListener('DOMContentLoaded', () => {
    loadHomeData();
    
    // ✅ Start next update timer
    startNextUpdateTimer();
    
    // Setup event listeners for refresh button
    const refreshBtn = document.getElementById('globalRefreshBtn');
    if (refreshBtn) {
      refreshBtn.addEventListener('click', () => {
        loadHomeData();
        loadNextUpdateTime(); // อัปเดตเวลาที่เหลือเมื่อ refresh
      });
    }
    
    // Setup toggle for raw feed
    const toggleRawFeed = document.getElementById('toggleRawFeed');
    if (toggleRawFeed) {
      let isCollapsed = false;
      toggleRawFeed.addEventListener('click', () => {
        const container = document.getElementById('rawFeedContainer');
        if (container) {
          isCollapsed = !isCollapsed;
          container.style.display = isCollapsed ? 'none' : 'block';
          toggleRawFeed.textContent = isCollapsed ? 'Expand' : 'Collapse';
        }
      });
    }
    
    // ✅ Cleanup timer when page unloads
    window.addEventListener('beforeunload', stopNextUpdateTimer);
    
    // Setup trending topics source filter listener ONCE
    const topicsSourceSelect = document.getElementById('topicsSource');
    if (topicsSourceSelect) {
      topicsSourceSelect.addEventListener('change', (e) => {
        console.log('📊 Trending tickers source changed to:', e.target.value);
        const container = document.getElementById('wordcloudContainer');
        if (container) {
          showCardLoading(container.closest('.widget-card'));
        }
        loadTrendingTopics();
      });
      console.log('✅ Trending tickers source filter listener setup');
    }
    
    // Setup trending topics time range filter listener
    const topicsTimeRangeSelect = document.getElementById('topicsTimeRange');
    if (topicsTimeRangeSelect) {
      topicsTimeRangeSelect.addEventListener('change', (e) => {
        console.log('⏰ Trending tickers time range changed to:', e.target.value);
        const container = document.getElementById('wordcloudContainer');
        if (container) {
          showCardLoading(container.closest('.widget-card'));
        }
        loadTrendingTopics();
      });
      console.log('✅ Trending tickers time range filter listener setup');
    }
    
    // Setup trending sort by listener
    const trendingSortBy = document.getElementById('trendingSortBy');
    if (trendingSortBy) {
      trendingSortBy.addEventListener('change', (e) => {
        console.log('📊 Trending sort changed to:', e.target.value);
        const container = document.getElementById('wordcloudContainer');
        if (container) {
          showCardLoading(container.closest('.widget-card'));
        }
        loadTrendingTopics();
      });
      console.log('✅ Trending sort listener setup');
    }
    
    // Setup real-time mode toggle
    const realtimeToggle = document.getElementById('realtimeModeToggle');
    const realtimeLimitSelect = document.getElementById('realtimeLimit');
    
    if (realtimeToggle) {
      // Load saved preference
      const savedRealtime = localStorage.getItem('realtimeMode') === 'true';
      realtimeToggle.checked = savedRealtime;
      
      // Show/hide limit selector based on real-time mode
      if (realtimeLimitSelect) {
        realtimeLimitSelect.style.display = savedRealtime ? 'inline-block' : 'none';
      }
      
      realtimeToggle.addEventListener('change', (e) => {
        const isEnabled = e.target.checked;
        localStorage.setItem('realtimeMode', isEnabled.toString());
        console.log('🔄 Real-time mode:', isEnabled ? 'ENABLED' : 'DISABLED');
        
        // Show/hide limit selector
        if (realtimeLimitSelect) {
          realtimeLimitSelect.style.display = isEnabled ? 'inline-block' : 'none';
        }
        
        // Reload trending topics with new mode
        const container = document.getElementById('wordcloudContainer');
        if (container) {
          showCardLoading(container.closest('.widget-card'));
        }
        loadTrendingTopics();
      });
      console.log('✅ Real-time mode toggle listener setup');
    }
    
    // Setup real-time limit selector
    if (realtimeLimitSelect) {
      // Load saved limit (default to 50 for speed)
      // ถ้าเคยตั้งค่าไว้มากกว่า 100 ให้รีเซ็ตเป็น 50 เพื่อป้องกัน timeout
      let savedLimit = localStorage.getItem('realtimeLimit') || '50';
      if (parseInt(savedLimit) > 100) {
        savedLimit = '50';
        localStorage.setItem('realtimeLimit', '50');
        console.log('⚠️ Reset limit from', localStorage.getItem('realtimeLimit'), 'to 50 to prevent timeout');
      }
      realtimeLimitSelect.value = savedLimit;
    }
    
    // Setup price filter dropdown
    const priceRangeFilter = document.getElementById('priceRangeFilter');
    if (priceRangeFilter) {
      // Load saved price filter preference
      const savedPriceRange = localStorage.getItem('priceRangeFilter') || 'all';
      priceRangeFilter.value = savedPriceRange;
      
      // Listen for changes
      priceRangeFilter.addEventListener('change', async (e) => {
        const selectedRange = e.target.value;
        localStorage.setItem('priceRangeFilter', selectedRange);
        console.log('💰 Price range filter changed to:', selectedRange);
        
        // ถ้าเลือก price range ที่ไม่ใช่ "all" ให้ดึงราคาก่อน render
        if (selectedRange !== 'all' && currentTopics.length > 0) {
          const container = document.getElementById('wordcloudContainer');
          if (container) {
            showCardLoading(container.closest('.widget-card'));
            container.innerHTML = `
              <div style="padding: 2rem; text-align: center; color: #94a3b8;">
                <p>💰 Fetching prices for ${currentTopics.length} tickers...</p>
                <p style="font-size: 0.875rem; margin-top: 0.5rem;">
                  Please wait while we fetch stock prices to filter by range $${selectedRange}
                </p>
              </div>
            `;
          }
          
          // ดึงราคาสำหรับ tickers ที่ยังไม่มีราคา
          const tickersNeedingPrice = currentTopics.filter(t => {
            const price = t.currentPrice || t.price || 0;
            return price === 0 || price === null || price === undefined;
          });
          
          if (tickersNeedingPrice.length > 0) {
            console.log(`💰 Fetching prices for ${tickersNeedingPrice.length} tickers to apply price filter...`);
            await fetchStockPricesForTickers(tickersNeedingPrice);
            // อัปเดต currentTopics ด้วยราคาใหม่
            currentTopics.forEach(topic => {
              const updated = tickersNeedingPrice.find(t => (t.ticker || t.word) === (topic.ticker || topic.word));
              if (updated && updated.currentPrice) {
                topic.currentPrice = updated.currentPrice;
                topic.price = updated.price;
                topic.priceChange = updated.priceChange;
                topic.priceChangePercent = updated.priceChangePercent;
              }
            });
          }
          
          // Re-render ด้วย price filter
          renderWordCloud(currentTopics, skipPriceFetch=true);
          
          if (container) {
            hideCardLoading(container.closest('.widget-card'));
          }
        } else {
          // ถ้าเลือก "all" ให้ reload trending topics
          const container = document.getElementById('wordcloudContainer');
          if (container) {
            showCardLoading(container.closest('.widget-card'));
          }
          loadTrendingTopics();
        }
      });
      console.log('✅ Price range filter dropdown listener setup');
    }
    
    // Setup real-time limit selector listener
    if (realtimeLimitSelect) {
      realtimeLimitSelect.addEventListener('change', (e) => {
        const limit = e.target.value;
        localStorage.setItem('realtimeLimit', limit);
        console.log('🔄 Real-time limit changed to:', limit);
        
        // Reload if real-time mode is enabled
        if (realtimeToggle?.checked) {
          const container = document.getElementById('wordcloudContainer');
          if (container) {
            showCardLoading(container.closest('.widget-card'));
          }
          loadTrendingTopics();
        }
      });
      console.log('✅ Real-time limit selector listener setup');
    }
    
    // Setup fetch new posts button
    const fetchNewPostsBtn = document.getElementById('fetchNewPostsBtn');
    if (fetchNewPostsBtn) {
      fetchNewPostsBtn.addEventListener('click', async () => {
        try {
          fetchNewPostsBtn.disabled = true;
          fetchNewPostsBtn.textContent = '⏳ Fetching...';
          const fetchingMsg = window.i18n?.t('msg.fetchingNewPosts') || 'Fetching new posts from Reddit...';
          showLoading(fetchingMsg);
          
          const response = await fetch(`${API_BASE_URL}/fetch-new-posts`, {
            method: 'POST'
          });
          
          const data = await response.json();
          
          if (data.success) {
            const fetchedMsg = window.i18n?.t('msg.fetchedNewPosts', { count: data.totalFetched }) || `Fetched ${data.totalFetched} new posts! Refreshing trending tickers...`;
            showNotification(fetchedMsg, 'success');
            // Reload trending topics after fetching new posts
            setTimeout(() => {
              loadTrendingTopics();
            }, 1000);
          } else {
            const errorMsg = window.i18n?.t('msg.errorFetchingPosts', { error: data.error || 'Failed to fetch new posts' }) || `Error: ${data.error || 'Failed to fetch new posts'}`;
            showNotification(errorMsg, 'error');
          }
          
          hideLoading();
        } catch (error) {
          console.error('Error fetching new posts:', error);
          const failedMsg = window.i18n?.t('msg.failedFetchPosts') || 'Failed to fetch new posts. Check API connection.';
          showNotification(failedMsg, 'error');
          hideLoading();
        } finally {
          fetchNewPostsBtn.disabled = false;
          fetchNewPostsBtn.textContent = '🔄 Fetch New Posts';
        }
      });
      console.log('✅ Fetch new posts button listener setup');
    }
  });
  
  // Setup refresh intervals - Update trending topics every 10 minutes
  setInterval(loadTrendingTopics, 600000); // Refresh trending topics every 10 minutes (600000 ms = 10 minutes)
}

// Global functions for ticker search
let currentTickerSearch = null;
let isSearching = false; // Flag to prevent concurrent searches

async function handleTickerSearch() {
  const searchInput = document.getElementById('tickerSearchInput');
  if (!searchInput) return;
  
  const searchTerm = searchInput.value.trim().toUpperCase();
  if (!searchTerm) {
    clearTickerSearch();
    return;
  }
  
  // Prevent concurrent searches
  if (isSearching) {
    console.log('⏳ Search already in progress, skipping...');
    return;
  }
  
  // Prevent searching the same term again
  if (currentTickerSearch === searchTerm) {
    console.log('⏳ Already showing results for', searchTerm);
    return;
  }
  
  isSearching = true;
  currentTickerSearch = searchTerm;
  console.log('🔍 Searching for ticker:', searchTerm);
  
  // Show loading state
  const container = document.getElementById('wordcloudContainer');
  if (container) {
    container.innerHTML = `
      <div style="padding: 2rem; text-align: center; color: #94a3b8;">
        <div class="loading-spinner" style="margin: 0 auto 1rem;"></div>
        <p>🔍 Searching for ${searchTerm}...</p>
        <p style="font-size: 0.875rem; margin-top: 0.5rem;">
          Fetching data and calculating sentiment...
        </p>
      </div>
    `;
  }
  
  try {
    // First, check if ticker exists in trending topics
    const trendingResponse = await fetch(`${API_BASE_URL}/trending-topics?source=all&timeRange=30d`);
    const trendingData = await trendingResponse.json();
    
    // Filter topics by search term
    const filteredTopics = (trendingData.topics || []).filter(topic => {
      const ticker = (topic.ticker || topic.word || '').toUpperCase();
      return ticker === searchTerm;
    });
    
    if (filteredTopics.length > 0) {
      // Found in trending - show it
      console.log(`✅ Found ${searchTerm} in trending topics`);
      // Don't fetch prices again - they should already be in the data
      renderWordCloud(filteredTopics);
      showNotification(`Found ${searchTerm} in trending list`, 'success');
      return;
    }
    
    // Not found in trending - fetch and calculate sentiment from API
    // This will fetch data directly from News, Reddit, Twitter, YouTube for this specific ticker
    console.log(`📊 ${searchTerm} not in trending - fetching data directly from all sources...`);
    showNotification(`Fetching data for ${searchTerm} from News, Reddit, Twitter, YouTube and calculating sentiment...`, 'info');
    
    // Call API to aggregate data and calculate sentiment
    // This endpoint will fetch data directly from all sources for this specific ticker
    console.log(`📡 Calling API: ${API_BASE_URL}/stock/${searchTerm}?days=7`);
    console.log(`   This will fetch from: News API, Reddit, Twitter/X, YouTube, Google Trends`);
    const stockResponse = await fetch(`${API_BASE_URL}/stock/${searchTerm}?days=7`);
    
    if (!stockResponse.ok) {
      const errorText = await stockResponse.text();
      console.error(`❌ API Error (${stockResponse.status}):`, errorText);
      
      if (stockResponse.status === 404) {
        container.innerHTML = `
          <div style="padding: 2rem; text-align: center; color: #ef4444;">
            <p>❌ Ticker ${searchTerm} not found</p>
            <p style="font-size: 0.875rem; margin-top: 0.5rem; color: #94a3b8;">
              Please check the symbol and try again.
            </p>
          </div>
        `;
        showNotification(`Ticker ${searchTerm} not found. Please check the symbol.`, 'error');
        return;
      } else if (stockResponse.status === 500) {
        // Server error - might be processing
        container.innerHTML = `
          <div style="padding: 2rem; text-align: center; color: #f59e0b;">
            <p>⏳ Processing ${searchTerm}...</p>
            <p style="font-size: 0.875rem; margin-top: 0.5rem; color: #94a3b8;">
              The server is fetching data and calculating sentiment. This may take a moment.
              <br>Please wait and try again in a few seconds.
            </p>
          </div>
        `;
        showNotification(`Processing ${searchTerm}... Please wait and try again.`, 'warning');
        return;
      }
      throw new Error(`API error: ${stockResponse.status} - ${errorText}`);
    }
    
    const stockData = await stockResponse.json();
    console.log(`✅ Received stock data for ${searchTerm}:`, stockData);
    
    // Check if API returned an error
    if (stockData.error) {
      console.error(`❌ API returned error:`, stockData.error);
      container.innerHTML = `
        <div style="padding: 2rem; text-align: center; color: #ef4444;">
          <p>❌ Error fetching data for ${searchTerm}</p>
          <p style="font-size: 0.875rem; margin-top: 0.5rem; color: #94a3b8;">
            ${stockData.error}
            <br>Please check:
            <br>• Backend API is running (http://localhost:5000)
            <br>• The ticker symbol is correct
            <br>• Try again in a few moments
          </p>
        </div>
      `;
      showNotification(`Error: ${stockData.error}`, 'error');
      return;
    }
    
    // Try to fetch stock info separately if not in aggregated data
    let stockInfo = stockData.stockInfo;
    if (!stockInfo) {
      console.log(`📡 Stock info not in aggregated data, fetching separately...`);
      try {
        const infoResponse = await fetch(`${API_BASE_URL}/stock/${searchTerm}/info`);
        if (infoResponse.ok) {
          stockInfo = await infoResponse.json();
          console.log(`✅ Fetched stock info separately:`, stockInfo);
          // Update stockData for consistency
          stockData.stockInfo = stockInfo;
        } else {
          console.warn(`⚠️ Could not fetch stock info: ${infoResponse.status}`);
        }
      } catch (e) {
        console.warn(`⚠️ Error fetching stock info separately:`, e);
      }
    }
    
    // Extract sentiment data
    const overallSentiment = stockData.overallSentiment || {};
    const redditSentiment = stockData.redditData?.sentiment || {};
    const newsSentiment = stockData.newsData?.sentiment || {};
    const twitterSentiment = stockData.twitterData?.sentiment || {};
    
    // Use overall sentiment if available, otherwise use the best available source
    let avgSentiment = overallSentiment.compound || 0;
    if (avgSentiment === 0) {
      // Try to get sentiment from any available source
      if (redditSentiment.compound !== undefined) {
        avgSentiment = redditSentiment.compound;
      } else if (newsSentiment.compound !== undefined) {
        avgSentiment = newsSentiment.compound;
      } else if (twitterSentiment.compound !== undefined) {
        avgSentiment = twitterSentiment.compound;
      }
    }
    
    // Count mentions from all sources (including YouTube)
    const mentionCount = (stockData.redditData?.mentionCount || 0) + 
                        (stockData.newsData?.articleCount || 0) + 
                        (stockData.twitterData?.tweetCount || 0) +
                        (stockData.youtubeData?.videoCount || 0);
    
    // Collect sources that have data
    const sources = [];
    if (stockData.redditData?.mentionCount > 0) sources.push('reddit');
    if (stockData.newsData?.articleCount > 0) sources.push('news');
    if (stockData.twitterData?.tweetCount > 0) sources.push('twitter');
    if (stockData.youtubeData?.videoCount > 0) sources.push('youtube');
    
    console.log(`📊 Data fetched for ${searchTerm}:`, {
      reddit: stockData.redditData?.mentionCount || 0,
      news: stockData.newsData?.articleCount || 0,
      twitter: stockData.twitterData?.tweetCount || 0,
      youtube: stockData.youtubeData?.videoCount || 0,
      totalMentions: mentionCount,
      hasStockInfo: !!stockInfo
    });
    
    // Create topic object with real data
    const searchedTopic = {
      ticker: searchTerm,
      word: searchTerm,
      count: mentionCount || 1, // At least 1 to ensure it displays
      mentions: mentionCount || 1,
      uniquePosts: mentionCount || 1,
      avgSentiment: avgSentiment,
      sources: sources,
      sourceCount: sources.length,
      currentPrice: stockInfo?.currentPrice || 0,
      price: stockInfo?.currentPrice || 0,
      priceChange: stockInfo?.change || 0,
      priceChangePercent: stockInfo?.changePercent || 0,
      // Additional data
      stockInfo: stockInfo,
      sentimentDetails: {
        overall: overallSentiment,
        reddit: redditSentiment,
        news: newsSentiment,
        twitter: twitterSentiment
      },
      fetchedAt: new Date().toISOString()
    };
    
    // Validate that we have at least stock info or some data
    // If no stock info and no mentions, the ticker likely doesn't exist
    if (!stockInfo && mentionCount === 0) {
      // No stock info and no mentions from any source - ticker likely doesn't exist
      container.innerHTML = `
        <div style="padding: 2rem; text-align: center; color: #ef4444;">
          <p>❌ No data found for ${searchTerm}</p>
          <p style="font-size: 0.875rem; margin-top: 0.5rem; color: #94a3b8;">
            We searched for ${searchTerm} in:
            <br>• Yahoo Finance (stock info)
            <br>• News API (news articles)
            <br>• Reddit (posts and discussions)
            <br>• Twitter/X (tweets)
            <br>• YouTube (videos)
            <br><br>
            No data was found from any source.
            <br>• Please check if the symbol is correct
            <br>• Try searching for a different ticker
            <br>• Some tickers may not be available in all markets
          </p>
        </div>
      `;
      showNotification(`No data found for ${searchTerm} from any source. Please check the symbol.`, 'error');
      return;
    }
    
    // If we have mentions but no stock info, still show the data
    if (!stockInfo && mentionCount > 0) {
      console.warn(`⚠️ Found ${mentionCount} mentions for ${searchTerm} but no stock info from Yahoo Finance`);
      console.log(`   Sources: ${sources.join(', ')}`);
      // Continue to render with available data
    }
    
    // If we have stock info but no mentions, still show the stock info
    if (stockInfo && mentionCount === 0) {
      console.log(`✅ Found stock info for ${searchTerm} but no mentions yet`);
      // Continue to render with stock info
    }
    
    // Render the searched ticker
    // Note: We don't call fetchStockPricesForTickers here because:
    // 1. We already have stockInfo from the API call
    // 2. fetchStockPricesForTickers would call renderWordCloud again, causing infinite loop
    console.log(`📊 Rendering searched topic:`, searchedTopic);
    renderWordCloud([searchedTopic]);
    
    // Show success message with sentiment info
    const sentimentLabel = overallSentiment.label || (avgSentiment > 0.05 ? 'positive' : (avgSentiment < -0.05 ? 'negative' : 'neutral'));
    const sentimentPercent = (avgSentiment * 100).toFixed(1);
    
    if (mentionCount > 0) {
      const sourceNames = sources.map(s => s.charAt(0).toUpperCase() + s.slice(1)).join(', ');
      showNotification(
        `✅ ${searchTerm}: ${sentimentLabel} sentiment (${sentimentPercent > 0 ? '+' : ''}${sentimentPercent}%) | ${mentionCount} mentions from ${sources.length} source(s): ${sourceNames}`,
        'success'
      );
    } else if (stockInfo) {
      // No mentions but has stock info
      showNotification(
        `✅ ${searchTerm}: Stock found ($${stockInfo.currentPrice?.toFixed(2) || 'N/A'}) but no mentions yet from News/Reddit/Twitter/YouTube`,
        'info'
      );
    } else {
      // Should not reach here due to validation above, but just in case
      showNotification(
        `⚠️ ${searchTerm}: Limited data available`,
        'warning'
      );
    }
    
    console.log(`✅ Successfully fetched and calculated sentiment for ${searchTerm}:`, {
      sentiment: avgSentiment,
      mentions: mentionCount,
      sources: sources,
      stockInfo: stockData.stockInfo ? 'Available' : 'Not available'
    });
    
  } catch (error) {
    console.error('❌ Error searching ticker:', error);
    const container = document.getElementById('wordcloudContainer');
    if (container) {
      container.innerHTML = `
        <div style="padding: 2rem; text-align: center; color: #ef4444;">
          <p>❌ Error searching for ${searchTerm}</p>
          <p style="font-size: 0.875rem; margin-top: 0.5rem; color: #94a3b8;">
            ${error.message || 'Unknown error occurred'}
            <br>Please check:
            <br>• Backend API is running (http://localhost:5000)
            <br>• Network connection
            <br>• Browser console for details
          </p>
        </div>
      `;
    }
    showNotification(`Error searching ticker ${searchTerm}: ${error.message}`, 'error');
  } finally {
    // Always reset the searching flag
    isSearching = false;
  }
}

function clearTickerSearch() {
  const searchInput = document.getElementById('tickerSearchInput');
  if (searchInput) {
    searchInput.value = '';
  }
  currentTickerSearch = null;
  
  // Reload all trending topics
  loadTrendingTopics();
}

