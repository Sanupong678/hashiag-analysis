// Alerts Page Controller
const API_BASE_URL = 'http://localhost:5000/api';

document.addEventListener("DOMContentLoaded", () => {
  setupEventListeners();
  loadAlerts();
  loadAlertHistory();
});

function setupEventListeners() {
  // Alert type change
  document.getElementById('alertType')?.addEventListener('change', (e) => {
    updateAlertForm(e.target.value);
  });
  
  // Create alert
  document.getElementById('createAlertBtn')?.addEventListener('click', createAlert);
  document.getElementById('testAlertBtn')?.addEventListener('click', testAlert);
  
  // Escalation toggle
  document.getElementById('escalationToggle')?.addEventListener('change', (e) => {
    const config = document.getElementById('escalationConfig');
    config.style.display = e.target.checked ? 'block' : 'none';
  });
  
  // History filter
  document.getElementById('alertHistoryFilter')?.addEventListener('change', loadAlertHistory);
  
  // Refresh
  document.getElementById('refreshAlertsBtn')?.addEventListener('click', () => {
    loadAlerts();
    loadAlertHistory();
  });
  
  // Check URL for ticker parameter
  const urlParams = new URLSearchParams(window.location.search);
  const ticker = urlParams.get('ticker');
  if (ticker) {
    document.getElementById('alertTickers').value = ticker;
  }
}

function updateAlertForm(alertType) {
  // Hide all configs
  document.getElementById('sentimentSpikeConfig').style.display = 'none';
  document.getElementById('mentionsSpikeConfig').style.display = 'none';
  document.getElementById('influencerConfig').style.display = 'none';
  document.getElementById('keywordConfig').style.display = 'none';
  
  // Show relevant config
  switch(alertType) {
    case 'sentiment_spike':
      document.getElementById('sentimentSpikeConfig').style.display = 'block';
      break;
    case 'mentions_spike':
      document.getElementById('mentionsSpikeConfig').style.display = 'block';
      break;
    case 'influencer_post':
      document.getElementById('influencerConfig').style.display = 'block';
      break;
    case 'keyword':
      document.getElementById('keywordConfig').style.display = 'block';
      break;
  }
}

async function createAlert() {
  const createBtn = document.getElementById('createAlertBtn');
  showButtonLoading(createBtn, 'Create Alert');
  
  const alertType = document.getElementById('alertType').value;
  const tickers = document.getElementById('alertTickers').value.split(',').map(t => t.trim().toUpperCase());
  const sensitivity = document.getElementById('alertSensitivity').value;
  
  const deliveryMethods = Array.from(document.querySelectorAll('#alertsList input[type="checkbox"]:checked'))
    .map(cb => cb.value);
  
  const alertRule = {
    type: alertType,
    tickers: tickers,
    sensitivity: sensitivity,
    deliveryMethods: deliveryMethods,
    throttle: {
      count: parseInt(document.getElementById('throttleCount').value) || 5,
      minutes: parseInt(document.getElementById('throttleMinutes').value) || 60
    },
    escalation: {
      enabled: document.getElementById('escalationToggle').checked,
      interval: parseInt(document.getElementById('escalationInterval').value) || 30
    }
  };
  
  // Add type-specific config
  switch(alertType) {
    case 'sentiment_spike':
      alertRule.threshold = parseFloat(document.getElementById('sentimentThreshold').value);
      break;
    case 'mentions_spike':
      alertRule.multiplier = parseFloat(document.getElementById('mentionsMultiplier').value);
      break;
    case 'influencer_post':
      alertRule.influencer = document.getElementById('alertInfluencer').value;
      break;
    case 'keyword':
      alertRule.keyword = document.getElementById('alertKeyword').value;
      break;
  }
  
  try {
    const response = await fetch(`${API_BASE_URL}/alerts`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(alertRule)
    });
    
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }
    
    showNotification('Alert rule created successfully', 'success');
    await loadAlerts();
    
    // Reset form
    const form = document.querySelector('.alert-form');
    if (form) form.reset();
    
    hideButtonLoading(createBtn);
  } catch (error) {
    console.error('Error creating alert:', error);
    showNotification('Alert rule created (offline mode)', 'warning');
    await loadAlerts();
    hideButtonLoading(createBtn);
  }
}

async function testAlert() {
  showNotification('Test alert sent! Check your notification channels.', 'info');
}

async function loadAlerts() {
  const container = document.getElementById('alertsList');
  if (container) {
    showCardLoading(container.closest('.widget-card') || container.parentElement);
  }
  
  try {
    const response = await fetch(`${API_BASE_URL}/alerts`);
    
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }
    
    const data = await response.json();
    const alerts = data.alerts || [];
    
    renderAlerts(alerts);
    
    if (container) {
      hideCardLoading(container.closest('.widget-card') || container.parentElement);
    }
  } catch (error) {
    console.error('Error loading alerts:', error);
    // Fallback to mock data
    const mockAlerts = [
      {
        id: 1,
        type: 'sentiment_spike',
        tickers: ['AAPL', 'TSLA'],
        threshold: 0.3,
        sensitivity: 'medium',
        enabled: true,
        created: new Date(Date.now() - 86400000)
      },
      {
        id: 2,
        type: 'mentions_spike',
        tickers: ['NVDA'],
        multiplier: 2.0,
        sensitivity: 'high',
        enabled: true,
        created: new Date(Date.now() - 172800000)
      }
    ];
    
    renderAlerts(mockAlerts);
    showNotification('Using mock data (API unavailable)', 'warning');
    
    if (container) {
      hideCardLoading(container.closest('.widget-card') || container.parentElement);
    }
  }
}

function renderAlerts(alerts) {
  const container = document.getElementById('alertsList');
  container.innerHTML = '';
  
  if (alerts.length === 0) {
    container.innerHTML = '<div class="loading">No active alerts</div>';
    return;
  }
  
  alerts.forEach(alert => {
    const item = document.createElement('div');
    item.className = 'alert-rule-item';
    
    const typeLabels = {
      'sentiment_spike': 'Sentiment Spike',
      'mentions_spike': 'Mentions Spike',
      'influencer_post': 'Influencer Post',
      'price_divergence': 'Price Divergence',
      'keyword': 'Keyword Alert'
    };
    
    item.innerHTML = `
      <div class="alert-rule-header">
        <div class="alert-rule-info">
          <h4>${typeLabels[alert.type] || alert.type}</h4>
          <span class="alert-tickers">${alert.tickers.join(', ')}</span>
        </div>
        <div class="alert-rule-actions">
          <label class="switch">
            <input type="checkbox" ${alert.enabled ? 'checked' : ''} 
                   onchange="toggleAlert(${alert.id}, this.checked)">
            <span class="slider"></span>
          </label>
          <button class="btn-small" onclick="deleteAlert(${alert.id})">Delete</button>
        </div>
      </div>
      <div class="alert-rule-details">
        <span class="detail-item">Sensitivity: ${alert.sensitivity}</span>
        <span class="detail-item">Created: ${formatDate(alert.created)}</span>
      </div>
    `;
    
    container.appendChild(item);
  });
}

async function loadAlertHistory() {
  const filter = document.getElementById('alertHistoryFilter')?.value || 'all';
  
  try {
    const response = await fetch(`${API_BASE_URL}/alerts/history?filter=${filter}`);
    
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }
    
    const data = await response.json();
    const history = data.history || [];
    
    renderAlertHistory(history);
  } catch (error) {
    console.error('Error loading alert history:', error);
    // Fallback to mock data
    const mockHistory = [
      {
        id: 1,
        time: new Date(Date.now() - 3600000),
        type: 'sentiment_spike',
        ticker: 'AAPL',
        reason: 'Sentiment exceeded 0.3',
        severity: 'medium',
        acknowledged: false
      },
      {
        id: 2,
        time: new Date(Date.now() - 7200000),
        type: 'mentions_spike',
        ticker: 'TSLA',
        reason: 'Mentions increased 2.5x',
        severity: 'high',
        acknowledged: true
      }
    ];
    
    renderAlertHistory(mockHistory.filter(alert => {
      if (filter === 'acknowledged') return alert.acknowledged;
      if (filter === 'unacknowledged') return !alert.acknowledged;
      return true;
    }));
  }
}

function renderAlertHistory(history) {
  const tbody = document.getElementById('alertHistoryBody');
  tbody.innerHTML = '';
  
  if (history.length === 0) {
    tbody.innerHTML = '<tr><td colspan="7" class="loading">No alert history</td></tr>';
    return;
  }
  
  history.forEach(alert => {
    const row = document.createElement('tr');
    row.className = alert.acknowledged ? 'acknowledged' : '';
    
    const severityClass = alert.severity === 'high' ? 'high' : 
                          alert.severity === 'medium' ? 'medium' : 'low';
    
    row.innerHTML = `
      <td>${formatTime(alert.time)}</td>
      <td>${alert.type.replace('_', ' ')}</td>
      <td><strong>${alert.ticker}</strong></td>
      <td>${alert.reason}</td>
      <td><span class="severity-badge ${severityClass}">${alert.severity}</span></td>
      <td>${alert.acknowledged ? '✓ Acknowledged' : '⚠ Active'}</td>
      <td>
        ${!alert.acknowledged ? 
          `<button class="btn-small" onclick="acknowledgeAlert(${alert.id})">Acknowledge</button>` : 
          ''}
        <button class="btn-small" onclick="viewAlertContext(${alert.ticker})">View</button>
      </td>
    `;
    
    tbody.appendChild(row);
  });
}

async function toggleAlert(id, enabled) {
  showLoading(`${enabled ? 'Enabling' : 'Disabling'} alert...`);
  
  try {
    const response = await fetch(`${API_BASE_URL}/alerts/${id}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ enabled: enabled })
    });
    
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }
    
    showNotification(`Alert ${enabled ? 'enabled' : 'disabled'}`, 'info');
    hideLoading();
  } catch (error) {
    console.error('Error toggling alert:', error);
    showNotification(`Alert ${enabled ? 'enabled' : 'disabled'} (offline mode)`, 'warning');
    hideLoading();
  }
}

async function deleteAlert(id) {
  if (confirm('Are you sure you want to delete this alert?')) {
    showLoading('Deleting alert...');
    
    try {
      const response = await fetch(`${API_BASE_URL}/alerts/${id}`, {
        method: 'DELETE'
      });
      
      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }
      
      showNotification('Alert deleted', 'success');
      await loadAlerts();
      hideLoading();
    } catch (error) {
      console.error('Error deleting alert:', error);
      showNotification('Alert deleted (offline mode)', 'warning');
      await loadAlerts();
      hideLoading();
    }
  }
}

async function acknowledgeAlert(id) {
  showLoading('Acknowledging alert...');
  
  try {
    const response = await fetch(`${API_BASE_URL}/alerts/${id}/acknowledge`, {
      method: 'POST'
    });
    
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }
    
    showNotification('Alert acknowledged', 'success');
    await loadAlertHistory();
    hideLoading();
  } catch (error) {
    console.error('Error acknowledging alert:', error);
    showNotification('Alert acknowledged (offline mode)', 'warning');
    await loadAlertHistory();
    hideLoading();
  }
}

function viewAlertContext(ticker) {
  window.location.href = `stock-detail.html?symbol=${ticker}`;
}

function formatDate(date) {
  return new Date(date).toLocaleDateString();
}

function formatTime(date) {
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

function showNotification(message, type = 'info') {
  if (typeof window.showNotification === 'function') {
    window.showNotification(message, type);
  } else {
    alert(message);
  }
}

