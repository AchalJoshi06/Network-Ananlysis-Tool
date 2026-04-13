// ============================================
// NETWORK DASHBOARD - IMPROVED JAVASCRIPT
// Complete Features: Notifications, Interactivity, Real-time Updates
// ============================================

// ==================== GLOBAL STATE ====================
const AppState = {
    isMonitoring: false,
    monitoringStartedAt: null,
    speedTrendDelayMs: 5000,
    updateInterval: null,
    speed: { upload: 0, download: 0, peakUp: 0, peakDown: 0 },
    data: { connections: [], processes: [] },
    charts: { speed: null, risk: null, category: null, topTalkers: null },
    notifications: { list: [], count: 0 },
    ui: { dropdownOpen: false, speedRefreshInProgress: false },
    sort: { column: null, direction: 'asc' },
    previousStats: { connections: 0, processes: 0 },
    debounceTimers: {},
    maxDataPoints: 60,  // Kept for backward compatibility
    timeRangeSeconds: 60,
    liveWindowSeconds: 120,
    liveUpdatesEnabled: false,
    speedHistory: [],
    maxSpeedHistorySeconds: 7200,
    speedAxis: {
        // Set useLogScale=true manually if you want logarithmic mode.
        useLogScale: false,
        autoLogScale: false,
        minLinearMax: 128,
        maxLinearMax: 1024 * 1024,
        currentMin: 0,
        currentMax: 128,
        currentMode: 'linear',
        hasError: false
    }
};

// ==================== INITIALIZATION ====================
document.addEventListener('DOMContentLoaded', () => {
    initializeApp();
});

function initializeApp() {
    console.log('🚀 Initializing Dashboard...');
    
    loadDarkMode();
    setupEventListeners();
    initializeCharts();
    updateStatus();
    
    // Default to Live so chart starts streaming immediately.
    changeTimeRange(0);
    
    // Main update loop
    setInterval(updateDashboard, 1000);
    setInterval(updateStatus, 1000);
    
    // Close dropdown when clicking outside
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.notification-bell') && 
            !e.target.closest('.notifications-dropdown')) {
            closeNotificationDropdown();
        }
    });
    
    addNotification('System Started', 'Dashboard initialized and ready', 'info');
    console.log('✅ Dashboard initialized successfully');
}

// ==================== EVENT LISTENERS ====================
function setupEventListeners() {
    // Prevent any unhandled errors from breaking the app
    window.addEventListener('error', (e) => {
        console.error('Application Error:', e);
        addNotification('Error', e.message, 'error');
    });
}

// ==================== MONITORING CONTROLS ====================
async function startMonitoring() {
    try {
        // Show loading skeleton for all stat cards
        ['uploadSpeed', 'downloadSpeed', 'totalConnections', 'totalProcesses', 
         'totalSent', 'totalReceived'].forEach(id => {
            showSkeleton(id);
        });
        
        showToast('Initializing monitoring...', 'info');
        
        const response = await fetch('/api/start', { method: 'POST' });
        const data = await response.json();
        
        if (data.success) {
            AppState.isMonitoring = true;
            AppState.monitoringStartedAt = Date.now();
            showToast('✓ Monitoring Started', 'success');
            addNotification('Monitoring Started', 'Network monitoring is now active', 'info');
            
            setTimeout(() => hideSkeleton(['uploadSpeed', 'downloadSpeed', 'totalConnections', 
                                          'totalProcesses', 'totalSent', 'totalReceived']), 1500);
            updateDashboard();
        } else {
            showToast('Failed to start monitoring: ' + (data.message || 'Unknown error'), 'error');
            addNotification('Error', 'Failed to start monitoring', 'error');
        }
    } catch (error) {
        console.error('Start error:', error);
        showToast('Error starting monitoring', 'error');
        addNotification('Error', error.message, 'error');
    }
}

async function stopMonitoring() {
    try {
        showToast('Stopping monitoring...', 'info');
        
        const response = await fetch('/api/stop', { method: 'POST' });
        const data = await response.json();
        
        if (data.success) {
            AppState.isMonitoring = false;
            AppState.monitoringStartedAt = null;
            showToast('✓ Monitoring Stopped', 'success');
            addNotification('Monitoring Stopped', 'Network monitoring has been stopped', 'info');
        } else {
            showToast('Failed to stop: ' + (data.message || 'Unknown error'), 'error');
        }
    } catch (error) {
        console.error('Stop error:', error);
        showToast('Error stopping monitoring', 'error');
    }
}

async function updateStatus() {
    try {
        const wasMonitoring = AppState.isMonitoring;
        const response = await fetch('/api/status');
        const data = await response.json();
        
        AppState.isMonitoring = data.running;

        if (data.running) {
            // Keep JS timeline aligned with backend runtime.
            AppState.monitoringStartedAt = Date.now() - ((data.elapsed_seconds || 0) * 1000);
        } else if (wasMonitoring) {
            AppState.monitoringStartedAt = null;
        }

        updateStatusUI(data);
    } catch (error) {
        console.error('Status update error:', error);
    }
}

function updateStatusUI(data) {
    const badge = document.getElementById('statusBadge');
    const dot = document.getElementById('statusDot');
    const text = document.getElementById('statusText');
    const runtime = document.getElementById('statusRuntime');
    const startBtn = document.getElementById('startBtn');
    const stopBtn = document.getElementById('stopBtn');
    
    if (!badge || !startBtn) return;
    
    if (data.running) {
        badge.className = 'status-badge running';
        dot?.classList.add('running');
        if (text) text.textContent = 'Running';
        if (runtime) runtime.textContent = `(${formatRuntime(data.elapsed_seconds || 0)})`;
        startBtn.disabled = true;
        stopBtn.disabled = false;
    } else {
        badge.className = 'status-badge stopped';
        dot?.classList.remove('running');
        if (text) text.textContent = 'Stopped';
        if (runtime) runtime.textContent = '(00:00:00)';
        startBtn.disabled = false;
        stopBtn.disabled = true;
    }
}

async function exportData() {
    showToast('Exporting data...', 'info');
    
    try {
        const response = await fetch('/api/export', { method: 'POST' });
        const data = await response.json();
        
        if (data.success) {
            showToast('✓ Data exported successfully', 'success');
            addNotification('Export Complete', 'Network data has been exported', 'info');
        } else {
            showToast('Export failed', 'error');
        }
    } catch (error) {
        console.error('Export error:', error);
        showToast('Error exporting data', 'error');
    }
}

// ==================== NOTIFICATIONS SYSTEM ====================
function toggleNotificationDropdown() {
    const dropdown = document.getElementById('notificationsDropdown');
    if (!dropdown) return;
    
    AppState.ui.dropdownOpen = !AppState.ui.dropdownOpen;
    
    if (AppState.ui.dropdownOpen) {
        dropdown.classList.add('active');
    } else {
        dropdown.classList.remove('active');
    }
}

function closeNotificationDropdown() {
    const dropdown = document.getElementById('notificationsDropdown');
    if (dropdown) {
        dropdown.classList.remove('active');
        AppState.ui.dropdownOpen = false;
    }
}

/**
 * Add a notification to the system
 * @param {string} title - Notification title
 * @param {string} message - Notification message
 * @param {string} type - 'info', 'warning', 'error'
 */
function addNotification(title, message, type = 'info') {
    const notification = {
        id: Date.now(),
        title,
        message,
        type,
        timestamp: new Date(),
        unread: true
    };
    
    AppState.notifications.list.unshift(notification);
    
    // Keep only last 50 notifications
    if (AppState.notifications.list.length > 50) {
        AppState.notifications.list.pop();
    }
    
    updateNotificationUI();
    
    // Auto-remove old notifications after 1 hour
    if (AppState.notifications.list.length > 30) {
        const oneHourAgo = Date.now() - (60 * 60 * 1000);
        AppState.notifications.list = AppState.notifications.list.filter(n => 
            n.timestamp.getTime() > oneHourAgo
        );
    }
}

function updateNotificationUI() {
    const list = document.getElementById('notificationsList');
    const badge = document.getElementById('notificationBadge');
    
    if (!list) return;
    
    const unreadCount = AppState.notifications.list.filter(n => n.unread).length;
    
    // Update badge
    if (badge) {
        if (unreadCount > 0) {
            badge.textContent = unreadCount > 9 ? '9+' : unreadCount;
            badge.style.display = 'flex';
        } else {
            badge.style.display = 'none';
        }
    }
    
    // Update list
    if (AppState.notifications.list.length === 0) {
        list.innerHTML = `
            <div class="empty-notifications">
                <i class="fas fa-check-circle"></i>
                <p>No notifications</p>
            </div>
        `;
    } else {
        list.innerHTML = AppState.notifications.list.map(n => `
            <div class="notification-item ${n.unread ? 'unread' : ''}">
                <div class="notification-item-header">
                    <div class="notification-item-title">${escapeHtml(n.title)}</div>
                    <div class="notification-item-actions">
                        <span class="notification-item-type ${n.type}">
                            <i class="fas fa-${getNotificationIcon(n.type)}"></i>
                            ${n.type}
                        </span>
                        ${n.unread ? `
                            <button
                                class="notification-read-btn"
                                onclick="markNotificationAsRead(${n.id})"
                                title="Mark as read"
                                aria-label="Mark notification as read"
                            >
                                <i class="fas fa-check"></i>
                            </button>
                        ` : ''}
                    </div>
                </div>
                <div class="notification-item-time">${formatTimeAgo(n.timestamp)}</div>
                <div class="notification-item-message">${escapeHtml(n.message)}</div>
            </div>
        `).join('');
    }
}

function markNotificationAsRead(notificationId) {
    const notification = AppState.notifications.list.find(n => n.id === notificationId);
    if (!notification || !notification.unread) return;

    notification.unread = false;
    updateNotificationUI();
}

function clearNotifications() {
    if (confirm('Clear all notifications?')) {
        AppState.notifications.list = [];
        updateNotificationUI();
        showToast('Notifications cleared', 'info');
    }
}

function getNotificationIcon(type) {
    const icons = {
        info: 'info-circle',
        warning: 'exclamation-circle',
        error: 'times-circle',
        success: 'check-circle'
    };
    return icons[type] || 'info-circle';
}

// ==================== AUTO-NOTIFICATIONS ====================
function generateSystemNotifications(stats) {
    // New connection detected
    if (stats.connections > AppState.previousStats.connections) {
        const diff = stats.connections - AppState.previousStats.connections;
        addNotification(
            '🔗 New Connections',
            `${diff} new network connection${diff > 1 ? 's' : ''} detected`,
            'info'
        );
    }
    
    // Connection dropped
    if (stats.connections < AppState.previousStats.connections) {
        const diff = AppState.previousStats.connections - stats.connections;
        addNotification(
            '🔌 Connections Closed',
            `${diff} network connection${diff > 1 ? 's' : ''} closed`,
            'info'
        );
    }
    
    // High upload bandwidth
    if (AppState.speed.upload > 5000) { // > 5 MB/s
        addNotification(
            '📤 High Upload Activity',
            `Upload speed peaked at ${formatSpeed(AppState.speed.upload)}`,
            'warning'
        );
    }
    
    // High download bandwidth
    if (AppState.speed.download > 5000) { // > 5 MB/s
        addNotification(
            '📥 High Download Activity',
            `Download speed peaked at ${formatSpeed(AppState.speed.download)}`,
            'warning'
        );
    }
    
    // Process activity
    if (stats.processes > AppState.previousStats.processes) {
        const diff = stats.processes - AppState.previousStats.processes;
        addNotification(
            '⚙️ Process Activity',
            `${diff} new network process${diff > 1 ? 'es' : ''} started`,
            'info'
        );
    }
    
    AppState.previousStats = { 
        connections: stats.connections, 
        processes: stats.processes 
    };
}

// ==================== DARK MODE ====================
function toggleDarkMode() {
    const isDark = document.body.classList.toggle('dark-mode');
    localStorage.setItem('darkMode', isDark ? 'enabled' : 'disabled');
    
    const icon = document.querySelector('#darkModeToggle i');
    if (icon) {
        icon.className = isDark ? 'fas fa-sun' : 'fas fa-moon';
    }
    
    // Update charts
    updateChartColors();
    showToast(isDark ? '🌙 Dark mode enabled' : '☀️ Light mode enabled', 'info');
}

function loadDarkMode() {
    if (localStorage.getItem('darkMode') === 'enabled') {
        document.body.classList.add('dark-mode');
        const icon = document.querySelector('#darkModeToggle i');
        if (icon) icon.className = 'fas fa-sun';
    }
}

// ==================== CHARTS ====================
function initializeCharts() {
    const isDark = document.body.classList.contains('dark-mode');
    const textColor = isDark ? '#f1f5f9' : '#0f172a';
    const gridColor = isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.05)';
    
    // Speed Chart - Line with dual Y-axis
    const speedCtx = document.getElementById('speedChart');
    if (speedCtx) {
        AppState.charts.speed = new Chart(speedCtx, {
            type: 'line',
            data: { labels: [], datasets: [
                {
                    label: 'Upload (KB/s)',
                    data: [],
                    borderColor: 'rgb(34, 197, 94)',
                    backgroundColor: 'rgba(34, 197, 94, 0.05)',
                    tension: 0.3,
                    fill: true,
                    yAxisID: 'y-upload',
                    borderWidth: 2,
                    pointRadius: 2,
                    pointHoverRadius: 4
                },
                {
                    label: 'Download (KB/s)',
                    data: [],
                    borderColor: 'rgb(59, 130, 246)',
                    backgroundColor: 'rgba(59, 130, 246, 0.05)',
                    tension: 0.3,
                    fill: true,
                    yAxisID: 'y-download',
                    borderWidth: 2,
                    pointRadius: 2,
                    pointHoverRadius: 4
                }
            ]},
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: {
                    duration: 280,
                    easing: 'easeOutCubic'
                },
                interaction: { mode: 'index', intersect: false },
                plugins: {
                    legend: { display: true, position: 'top', labels: { color: textColor, usePointStyle: true } },
                    tooltip: {
                        enabled: true,
                        mode: 'index',
                        intersect: false,
                        callbacks: {
                            afterBody: () => [
                                '',
                                `Peak Upload: ${formatSpeed(AppState.speed.peakUp)}`,
                                `Peak Download: ${formatSpeed(AppState.speed.peakDown)}`
                            ]
                        }
                    }
                },
                scales: {
                    x: { 
                        display: true, 
                        ticks: { 
                            color: textColor,
                            maxTicksLimit: 5,
                            maxRotation: 45,
                            minRotation: 0
                        }, 
                        grid: { display: false } 
                    },
                    'y-upload': {
                        type: 'linear',
                        position: 'left',
                        ticks: { color: 'rgb(34, 197, 94)', callback: v => formatSpeed(v) },
                        grid: { color: 'rgba(34, 197, 94, 0.05)' }
                    },
                    'y-download': {
                        type: 'linear',
                        position: 'right',
                        ticks: { color: 'rgb(59, 130, 246)', callback: v => formatSpeed(v) },
                        grid: { color: 'rgba(59, 130, 246, 0.05)' }
                    }
                }
            }
        });
    }
    
    // Risk Chart - Doughnut with inline legend
    const riskCtx = document.getElementById('riskChart');
    if (riskCtx) {
        AppState.charts.risk = new Chart(riskCtx, {
            type: 'doughnut',
            data: {
                labels: ['Low Risk', 'Medium Risk', 'High Risk', 'Critical'],
                datasets: [{
                    data: [0, 0, 0, 0],
                    backgroundColor: [
                        'rgba(16, 185, 129, 0.8)',
                        'rgba(245, 158, 11, 0.8)',
                        'rgba(239, 68, 68, 0.8)',
                        'rgba(220, 38, 38, 0.8)'
                    ],
                    borderColor: [
                        'rgb(16, 185, 129)',
                        'rgb(245, 158, 11)',
                        'rgb(239, 68, 68)',
                        'rgb(220, 38, 38)'
                    ],
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'bottom', labels: { color: textColor, padding: 15 } },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => {
                                const val = ctx.parsed || 0;
                                const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
                                const pct = total > 0 ? ((val / total) * 100).toFixed(1) : 0;
                                return `${ctx.label}: ${val} (${pct}%)`;
                            }
                        }
                    }
                }
            }
        });
    }
    
    // Category Chart - Bar
    const categoryCtx = document.getElementById('categoryChart');
    if (categoryCtx) {
        AppState.charts.category = new Chart(categoryCtx, {
            type: 'bar',
            data: { labels: [], datasets: [{
                label: 'Connections',
                data: [],
                backgroundColor: 'rgba(99, 102, 241, 0.8)',
                borderColor: 'rgb(99, 102, 241)',
                borderWidth: 1,
                borderRadius: 4
            }]},
            options: {
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: undefined,
                plugins: { legend: { display: false } },
                scales: {
                    x: { ticks: { color: textColor }, grid: { display: false } },
                    y: { beginAtZero: true, ticks: { color: textColor }, grid: { color: gridColor } }
                }
            }
        });
    }
    
    // Top Talkers Chart - Horizontal Bar
    const topTalkersCtx = document.getElementById('topTalkersChart');
    if (topTalkersCtx) {
        AppState.charts.topTalkers = new Chart(topTalkersCtx, {
            type: 'bar',
            data: { labels: [], datasets: [{
                label: 'Data Transfer',
                data: [],
                backgroundColor: 'rgba(168, 85, 247, 0.8)',
                borderColor: 'rgb(168, 85, 247)',
                borderWidth: 1,
                borderRadius: 4
            }]},
            options: {
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: 'y',
                plugins: { legend: { display: false } },
                scales: {
                    x: { 
                        beginAtZero: true, 
                        ticks: { color: textColor, callback: v => formatBytes(v) },
                        grid: { color: gridColor }
                    },
                    y: { ticks: { color: textColor }, grid: { display: false } }
                }
            }
        });
    }
}

function updateChartColors() {
    if (!AppState.charts.speed) return;
    
    const isDark = document.body.classList.contains('dark-mode');
    const textColor = isDark ? '#f1f5f9' : '#0f172a';
    const gridColor = isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.05)';
    
    Object.values(AppState.charts).forEach(chart => {
        if (chart?.options?.plugins?.legend?.labels) {
            chart.options.plugins.legend.labels.color = textColor;
        }
        if (chart?.options?.scales) {
            Object.values(chart.options.scales).forEach(scale => {
                if (scale?.ticks) scale.ticks.color = textColor;
                if (scale?.grid) scale.grid.color = gridColor;
            });
        }
        chart?.update('none');
    });
}

async function updateDashboard() {
    // Always update - backend state is authoritative, not frontend flag
    try {
        // Fetch data in parallel
        const [statsRes, connRes, procRes] = await Promise.all([
            fetch('/api/statistics'),
            fetch('/api/connections'),
            fetch('/api/processes')
        ]);
        
        const statsWrapper = await statsRes.json();
        const connectionsWrapper = await connRes.json();
        const processesWrapper = await procRes.json();
        
        // Extract actual data from wrapper objects
        const stats = statsWrapper.statistics || statsWrapper;
        const connectionsData = connectionsWrapper.connections || connectionsWrapper.data || [];
        const processesData = processesWrapper.processes || processesWrapper.data || [];
        
        console.log('Dashboard update - processes count:', processesData.length, 'processes:', processesData);
        
        // Update state
        AppState.speed = {
            upload: stats.upload_speed || 0,
            download: stats.download_speed || 0,
            peakUp: Math.max(AppState.speed.peakUp, stats.upload_speed || 0),
            peakDown: Math.max(AppState.speed.peakDown, stats.download_speed || 0)
        };
        
        AppState.data = { connections: connectionsData, processes: processesData };
        
        // Update UI
        updateStatistics(stats);
        updateCharts(stats, connectionsData, processesData);
        generateSystemNotifications(stats);
        
    } catch (error) {
        console.error('Dashboard update error:', error);
    }
}

function updateStatistics(stats) {
    // Update stat cards with smooth transitions
    // Use pre-formatted values from API when available
    updateStatValue('uploadSpeed', stats.upload_speed_formatted || formatSpeed(stats.upload_speed || 0));
    updateStatValue('downloadSpeed', stats.download_speed_formatted || formatSpeed(stats.download_speed || 0));
    updateStatValue('totalConnections', stats.total_connections || stats.active_connections || 0);
    updateStatValue('totalProcesses', stats.total_processes || stats.network_processes || 0);
    updateStatValue('totalSent', stats.total_sent_formatted || formatBytes(stats.bytes_sent || 0));
    updateStatValue('totalReceived', stats.total_recv_formatted || formatBytes(stats.bytes_recv || 0));
}

function updateStatValue(elementId, value) {
    const el = document.getElementById(elementId);
    if (!el) {
        console.warn(`Element not found: ${elementId}`);
        return;
    }
    
    // Convert value to string if it's a number
    const newValue = typeof value === 'number' ? String(value) : String(value || '0');
    const current = el.textContent.trim();
    
    if (current !== newValue) {
        el.style.opacity = '0.5';
        el.textContent = newValue;
        setTimeout(() => el.style.opacity = '1', 100);
    }
}

function updateCharts(stats, connections, processes) {
    // Speed chart
    const hasSpeedTrendDelayElapsed =
        AppState.monitoringStartedAt &&
        (Date.now() - AppState.monitoringStartedAt) >= AppState.speedTrendDelayMs;

    if (AppState.charts.speed && AppState.isMonitoring && hasSpeedTrendDelayElapsed && !AppState.speedAxis.hasError) {
        try {
            // Keep collecting history even in static ranges so Live can resume fresh.
            addSpeedHistoryPoint(stats.upload_speed || 0, stats.download_speed || 0, Date.now());

            // Only repaint continuously in Live mode.
            if (AppState.liveUpdatesEnabled) {
                renderSpeedChartFromHistory();
            }
        } catch (error) {
            console.error('Speed chart update failed, using fallback axis:', error);
            const uploadAxis = AppState.charts.speed.options?.scales?.['y-upload'];
            const downloadAxis = AppState.charts.speed.options?.scales?.['y-download'];
            if (uploadAxis) {
                uploadAxis.min = 0;
                uploadAxis.max = AppState.speedAxis.minLinearMax;
            }
            if (downloadAxis) {
                downloadAxis.min = 0;
                downloadAxis.max = AppState.speedAxis.minLinearMax;
            }
            // Avoid recursive update attempts in the same render cycle.
            AppState.speedAxis.hasError = true;
        }
    }
    
    // Risk chart - pie/doughnut
    if (AppState.charts.risk && stats.risk_distribution) {
        try {
            const rd = stats.risk_distribution;
            AppState.charts.risk.data.datasets[0].data = [
                rd.LOW || 0,
                rd.MEDIUM || 0,
                rd.HIGH || 0,
                rd.CRITICAL || 0
            ];
            AppState.charts.risk.update('none');

            // Update inline legend
            updateRiskLegend(rd);
        } catch (error) {
            console.error('Risk chart update error:', error);
        }
    }
    
    // Category chart - protocols from connections
    if (AppState.charts.category && connections && connections.length > 0) {
        try {
            const protocols = {};
            connections.forEach(conn => {
                const proto = conn.app_protocol || conn.protocol || 'Unknown';
                protocols[proto] = (protocols[proto] || 0) + 1;
            });

            // Sort by count and take top 10
            const sorted = Object.entries(protocols)
                .sort((a, b) => b[1] - a[1])
                .slice(0, 10);

            AppState.charts.category.data.labels = sorted.map(s => s[0]);
            AppState.charts.category.data.datasets[0].data = sorted.map(s => s[1]);
            AppState.charts.category.update('none');
        } catch (error) {
            console.error('Category chart update error:', error);
        }
    }
    
    // Top Bandwidth Users chart - processes
    if (AppState.charts.topTalkers && processes && processes.length > 0) {
        try {
            console.log('Updating topTalkers chart with processes:', processes.length);
            // Sort by total bandwidth and take top 10
            const sorted = processes
                .slice()
                .sort((a, b) => ((b.bytes_sent || 0) + (b.bytes_recv || 0)) - ((a.bytes_sent || 0) + (a.bytes_recv || 0)))
                .slice(0, 10);

            console.log('Sorted processes for topTalkers:', sorted.map(p => ({ name: p.process_name, bytes: (p.bytes_sent || 0) + (p.bytes_recv || 0) })));

            AppState.charts.topTalkers.data.labels = sorted.map(p => p.process_name || 'Unknown');
            // Keep data in bytes, not MB
            AppState.charts.topTalkers.data.datasets[0].data = sorted.map(p => (p.bytes_sent || 0) + (p.bytes_recv || 0));

            // Generate colors based on usage
            const colors = sorted.map((item, index) => {
                const bytes = (item.bytes_sent || 0) + (item.bytes_recv || 0);
                const maxBytes = ((sorted[0].bytes_sent || 0) + (sorted[0].bytes_recv || 0));
                const ratio = maxBytes > 0 ? bytes / maxBytes : 0;

                if (ratio > 0.7) return 'rgba(239, 68, 68, 0.8)';
                if (ratio > 0.4) return 'rgba(251, 191, 36, 0.8)';
                return 'rgba(139, 92, 246, 0.8)';
            });

            AppState.charts.topTalkers.data.datasets[0].backgroundColor = colors;
            AppState.charts.topTalkers.update('none');
        } catch (error) {
            console.error('TopTalkers chart update error:', error);
        }
    } else if (AppState.charts.topTalkers) {
        // Clear chart if no process data
        console.warn('No process data available for topTalkers chart - processes:', processes);
    }
    
    // Update connections table
    if (connections && connections.length > 0) {
        renderConnectionsTable(connections);
    }
    
    // Update processes table
    if (processes && processes.length > 0) {
        renderProcessesTable(processes);
    }
}

function canCollectSpeedPoint() {
    const hasSpeedTrendDelayElapsed =
        AppState.monitoringStartedAt &&
        (Date.now() - AppState.monitoringStartedAt) >= AppState.speedTrendDelayMs;

    return AppState.isMonitoring && hasSpeedTrendDelayElapsed && !AppState.speedAxis.hasError;
}

async function refreshSpeedTrendChart() {
    if (!AppState.charts.speed || AppState.ui.speedRefreshInProgress) return;

    const refreshBtn = document.getElementById('speedRefreshBtn');
    AppState.ui.speedRefreshInProgress = true;

    if (refreshBtn) {
        refreshBtn.disabled = true;
        refreshBtn.classList.add('loading');
    }

    try {
        // Chart-only refresh: fetch latest statistics and update speed history/chart.
        const statsRes = await fetch('/api/statistics', { cache: 'no-store' });
        const statsWrapper = await statsRes.json();
        const stats = statsWrapper.statistics || statsWrapper;

        if (canCollectSpeedPoint()) {
            addSpeedHistoryPoint(stats.upload_speed || 0, stats.download_speed || 0, Date.now());
        }

        // Re-render only the speed chart using current selected range/mode.
        renderSpeedChartFromHistory('none');
    } catch (error) {
        console.error('Manual speed chart refresh failed:', error);
        showToast('Failed to refresh speed chart', 'error');
    } finally {
        AppState.ui.speedRefreshInProgress = false;
        if (refreshBtn) {
            refreshBtn.disabled = false;
            refreshBtn.classList.remove('loading');
        }
    }
}

function addSpeedHistoryPoint(upload, download, timestampMs) {
    AppState.speedHistory.push({
        ts: Number(timestampMs),
        upload: Number(upload) || 0,
        download: Number(download) || 0
    });

    const cutoff = Date.now() - (AppState.maxSpeedHistorySeconds * 1000);
    AppState.speedHistory = AppState.speedHistory.filter(p => p.ts >= cutoff);
}

function getFilteredSpeedHistory() {
    if (!AppState.speedHistory.length) return [];

    const now = Date.now();
    const rangeSeconds = AppState.timeRangeSeconds;

    if (rangeSeconds === 0) {
        const liveCutoff = now - (AppState.liveWindowSeconds * 1000);
        return AppState.speedHistory.filter(p => p.ts >= liveCutoff);
    }

    const cutoff = now - (rangeSeconds * 1000);
    return AppState.speedHistory.filter(p => p.ts >= cutoff);
}

function formatSpeedAxisLabel(timestampMs) {
    const date = new Date(timestampMs);
    const range = AppState.timeRangeSeconds;

    if (range === 0 || range <= 300) {
        return date.toLocaleTimeString('en-US', {
            hour12: false,
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
    }

    return date.toLocaleTimeString('en-US', {
        hour12: false,
        hour: '2-digit',
        minute: '2-digit'
    });
}

function resetSpeedAxisState() {
    AppState.speedAxis.currentMin = 0;
    AppState.speedAxis.currentMax = AppState.speedAxis.minLinearMax;
    AppState.speedAxis.currentMode = 'linear';
}

function renderSpeedChartFromHistory(updateMode) {
    const chart = AppState.charts.speed;
    if (!chart) return;

    const filtered = getFilteredSpeedHistory();
    chart.data.labels = filtered.map(point => formatSpeedAxisLabel(point.ts));
    chart.data.datasets[0].data = filtered.map(point => point.upload);
    chart.data.datasets[1].data = filtered.map(point => point.download);

    if (!filtered.length) {
        resetSpeedAxisState();
        const uploadAxis = chart.options?.scales?.['y-upload'];
        const downloadAxis = chart.options?.scales?.['y-download'];
        if (uploadAxis) {
            uploadAxis.min = 0;
            uploadAxis.max = AppState.speedAxis.minLinearMax;
        }
        if (downloadAxis) {
            downloadAxis.min = 0;
            downloadAxis.max = AppState.speedAxis.minLinearMax;
        }
        chart.update(updateMode || 'none');
        return;
    }

    applyDynamicSpeedAxisScaling(chart);
    chart.update(updateMode);
}

function getPercentile(sortedValues, percentile) {
    if (!sortedValues.length) return 0;
    const idx = (percentile / 100) * (sortedValues.length - 1);
    const low = Math.floor(idx);
    const high = Math.ceil(idx);
    if (low === high) return sortedValues[low];
    const weight = idx - low;
    return (sortedValues[low] * (1 - weight)) + (sortedValues[high] * weight);
}

function applyDynamicSpeedAxisScaling(chart) {
    const upload = chart.data.datasets?.[0]?.data || [];
    const download = chart.data.datasets?.[1]?.data || [];
    const values = [...upload, ...download]
        .map(v => Number(v))
        .filter(v => Number.isFinite(v) && v >= 0);

    if (!values.length) return;

    const sorted = values.slice().sort((a, b) => a - b);
    const p50 = getPercentile(sorted, 50);
    const p90 = getPercentile(sorted, 90);
    const p95 = getPercentile(sorted, 95);
    const p99 = getPercentile(sorted, 99);
    const peak = sorted[sorted.length - 1] || 0;

    // Robust top ignores isolated spikes but still reacts to sustained traffic.
    const robustTop = Math.max(p95, p90 * 1.15, p50 * 4, 1);
    let targetMax = robustTop * 1.25;

    // Cap extreme single spikes from stretching the full chart.
    const extremeCap = Math.max(p99 * 1.15, p95 * 1.5, AppState.speedAxis.minLinearMax);
    targetMax = Math.min(targetMax, extremeCap);

    targetMax = Math.max(AppState.speedAxis.minLinearMax, targetMax);
    targetMax = Math.min(AppState.speedAxis.maxLinearMax, targetMax);

    const ratio = p50 > 0 ? peak / p50 : 1;
    const canUseLogScale = sorted[0] > 0;
    // Keep linear by default for stability; log mode can still be enabled manually.
    const useLog = canUseLogScale && AppState.speedAxis.useLogScale;

    const smoothing = 0.25;
    const baselineMax = Number.isFinite(AppState.speedAxis.currentMax)
        ? AppState.speedAxis.currentMax
        : AppState.speedAxis.minLinearMax;
    const nextMax = baselineMax + (targetMax - baselineMax) * smoothing;

    AppState.speedAxis.currentMode = useLog ? 'logarithmic' : 'linear';
    AppState.speedAxis.currentMin = useLog ? Math.max(0.1, p50 / 10, 0.1) : 0;
    AppState.speedAxis.currentMax = Math.max(AppState.speedAxis.currentMin * 2, nextMax);
    if (!Number.isFinite(AppState.speedAxis.currentMax) || AppState.speedAxis.currentMax <= AppState.speedAxis.currentMin) {
        AppState.speedAxis.currentMode = 'linear';
        AppState.speedAxis.currentMin = 0;
        AppState.speedAxis.currentMax = AppState.speedAxis.minLinearMax;
    }

    ['y-upload', 'y-download'].forEach(axisId => {
        const axis = chart.options.scales[axisId];
        if (!axis) return;

        // Do not reassign complex proxied objects (ticks/type) every frame.
        // Only update numeric bounds to prevent recursive setter loops in Chart.js.
        axis.min = AppState.speedAxis.currentMin;
        axis.max = AppState.speedAxis.currentMax;
    });
}

function renderConnectionsTable(connections) {
    const tbody = document.getElementById('connectionsTableBody');
    if (!tbody) return;
    
    if (!connections || connections.length === 0) {
        tbody.innerHTML = '<tr><td colspan="9" class="text-center text-muted">No active connections found</td></tr>';
        return;
    }
    
    const rows = connections.slice(0, 100).map(conn => {
        const riskColor = {
            'LOW': '#10b981',
            'MEDIUM': '#f59e0b', 
            'HIGH': '#ef4444',
            'CRITICAL': '#dc2626'
        }[conn.risk_level] || '#6b7280';
        
        return `<tr>
            <td>${conn.process_name || 'Unknown'}</td>
            <td>${conn.remote_ip}:${conn.remote_port}</td>
            <td>${conn.country_name || conn.country || '-'}</td>
            <td>${conn.state || 'ESTABLISHED'}</td>
            <td>${conn.app_protocol || conn.protocol || 'TCP'}</td>
            <td>${conn.bytes_sent_formatted || '0 B'}</td>
            <td>${conn.bytes_recv_formatted || '0 B'}</td>
            <td><span style="color: ${riskColor};">${conn.risk_level || 'LOW'}</span></td>
            <td><button class="btn-sm" onclick="showWhoisInfo('${conn.remote_ip}')">WHOIS</button></td>
        </tr>`;
    }).join('');
    
    tbody.innerHTML = rows;
    
    // Update connections count
    const countEl = document.getElementById('connectionCount');
    if (countEl) countEl.textContent = `(${connections.length})`;
}

function renderProcessesTable(processes) {
    const tbody = document.getElementById('processesTableBody');
    if (!tbody) return;
    
    if (!processes || processes.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted">No process data available</td></tr>';
        return;
    }
    
    const rows = processes.slice(0, 50).map(proc => {
        return `<tr>
            <td>${proc.process_name || 'Unknown'}</td>
            <td>${proc.pid}</td>
            <td>${proc.process_path || 'System'}</td>
            <td>${proc.num_connections || 0}</td>
            <td>${proc.bytes_sent_formatted || '0 B'}</td>
            <td>${proc.bytes_recv_formatted || '0 B'}</td>
            <td>${proc.total_formatted || '0 B'}</td>
            <td>${proc.risk_level || 'LOW'}</td>
        </tr>`;
    }).join('');
    
    tbody.innerHTML = rows;
    
    // Update process count
    const countEl = document.getElementById('processCount');
    if (countEl) countEl.textContent = `(${processes.length})`;
}

function updateRiskLegend(riskData) {
    const legend = document.getElementById('riskLegend');
    if (!legend) return;
    
    const total = Object.values(riskData).reduce((a, b) => a + b, 0);
    if (total === 0) return;
    
    const items = [
        { label: 'Low', value: riskData.LOW || 0, color: '#10b981' },
        { label: 'Medium', value: riskData.MEDIUM || 0, color: '#f59e0b' },
        { label: 'High', value: riskData.HIGH || 0, color: '#ef4444' },
        { label: 'Critical', value: riskData.CRITICAL || 0, color: '#dc2626' }
    ];
    
    legend.innerHTML = items.map(item => {
        const pct = ((item.value / total) * 100).toFixed(0);
        return `
            <div class="legend-item">
                <div class="legend-color" style="background: ${item.color};"></div>
                <span>${item.label}: ${item.value} (${pct}%)</span>
            </div>
        `;
    }).join('');
}

function changeTimeRange(seconds) {
    const nextRange = Number(seconds);

    AppState.timeRangeSeconds = nextRange;
    AppState.liveUpdatesEnabled = (nextRange === 0);

    // Update active button
    document.querySelectorAll('.time-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.range === String(seconds));
    });

    // Force immediate reset and re-render when switching ranges.
    if (!AppState.charts.speed) return;

    // Allow speed chart updates again after user-triggered range changes.
    AppState.speedAxis.hasError = false;

    AppState.charts.speed.data.labels = [];
    AppState.charts.speed.data.datasets[0].data = [];
    AppState.charts.speed.data.datasets[1].data = [];
    resetSpeedAxisState();
    renderSpeedChartFromHistory();
}

// ==================== TOAST NOTIFICATIONS ====================
function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    if (!container) return;
    
    const toast = document.createElement('div');
    toast.className = `toast-notification ${type}`;
    
    const icons = { info: 'info-circle', success: 'check-circle', warning: 'exclamation-circle', error: 'times-circle' };
    
    toast.innerHTML = `
        <i class="fas fa-${icons[type] || 'info-circle'}"></i>
        <div>${escapeHtml(message)}</div>
    `;
    
    container.appendChild(toast);
    
    setTimeout(() => toast.remove(), 4000);
}

// ==================== UTILITY FUNCTIONS ====================
function formatSpeed(kb) {
    if (kb < 1024) return `${kb.toFixed(1)} KB/s`;
    if (kb < 1024 * 1024) return `${(kb / 1024).toFixed(2)} MB/s`;
    return `${(kb / 1024 / 1024).toFixed(2)} GB/s`;
}

function formatBytes(bytes) {
    if (bytes === 0) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    const index = Math.floor(Math.log(bytes) / Math.log(1024));
    return (bytes / Math.pow(1024, index)).toFixed(2) + ' ' + units[index];
}

function formatRuntime(seconds) {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = Math.floor(seconds % 60);
    return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}

function formatTimeAgo(date) {
    const seconds = Math.floor((new Date() - date) / 1000);
    if (seconds < 60) return 'just now';
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
    return `${Math.floor(seconds / 86400)}d ago`;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showSkeleton(elementId) {
    const el = document.getElementById(elementId);
    if (el) {
        el.innerHTML = '<span class="skeleton" style="width: 80%;"></span>';
    }
}

function hideSkeleton(elementIds) {
    // Override by dashboard update
}

// ==================== TABLE FUNCTIONS (STUBS) ====================
function sortTable(table, column) {
    console.log(`Sort ${table} by ${column}`);
}

function filterConnections() {
    const search = document.getElementById('connectionSearch')?.value || '';
    const risk = document.getElementById('riskFilter')?.value || '';
    debounce('filterConnections', () => {
        console.log(`Filter connections: search="${search}", risk="${risk}"`);
    }, 300);
}

function filterProcesses() {
    const search = document.getElementById('processSearch')?.value || '';
    debounce('filterProcesses', () => {
        console.log(`Filter processes: search="${search}"`);
    }, 300);
}

function debounce(key, fn, delay) {
    clearTimeout(AppState.debounceTimers[key]);
    AppState.debounceTimers[key] = setTimeout(fn, delay);
}

function showWhoisInfo(ip) {
    // Stub function for WHOIS modal
    addNotification('WHOIS Lookup', `Looking up information for ${ip}...`, 'info');
    console.log('WHOIS lookup for:', ip);
}

// Start the application
console.log('📡 Network Dashboard Script Loaded');
