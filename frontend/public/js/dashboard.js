// Dashboard Main Controller
const API_BASE = "http://localhost:5000/api";

// Global State
const globalState = {
  filters: {
    timeRange: '24h',
    dataSources: ['reddit', 'news'],
    market: 'us',
    sector: 'all',
    sentiment: 'all',
    mentionType: ['posts', 'comments'],
    language: 'en',
    minEngagement: {},
    timeDecay: 'off',
    weighting: 'default',
    alertMode: true
  },
  currentPage: 'home',
  sidebarOpen: true,
  filtersOpen: false,
  loading: false
};

// Loading Utility Functions
function showLoading(message = 'Loading...') {
  if (globalState.loading) return; // Prevent multiple loading overlays
  
  globalState.loading = true;
  
  const overlay = document.createElement('div');
  overlay.className = 'loading-overlay';
  overlay.id = 'globalLoadingOverlay';
  overlay.innerHTML = `
    <div>
      <div class="loading-spinner"></div>
      <div class="loading-text">${message}</div>
    </div>
  `;
  
  document.body.appendChild(overlay);
  document.body.style.overflow = 'hidden';
}

function hideLoading() {
  globalState.loading = false;
  
  const overlay = document.getElementById('globalLoadingOverlay');
  if (overlay) {
    overlay.remove();
  }
  document.body.style.overflow = '';
}

function showButtonLoading(button, originalText = null) {
  if (!button) return;
  
  if (!originalText) {
    button.dataset.originalText = button.textContent || button.innerHTML;
  }
  
  button.classList.add('btn-loading');
  button.disabled = true;
}

function hideButtonLoading(button) {
  if (!button) return;
  
  button.classList.remove('btn-loading');
  button.disabled = false;
  
  if (button.dataset.originalText) {
    button.textContent = button.dataset.originalText;
    button.innerHTML = button.dataset.originalText;
    delete button.dataset.originalText;
  }
}

function showCardLoading(card) {
  if (!card) return;
  card.classList.add('card-loading');
}

function hideCardLoading(card) {
  if (!card) return;
  card.classList.remove('card-loading');
}

// Make functions globally available
window.showLoading = showLoading;
window.hideLoading = hideLoading;
window.showButtonLoading = showButtonLoading;
window.hideButtonLoading = hideButtonLoading;
window.showCardLoading = showCardLoading;
window.hideCardLoading = hideCardLoading;

// Initialize Dashboard
document.addEventListener("DOMContentLoaded", () => {
  initializeDashboard();
  setupEventListeners();
  loadInitialData();
});

function initializeDashboard() {
  // Set timezone
  const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
  document.getElementById('timezoneDisplay').textContent = timezone;
  
  // Load saved filters from localStorage
  const savedFilters = localStorage.getItem('globalFilters');
  if (savedFilters) {
    try {
      globalState.filters = { ...globalState.filters, ...JSON.parse(savedFilters) };
      applyFiltersToUI();
    } catch (e) {
      console.error('Error loading saved filters:', e);
    }
  }
}

function setupEventListeners() {
  // Sidebar toggle
  document.getElementById('sidebarToggle').addEventListener('click', toggleSidebar);
  
  // Filter toggle
  document.getElementById('filterToggleBtn').addEventListener('click', toggleFilters);
  document.getElementById('closeFiltersBtn').addEventListener('click', toggleFilters);
  
  // Global refresh
  document.getElementById('globalRefreshBtn').addEventListener('click', () => {
    showButtonLoading(document.getElementById('globalRefreshBtn'), '🔄');
    refreshAllData().finally(() => {
      hideButtonLoading(document.getElementById('globalRefreshBtn'));
    });
  });
  
  // Navigation items
  document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', (e) => {
      e.preventDefault();
      const page = item.dataset.page;
      navigateToPage(page);
    });
  });
  
  // Filter controls
  setupFilterListeners();
  
  // Time range custom toggle
  document.getElementById('timeRangeFilter').addEventListener('change', (e) => {
    const customRange = document.getElementById('customTimeRange');
    if (e.target.value === 'custom') {
      customRange.style.display = 'block';
    } else {
      customRange.style.display = 'none';
    }
  });
  
  // Sentiment range toggle
  document.getElementById('sentimentFilter').addEventListener('change', (e) => {
    const rangeInputs = document.getElementById('sentimentRange');
    if (e.target.value === 'range') {
      rangeInputs.style.display = 'block';
    } else {
      rangeInputs.style.display = 'none';
    }
  });
  
  // Time decay alpha slider
  document.getElementById('timeDecayFilter').addEventListener('change', (e) => {
    const alphaSlider = document.getElementById('decayAlpha');
    if (e.target.value === 'exponential' || e.target.value === 'linear') {
      alphaSlider.style.display = 'block';
    } else {
      alphaSlider.style.display = 'none';
    }
  });
  
  // Apply filters
  document.getElementById('applyFiltersBtn').addEventListener('click', applyFilters);
  document.getElementById('resetFiltersBtn').addEventListener('click', resetFilters);
}

function setupFilterListeners() {
  // Data sources checkboxes
  const sourceCheckboxes = document.querySelectorAll('#globalFiltersPanel input[type="checkbox"][value]');
  sourceCheckboxes.forEach(cb => {
    cb.addEventListener('change', updateFilterCount);
  });
  
  // All other filter inputs
  const filterInputs = document.querySelectorAll('#globalFiltersPanel select, #globalFiltersPanel input');
  filterInputs.forEach(input => {
    input.addEventListener('change', updateFilterCount);
  });
}

function toggleSidebar() {
  const sidebar = document.getElementById('sidebar');
  globalState.sidebarOpen = !globalState.sidebarOpen;
  sidebar.classList.toggle('collapsed', !globalState.sidebarOpen);
}

function toggleFilters() {
  const panel = document.getElementById('globalFiltersPanel');
  globalState.filtersOpen = !globalState.filtersOpen;
  panel.style.display = globalState.filtersOpen ? 'block' : 'none';
}

function applyFilters() {
  // Collect filter values
  const filters = {
    timeRange: document.getElementById('timeRangeFilter').value,
    dataSources: Array.from(document.querySelectorAll('#globalFiltersPanel input[type="checkbox"][value]:checked'))
      .map(cb => cb.value),
    market: document.getElementById('marketFilter').value,
    sector: document.getElementById('sectorFilter').value,
    sentiment: document.getElementById('sentimentFilter').value,
    mentionType: Array.from(document.querySelectorAll('#globalFiltersPanel input[type="checkbox"][value]:checked'))
      .map(cb => cb.value),
    language: document.getElementById('languageFilter').value,
    minEngagement: {
      upvotes: parseInt(document.getElementById('minUpvotes').value) || 0,
      comments: parseInt(document.getElementById('minComments').value) || 0,
      shares: parseInt(document.getElementById('minShares').value) || 0
    },
    timeDecay: document.getElementById('timeDecayFilter').value,
    weighting: document.getElementById('weightingFilter').value,
    alertMode: document.getElementById('alertModeToggle').checked
  };
  
  // Handle custom time range
  if (filters.timeRange === 'custom') {
    filters.timeFrom = document.getElementById('timeFrom').value;
    filters.timeTo = document.getElementById('timeTo').value;
  }
  
  // Handle sentiment range
  if (filters.sentiment === 'range') {
    filters.sentimentMin = parseFloat(document.getElementById('sentimentMin').value) || -1;
    filters.sentimentMax = parseFloat(document.getElementById('sentimentMax').value) || 1;
  }
  
  // Update global state
  globalState.filters = filters;
  
  // Save to localStorage
  localStorage.setItem('globalFilters', JSON.stringify(filters));
  
  // Update filter count
  updateFilterCount();
  
  // Close filters panel
  toggleFilters();
  
  // Reload data with new filters
  refreshAllData();
  
  // Show notification
  showNotification('Filters applied successfully', 'success');
}

function resetFilters() {
  // Reset to defaults
  globalState.filters = {
    timeRange: '24h',
    dataSources: ['reddit', 'news'],
    market: 'us',
    sector: 'all',
    sentiment: 'all',
    mentionType: ['posts', 'comments'],
    language: 'en',
    minEngagement: {},
    timeDecay: 'off',
    weighting: 'default',
    alertMode: true
  };
  
  applyFiltersToUI();
  applyFilters();
}

function applyFiltersToUI() {
  const filters = globalState.filters;
  
  // Apply to UI elements
  if (document.getElementById('timeRangeFilter')) {
    document.getElementById('timeRangeFilter').value = filters.timeRange || '24h';
  }
  
  // Update checkboxes
  document.querySelectorAll('#globalFiltersPanel input[type="checkbox"][value]').forEach(cb => {
    if (filters.dataSources && filters.dataSources.includes(cb.value)) {
      cb.checked = true;
    } else if (filters.mentionType && filters.mentionType.includes(cb.value)) {
      cb.checked = true;
    } else {
      cb.checked = false;
    }
  });
  
  if (document.getElementById('marketFilter')) {
    document.getElementById('marketFilter').value = filters.market || 'us';
  }
  if (document.getElementById('sectorFilter')) {
    document.getElementById('sectorFilter').value = filters.sector || 'all';
  }
  if (document.getElementById('sentimentFilter')) {
    document.getElementById('sentimentFilter').value = filters.sentiment || 'all';
  }
  if (document.getElementById('languageFilter')) {
    document.getElementById('languageFilter').value = filters.language || 'en';
  }
  if (document.getElementById('timeDecayFilter')) {
    document.getElementById('timeDecayFilter').value = filters.timeDecay || 'off';
  }
  if (document.getElementById('weightingFilter')) {
    document.getElementById('weightingFilter').value = filters.weighting || 'default';
  }
  if (document.getElementById('alertModeToggle')) {
    document.getElementById('alertModeToggle').checked = filters.alertMode !== false;
  }
}

function updateFilterCount() {
  // Count active filters
  let count = 0;
  
  // Count non-default selections
  if (document.getElementById('timeRangeFilter')?.value !== '24h') count++;
  if (document.getElementById('marketFilter')?.value !== 'us') count++;
  if (document.getElementById('sectorFilter')?.value !== 'all') count++;
  if (document.getElementById('sentimentFilter')?.value !== 'all') count++;
  if (document.getElementById('languageFilter')?.value !== 'en') count++;
  
  // Count checked sources
  const checkedSources = document.querySelectorAll('#globalFiltersPanel input[type="checkbox"][value]:checked').length;
  if (checkedSources !== 2) count++; // Default is 2 (reddit, news)
  
  // Update filter count badge
  const filterCount = document.getElementById('filterCount');
  if (filterCount) {
    filterCount.textContent = count;
    filterCount.style.display = count > 0 ? 'inline-block' : 'none';
  }
}

function navigateToPage(page) {
  // Update active nav item
  document.querySelectorAll('.nav-item').forEach(item => {
    item.classList.remove('active');
    if (item.dataset.page === page) {
      item.classList.add('active');
    }
  });
  
  globalState.currentPage = page;
  
  // Load page content (for SPA behavior)
  // In a real implementation, you'd load different pages here
  // For now, we'll just update the URL
  if (page !== 'home') {
    window.location.href = `${page}.html`;
  }
}

async function refreshAllData() {
  showLoading('Refreshing all data...');
  
  try {
    // Trigger refresh for current page
    if (typeof refreshHomeData === 'function') {
      await refreshHomeData();
    }
    
    // Refresh alerts
    if (typeof loadAlerts === 'function') {
      await loadAlerts();
    }
    
    showNotification('Data refreshed', 'success');
    hideLoading();
  } catch (error) {
    console.error('Error refreshing data:', error);
    showNotification('Error refreshing data', 'error');
    hideLoading();
  }
}

async function loadInitialData() {
  // Load home page data if on home page
  if (globalState.currentPage === 'home' && typeof loadHomeData === 'function') {
    await loadHomeData();
  }
  
  // Load alerts
  if (typeof loadAlerts === 'function') {
    await loadAlerts();
  }
}

function showNotification(message, type = 'info') {
  // Simple notification system
  const notification = document.createElement('div');
  notification.className = `notification notification-${type}`;
  notification.textContent = message;
  notification.style.cssText = `
    position: fixed;
    top: 80px;
    right: 2rem;
    padding: 1rem 1.5rem;
    background: ${type === 'success' ? '#10b981' : type === 'error' ? '#ef4444' : '#3b82f6'};
    color: white;
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
    z-index: 10000;
    animation: slideIn 0.3s ease;
  `;
  
  document.body.appendChild(notification);
  
  setTimeout(() => {
    notification.style.animation = 'slideOut 0.3s ease';
    setTimeout(() => notification.remove(), 300);
  }, 3000);
}

// Export for use in other scripts
window.globalState = globalState;
window.API_BASE = API_BASE;

