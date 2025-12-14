// Stock Detail Page Controller
const API_BASE_URL = 'http://localhost:5000/api';

let multiAxisChart = null;
let correlationChart = null;
let currentSymbol = null;

// Initialize on page load
document.addEventListener("DOMContentLoaded", () => {
  // Get symbol from URL parameter
  const urlParams = new URLSearchParams(window.location.search);
  currentSymbol = urlParams.get('symbol') || 'AAPL';
  
  loadStockDetail(currentSymbol);
  setupEventListeners();
});

function setupEventListeners() {
  // Chart controls
  document.getElementById('chartTimeRange')?.addEventListener('change', () => loadChartData(currentSymbol));
  document.getElementById('chartAggregation')?.addEventListener('change', () => loadChartData(currentSymbol));
  document.getElementById('impactTimeWindow')?.addEventListener('change', () => loadImpactTimeline());
  document.getElementById('topicTimeRange')?.addEventListener('change', () => loadTopicClusters());
  document.getElementById('correlationPeriod')?.addEventListener('change', () => loadCorrelation());
  
  // Post table filters
  document.getElementById('postSearchInput')?.addEventListener('input', filterPosts);
  document.getElementById('postSourceFilter')?.addEventListener('change', filterPosts);
  document.getElementById('postSentimentFilter')?.addEventListener('change', filterPosts);
  document.getElementById('minEngagementFilter')?.addEventListener('input', filterPosts);
  
  // Actions
  document.getElementById('addToCompareBtn')?.addEventListener('click', () => {
    window.location.href = `compare.html?add=${currentSymbol}`;
  });
  
  document.getElementById('addToWatchlistBtn')?.addEventListener('click', () => {
    addToWatchlist(currentSymbol);
  });
  
  document.getElementById('setAlertBtn')?.addEventListener('click', () => {
    window.location.href = `alerts.html?ticker=${currentSymbol}`;
  });
  
  document.getElementById('exportCSVBtn')?.addEventListener('click', () => exportData('csv'));
  document.getElementById('exportExcelBtn')?.addEventListener('click', () => exportData('excel'));
  
  document.getElementById('compareBenchmarkBtn')?.addEventListener('click', () => {
    // Toggle benchmark comparison
    loadChartData(currentSymbol, true);
  });
}

async function loadStockDetail(symbol) {
  try {
    showLoading('Loading stock details...');
    
    // Update currentSymbol
    currentSymbol = symbol;
    
    // Load all data in parallel
    await Promise.all([
      loadStockHeader(symbol),
      loadPressureScore(symbol),
      loadChartData(symbol),
      loadImpactTimeline(symbol),
      loadTopicClusters(symbol),
      loadWordCloud(symbol),
      loadPosts(symbol),
      loadCorrelation(symbol)
    ]);
    
    hideLoading();
  } catch (error) {
    console.error('Error loading stock detail:', error);
    showNotification('Error loading stock data', 'error');
    hideLoading();
  }
}

async function loadStockHeader(symbol) {
  try {
    // Get stock info from Yahoo Finance
    const priceResponse = await fetch(`${API_BASE_URL}/stock/${symbol}/price`);
    const aggregatedResponse = await fetch(`${API_BASE_URL}/stock/${symbol}?days=7`);
    
    let stockInfo = null;
    let aggregatedData = null;
    
    if (priceResponse.ok) {
      stockInfo = await priceResponse.json();
    }
    
    if (aggregatedResponse.ok) {
      aggregatedData = await aggregatedResponse.json();
    }
    
    // Use price data first, fallback to aggregated data
    const stockData = stockInfo || aggregatedData?.stockInfo || aggregatedData || {};
    
    const name = stockData.name || stockData.longName || symbol;
    const exchange = stockData.exchange || aggregatedData?.stockInfo?.exchange || 'N/A';
    const sector = stockData.sector || aggregatedData?.stockInfo?.sector || 'Unknown';
    const marketCap = stockData.marketCap || aggregatedData?.stockInfo?.marketCap || 0;
    const currentPrice = stockData.currentPrice || stockData.price || 0;
    const change = stockData.change || 0;
    const changePercent = stockData.changePercent || ((change / (currentPrice - change)) * 100) || 0;
    const volume = stockData.volume || 0;
    
    if (document.getElementById('stockNameLarge')) document.getElementById('stockNameLarge').textContent = name;
    if (document.getElementById('stockSymbolLarge')) document.getElementById('stockSymbolLarge').textContent = symbol;
    if (document.getElementById('stockExchange')) document.getElementById('stockExchange').textContent = exchange;
    if (document.getElementById('stockSector')) document.getElementById('stockSector').textContent = sector;
    if (document.getElementById('stockMarketCap')) document.getElementById('stockMarketCap').textContent = formatMarketCap(marketCap);
    if (document.getElementById('stockPriceLarge')) document.getElementById('stockPriceLarge').textContent = `$${currentPrice.toFixed(2)}`;
    
    const changeEl = document.getElementById('stockChangeLarge');
    if (changeEl) {
      changeEl.textContent = `${change >= 0 ? '+' : ''}${change.toFixed(2)} (${changePercent >= 0 ? '+' : ''}${changePercent.toFixed(2)}%)`;
      changeEl.className = `change-large ${change >= 0 ? 'positive' : 'negative'}`;
    }
    
    if (document.getElementById('stockVolume')) document.getElementById('stockVolume').textContent = formatNumber(volume);
  } catch (error) {
    console.error('Error loading stock header:', error);
    // Fallback to mock data
    const mockData = {
      name: "Apple Inc.",
      symbol: symbol,
      exchange: "NASDAQ",
      sector: "Technology",
      marketCap: 2500000000000,
      currentPrice: 150.00,
      change: 2.50,
      changePercent: 1.69,
      volume: 50000000
    };
    
    if (document.getElementById('stockNameLarge')) document.getElementById('stockNameLarge').textContent = mockData.name;
    if (document.getElementById('stockSymbolLarge')) document.getElementById('stockSymbolLarge').textContent = mockData.symbol;
    if (document.getElementById('stockExchange')) document.getElementById('stockExchange').textContent = mockData.exchange;
    if (document.getElementById('stockSector')) document.getElementById('stockSector').textContent = mockData.sector;
    if (document.getElementById('stockMarketCap')) document.getElementById('stockMarketCap').textContent = formatMarketCap(mockData.marketCap);
    if (document.getElementById('stockPriceLarge')) document.getElementById('stockPriceLarge').textContent = `$${mockData.currentPrice.toFixed(2)}`;
    
    const changeEl = document.getElementById('stockChangeLarge');
    if (changeEl) {
      changeEl.textContent = `${mockData.change >= 0 ? '+' : ''}${mockData.change.toFixed(2)} (${mockData.changePercent >= 0 ? '+' : ''}${mockData.changePercent.toFixed(2)}%)`;
      changeEl.className = `change-large ${mockData.change >= 0 ? 'positive' : 'negative'}`;
    }
    
    if (document.getElementById('stockVolume')) document.getElementById('stockVolume').textContent = formatNumber(mockData.volume);
  }
}

async function loadPressureScore(symbol) {
  try {
    const response = await fetch(`${API_BASE_URL}/stock/${symbol}/pressure-score`);
    
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }
    
    const data = await response.json();
    const buyPressure = data.buyPressure || data.score || 50;
    const sellPressure = 100 - buyPressure;
    
    if (document.getElementById('pressureValue')) document.getElementById('pressureValue').textContent = buyPressure;
    if (document.getElementById('pressureGauge')) document.getElementById('pressureGauge').style.width = `${buyPressure}%`;
    if (document.getElementById('buyPressure')) document.getElementById('buyPressure').textContent = `${buyPressure}%`;
    if (document.getElementById('sellPressure')) document.getElementById('sellPressure').textContent = `${sellPressure}%`;
  } catch (error) {
    console.error('Error loading pressure score:', error);
    // Fallback to mock data
    const buyPressure = 65;
    const sellPressure = 35;
    
    if (document.getElementById('pressureValue')) document.getElementById('pressureValue').textContent = buyPressure;
    if (document.getElementById('pressureGauge')) document.getElementById('pressureGauge').style.width = `${buyPressure}%`;
    if (document.getElementById('buyPressure')) document.getElementById('buyPressure').textContent = `${buyPressure}%`;
    if (document.getElementById('sellPressure')) document.getElementById('sellPressure').textContent = `${sellPressure}%`;
  }
}

async function loadChartData(symbol = null, includeBenchmark = false) {
  const ticker = symbol || currentSymbol || 'AAPL';
  const timeRange = document.getElementById('chartTimeRange')?.value || '24h';
  const aggregation = document.getElementById('chartAggregation')?.value || '1h';
  
  try {
    // Try to fetch real data from API
    const period = timeRange === '24h' ? '1d' : timeRange === '7d' ? '7d' : '30d';
    const interval = aggregation === '1m' ? '1m' : aggregation === '5m' ? '5m' : aggregation === '1h' ? '1h' : '1d';
    
    const historyResponse = await fetch(`${API_BASE_URL}/stock/${ticker}/history?period=${period}&interval=${interval}`);
    const aggregatedResponse = await fetch(`${API_BASE_URL}/stock/${ticker}?days=${timeRange === '24h' ? 1 : timeRange === '7d' ? 7 : 30}`);
    
    let priceData = [];
    let sentimentData = [];
    let mentionsData = [];
    
    if (historyResponse.ok) {
      const historyData = await historyResponse.json();
      priceData = historyData.data || [];
    }
    
    if (aggregatedResponse.ok) {
      const aggData = await aggregatedResponse.json();
      // Extract sentiment and mentions from aggregated data
      // This is a simplified version - in production, you'd have time-series data
      sentimentData = [];
      mentionsData = [];
    }
    
    // If we have real data, use it; otherwise use mock
    const chartData = priceData.length > 0 ? 
      generateChartDataFromHistory(priceData, sentimentData, mentionsData) :
      generateMockTimeSeriesData(timeRange, aggregation);
    
    renderChart(chartData, includeBenchmark);
  } catch (error) {
    console.error('Error loading chart data:', error);
    // Fallback to mock data
    const mockData = generateMockTimeSeriesData(timeRange, aggregation);
    renderChart(mockData, includeBenchmark);
  }
}

function generateChartDataFromHistory(priceData, sentimentData, mentionsData) {
  const labels = priceData.map(d => new Date(d.date).toLocaleTimeString());
  const price = priceData.map(d => d.close);
  const sentiment = sentimentData.length > 0 ? sentimentData : price.map(() => 0.5);
  const mentions = mentionsData.length > 0 ? mentionsData : price.map(() => 10);
  
  return { labels, price, sentiment, mentions, benchmark: price.map(p => p * 0.98) };
}

function renderChart(chartData, includeBenchmark = false) {
  
  const ctx = document.getElementById('multiAxisChart')?.getContext('2d');
  if (!ctx) return;
  
  if (multiAxisChart) {
    multiAxisChart.destroy();
  }
  
  const datasets = [
    {
      label: "Price ($)",
      data: chartData.price,
      yAxisID: "y",
      borderColor: "rgb(59, 130, 246)",
      backgroundColor: "rgba(59, 130, 246, 0.1)",
      tension: 0.4
    },
    {
      label: "Sentiment Score",
      data: chartData.sentiment,
      yAxisID: "y1",
      borderColor: "rgb(16, 185, 129)",
      backgroundColor: "rgba(16, 185, 129, 0.1)",
      tension: 0.4,
      borderDash: [5, 5]
    },
    {
      label: "Mentions",
      data: chartData.mentions,
      yAxisID: "y2",
      type: "bar",
      backgroundColor: "rgba(245, 158, 11, 0.3)",
      borderColor: "rgb(245, 158, 11)"
    }
  ];
  
  // Add benchmark if requested
  if (includeBenchmark) {
    datasets.push({
      label: "Benchmark (SPY)",
      data: chartData.benchmark,
      yAxisID: "y",
      borderColor: "rgb(107, 114, 128)",
      backgroundColor: "rgba(107, 114, 128, 0.1)",
      tension: 0.4,
      borderDash: [10, 5]
    });
  }
  
  multiAxisChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: chartData.labels,
      datasets: datasets
    },
    options: {
      responsive: true,
      interaction: {
        mode: "index",
        intersect: false
      },
      plugins: {
        legend: {
          display: true
        },
        tooltip: {
          mode: "index",
          intersect: false
        }
      },
      scales: {
        y: {
          type: "linear",
          display: true,
          position: "left",
          title: {
            display: true,
            text: "Price ($)"
          }
        },
        y1: {
          type: "linear",
          display: true,
          position: "right",
          title: {
            display: true,
            text: "Sentiment Score"
          },
          grid: {
            drawOnChartArea: false
          }
        },
        y2: {
          type: "linear",
          display: true,
          position: "right",
          title: {
            display: true,
            text: "Mentions"
          },
          grid: {
            drawOnChartArea: false
          }
        }
      }
    }
  });
}

function generateMockTimeSeriesData(timeRange, aggregation) {
  const now = new Date();
  const points = timeRange === '24h' ? 24 : timeRange === '7d' ? 168 : 720;
  
  const labels = [];
  const price = [];
  const sentiment = [];
  const mentions = [];
  const benchmark = [];
  
  let basePrice = 150;
  let baseSentiment = 0.2;
  
  for (let i = points; i >= 0; i--) {
    const date = new Date(now.getTime() - i * (timeRange === '24h' ? 3600000 : 86400000));
    labels.push(date.toLocaleTimeString());
    
    // Generate realistic-looking data
    basePrice += (Math.random() - 0.5) * 2;
    price.push(basePrice);
    
    baseSentiment += (Math.random() - 0.5) * 0.1;
    baseSentiment = Math.max(-1, Math.min(1, baseSentiment));
    sentiment.push((baseSentiment + 1) * 50); // Scale to 0-100
    
    mentions.push(Math.floor(Math.random() * 50) + 10);
    
    benchmark.push(basePrice * 0.98 + (Math.random() - 0.5) * 1);
  }
  
  return { labels, price, sentiment, mentions, benchmark };
}

async function loadImpactTimeline(symbol = null) {
  const ticker = symbol || currentSymbol || 'AAPL';
  const timeWindow = document.getElementById('impactTimeWindow')?.value || '1h';
  
  // Mock data - in production, fetch from API
  const mockEvents = [
    {
      influencer: "Elon Musk",
      platform: "twitter",
      time: new Date(Date.now() - 2 * 3600000),
      post: "Just bought more $AAPL",
      priceBefore: 148.50,
      priceAfter: 151.20,
      impact: 1.82
    },
    {
      influencer: "Warren Buffett",
      platform: "twitter",
      time: new Date(Date.now() - 5 * 3600000),
      post: "Apple continues to innovate",
      priceBefore: 147.80,
      priceAfter: 149.10,
      impact: 0.88
    }
  ];
  
  const container = document.getElementById('impactTimelineContainer');
  container.innerHTML = '';
  
  mockEvents.forEach(event => {
    const item = document.createElement('div');
    item.className = 'impact-event';
    
    item.innerHTML = `
      <div class="impact-event-header">
        <div class="impact-influencer">
          <span class="impact-platform">${getPlatformIcon(event.platform)}</span>
          <span class="impact-name">${event.influencer}</span>
        </div>
        <div class="impact-time">${formatTime(event.time)}</div>
      </div>
      <div class="impact-post">"${event.post}"</div>
      <div class="impact-price">
        <span>Before: $${event.priceBefore.toFixed(2)}</span>
        <span class="arrow">→</span>
        <span>After: $${event.priceAfter.toFixed(2)}</span>
        <span class="impact-value ${event.impact >= 0 ? 'positive' : 'negative'}">
          ${event.impact >= 0 ? '+' : ''}${event.impact.toFixed(2)}%
        </span>
      </div>
    `;
    
    container.appendChild(item);
  });
  
  // Update metrics
  const impacts = mockEvents.map(e => e.impact);
  const avg = impacts.reduce((a, b) => a + b, 0) / impacts.length;
  const variance = impacts.reduce((sum, val) => sum + Math.pow(val - avg, 2), 0) / impacts.length;
  const stdDev = Math.sqrt(variance);
  
  document.getElementById('avgImpact').textContent = `${avg >= 0 ? '+' : ''}${avg.toFixed(2)}%`;
  document.getElementById('stdDev').textContent = `${stdDev.toFixed(2)}%`;
  document.getElementById('totalEvents').textContent = mockEvents.length;
}

async function loadTopicClusters(symbol = null) {
  const ticker = symbol || currentSymbol || 'AAPL';
  
  try {
    // Try to fetch real topics from API
    const response = await fetch(`${API_BASE_URL}/stock/${ticker}/topics`);
    if (response.ok) {
      const data = await response.json();
      renderTopics(data.topics || []);
      return;
    }
  } catch (error) {
    console.error('Error loading topics:', error);
  }
  
  // Fallback to mock data
  const mockTopics = [
    { id: 1, name: "Earnings & Financials", weight: 0.35, posts: 45 },
    { id: 2, name: "Product Launches", weight: 0.28, posts: 32 },
    { id: 3, name: "Market Analysis", weight: 0.22, posts: 28 },
    { id: 4, name: "Competition", weight: 0.15, posts: 18 }
  ];
  renderTopics(mockTopics);
}

function renderTopics(topics) {
  const container = document.getElementById('topicsList');
  if (!container) return;
  
  container.innerHTML = '';
  
  topics.forEach(topic => {
    const item = document.createElement('div');
    item.className = 'topic-item';
    item.dataset.topicId = topic.id;
    
    item.innerHTML = `
      <div class="topic-header">
        <span class="topic-name">${topic.name}</span>
        <span class="topic-weight">${(topic.weight * 100).toFixed(0)}%</span>
      </div>
      <div class="topic-bar">
        <div class="topic-bar-fill" style="width: ${topic.weight * 100}%"></div>
      </div>
      <div class="topic-meta">${topic.posts} posts</div>
    `;
    
    item.addEventListener('click', () => showTopicDetails(topic));
    container.appendChild(item);
  });
}

function showTopicDetails(topic) {
  const container = document.getElementById('topicDetails');
  container.innerHTML = `
    <h4>${topic.name}</h4>
    <p>Weight: ${(topic.weight * 100).toFixed(1)}%</p>
    <p>Posts: ${topic.posts}</p>
    <div class="topic-keywords">
      <span class="keyword-tag">earnings</span>
      <span class="keyword-tag">revenue</span>
      <span class="keyword-tag">profit</span>
    </div>
  `;
}

async function loadWordCloud(symbol = null) {
  const ticker = symbol || currentSymbol || 'AAPL';
  
  // Try to fetch real word cloud data
  try {
    const response = await fetch(`${API_BASE_URL}/stock/${ticker}`);
    if (response.ok) {
      const data = await response.json();
      // Extract words from aggregated data
      // This is simplified - in production, you'd have a dedicated endpoint
    }
  } catch (error) {
    console.error('Error loading word cloud:', error);
  }
  
  // Mock data
  const words = [
    { word: "earnings", size: 50 },
    { word: "revenue", size: 45 },
    { word: "iphone", size: 40 },
    { word: "growth", size: 35 },
    { word: "profit", size: 30 },
    { word: "innovation", size: 28 },
    { word: "market", size: 25 }
  ];
  
  const container = document.getElementById('wordcloudDetailContainer');
  container.innerHTML = '';
  
  words.forEach(w => {
    const tag = document.createElement('span');
    tag.className = 'word-tag-large';
    tag.style.fontSize = `${w.size}px`;
    tag.textContent = w.word;
    tag.addEventListener('click', () => filterPostsByWord(w.word));
    container.appendChild(tag);
  });
  
  // Top phrases
  const phrases = [
    "strong earnings report",
    "record revenue growth",
    "new product launch",
    "market leadership"
  ];
  
  const phrasesContainer = document.getElementById('topPhrasesList');
  phrasesContainer.innerHTML = '';
  phrases.forEach(phrase => {
    const item = document.createElement('div');
    item.className = 'phrase-item';
    item.textContent = phrase;
    item.addEventListener('click', () => filterPostsByWord(phrase));
    phrasesContainer.appendChild(item);
  });
}

async function loadPosts(symbol = null) {
  const ticker = symbol || currentSymbol || 'AAPL';
  
  try {
    // Fetch news from Yahoo Finance
    const newsResponse = await fetch(`${API_BASE_URL}/stock/${ticker}/news`);
    const postsResponse = await fetch(`${API_BASE_URL}/stock/${ticker}?days=7`);
    
    let newsPosts = [];
    let redditPosts = [];
    
    if (newsResponse.ok) {
      const newsData = await newsResponse.json();
      newsPosts = (newsData.news || []).map(news => ({
        time: new Date(news.publishedAt * 1000),
        source: 'news',
        author: news.publisher || 'Yahoo Finance',
        sentiment: news.sentiment || { label: 'neutral', score: 0 },
        engagement: { upvotes: 0, comments: 0 },
        text: news.title + (news.summary ? ': ' + news.summary : ''),
        url: news.link || '#',
        impact: news.impact || 'medium'
      }));
    }
    
    if (postsResponse.ok) {
      const aggData = await postsResponse.json();
      // Extract Reddit posts from aggregated data
      redditPosts = (aggData.redditData?.posts || []).slice(0, 10).map(post => ({
        time: new Date(post.created_utc),
        source: 'reddit',
        author: post.author || 'Unknown',
        sentiment: post.sentiment || { label: 'neutral', score: 0 },
        engagement: { 
          upvotes: post.score || 0, 
          comments: post.num_comments || 0 
        },
        text: post.title + (post.selftext ? ': ' + post.selftext.substring(0, 100) : ''),
        url: post.url || '#'
      }));
    }
    
    // Combine and sort by time
    const allPosts = [...newsPosts, ...redditPosts].sort((a, b) => b.time - a.time);
    
    if (allPosts.length > 0) {
      renderPosts(allPosts);
      return;
    }
  } catch (error) {
    console.error('Error loading posts:', error);
  }
  
  // Fallback to mock data
  const mockPosts = [
    {
      time: new Date(Date.now() - 3600000),
      source: "reddit",
      author: "u/trader123",
      sentiment: { label: "positive", score: 0.65 },
      engagement: { upvotes: 125, comments: 45 },
      text: "AAPL earnings beat expectations! Strong buy signal.",
      url: "https://reddit.com/r/stocks/..."
    },
    {
      time: new Date(Date.now() - 7200000),
      source: "news",
      author: "Reuters",
      sentiment: { label: "neutral", score: 0.05 },
      engagement: { upvotes: 0, comments: 0 },
      text: "Apple reports quarterly earnings...",
      url: "https://reuters.com/..."
    }
  ];
  
  renderPosts(mockPosts);
}

function renderPosts(posts) {
  const tbody = document.getElementById('postTableBody');
  tbody.innerHTML = '';
  
  posts.forEach(post => {
    const row = document.createElement('tr');
    row.className = `post-row ${post.sentiment.label}`;
    
    row.innerHTML = `
      <td>${formatTime(post.time)}</td>
      <td><span class="source-badge ${post.source}">${getSourceIcon(post.source)}</span></td>
      <td>${post.author}</td>
      <td><span class="sentiment-badge ${post.sentiment.label}">${post.sentiment.label}</span></td>
      <td>👍 ${post.engagement.upvotes} 💬 ${post.engagement.comments}</td>
      <td class="post-text">${post.text}</td>
      <td><a href="${post.url}" target="_blank">🔗</a></td>
    `;
    
    tbody.appendChild(row);
  });
}

function filterPosts() {
  // Filter logic - in production, would filter server-side
  const search = document.getElementById('postSearchInput')?.value.toLowerCase() || '';
  const source = document.getElementById('postSourceFilter')?.value || 'all';
  const sentiment = document.getElementById('postSentimentFilter')?.value || 'all';
  const minEngagement = parseInt(document.getElementById('minEngagementFilter')?.value || '0');
  
  const rows = document.querySelectorAll('#postTableBody tr');
  rows.forEach(row => {
    const text = row.querySelector('.post-text')?.textContent.toLowerCase() || '';
    const rowSource = row.querySelector('.source-badge')?.classList.contains(source) || source === 'all';
    const rowSentiment = row.querySelector('.sentiment-badge')?.classList.contains(sentiment) || sentiment === 'all';
    
    const matches = text.includes(search) && rowSource && rowSentiment;
    row.style.display = matches ? '' : 'none';
  });
}

function filterPostsByWord(word) {
  document.getElementById('postSearchInput').value = word;
  filterPosts();
}

async function loadCorrelation(symbol = null) {
  const ticker = symbol || currentSymbol || 'AAPL';
  
  try {
    // Try to fetch real correlation data
    const response = await fetch(`${API_BASE_URL}/stock/${ticker}/correlation`);
    if (response.ok) {
      const data = await response.json();
      renderCorrelationChart(data);
      return;
    }
  } catch (error) {
    console.error('Error loading correlation:', error);
  }
  
  // Fallback to mock data
  const ctx = document.getElementById('correlationChart')?.getContext('2d');
  if (!ctx) return;
  
  if (correlationChart) {
    correlationChart.destroy();
  }
  
  // Generate mock correlation data
  const lags = ['-24h', '-12h', '-6h', '-3h', '-1h', '0', '+1h', '+3h', '+6h', '+12h', '+24h'];
  const correlations = [-0.2, 0.1, 0.3, 0.5, 0.65, 0.72, 0.68, 0.55, 0.4, 0.2, 0.1];
  
  correlationChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: lags,
      datasets: [{
        label: "Correlation Coefficient",
        data: correlations,
        borderColor: "rgb(59, 130, 246)",
        backgroundColor: "rgba(59, 130, 246, 0.1)",
        tension: 0.4,
        fill: true
      }]
    },
    options: {
      responsive: true,
      plugins: {
        legend: {
          display: false
        }
      },
      scales: {
        y: {
          min: -1,
          max: 1,
          title: {
            display: true,
            text: "Correlation"
          }
        },
        x: {
          title: {
            display: true,
            text: "Time Lag (Sentiment → Price)"
          }
        }
      }
    }
  });
  
  // Update correlation values
  document.getElementById('corr0').textContent = correlations[5].toFixed(2);
  document.getElementById('corr1h').textContent = correlations[6].toFixed(2);
  document.getElementById('corr1d').textContent = correlations[9].toFixed(2);
}

function renderCorrelationChart(data) {
  const ctx = document.getElementById('correlationChart')?.getContext('2d');
  if (!ctx) return;
  
  if (correlationChart) {
    correlationChart.destroy();
  }
  
  const lags = data.lags || ['-24h', '-12h', '-6h', '-3h', '-1h', '0', '+1h', '+3h', '+6h', '+12h', '+24h'];
  const correlations = data.correlations || [-0.2, 0.1, 0.3, 0.5, 0.65, 0.72, 0.68, 0.55, 0.4, 0.2, 0.1];
  
  correlationChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: lags,
      datasets: [{
        label: "Correlation Coefficient",
        data: correlations,
        borderColor: "rgb(59, 130, 246)",
        backgroundColor: "rgba(59, 130, 246, 0.1)",
        tension: 0.4,
        fill: true
      }]
    },
    options: {
      responsive: true,
      plugins: {
        legend: {
          display: false
        }
      },
      scales: {
        y: {
          min: -1,
          max: 1,
          title: {
            display: true,
            text: "Correlation"
          }
        },
        x: {
          title: {
            display: true,
            text: "Time Lag (Sentiment → Price)"
          }
        }
      }
    }
  });
  
  // Update correlation values
  if (correlations.length >= 10) {
    document.getElementById('corr0').textContent = correlations[5].toFixed(2);
    document.getElementById('corr1h').textContent = correlations[6].toFixed(2);
    document.getElementById('corr1d').textContent = correlations[9].toFixed(2);
  }
}

async function addToWatchlist(symbol) {
  showLoading(`Adding ${symbol} to watchlist...`);
  
  try {
    const response = await fetch(`${API_BASE_URL}/watchlist`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ ticker: symbol })
    });
    
    if (response.ok) {
      showNotification(`Added ${symbol} to watchlist`, 'success');
    } else {
      throw new Error('Failed to add to watchlist');
    }
    hideLoading();
  } catch (error) {
    console.error('Error adding to watchlist:', error);
    showNotification(`Added ${symbol} to watchlist (offline mode)`, 'warning');
    hideLoading();
  }
}

async function exportData(format) {
  showLoading(`Exporting data as ${format.toUpperCase()}...`);
  
  try {
    const response = await fetch(`${API_BASE_URL}/export/${format}?ticker=${currentSymbol}`);
    
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }
    
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${currentSymbol}_export.${format}`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
    
    showNotification(`Exported as ${format.toUpperCase()}`, 'success');
    hideLoading();
  } catch (error) {
    console.error('Error exporting data:', error);
    showNotification(`Exporting as ${format.toUpperCase()}... (offline mode)`, 'warning');
    hideLoading();
  }
}

// Helper functions
function formatMarketCap(cap) {
  if (cap >= 1e12) return `$${(cap / 1e12).toFixed(2)}T`;
  if (cap >= 1e9) return `$${(cap / 1e9).toFixed(2)}B`;
  if (cap >= 1e6) return `$${(cap / 1e6).toFixed(2)}M`;
  return `$${formatNumber(cap)}`;
}

function formatNumber(num) {
  return new Intl.NumberFormat().format(num);
}

function formatTime(date) {
  if (!date) return 'Unknown';
  const d = new Date(date);
  const now = new Date();
  const diff = now - d;
  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(minutes / 60);
  
  if (minutes < 1) return 'Just now';
  if (minutes < 60) return `${minutes}m ago`;
  if (hours < 24) return `${hours}h ago`;
  return d.toLocaleDateString();
}

function getPlatformIcon(platform) {
  const icons = {
    'twitter': '🐦',
    'reddit': '🔴',
    'news': '📰',
    'youtube': '📺'
  };
  return icons[platform] || '📄';
}

function getSourceIcon(source) {
  return getPlatformIcon(source);
}

function showLoading() {
  document.body.style.cursor = 'wait';
}

function hideLoading() {
  document.body.style.cursor = 'default';
}

function showNotification(message, type = 'info') {
  // Use notification from dashboard.js if available
  if (typeof window.showNotification === 'function') {
    window.showNotification(message, type);
  } else {
    alert(message);
  }
}

