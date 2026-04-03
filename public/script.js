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

// Update progress from server
async function updateProgress() {
    try {
        const response = await fetch(`${API_URL}/status`);
        const status = await response.json();
        
        if (status.total > 0) {
            const percentage = (status.progress / status.total) * 100;
            progressFill.style.width = `${percentage}%`;
            progressText.textContent = `Processing channel ${status.progress} of ${status.total}`;
            
            if (status.current_channel) {
                currentTask.textContent = `Current: ${status.current_channel}`;
            }
        }
    } catch (error) {
        console.error('Error updating progress:', error);
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