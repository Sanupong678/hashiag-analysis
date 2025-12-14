// Influencer Tracker Controller
const API_BASE_URL = 'http://localhost:5000/api';

let selectedInfluencer = null;

document.addEventListener("DOMContentLoaded", () => {
  setupEventListeners();
  loadInfluencers();
});

function setupEventListeners() {
  document.getElementById('influencerFilter')?.addEventListener('change', loadInfluencers);
}

async function loadInfluencers() {
  const filter = document.getElementById('influencerFilter')?.value || 'all';
  const container = document.getElementById('influencerDirectory');
  
  if (container) {
    showCardLoading(container.closest('.widget-card') || container.parentElement);
  }
  
  try {
    const response = await fetch(`${API_BASE_URL}/influencers?filter=${filter}`);
    
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }
    
    const data = await response.json();
    const influencers = data.influencers || [];
    
    renderInfluencers(influencers);
    
    if (container) {
      hideCardLoading(container.closest('.widget-card') || container.parentElement);
    }
  } catch (error) {
    console.error('Error loading influencers:', error);
    // Fallback to mock data
    const mockInfluencers = [
      {
        id: 1,
        name: 'Elon Musk',
        handle: 'elonmusk',
        platform: 'twitter',
        verified: true,
        followed: true,
        posts: 5,
        avgSentiment: 0.3,
        avgImpact: 2.5,
        reliability: 0.85
      },
      {
        id: 2,
        name: 'Warren Buffett',
        handle: 'WarrenBuffett',
        platform: 'twitter',
        verified: true,
        followed: false,
        posts: 2,
        avgSentiment: 0.1,
        avgImpact: 1.8,
        reliability: 0.92
      }
    ];
    
    renderInfluencers(mockInfluencers.filter(inf => {
      if (filter === 'followed') return inf.followed;
      if (filter === 'detected') return !inf.followed && !inf.suggested;
      if (filter === 'suggested') return inf.suggested;
      return true;
    }));
    showNotification('Using mock data (API unavailable)', 'warning');
    
    if (container) {
      hideCardLoading(container.closest('.widget-card') || container.parentElement);
    }
  }
}

function renderInfluencers(influencers) {
  const container = document.getElementById('influencerDirectory');
  container.innerHTML = '';
  
  influencers.forEach(inf => {
    const item = document.createElement('div');
    item.className = 'influencer-directory-item';
    
    item.innerHTML = `
      <div class="influencer-avatar-large">${inf.name[0]}</div>
      <div class="influencer-info-large">
        <h4>${inf.name} ${inf.verified ? '✓' : ''}</h4>
        <p>@${inf.handle} • ${inf.platform}</p>
        <div class="influencer-stats">
          <span>Posts: ${inf.posts}</span>
          <span>Avg Sentiment: ${(inf.avgSentiment * 100).toFixed(1)}%</span>
          <span>Avg Impact: ${inf.avgImpact.toFixed(1)}%</span>
          <span>Reliability: ${(inf.reliability * 100).toFixed(0)}%</span>
        </div>
      </div>
      <div class="influencer-actions">
        <button class="btn-small ${inf.followed ? 'unfollow' : 'follow'}" 
                onclick="toggleFollow(${inf.id}, ${inf.followed})">
          ${inf.followed ? 'Unfollow' : 'Follow'}
        </button>
        <button class="btn-small" onclick="viewTimeline(${inf.id})">View Timeline</button>
      </div>
    `;
    
    container.appendChild(item);
  });
}

async function toggleFollow(id, currentlyFollowed) {
  showLoading(`${currentlyFollowed ? 'Unfollowing' : 'Following'} influencer...`);
  
  try {
    const method = currentlyFollowed ? 'DELETE' : 'POST';
    const response = await fetch(`${API_BASE_URL}/influencers/${id}/follow`, {
      method: method
    });
    
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }
    
    showNotification(`${currentlyFollowed ? 'Unfollowed' : 'Following'} influencer`, 'success');
    await loadInfluencers();
    hideLoading();
  } catch (error) {
    console.error('Error toggling follow:', error);
    showNotification(`${currentlyFollowed ? 'Unfollowed' : 'Following'} influencer (offline mode)`, 'warning');
    await loadInfluencers();
    hideLoading();
  }
}

async function viewTimeline(id) {
  selectedInfluencer = id;
  const timelineSection = document.getElementById('influencerTimelineSection');
  if (timelineSection) timelineSection.style.display = 'block';
  
  const timelineContainer = document.getElementById('influencerTimeline');
  if (timelineContainer) {
    showCardLoading(timelineContainer);
  }
  
  try {
    const response = await fetch(`${API_BASE_URL}/influencers/${id}/timeline`);
    
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }
    
    const data = await response.json();
    const timeline = data.timeline || [];
    
    renderTimeline(timeline);
    
    if (timelineContainer) {
      hideCardLoading(timelineContainer);
    }
  } catch (error) {
    console.error('Error loading timeline:', error);
    // Fallback to mock data
    const timeline = [
      { time: new Date(Date.now() - 3600000), post: 'Just bought more $AAPL', impact: 1.82, ticker: 'AAPL' },
      { time: new Date(Date.now() - 7200000), post: 'Tesla production looking good', impact: 0.5, ticker: 'TSLA' }
    ];
    
    renderTimeline(timeline);
    
    if (timelineContainer) {
      hideCardLoading(timelineContainer);
    }
  }
}

function renderTimeline(timeline) {
  const container = document.getElementById('influencerTimeline');
  container.innerHTML = '';
  
  timeline.forEach(event => {
    const item = document.createElement('div');
    item.className = 'timeline-event';
    
    item.innerHTML = `
      <div class="timeline-time">${formatTime(event.time)}</div>
      <div class="timeline-content">
        <p>${event.post}</p>
        <div class="timeline-impact">
          <span>Impact on ${event.ticker}: ${event.impact >= 0 ? '+' : ''}${event.impact.toFixed(2)}%</span>
        </div>
      </div>
    `;
    
    container.appendChild(item);
  });
}

function closeTimeline() {
  document.getElementById('influencerTimelineSection').style.display = 'none';
  selectedInfluencer = null;
}

function formatTime(date) {
  const d = new Date(date);
  return d.toLocaleString();
}

function showNotification(message, type) {
  if (typeof window.showNotification === 'function') {
    window.showNotification(message, type);
  } else {
    alert(message);
  }
}

