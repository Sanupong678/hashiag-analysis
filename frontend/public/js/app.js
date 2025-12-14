// API Base URL
const API_BASE = "http://localhost:5000/api";

// Chart instances
let priceSentimentChart = null;
let mentionsChart = null;

// Current stock symbol
let currentSymbol = null;

// Initialize
document.addEventListener("DOMContentLoaded", () => {
  initializeEventListeners();
  loadAlerts();
  setInterval(loadAlerts, 60000); // Refresh alerts every minute
});

function initializeEventListeners() {
  // Search button
  document.getElementById("searchBtn").addEventListener("click", handleSearch);
  
  // Enter key in search input
  document.getElementById("stockInput").addEventListener("keypress", (e) => {
    if (e.key === "Enter") handleSearch();
  });
  
  // Refresh button
  document.getElementById("refreshBtn").addEventListener("click", () => {
    if (currentSymbol) {
      handleSearch();
    }
  });
  
  // Quick stock buttons
  document.querySelectorAll(".quick-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const symbol = btn.dataset.symbol;
      document.getElementById("stockInput").value = symbol;
      handleSearch();
    });
  });
}

async function handleSearch() {
  const symbol = document.getElementById("stockInput").value.trim().toUpperCase();
  if (!symbol) {
    alert("Please enter a stock symbol");
    return;
  }
  
  currentSymbol = symbol;
  await loadStockData(symbol);
}

async function loadStockData(symbol) {
  try {
    showLoading();
    
    const response = await fetch(`${API_BASE}/stock/${symbol}?days=7`);
    if (!response.ok) {
      throw new Error(`Failed to fetch data: ${response.statusText}`);
    }
    
    const data = await response.json();
    renderStockData(data);
    
  } catch (error) {
    console.error("Error loading stock data:", error);
    alert(`Error: ${error.message}`);
    hideLoading();
  }
}

function renderStockData(data) {
  // Show sections
  document.getElementById("stockInfoSection").style.display = "block";
  document.getElementById("sentimentSection").style.display = "block";
  
  // Stock Info
  const stockInfo = data.stockInfo;
  if (stockInfo) {
    document.getElementById("stockName").textContent = stockInfo.name || stockInfo.symbol;
    document.getElementById("stockSymbol").textContent = stockInfo.symbol;
    
    const price = stockInfo.currentPrice || 0;
    const change = stockInfo.change || 0;
    const changePercent = stockInfo.changePercent || 0;
    
    document.getElementById("stockPrice").textContent = `$${price.toFixed(2)}`;
    
    const changeEl = document.getElementById("stockChange");
    changeEl.textContent = `${change >= 0 ? '+' : ''}${change.toFixed(2)} (${changePercent >= 0 ? '+' : ''}${changePercent.toFixed(2)}%)`;
    changeEl.className = `change ${change >= 0 ? 'positive' : 'negative'}`;
    
    document.getElementById("marketCap").textContent = formatMarketCap(stockInfo.marketCap);
    document.getElementById("volume").textContent = formatNumber(stockInfo.volume);
    document.getElementById("sector").textContent = stockInfo.sector || "Unknown";
  }
  
  // Sentiment Data
  const overallSentiment = data.overallSentiment;
  if (overallSentiment) {
    const compound = overallSentiment.compound || 0;
    const label = overallSentiment.label || "neutral";
    
    document.getElementById("overallSentiment").textContent = 
      `${(compound * 100).toFixed(1)}% (${label})`;
    
    const bar = document.getElementById("sentimentBar");
    const percentage = ((compound + 1) / 2) * 100; // Convert -1 to 1 range to 0-100%
    bar.style.width = `${percentage}%`;
    bar.className = `sentiment-fill ${label}`;
  }
  
  // Reddit Data
  const redditData = data.redditData || {};
  document.getElementById("redditMentions").textContent = redditData.mentionCount || 0;
  if (redditData.sentiment) {
    document.getElementById("redditSentiment").textContent = 
      `${redditData.sentiment.label} (${(redditData.sentiment.compound * 100).toFixed(1)}%)`;
  }
  
  // News Data
  const newsData = data.newsData || {};
  document.getElementById("newsCount").textContent = newsData.articleCount || 0;
  if (newsData.sentiment) {
    document.getElementById("newsSentiment").textContent = 
      `${newsData.sentiment.label} (${(newsData.sentiment.compound * 100).toFixed(1)}%)`;
  }
  
  // Render Tables
  renderRedditTable(redditData.posts || []);
  renderNewsTable(newsData.articles || []);
  
  // Render Charts
  renderCharts(data);
  
  hideLoading();
}

function renderRedditTable(posts) {
  const tbody = document.querySelector("#redditTable tbody");
  tbody.innerHTML = "";
  
  if (posts.length === 0) {
    tbody.innerHTML = "<tr><td colspan='5' class='loading'>No Reddit posts found</td></tr>";
    return;
  }
  
  posts.forEach(post => {
    const row = document.createElement("tr");
    
    // Analyze sentiment for this post
    const text = `${post.title || ''} ${post.selftext || ''}`;
    const sentiment = analyzeTextSentiment(text);
    
    row.innerHTML = `
      <td>${post.title || 'N/A'}</td>
      <td>${post.subreddit || 'N/A'}</td>
      <td>${post.score || 0}</td>
      <td><span class="sentiment-badge ${sentiment.label}">${sentiment.label}</span></td>
      <td>${formatDate(post.created_utc)}</td>
    `;
    
    tbody.appendChild(row);
  });
}

function renderNewsTable(articles) {
  const tbody = document.querySelector("#newsTable tbody");
  tbody.innerHTML = "";
  
  if (articles.length === 0) {
    tbody.innerHTML = "<tr><td colspan='4' class='loading'>No news articles found</td></tr>";
    return;
  }
  
  articles.forEach(article => {
    const row = document.createElement("tr");
    
    const text = `${article.title || ''} ${article.description || ''}`;
    const sentiment = analyzeTextSentiment(text);
    
    row.innerHTML = `
      <td><a href="${article.url || '#'}" target="_blank">${article.title || 'N/A'}</a></td>
      <td>${article.source || 'Unknown'}</td>
      <td><span class="sentiment-badge ${sentiment.label}">${sentiment.label}</span></td>
      <td>${formatDate(article.publishedAt)}</td>
    `;
    
    tbody.appendChild(row);
  });
}

function renderCharts(data) {
  // Price vs Sentiment Chart
  renderPriceSentimentChart(data);
  
  // Mentions Chart
  renderMentionsChart(data);
}

function renderPriceSentimentChart(data) {
  const ctx = document.getElementById("priceSentimentChart").getContext("2d");
  
  // Get historical price data
  fetch(`${API_BASE}/stock/${currentSymbol}/history?period=1mo&interval=1d`)
    .then(res => res.json())
    .then(priceData => {
      const pricePoints = priceData.data || [];
      const dates = pricePoints.map(p => p.date);
      const prices = pricePoints.map(p => p.close);
      
      // Create sentiment timeline (simplified - using overall sentiment as constant for now)
      const sentiment = data.overallSentiment?.compound || 0;
      const sentimentLine = dates.map(() => (sentiment + 1) * 50); // Scale to 0-100
      
      if (priceSentimentChart) {
        priceSentimentChart.destroy();
      }
      
      priceSentimentChart = new Chart(ctx, {
        type: "line",
        data: {
          labels: dates,
          datasets: [
            {
              label: "Price ($)",
              data: prices,
              yAxisID: "y",
              borderColor: "rgb(37, 99, 235)",
              backgroundColor: "rgba(37, 99, 235, 0.1)",
              tension: 0.4
            },
            {
              label: "Sentiment Score",
              data: sentimentLine,
              yAxisID: "y1",
              borderColor: "rgb(16, 185, 129)",
              backgroundColor: "rgba(16, 185, 129, 0.1)",
              tension: 0.4,
              borderDash: [5, 5]
            }
          ]
        },
        options: {
          responsive: true,
          interaction: {
            mode: "index",
            intersect: false
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
            }
          }
        }
      });
    })
    .catch(err => {
      console.error("Error loading price history:", err);
    });
}

function renderMentionsChart(data) {
  const ctx = document.getElementById("mentionsChart").getContext("2d");
  
  const redditCount = data.redditData?.mentionCount || 0;
  const newsCount = data.newsData?.articleCount || 0;
  
  if (mentionsChart) {
    mentionsChart.destroy();
  }
  
  mentionsChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: ["Reddit Mentions", "News Articles"],
      datasets: [{
        label: "Count",
        data: [redditCount, newsCount],
        backgroundColor: [
          "rgba(239, 68, 68, 0.6)",
          "rgba(37, 99, 235, 0.6)"
        ],
        borderColor: [
          "rgba(239, 68, 68, 1)",
          "rgba(37, 99, 235, 1)"
        ],
        borderWidth: 2
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
          beginAtZero: true,
          ticks: {
            stepSize: 1
          }
        }
      }
    }
  });
}

async function loadAlerts() {
  try {
    const response = await fetch(`${API_BASE}/alerts?threshold=0.3&hours=24`);
    if (!response.ok) return;
    
    const data = await response.json();
    renderAlerts(data.alerts || []);
  } catch (error) {
    console.error("Error loading alerts:", error);
  }
}

function renderAlerts(alerts) {
  // Render to alerts panel (inside page-content)
  const alertsPanel = document.getElementById("alertsPanel");
  const alertSummaryContent = document.getElementById("alertSummaryContent");
  
  // Also check for legacy container
  const legacyContainer = document.getElementById("alertsContainer");
  
  if (!alerts || alerts.length === 0) {
    // Hide alerts panel if no alerts
    if (alertsPanel) {
      alertsPanel.style.display = 'none';
    }
    if (alertSummaryContent) {
      alertSummaryContent.innerHTML = "<div style='padding: 1rem; text-align: center; color: #94a3b8;'>No alerts in the last 24 hours</div>";
    }
    if (legacyContainer) {
      legacyContainer.innerHTML = "<div class='loading'>No alerts in the last 24 hours</div>";
    }
    return;
  }
  
  // Show alerts panel if there are alerts
  if (alertsPanel) {
    alertsPanel.style.display = 'block';
  }
  
  // Render alerts to alert summary content
  if (alertSummaryContent) {
    alertSummaryContent.innerHTML = alerts.map(alert => {
      const severity = alert.severity || (alert.value > 0.5 ? 'high' : alert.value > 0.2 ? 'medium' : 'low');
      return `
        <div class="alert-summary-item ${severity}" onclick="window.location.href='alerts.html?ticker=${alert.symbol || ''}'">
          <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 0.5rem;">
            <div>
              <strong style="color: #e2e8f0;">${alert.symbol || 'N/A'}</strong>
              <span style="color: #94a3b8; font-size: 0.875rem; margin-left: 0.5rem;">${formatDate(alert.timestamp)}</span>
            </div>
          </div>
          <div style="color: #cbd5e1; font-size: 0.875rem;">
            <strong>${alert.type === 'sentiment_spike' ? 'Sentiment Spike' : 'Alert'}:</strong>
            ${alert.label || 'alert'} sentiment (${(alert.value * 100).toFixed(1)}%)
          </div>
        </div>
      `;
    }).join("");
  }
  
  // Also render to legacy container if exists
  if (legacyContainer) {
    legacyContainer.innerHTML = alerts.map(alert => `
      <div class="alert-item ${alert.label}">
        <div class="alert-header">
          <span class="alert-symbol">${alert.symbol}</span>
          <span class="alert-time">${formatDate(alert.timestamp)}</span>
        </div>
        <div>
          <strong>${alert.type === 'sentiment_spike' ? 'Sentiment Spike' : 'Alert'}:</strong>
          ${alert.label} sentiment (${(alert.value * 100).toFixed(1)}%)
        </div>
      </div>
    `).join("");
  }
}

// Helper Functions
function analyzeTextSentiment(text) {
  // Simple sentiment analysis (in production, this would call the backend)
  const positiveWords = ['good', 'great', 'excellent', 'bullish', 'buy', 'up', 'rise', 'gain'];
  const negativeWords = ['bad', 'terrible', 'bearish', 'sell', 'down', 'fall', 'drop', 'crash'];
  
  const lowerText = text.toLowerCase();
  let score = 0;
  
  positiveWords.forEach(word => {
    if (lowerText.includes(word)) score += 0.1;
  });
  
  negativeWords.forEach(word => {
    if (lowerText.includes(word)) score -= 0.1;
  });
  
  if (score >= 0.05) return { label: 'positive', score };
  if (score <= -0.05) return { label: 'negative', score };
  return { label: 'neutral', score };
}

function formatDate(dateString) {
  if (!dateString) return "N/A";
  const date = new Date(dateString);
  return date.toLocaleDateString() + " " + date.toLocaleTimeString();
}

function formatNumber(num) {
  if (!num) return "N/A";
  return new Intl.NumberFormat().format(num);
}

function formatMarketCap(cap) {
  if (!cap) return "N/A";
  if (cap >= 1e12) return `$${(cap / 1e12).toFixed(2)}T`;
  if (cap >= 1e9) return `$${(cap / 1e9).toFixed(2)}B`;
  if (cap >= 1e6) return `$${(cap / 1e6).toFixed(2)}M`;
  return `$${formatNumber(cap)}`;
}

function showLoading() {
  // You can add a loading spinner here
  document.body.style.cursor = "wait";
}

function hideLoading() {
  document.body.style.cursor = "default";
}
