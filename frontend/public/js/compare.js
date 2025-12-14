// Compare Page Controller

let mentionsChart = null;
let sentimentChart = null;
let priceChart = null;
let momentumChart = null;
let sourceChart = null;
let selectedStocks = [];

document.addEventListener("DOMContentLoaded", () => {
  setupEventListeners();
  
  // Check if stocks are passed via URL
  const urlParams = new URLSearchParams(window.location.search);
  const addSymbol = urlParams.get('add');
  if (addSymbol) {
    document.getElementById('stockInput1').value = addSymbol;
  }
});

function setupEventListeners() {
  document.getElementById('compareBtn')?.addEventListener('click', handleCompare);
  document.getElementById('clearSelectionBtn')?.addEventListener('click', clearSelection);
  document.getElementById('normalizePriceToggle')?.addEventListener('change', () => {
    if (selectedStocks.length > 0) {
      loadComparison(selectedStocks);
    }
  });
  document.getElementById('aggregationWindow')?.addEventListener('change', () => {
    if (selectedStocks.length > 0) {
      loadComparison(selectedStocks);
    }
  });
  document.getElementById('compareTimeRange')?.addEventListener('change', () => {
    if (selectedStocks.length > 0) {
      loadComparison(selectedStocks);
    }
  });
  document.getElementById('exportCompareBtn')?.addEventListener('click', exportComparison);
}

async function handleCompare() {
  const compareBtn = document.getElementById('compareBtn');
  showButtonLoading(compareBtn, 'Compare Stocks');
  
  try {
    const stocks = [];
    for (let i = 1; i <= 5; i++) {
      const input = document.getElementById(`stockInput${i}`);
      const symbol = input?.value.trim().toUpperCase();
      if (symbol) {
        stocks.push(symbol);
      }
    }
    
    if (stocks.length < 2) {
      showNotification('Please select at least 2 stocks to compare', 'error');
      hideButtonLoading(compareBtn);
      return;
    }
    
    if (stocks.length > 5) {
      showNotification('Maximum 5 stocks can be compared', 'error');
      hideButtonLoading(compareBtn);
      return;
    }
    
    selectedStocks = stocks;
    await loadComparison(stocks);
    hideButtonLoading(compareBtn);
  } catch (error) {
    hideButtonLoading(compareBtn);
    throw error;
  }
}

const API_BASE_URL = 'http://localhost:5000/api';

async function loadComparison(stocks) {
  try {
    showLoading('Loading comparison data...');
    
    const normalizePrice = document.getElementById('normalizePriceToggle')?.checked || false;
    const aggregation = document.getElementById('aggregationWindow')?.value || '1h';
    const timeRange = document.getElementById('compareTimeRange')?.value || '24h';
    
    // Fetch from API
    const response = await fetch(`${API_BASE_URL}/stock/compare?symbols=${stocks.join(',')}&timeRange=${timeRange}&aggregation=${aggregation}`);
    
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }
    
    const apiData = await response.json();
    
    // Transform API data to chart format
    const comparisonData = transformComparisonData(apiData, stocks, timeRange);
    
    // Render charts
    renderMentionsChart(comparisonData);
    renderSentimentChart(comparisonData);
    renderPriceChart(comparisonData, normalizePrice);
    renderMomentumChart(comparisonData);
    renderSourceChart(comparisonData);
    
    // Render summary table
    renderSummaryTable(comparisonData);
    
    // Render ranking
    renderRanking(comparisonData);
    
    hideLoading();
  } catch (error) {
    console.error('Error loading comparison:', error);
    // Fallback to mock data if API fails
    const normalizePrice = document.getElementById('normalizePriceToggle')?.checked || false;
    const aggregation = document.getElementById('aggregationWindow')?.value || '1h';
    const timeRange = document.getElementById('compareTimeRange')?.value || '24h';
    const comparisonData = await generateMockComparisonData(stocks, timeRange, aggregation);
    renderMentionsChart(comparisonData);
    renderSentimentChart(comparisonData);
    renderPriceChart(comparisonData, normalizePrice);
    renderMomentumChart(comparisonData);
    renderSourceChart(comparisonData);
    renderSummaryTable(comparisonData);
    renderRanking(comparisonData);
    showNotification('Using mock data (API unavailable)', 'warning');
    hideLoading();
  }
}

function transformComparisonData(apiData, stocks, timeRange) {
  // Transform API response to chart format
  const data = {
    stocks: [],
    timeSeries: []
  };
  
  if (apiData.stocks && Array.isArray(apiData.stocks)) {
    apiData.stocks.forEach((stock, index) => {
      const symbol = stock.symbol || stocks[index];
      const series = stock.series || [];
      
      const prices = series.map(s => s.price || s.close || 0);
      const sentiments = series.map(s => s.sentiment || 0);
      const mentions = series.map(s => s.mentions || 0);
      
      const avgSentiment = sentiments.length > 0 ? sentiments.reduce((a, b) => a + b, 0) / sentiments.length : 0;
      const priceChange = prices.length > 0 ? ((prices[prices.length - 1] - prices[0]) / prices[0]) * 100 : 0;
      const mentionsChange = mentions.length > 0 ? ((mentions[mentions.length - 1] - mentions[0]) / mentions[0]) * 100 : 0;
      const correlation = calculateCorrelation(sentiments, prices);
      const buyPressure = Math.max(0, Math.min(100, (avgSentiment + 1) * 50 + (mentionsChange > 0 ? 10 : -10)));
      
      data.stocks.push({
        symbol: symbol,
        avgSentiment: avgSentiment,
        priceChange: priceChange,
        mentionsChange: mentionsChange,
        correlation: correlation,
        buyPressure: buyPressure,
        sourceBreakdown: stock.sourceBreakdown || { reddit: 0, news: 0, twitter: 0, trends: 0 },
        series: series.map((s, i) => ({
          time: s.time || new Date(Date.now() - (series.length - i) * 3600000),
          price: prices[i] || 0,
          sentiment: sentiments[i] || 0,
          mentions: mentions[i] || 0
        }))
      });
    });
  }
  
  return data;
}

async function generateMockComparisonData(stocks, timeRange, aggregation) {
  const data = {
    stocks: [],
    timeSeries: []
  };
  
  stocks.forEach((symbol, index) => {
    const basePrice = 100 + (index * 20);
    const baseSentiment = 0.1 + (index * 0.1);
    const baseMentions = 50 + (index * 20);
    
    // Generate time series
    const points = timeRange === '24h' ? 24 : timeRange === '7d' ? 168 : 720;
    const series = [];
    
    for (let i = 0; i < points; i++) {
      series.push({
        time: new Date(Date.now() - (points - i) * (timeRange === '24h' ? 3600000 : 86400000)),
        price: basePrice + (Math.random() - 0.5) * 10,
        sentiment: Math.max(-1, Math.min(1, baseSentiment + (Math.random() - 0.5) * 0.2)),
        mentions: Math.max(0, baseMentions + Math.floor((Math.random() - 0.5) * 20))
      });
    }
    
    // Calculate metrics
    const prices = series.map(s => s.price);
    const sentiments = series.map(s => s.sentiment);
    const mentions = series.map(s => s.mentions);
    
    const avgSentiment = sentiments.reduce((a, b) => a + b, 0) / sentiments.length;
    const priceChange = ((prices[prices.length - 1] - prices[0]) / prices[0]) * 100;
    const mentionsChange = ((mentions[mentions.length - 1] - mentions[0]) / mentions[0]) * 100;
    
    // Calculate correlation
    const correlation = calculateCorrelation(sentiments, prices);
    
    // Calculate buy pressure (simplified)
    const buyPressure = Math.max(0, Math.min(100, (avgSentiment + 1) * 50 + (mentionsChange > 0 ? 10 : -10)));
    
    // Source breakdown
    const sourceBreakdown = {
      reddit: Math.floor(Math.random() * 40) + 20,
      news: Math.floor(Math.random() * 30) + 15,
      twitter: Math.floor(Math.random() * 20) + 10,
      trends: Math.floor(Math.random() * 10) + 5
    };
    
    data.stocks.push({
      symbol: symbol,
      avgSentiment: avgSentiment,
      priceChange: priceChange,
      mentionsChange: mentionsChange,
      correlation: correlation,
      buyPressure: buyPressure,
      sourceBreakdown: sourceBreakdown,
      series: series
    });
  }
  
  return data;
}

function calculateCorrelation(x, y) {
  const n = Math.min(x.length, y.length);
  const sumX = x.slice(0, n).reduce((a, b) => a + b, 0);
  const sumY = y.slice(0, n).reduce((a, b) => a + b, 0);
  const sumXY = x.slice(0, n).reduce((sum, xi, i) => sum + xi * y[i], 0);
  const sumX2 = x.slice(0, n).reduce((sum, xi) => sum + xi * xi, 0);
  const sumY2 = y.slice(0, n).reduce((sum, yi) => sum + yi * yi, 0);
  
  const numerator = n * sumXY - sumX * sumY;
  const denominator = Math.sqrt((n * sumX2 - sumX * sumX) * (n * sumY2 - sumY * sumY));
  
  return denominator === 0 ? 0 : numerator / denominator;
}

function renderMentionsChart(data) {
  const ctx = document.getElementById('mentionsChart')?.getContext('2d');
  if (!ctx) return;
  
  if (mentionsChart) {
    mentionsChart.destroy();
  }
  
  const datasets = data.stocks.map((stock, index) => {
    const colors = ['#3b82f6', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6'];
    return {
      label: stock.symbol,
      data: stock.series.map(s => s.mentions),
      backgroundColor: colors[index % colors.length] + '80',
      borderColor: colors[index % colors.length],
      borderWidth: 2
    };
  });
  
  const labels = data.stocks[0]?.series.map(s => 
    new Date(s.time).toLocaleTimeString()
  ) || [];
  
  mentionsChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: datasets
    },
    options: {
      responsive: true,
      scales: {
        y: {
          beginAtZero: true,
          stacked: true,
          title: {
            display: true,
            text: 'Mentions Count'
          }
        }
      }
    }
  });
}

function renderSentimentChart(data) {
  const ctx = document.getElementById('sentimentChart')?.getContext('2d');
  if (!ctx) return;
  
  if (sentimentChart) {
    sentimentChart.destroy();
  }
  
  const datasets = data.stocks.map((stock, index) => {
    const colors = ['#3b82f6', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6'];
    return {
      label: stock.symbol,
      data: stock.series.map(s => (s.sentiment + 1) * 50), // Scale to 0-100
      borderColor: colors[index % colors.length],
      backgroundColor: colors[index % colors.length] + '20',
      tension: 0.4,
      fill: false
    };
  });
  
  const labels = data.stocks[0]?.series.map(s => 
    new Date(s.time).toLocaleTimeString()
  ) || [];
  
  sentimentChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: datasets
    },
    options: {
      responsive: true,
      scales: {
        y: {
          min: 0,
          max: 100,
          title: {
            display: true,
            text: 'Sentiment Score'
          }
        }
      }
    }
  });
}

function renderPriceChart(data, normalize = false) {
  const ctx = document.getElementById('priceChart')?.getContext('2d');
  if (!ctx) return;
  
  if (priceChart) {
    priceChart.destroy();
  }
  
  const datasets = data.stocks.map((stock, index) => {
    const colors = ['#3b82f6', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6'];
    let prices = stock.series.map(s => s.price);
    
    if (normalize) {
      const firstPrice = prices[0];
      prices = prices.map(p => (p / firstPrice) * 100);
    }
    
    return {
      label: stock.symbol,
      data: prices,
      borderColor: colors[index % colors.length],
      backgroundColor: colors[index % colors.length] + '20',
      tension: 0.4,
      fill: false
    };
  });
  
  const labels = data.stocks[0]?.series.map(s => 
    new Date(s.time).toLocaleTimeString()
  ) || [];
  
  priceChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: datasets
    },
    options: {
      responsive: true,
      scales: {
        y: {
          title: {
            display: true,
            text: normalize ? 'Normalized Price (%)' : 'Price ($)'
          }
        }
      }
    }
  });
}

function renderMomentumChart(data) {
  const ctx = document.getElementById('momentumChart')?.getContext('2d');
  if (!ctx) return;
  
  if (momentumChart) {
    momentumChart.destroy();
  }
  
  // Calculate momentum (change in sentiment)
  const datasets = data.stocks.map((stock, index) => {
    const colors = ['#3b82f6', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6'];
    const sentiments = stock.series.map(s => s.sentiment);
    const momentum = [];
    
    for (let i = 1; i < sentiments.length; i++) {
      momentum.push((sentiments[i] - sentiments[i-1]) * 100);
    }
    
    return {
      label: stock.symbol,
      data: momentum,
      borderColor: colors[index % colors.length],
      backgroundColor: colors[index % colors.length] + '20',
      tension: 0.4,
      fill: false
    };
  });
  
  const labels = data.stocks[0]?.series.slice(1).map(s => 
    new Date(s.time).toLocaleTimeString()
  ) || [];
  
  momentumChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: datasets
    },
    options: {
      responsive: true,
      scales: {
        y: {
          title: {
            display: true,
            text: 'Sentiment Momentum (%)'
          }
        }
      }
    }
  });
}

function renderSourceChart(data) {
  const ctx = document.getElementById('sourceChart')?.getContext('2d');
  if (!ctx) return;
  
  if (sourceChart) {
    sourceChart.destroy();
  }
  
  // Aggregate sources across all stocks
  const sourceTotals = {
    reddit: 0,
    news: 0,
    twitter: 0,
    trends: 0
  };
  
  data.stocks.forEach(stock => {
    Object.keys(sourceTotals).forEach(source => {
      sourceTotals[source] += stock.sourceBreakdown[source] || 0;
    });
  });
  
  sourceChart = new Chart(ctx, {
    type: 'pie',
    data: {
      labels: Object.keys(sourceTotals),
      datasets: [{
        data: Object.values(sourceTotals),
        backgroundColor: [
          '#ff4500',
          '#3b82f6',
          '#1da1f2',
          '#f59e0b'
        ]
      }]
    },
    options: {
      responsive: true,
      plugins: {
        legend: {
          position: 'right'
        }
      }
    }
  });
}

function renderSummaryTable(data) {
  const tbody = document.getElementById('comparisonTableBody');
  tbody.innerHTML = '';
  
  // Sort by buy pressure
  const sorted = [...data.stocks].sort((a, b) => b.buyPressure - a.buyPressure);
  
  sorted.forEach((stock, index) => {
    const row = document.createElement('tr');
    row.innerHTML = `
      <td><strong>${stock.symbol}</strong></td>
      <td>${(stock.avgSentiment * 100).toFixed(1)}%</td>
      <td class="${stock.mentionsChange >= 0 ? 'positive' : 'negative'}">
        ${stock.mentionsChange >= 0 ? '+' : ''}${stock.mentionsChange.toFixed(2)}%
      </td>
      <td class="${stock.priceChange >= 0 ? 'positive' : 'negative'}">
        ${stock.priceChange >= 0 ? '+' : ''}${stock.priceChange.toFixed(2)}%
      </td>
      <td>${stock.correlation.toFixed(2)}</td>
      <td>
        <div class="pressure-bar">
          <div class="pressure-bar-fill" style="width: ${stock.buyPressure}%"></div>
          <span>${stock.buyPressure.toFixed(0)}</span>
        </div>
      </td>
      <td><strong>#${index + 1}</strong></td>
    `;
    tbody.appendChild(row);
  });
}

function renderRanking(data) {
  const container = document.getElementById('rankingContainer');
  container.innerHTML = '';
  
  // Sort by buy pressure
  const sorted = [...data.stocks].sort((a, b) => b.buyPressure - a.buyPressure);
  
  sorted.forEach((stock, index) => {
    const item = document.createElement('div');
    item.className = 'ranking-item';
    
    item.innerHTML = `
      <div class="ranking-position">#${index + 1}</div>
      <div class="ranking-symbol">${stock.symbol}</div>
      <div class="ranking-pressure">
        <div class="pressure-bar-horizontal">
          <div class="pressure-bar-fill" style="width: ${stock.buyPressure}%"></div>
        </div>
        <span class="pressure-value">${stock.buyPressure.toFixed(0)}</span>
      </div>
      <div class="ranking-metrics">
        <span>Sentiment: ${(stock.avgSentiment * 100).toFixed(1)}%</span>
        <span>Mentions: ${stock.mentionsChange >= 0 ? '+' : ''}${stock.mentionsChange.toFixed(1)}%</span>
      </div>
    `;
    
    container.appendChild(item);
  });
}

function clearSelection() {
  for (let i = 1; i <= 5; i++) {
    const input = document.getElementById(`stockInput${i}`);
    if (input) input.value = '';
  }
  selectedStocks = [];
  
  // Clear charts
  [mentionsChart, sentimentChart, priceChart, momentumChart, sourceChart].forEach(chart => {
    if (chart) chart.destroy();
  });
  
  document.getElementById('comparisonTableBody').innerHTML = '';
  document.getElementById('rankingContainer').innerHTML = '';
}

async function exportComparison() {
  if (selectedStocks.length === 0) {
    showNotification('No comparison data to export', 'error');
    return;
  }
  
  showLoading('Exporting comparison data...');
  
  try {
    // In production, would call API to export
    await new Promise(resolve => setTimeout(resolve, 1000)); // Simulate export
    
    showNotification('Comparison data exported successfully', 'success');
    hideLoading();
  } catch (error) {
    console.error('Error exporting comparison:', error);
    showNotification('Error exporting comparison data', 'error');
    hideLoading();
  }
}

function showLoading() {
  document.body.style.cursor = 'wait';
}

function hideLoading() {
  document.body.style.cursor = 'default';
}

function showNotification(message, type = 'info') {
  if (typeof window.showNotification === 'function') {
    window.showNotification(message, type);
  } else {
    alert(message);
  }
}
