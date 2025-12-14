// Settings Controller
const API_BASE_URL = 'http://localhost:5000/api';

document.addEventListener("DOMContentLoaded", () => {
  loadSettings();
  setupEventListeners();
});

function setupEventListeners() {
  // Theme change handler
  const themeSelect = document.getElementById('themeSelect');
  if (themeSelect) {
    themeSelect.addEventListener('change', (e) => {
      applyTheme(e.target.value);
    });
  }

  // Timezone change handler
  const timezoneSelect = document.getElementById('timezoneSelect');
  if (timezoneSelect) {
    timezoneSelect.addEventListener('change', (e) => {
      updateTimezoneDisplay(e.target.value);
    });
  }
}

async function loadSettings() {
  try {
    const response = await fetch(`${API_BASE_URL}/settings?userId=default`);
    const data = await response.json();
    
    if (data.settings) {
      const settings = data.settings;
      
      // Load user preferences
      if (settings.theme) {
        document.getElementById('themeSelect').value = settings.theme;
        applyTheme(settings.theme);
      }
      if (settings.timezone) {
        document.getElementById('timezoneSelect').value = settings.timezone;
        updateTimezoneDisplay(settings.timezone);
      }
      if (settings.defaultTimeRange) {
        document.getElementById('defaultTimeRange').value = settings.defaultTimeRange;
      }
      
      // Load API keys (masked)
      if (settings.apiKeys) {
        const newsApiKey = document.getElementById('newsApiKey');
        const twitterToken = document.getElementById('twitterToken');
        if (newsApiKey && settings.apiKeys.newsApi === "***") {
          newsApiKey.placeholder = "API key saved (click to change)";
        }
        if (twitterToken && settings.apiKeys.twitterToken === "***") {
          twitterToken.placeholder = "Token saved (click to change)";
        }
      }
      
      // Load notification settings
      if (settings.notifications) {
        const telegramToken = document.getElementById('telegramToken');
        const lineToken = document.getElementById('lineToken');
        const emailAddress = document.getElementById('emailAddress');
        
        if (telegramToken && settings.notifications.telegramToken === "***") {
          telegramToken.placeholder = "Token saved (click to change)";
        }
        if (lineToken && settings.notifications.lineToken === "***") {
          lineToken.placeholder = "Token saved (click to change)";
        }
        if (emailAddress && settings.notifications.email) {
          emailAddress.value = settings.notifications.email;
        }
      }
    }
  } catch (error) {
    console.error('Error loading settings:', error);
    // Fallback to localStorage
    loadSettingsFromLocalStorage();
  }
}

function loadSettingsFromLocalStorage() {
  const settings = JSON.parse(localStorage.getItem('userSettings') || '{}');
  
  if (settings.theme) {
    document.getElementById('themeSelect').value = settings.theme;
    applyTheme(settings.theme);
  }
  if (settings.timezone) {
    document.getElementById('timezoneSelect').value = settings.timezone;
    updateTimezoneDisplay(settings.timezone);
  }
  if (settings.defaultTimeRange) {
    document.getElementById('defaultTimeRange').value = settings.defaultTimeRange;
  }
}

async function saveSettings() {
  const saveBtn = document.querySelector('button[onclick="saveSettings()"]') || 
                  document.querySelector('.btn-primary');
  
  if (saveBtn) {
    showButtonLoading(saveBtn, 'Save Settings');
  }
  
  const settings = {
    theme: document.getElementById('themeSelect').value,
    timezone: document.getElementById('timezoneSelect').value,
    defaultTimeRange: document.getElementById('defaultTimeRange').value
  };
  
  try {
    const response = await fetch(`${API_BASE_URL}/settings?userId=default`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(settings)
    });
    
    const data = await response.json();
    
    if (response.ok) {
      // Also save to localStorage as backup
      localStorage.setItem('userSettings', JSON.stringify(settings));
      
      // Apply theme immediately
      applyTheme(settings.theme);
      updateTimezoneDisplay(settings.timezone);
      
      showNotification('Settings saved successfully!', 'success');
    } else {
      showNotification('Error saving settings: ' + (data.error || 'Unknown error'), 'error');
    }
    
    if (saveBtn) {
      hideButtonLoading(saveBtn);
    }
  } catch (error) {
    console.error('Error saving settings:', error);
    // Fallback to localStorage
    localStorage.setItem('userSettings', JSON.stringify(settings));
    applyTheme(settings.theme);
    updateTimezoneDisplay(settings.timezone);
    showNotification('Settings saved to local storage (offline mode)', 'warning');
    
    if (saveBtn) {
      hideButtonLoading(saveBtn);
    }
  }
}

async function saveApiKeys() {
  const saveBtn = document.querySelector('button[onclick="saveApiKeys()"]');
  
  if (saveBtn) {
    showButtonLoading(saveBtn, 'Save API Keys');
  }
  
  const newsApiKey = document.getElementById('newsApiKey').value.trim();
  const twitterToken = document.getElementById('twitterToken').value.trim();
  
  if (!newsApiKey && !twitterToken) {
    showNotification('Please enter at least one API key', 'warning');
    if (saveBtn) hideButtonLoading(saveBtn);
    return;
  }
  
  const apiKeys = {};
  if (newsApiKey) apiKeys.newsApi = newsApiKey;
  if (twitterToken) apiKeys.twitterToken = twitterToken;
  
  try {
    const response = await fetch(`${API_BASE_URL}/settings?userId=default`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ apiKeys })
    });
    
    const data = await response.json();
    
    if (response.ok) {
      // Clear input fields after saving
      if (newsApiKey) {
        document.getElementById('newsApiKey').value = '';
        document.getElementById('newsApiKey').placeholder = 'API key saved (click to change)';
      }
      if (twitterToken) {
        document.getElementById('twitterToken').value = '';
        document.getElementById('twitterToken').placeholder = 'Token saved (click to change)';
      }
      showNotification('API keys saved successfully!', 'success');
    } else {
      showNotification('Error saving API keys: ' + (data.error || 'Unknown error'), 'error');
    }
    
    if (saveBtn) {
      hideButtonLoading(saveBtn);
    }
  } catch (error) {
    console.error('Error saving API keys:', error);
    showNotification('Error saving API keys. Please try again.', 'error');
    
    if (saveBtn) {
      hideButtonLoading(saveBtn);
    }
  }
}

async function saveNotificationSettings() {
  const saveBtn = document.querySelector('button[onclick="saveNotificationSettings()"]');
  
  if (saveBtn) {
    showButtonLoading(saveBtn, 'Save Notification Settings');
  }
  
  const telegramToken = document.getElementById('telegramToken').value.trim();
  const lineToken = document.getElementById('lineToken').value.trim();
  const emailAddress = document.getElementById('emailAddress').value.trim();
  
  if (!telegramToken && !lineToken && !emailAddress) {
    showNotification('Please enter at least one notification method', 'warning');
    if (saveBtn) hideButtonLoading(saveBtn);
    return;
  }
  
  const notifications = {};
  if (telegramToken) notifications.telegramToken = telegramToken;
  if (lineToken) notifications.lineToken = lineToken;
  if (emailAddress) notifications.email = emailAddress;
  
  try {
    const response = await fetch(`${API_BASE_URL}/settings?userId=default`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ notifications })
    });
    
    const data = await response.json();
    
    if (response.ok) {
      // Clear input fields after saving
      if (telegramToken) {
        document.getElementById('telegramToken').value = '';
        document.getElementById('telegramToken').placeholder = 'Token saved (click to change)';
      }
      if (lineToken) {
        document.getElementById('lineToken').value = '';
        document.getElementById('lineToken').placeholder = 'Token saved (click to change)';
      }
      showNotification('Notification settings saved successfully!', 'success');
    } else {
      showNotification('Error saving notification settings: ' + (data.error || 'Unknown error'), 'error');
    }
    
    if (saveBtn) {
      hideButtonLoading(saveBtn);
    }
  } catch (error) {
    console.error('Error saving notification settings:', error);
    showNotification('Error saving notification settings. Please try again.', 'error');
    
    if (saveBtn) {
      hideButtonLoading(saveBtn);
    }
  }
}

function applyTheme(theme) {
  const body = document.body;
  if (theme === 'light') {
    body.classList.remove('dark-theme');
    body.classList.add('light-theme');
  } else {
    body.classList.remove('light-theme');
    body.classList.add('dark-theme');
  }
  
  // Save to localStorage for persistence
  localStorage.setItem('theme', theme);
}

function updateTimezoneDisplay(timezone) {
  const timezoneDisplay = document.getElementById('timezoneDisplay');
  if (timezoneDisplay) {
    // Format timezone for display
    const tzMap = {
      'UTC': 'UTC',
      'America/New_York': 'EST',
      'Asia/Bangkok': 'BKK'
    };
    timezoneDisplay.textContent = tzMap[timezone] || timezone;
  }
  
  // Save to localStorage
  localStorage.setItem('timezone', timezone);
}

function showNotification(message, type = 'info') {
  // Try to use dashboard notification if available
  if (typeof window.showNotification === 'function') {
    window.showNotification(message, type);
    return;
  }
  
  // Create custom notification
  const notification = document.createElement('div');
  notification.className = `notification notification-${type}`;
  notification.textContent = message;
  notification.style.cssText = `
    position: fixed;
    top: 20px;
    right: 20px;
    padding: 15px 20px;
    background: ${type === 'success' ? '#4caf50' : type === 'error' ? '#f44336' : type === 'warning' ? '#ff9800' : '#2196f3'};
    color: white;
    border-radius: 4px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.2);
    z-index: 10000;
    animation: slideIn 0.3s ease-out;
  `;
  
  document.body.appendChild(notification);
  
  setTimeout(() => {
    notification.style.animation = 'slideOut 0.3s ease-out';
    setTimeout(() => {
      document.body.removeChild(notification);
    }, 300);
  }, 3000);
}

// Load theme on page load
const savedTheme = localStorage.getItem('theme') || 'dark';
applyTheme(savedTheme);

// Load timezone on page load
const savedTimezone = localStorage.getItem('timezone') || 'UTC';
if (document.getElementById('timezoneSelect')) {
  document.getElementById('timezoneSelect').value = savedTimezone;
  updateTimezoneDisplay(savedTimezone);
}
