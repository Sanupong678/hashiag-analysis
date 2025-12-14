// Data Explorer Controller
const API_BASE_URL = 'http://localhost:5000/api';

document.addEventListener("DOMContentLoaded", () => {
  loadData();
  setupEventListeners();
});

function setupEventListeners() {
  document.getElementById('selectAll')?.addEventListener('change', (e) => {
    document.querySelectorAll('#dataTableBody input[type="checkbox"]').forEach(cb => {
      cb.checked = e.target.checked;
    });
  });
  
  // Filter button
  const applyFiltersBtn = document.getElementById('applyFiltersBtn');
  if (applyFiltersBtn) {
    applyFiltersBtn.addEventListener('click', applyFilters);
  }
  
  // Export buttons
  const exportCSVBtn = document.getElementById('exportCSVBtn');
  if (exportCSVBtn) {
    exportCSVBtn.addEventListener('click', () => exportData('csv'));
  }
  
  const exportExcelBtn = document.getElementById('exportExcelBtn');
  if (exportExcelBtn) {
    exportExcelBtn.addEventListener('click', () => exportData('excel'));
  }
  
  // Search on Enter
  const searchQuery = document.getElementById('searchQuery');
  if (searchQuery) {
    searchQuery.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') {
        applyFilters();
      }
    });
  }
}

async function loadData() {
  const container = document.getElementById('dataTableBody');
  if (container) {
    showCardLoading(container.closest('.widget-card') || container.parentElement);
  }
  
  try {
    const response = await fetch(`${API_BASE_URL}/raw-feed`);
    
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }
    
    const data = await response.json();
    const posts = data.posts || data.feed || [];
    
    renderData(posts);
    
    if (container) {
      hideCardLoading(container.closest('.widget-card') || container.parentElement);
    }
  } catch (error) {
    console.error('Error loading data:', error);
    // Fallback to mock data
    const mockData = [
      {
        time: new Date(Date.now() - 3600000),
        source: 'reddit',
        ticker: 'AAPL',
        author: 'u/trader123',
        sentiment: { label: 'positive', score: 0.65 },
        engagement: { upvotes: 125, comments: 45 },
        text: 'AAPL earnings beat expectations!',
        url: 'https://reddit.com/...'
      }
    ];
    
    renderData(mockData);
    showNotification('Using mock data (API unavailable)', 'warning');
    
    if (container) {
      hideCardLoading(container.closest('.widget-card') || container.parentElement);
    }
  }
}

function renderData(data) {
  const tbody = document.getElementById('dataTableBody');
  if (!tbody) return;
  
  tbody.innerHTML = '';
  
  if (data.length === 0) {
    tbody.innerHTML = '<tr><td colspan="9" class="loading">No data found</td></tr>';
    return;
  }
  
  data.forEach(item => {
    const row = document.createElement('tr');
    const time = item.time || item.created_at || item.createdAt || new Date();
    const source = item.source || 'unknown';
    const ticker = item.ticker || item.ticker_list?.[0] || 'N/A';
    const author = item.author || item.username || 'Unknown';
    const sentiment = item.sentiment || item.sentiment_score || { label: 'neutral', score: 0 };
    const sentimentLabel = typeof sentiment === 'object' ? (sentiment.label || 'neutral') : (sentiment > 0 ? 'positive' : sentiment < 0 ? 'negative' : 'neutral');
    const engagement = item.engagement || { upvotes: item.upvotes || 0, comments: item.comments_count || item.comments || 0 };
    const text = item.text || item.title || item.content || 'No content';
    const url = item.url || item.permalink || '#';
    
    row.innerHTML = `
      <td><input type="checkbox"></td>
      <td>${formatTime(time)}</td>
      <td><span class="source-badge ${source}">${source}</span></td>
      <td>${ticker}</td>
      <td>${author}</td>
      <td><span class="sentiment-badge ${sentimentLabel}">${sentimentLabel}</span></td>
      <td>👍 ${engagement.upvotes || 0} 💬 ${engagement.comments || 0}</td>
      <td class="post-text">${text.substring(0, 100)}${text.length > 100 ? '...' : ''}</td>
      <td><a href="${url}" target="_blank">🔗</a></td>
    `;
    tbody.appendChild(row);
  });
}

async function applyFilters() {
  const applyBtn = document.getElementById('applyFiltersBtn');
  if (applyBtn) {
    showButtonLoading(applyBtn, 'Apply Filters');
  }
  
  const query = document.getElementById('searchQuery')?.value || '';
  const source = document.getElementById('sourceFilter')?.value || 'all';
  const ticker = document.getElementById('tickerFilter')?.value || '';
  
  try {
    const params = new URLSearchParams();
    if (query) params.append('q', query);
    if (source !== 'all') params.append('source', source);
    if (ticker) params.append('ticker', ticker);
    
    const response = await fetch(`${API_BASE_URL}/raw-feed?${params.toString()}`);
    
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }
    
    const data = await response.json();
    const posts = data.posts || data.feed || [];
    
    renderData(posts);
    showNotification('Filters applied', 'info');
    
    if (applyBtn) {
      hideButtonLoading(applyBtn);
    }
  } catch (error) {
    console.error('Error applying filters:', error);
    showNotification('Error applying filters', 'error');
    await loadData();
    
    if (applyBtn) {
      hideButtonLoading(applyBtn);
    }
  }
}

async function exportData(format) {
  showLoading(`Exporting as ${format.toUpperCase()}...`);
  
  try {
    const response = await fetch(`${API_BASE_URL}/export/${format}`);
    
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }
    
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `export.${format}`;
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

function formatTime(date) {
  return new Date(date).toLocaleString();
}

function showNotification(message, type) {
  if (typeof window.showNotification === 'function') {
    window.showNotification(message, type);
  } else {
    alert(message);
  }
}

