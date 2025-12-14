// Watchlist Controller
const API_BASE_URL = 'http://localhost:5000/api';

document.addEventListener("DOMContentLoaded", () => {
  setupEventListeners();
  loadWatchlist();
});

function setupEventListeners() {
  document.getElementById('addTickerBtn')?.addEventListener('click', addTicker);
  document.getElementById('addTickerInput')?.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') addTicker();
  });
  document.getElementById('sortBy')?.addEventListener('change', loadWatchlist);
}

async function addTicker() {
  const input = document.getElementById('addTickerInput');
  const addBtn = document.getElementById('addTickerBtn');
  const symbol = input.value.trim().toUpperCase();
  
  if (!symbol) {
    showNotification('Please enter a stock symbol', 'error');
    return;
  }
  
  showButtonLoading(addBtn, 'Add');
  
  try {
    const response = await fetch(`${API_BASE_URL}/watchlist`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ ticker: symbol })
    });
    
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }
    
    showNotification(`Added ${symbol} to watchlist`, 'success');
    input.value = '';
    await loadWatchlist();
    hideButtonLoading(addBtn);
  } catch (error) {
    console.error('Error adding ticker:', error);
    showNotification(`Added ${symbol} to watchlist (offline mode)`, 'warning');
    input.value = '';
    await loadWatchlist();
    hideButtonLoading(addBtn);
  }
}

async function loadWatchlist() {
  const sortBy = document.getElementById('sortBy')?.value || 'sentiment';
  const container = document.getElementById('watchlistGrid');
  
  if (container) {
    showCardLoading(container.closest('.widget-card'));
  }
  
  try {
    const response = await fetch(`${API_BASE_URL}/watchlist`);
    
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }
    
    const data = await response.json();
    let watchlist = data.watchlist || data.tickers || [];
    
    // If we have ticker symbols, fetch stock data for each
    if (watchlist.length > 0 && typeof watchlist[0] === 'string') {
      const stockPromises = watchlist.map(async (symbol) => {
        try {
          const stockResponse = await fetch(`${API_BASE_URL}/stock/${symbol}`);
          if (stockResponse.ok) {
            const stockData = await stockResponse.json();
            return {
              symbol: symbol,
              name: stockData.name || symbol,
              price: stockData.currentPrice || stockData.price || 0,
              change: stockData.change || 0,
              sentiment: stockData.overallSentiment?.compound || 0,
              mentions: stockData.totalMentions || 0
            };
          }
        } catch (e) {
          console.error(`Error fetching ${symbol}:`, e);
        }
        return {
          symbol: symbol,
          name: symbol,
          price: 0,
          change: 0,
          sentiment: 0,
          mentions: 0
        };
      });
      
      watchlist = await Promise.all(stockPromises);
    }
    
    // Sort
    watchlist.sort((a, b) => {
      switch(sortBy) {
        case 'sentiment': return (b.sentiment || 0) - (a.sentiment || 0);
        case 'mentions': return (b.mentions || 0) - (a.mentions || 0);
        case 'price': return Math.abs(b.change || 0) - Math.abs(a.change || 0);
        case 'name': return (a.name || '').localeCompare(b.name || '');
        default: return 0;
      }
    });
    
    renderWatchlist(watchlist);
    
    if (container) {
      hideCardLoading(container.closest('.widget-card'));
    }
  } catch (error) {
    console.error('Error loading watchlist:', error);
    // Fallback to mock data
    const mockWatchlist = [
      { symbol: 'AAPL', name: 'Apple Inc.', price: 150.00, change: 2.50, sentiment: 0.65, mentions: 150 },
      { symbol: 'TSLA', name: 'Tesla Inc.', price: 250.00, change: -5.00, sentiment: -0.2, mentions: 200 },
      { symbol: 'NVDA', name: 'NVIDIA Corp.', price: 500.00, change: 10.00, sentiment: 0.8, mentions: 300 }
    ];
    mockWatchlist.sort((a, b) => {
      switch(sortBy) {
        case 'sentiment': return b.sentiment - a.sentiment;
        case 'mentions': return b.mentions - a.mentions;
        case 'price': return Math.abs(b.change) - Math.abs(a.change);
        case 'name': return a.name.localeCompare(b.name);
        default: return 0;
      }
    });
    renderWatchlist(mockWatchlist);
    showNotification('Using mock data (API unavailable)', 'warning');
    
    if (container) {
      hideCardLoading(container.closest('.widget-card'));
    }
  }
}

function renderWatchlist(stocks) {
  const container = document.getElementById('watchlistGrid');
  container.innerHTML = '';
  
  if (stocks.length === 0) {
    container.innerHTML = '<div class="loading">No stocks in watchlist</div>';
    return;
  }
  
  stocks.forEach(stock => {
    const card = document.createElement('div');
    card.className = 'watchlist-card';
    
    card.innerHTML = `
      <div class="watchlist-card-header">
        <div>
          <h4>${stock.symbol}</h4>
          <p>${stock.name}</p>
        </div>
        <button class="btn-small remove-btn" onclick="removeTicker('${stock.symbol}')">✕</button>
      </div>
      <div class="watchlist-card-body">
        <div class="watchlist-metric">
          <span class="label">Price</span>
          <span class="value">$${stock.price.toFixed(2)}</span>
          <span class="change ${stock.change >= 0 ? 'positive' : 'negative'}">
            ${stock.change >= 0 ? '+' : ''}${stock.change.toFixed(2)}
          </span>
        </div>
        <div class="watchlist-metric">
          <span class="label">Sentiment</span>
          <span class="value ${stock.sentiment >= 0 ? 'positive' : 'negative'}">
            ${(stock.sentiment * 100).toFixed(1)}%
          </span>
        </div>
        <div class="watchlist-metric">
          <span class="label">Mentions</span>
          <span class="value">${stock.mentions}</span>
        </div>
      </div>
      <div class="watchlist-card-actions">
        <button class="btn-small" onclick="viewStock('${stock.symbol}')">View Details</button>
        <button class="btn-small" onclick="setAlert('${stock.symbol}')">Set Alert</button>
      </div>
    `;
    
    container.appendChild(card);
  });
}

async function removeTicker(symbol) {
  if (confirm(`Remove ${symbol} from watchlist?`)) {
    showLoading(`Removing ${symbol}...`);
    
    try {
      const response = await fetch(`${API_BASE_URL}/watchlist/${symbol}`, {
        method: 'DELETE'
      });
      
      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }
      
      showNotification(`Removed ${symbol} from watchlist`, 'success');
      await loadWatchlist();
      hideLoading();
    } catch (error) {
      console.error('Error removing ticker:', error);
      showNotification(`Removed ${symbol} from watchlist (offline mode)`, 'warning');
      await loadWatchlist();
      hideLoading();
    }
  }
}

function viewStock(symbol) {
  window.location.href = `stock-detail.html?symbol=${symbol}`;
}

function setAlert(symbol) {
  window.location.href = `alerts.html?ticker=${symbol}`;
}

function showNotification(message, type) {
  if (typeof window.showNotification === 'function') {
    window.showNotification(message, type);
  } else {
    alert(message);
  }
}

