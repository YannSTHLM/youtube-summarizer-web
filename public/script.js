/**
 * YouTube Transcript Summarizer - Frontend JavaScript
 */

// API endpoint (relative to current domain for Vercel)
const API_URL = '/api';

// State
let isProcessing = false;
let results = [];

// DOM Elements
const channelInput = document.getElementById('channelInput');
const processBtn = document.getElementById('processBtn');
const addChannelsBtn = document.getElementById('addChannelsBtn');
const clearBtn = document.getElementById('clearBtn');
const progressSection = document.getElementById('progressSection');
const progressFill = document.getElementById('progressFill');
const progressText = document.getElementById('progressText');
const currentTask = document.getElementById('currentTask');
const resultsSection = document.getElementById('resultsSection');
const resultsList = document.getElementById('resultsList');
const statsBar = document.getElementById('statsBar');
const downloadAllBtn = document.getElementById('downloadAllBtn');
const clearResultsBtn = document.getElementById('clearResultsBtn');
const errorMessage = document.getElementById('errorMessage');
const youtubeStatus = document.getElementById('youtubeStatus');
const openaiStatus = document.getElementById('openaiStatus');
const historyList = document.getElementById('historyList');
const historySearch = document.getElementById('historySearch');
const clearHistoryBtn = document.getElementById('clearHistoryBtn');

// Example channels
const EXAMPLE_CHANNELS = [
    'UC_x5XG1OV2P6uZZ5FSM9Ttw',
    '@3Blue1Brown',
    '@mkbhd',
    '@veritasium'
];

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initDarkMode();
    checkConfig();
    setupEventListeners();
    loadSavedChannels();
});

// Initialize dark mode
function initDarkMode() {
    const darkModeToggle = document.getElementById('darkModeToggle');
    const toggleIcon = darkModeToggle.querySelector('.toggle-icon');
    
    // Check for saved preference or system preference
    const savedTheme = localStorage.getItem('theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    
    if (savedTheme === 'dark' || (!savedTheme && prefersDark)) {
        document.documentElement.setAttribute('data-theme', 'dark');
        toggleIcon.textContent = '☀️';
    } else {
        document.documentElement.setAttribute('data-theme', 'light');
        toggleIcon.textContent = '🌙';
    }
    
    // Toggle dark mode
    darkModeToggle.addEventListener('click', () => {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        
        document.documentElement.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);
        
        toggleIcon.textContent = newTheme === 'dark' ? '☀️' : '🌙';
    });
}

// Setup event listeners
function setupEventListeners() {
    processBtn.addEventListener('click', processChannels);
    addChannelsBtn.addEventListener('click', addExampleChannels);
    clearBtn.addEventListener('click', clearInput);
    downloadAllBtn.addEventListener('click', downloadAllSummaries);
    clearResultsBtn.addEventListener('click', clearResults);
    clearHistoryBtn.addEventListener('click', clearHistory);
    historySearch.addEventListener('input', filterHistory);
}

// Check API configuration
async function checkConfig() {
    try {
        const response = await fetch(`${API_URL}/config/check`);
        const config = await response.json();
        updateStatus(youtubeStatus, config.youtube_configured);
        updateStatus(openaiStatus, config.openai_configured);
    } catch (error) {
        console.error('Error checking config:', error);
        updateStatus(youtubeStatus, false);
        updateStatus(openaiStatus, false);
    }
}

// Update status indicator
function updateStatus(element, isConfigured) {
    const icon = element.querySelector('.status-icon');
    if (isConfigured) {
        element.classList.add('configured');
        element.classList.remove('not-configured');
        icon.textContent = '✅';
    } else {
        element.classList.add('not-configured');
        element.classList.remove('configured');
        icon.textContent = '❌';
    }
}

// Add example channels
function addExampleChannels() {
    const currentText = channelInput.value.trim();
    const newText = EXAMPLE_CHANNELS.join('\n');
    channelInput.value = currentText ? currentText + '\n' + newText : newText;
}

// Clear input
function clearInput() {
    channelInput.value = '';
}

// Show error
function showError(message) {
    errorMessage.textContent = message;
    errorMessage.style.display = 'block';
    setTimeout(() => {
        errorMessage.style.display = 'none';
    }, 5000);
}

// Process channels
async function processChannels() {
    if (isProcessing) return;
    
    const channelsText = channelInput.value.trim();
    if (!channelsText) {
        showError('Please enter at least one YouTube channel');
        return;
    }
    
    const channels = channelsText.split('\n').map(line => line.trim()).filter(line => line.length > 0);
    
    if (channels.length === 0) {
        showError('Please enter at least one valid channel');
        return;
    }
    
    isProcessing = true;
    processBtn.disabled = true;
    processBtn.innerHTML = '<span class="loading"></span> Processing...';
    
    progressSection.style.display = 'block';
    resultsSection.style.display = 'none';
    progressFill.style.width = '0%';
    progressText.textContent = 'Starting...';
    currentTask.textContent = '';
    
    // Set progress variables
    progressStep = 0;
    totalSteps = channels.length;
    
    const progressInterval = setInterval(updateProgress, 1000);
    
    try {
        const response = await fetch(`${API_URL}/process`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ channels })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.detail || 'Failed to process channels');
        }
        
        results = data.videos;
        displayResults(data);
        
    } catch (error) {
        console.error('Error processing channels:', error);
        showError(`Error: ${error.message}`);
        progressSection.style.display = 'none';
    } finally {
        clearInterval(progressInterval);
        isProcessing = false;
        processBtn.disabled = false;
        processBtn.innerHTML = '🚀 Process Channels & Generate Summaries';
    }
}

// Update progress - simulate based on channels count
let progressStep = 0;
let totalSteps = 0;

function updateProgress() {
    if (totalSteps > 0 && progressStep < totalSteps) {
        progressStep++;
        const percentage = (progressStep / totalSteps) * 100;
        progressFill.style.width = `${percentage}%`;
        progressText.textContent = `Processing channel ${progressStep} of ${totalSteps}`;
    }
}

// Display results
function displayResults(data) {
    progressSection.style.display = 'none';
    resultsSection.style.display = 'block';
    
    statsBar.innerHTML = `
        <div class="stat-item">
            <span class="stat-value">${data.stats.channels_processed}</span>
            <span class="stat-label">Channels</span>
        </div>
        <div class="stat-item">
            <span class="stat-value">${data.stats.videos_found}</span>
            <span class="stat-label">Videos Found</span>
        </div>
        <div class="stat-item">
            <span class="stat-value">${data.stats.summaries_generated}</span>
            <span class="stat-label">Summaries</span>
        </div>
        <div class="stat-item">
            <span class="stat-value">${data.stats.errors}</span>
            <span class="stat-label">Errors</span>
        </div>
    `;
    
    resultsList.innerHTML = '';
    
    if (data.videos.length === 0) {
        resultsList.innerHTML = '<p style="text-align: center; color: #666;">No videos found for today from these channels.</p>';
        return;
    }
    
    data.videos.forEach(video => {
        const card = createVideoCard(video);
        resultsList.appendChild(card);
    });
    
    // Save to history
    const channels = channelInput.value.trim().split('\n').filter(ch => ch.trim());
    saveToHistory(channels, data.videos);
}

// Create video card element
function createVideoCard(video) {
    const card = document.createElement('div');
    card.className = 'video-card';
    
    const publishedDate = new Date(video.published_at).toLocaleString();
    
    let bodyContent = '';
    if (video.summary) {
        bodyContent = `
            <div class="video-summary">${escapeHtml(video.summary)}</div>
            <button class="btn btn-secondary download-btn" onclick="downloadSummary('${escapeHtml(video.title)}', '${escapeHtml(video.summary)}')">
                📥 Download TXT
            </button>
        `;
    } else if (video.error) {
        bodyContent = `<p class="video-error">⚠️ ${escapeHtml(video.error)}</p>`;
    }
    
    card.innerHTML = `
        <div class="video-header">
            <div class="video-title">
                <a href="${escapeHtml(video.url)}" target="_blank" rel="noopener">
                    ${escapeHtml(video.title)}
                </a>
            </div>
            <div class="video-meta">
                <span>📺 ${escapeHtml(video.channel_name)}</span>
                <span>📅 ${publishedDate}</span>
            </div>
        </div>
        <div class="video-body">
            ${bodyContent}
        </div>
    `;
    
    return card;
}

// Download single summary
function downloadSummary(title, summary) {
    const content = `YouTube Video Summary\n${'='.repeat(50)}\n\nTitle: ${title}\n\n${'='.repeat(50)}\n\nSUMMARY:\n\n${summary}\n\n${'='.repeat(50)}\nGenerated on: ${new Date().toLocaleString()}\n`;
    downloadTextFile(content, `${sanitizeFilename(title)}.txt`);
}

// Download all summaries
function downloadAllSummaries() {
    if (results.length === 0) {
        showError('No summaries to download');
        return;
    }
    
    let allContent = `YouTube Video Summaries\nGenerated on: ${new Date().toLocaleString()}\n${'='.repeat(60)}\n\n`;
    
    results.forEach((video, index) => {
        if (video.summary) {
            allContent += `${index + 1}. ${video.title}\nChannel: ${video.channel_name}\nURL: ${video.url}\n${'='.repeat(40)}\n\n${video.summary}\n\n${'='.repeat(60)}\n\n`;
        }
    });
    
    downloadTextFile(allContent, `youtube_summaries_${new Date().toISOString().split('T')[0]}.txt`);
}

// Helper: Download text file
function downloadTextFile(content, filename) {
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
}

// Helper: Sanitize filename
function sanitizeFilename(filename) {
    return filename.replace(/[<>:"/\\|?*]/g, '_').substring(0, 200).trim();
}

// Helper: Escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Clear results
function clearResults() {
    results = [];
    resultsSection.style.display = 'none';
    resultsList.innerHTML = '';
    statsBar.innerHTML = '';
}

// Load history from localStorage
function loadHistory() {
    const history = JSON.parse(localStorage.getItem('summaryHistory') || '[]');
    displayHistory(history);
}

// Display history
function displayHistory(history) {
    if (history.length === 0) {
        historyList.innerHTML = '<p class="history-empty">No history yet. Process some channels to see your summaries here.</p>';
        return;
    }
    
    historyList.innerHTML = '';
    
    history.forEach((item, index) => {
        const historyItem = document.createElement('div');
        historyItem.className = 'history-item';
        historyItem.onclick = () => loadFromHistory(item);
        
        const date = new Date(item.timestamp).toLocaleDateString();
        const videoCount = item.videos ? item.videos.length : 0;
        
        historyItem.innerHTML = `
            <div class="history-item-title">${escapeHtml(item.channels.join(', '))}</div>
            <div class="history-item-meta">
                <span>📅 ${date}</span>
                <span>📺 ${videoCount} videos</span>
            </div>
        `;
        
        historyList.appendChild(historyItem);
    });
}

// Filter history
function filterHistory() {
    const searchTerm = historySearch.value.toLowerCase();
    const history = JSON.parse(localStorage.getItem('summaryHistory') || '[]');
    
    const filtered = history.filter(item => {
        const channelMatch = item.channels.some(ch => ch.toLowerCase().includes(searchTerm));
        const titleMatch = item.videos && item.videos.some(v => v.title.toLowerCase().includes(searchTerm));
        return channelMatch || titleMatch;
    });
    
    displayHistory(filtered);
}

// Clear history
function clearHistory() {
    if (confirm('Are you sure you want to clear all history?')) {
        localStorage.removeItem('summaryHistory');
        loadHistory();
    }
}

// Save to history
function saveToHistory(channels, videos) {
    const history = JSON.parse(localStorage.getItem('summaryHistory') || '[]');
    
    const newEntry = {
        channels: channels,
        videos: videos,
        timestamp: new Date().toISOString()
    };
    
    history.unshift(newEntry);
    
    // Keep only last 50 entries
    if (history.length > 50) {
        history.pop();
    }
    
    localStorage.setItem('summaryHistory', JSON.stringify(history));
    loadHistory();
}

// Load from history
function loadFromHistory(item) {
    results = item.videos || [];
    displayResults({
        videos: results,
        stats: {
            channels_processed: item.channels.length,
            videos_found: results.length,
            summaries_generated: results.filter(v => v.summary).length,
            errors: results.filter(v => v.error).length
        }
    });
}

// Initialize history on load
document.addEventListener('DOMContentLoaded', () => {
    loadHistory();
});

// Load saved channels from localStorage
function loadSavedChannels() {
    const savedChannels = localStorage.getItem('savedChannels');
    if (savedChannels) {
        const channels = JSON.parse(savedChannels);
        if (channels.length > 0) {
            channelInput.value = channels.join('\n');
        }
    }
}

// Save channels to localStorage
function saveChannels() {
    const channelsText = channelInput.value.trim();
    if (!channelsText) return;
    
    const channels = channelsText.split('\n').map(line => line.trim()).filter(line => line.length > 0);
    localStorage.setItem('savedChannels', JSON.stringify(channels));
}

// Add channel to saved list
function addChannelToList(channel) {
    const savedChannels = JSON.parse(localStorage.getItem('savedChannels') || '[]');
    if (!savedChannels.includes(channel)) {
        savedChannels.push(channel);
        localStorage.setItem('savedChannels', JSON.stringify(savedChannels));
    }
}

// Remove channel from saved list
function removeChannelFromList(channel) {
    const savedChannels = JSON.parse(localStorage.getItem('savedChannels') || '[]');
    const updatedChannels = savedChannels.filter(ch => ch !== channel);
    localStorage.setItem('savedChannels', JSON.stringify(updatedChannels));
}

// Get saved channels
function getSavedChannels() {
    return JSON.parse(localStorage.getItem('savedChannels') || '[]');
}

// Save channels when input changes
channelInput.addEventListener('change', saveChannels);
