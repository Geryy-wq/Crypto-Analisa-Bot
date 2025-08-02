
class CryptoDashboard {
    constructor() {
        this.currentSymbol = 'BTC/USDT';
        this.currentTimeframe = '1d';
        this.alertSystem = new AlertManager();
        this.isDarkMode = true;
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.loadInitialData();
        this.startAutoRefresh();
    }
    
    setupEventListeners() {
        // Symbol and timeframe selection
        document.getElementById('symbolSelect').addEventListener('change', (e) => {
            this.currentSymbol = e.target.value;
            this.loadAnalysis();
        });
        
        document.getElementById('timeframeSelect').addEventListener('change', (e) => {
            this.currentTimeframe = e.target.value;
            this.loadAnalysis();
        });
        
        // Buttons
        document.getElementById('analyzeBtn').addEventListener('click', () => {
            this.loadAnalysis();
        });
        
        document.getElementById('refreshBtn').addEventListener('click', () => {
            this.refreshAllData();
        });
        
        document.getElementById('themeToggle').addEventListener('click', () => {
            this.toggleTheme();
        });
        
        // Alert creation
        document.getElementById('createAlertBtn').addEventListener('click', () => {
            this.createAlert();
        });
        
        // Alert type changes
        document.getElementById('alertType').addEventListener('change', (e) => {
            this.updateAlertConditions(e.target.value);
        });
    }
    
    async loadInitialData() {
        this.showLoading(true);
        try {
            await Promise.all([
                this.loadRealtimeData(),
                this.loadAnalysis(),
                this.loadFibonacciLevels(),
                this.loadRecentAlerts()
            ]);
        } catch (error) {
            console.error('Error loading initial data:', error);
            this.showError('Failed to load dashboard data');
        } finally {
            this.showLoading(false);
        }
    }
    
    async loadRealtimeData() {
        try {
            const response = await fetch(`/api/realtime/${this.currentSymbol}`);
            const data = await response.json();
            
            if (response.ok) {
                this.updatePriceCards(data);
            } else {
                throw new Error(data.error);
            }
        } catch (error) {
            console.error('Error loading realtime data:', error);
        }
    }
    
    async loadAnalysis() {
        try {
            const response = await fetch(`/api/analyze?symbol=${this.currentSymbol}&timeframe=${this.currentTimeframe}`);
            const data = await response.json();
            
            if (response.ok) {
                this.updateTechnicalAnalysis(data);
                this.updatePriceCards(data);
            } else {
                throw new Error(data.error);
            }
        } catch (error) {
            console.error('Error loading analysis:', error);
            this.showError('Failed to load technical analysis');
        }
    }
    
    async loadFibonacciLevels() {
        try {
            const response = await fetch(`/api/fibonacci/${this.currentSymbol}`);
            const data = await response.json();
            
            if (response.ok) {
                this.updateFibonacciLevels(data);
            } else {
                throw new Error(data.error);
            }
        } catch (error) {
            console.error('Error loading Fibonacci levels:', error);
        }
    }
    
    async loadRecentAlerts() {
        try {
            const response = await fetch(`/api/alerts/${this.currentSymbol}`);
            const data = await response.json();
            
            if (response.ok) {
                this.updateRecentAlerts(data.alerts);
            } else {
                throw new Error(data.error);
            }
        } catch (error) {
            console.error('Error loading recent alerts:', error);
        }
    }
    
    updatePriceCards(data) {
        // Current price
        const price = data.close_price || data.price || 0;
        document.getElementById('currentPrice').textContent = `$${this.formatNumber(price)}`;
        
        // 24h change
        const change = data.change_24h || 0;
        const changeElement = document.getElementById('priceChange');
        changeElement.textContent = `${change >= 0 ? '+' : ''}${change.toFixed(2)}%`;
        changeElement.className = `text-2xl font-bold ${change >= 0 ? 'text-green-400' : 'text-red-400'}`;
        
        // Volume
        const volume = data.volume_24h || 0;
        document.getElementById('volume24h').textContent = `$${this.formatNumber(volume)}`;
        
        // RSI
        const rsi = data.technical_indicators?.rsi || 0;
        const rsiElement = document.getElementById('rsiValue');
        rsiElement.textContent = rsi.toFixed(1);
        rsiElement.className = `text-2xl font-bold ${
            rsi > 70 ? 'text-red-400' : rsi < 30 ? 'text-green-400' : 'text-white'
        }`;
    }
    
    updateTechnicalAnalysis(data) {
        const container = document.getElementById('technicalAnalysis');
        const indicators = data.technical_indicators || {};
        const signals = data.signals || {};
        
        const volumeAnalysis = data.market_sentiment?.volume_analysis || {};
        const onchainData = data.onchain_data || {};
        const fearGreed = data.market_sentiment?.fear_and_greed || {};
        
        container.innerHTML = `
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                <div>
                    <h3 class="text-lg font-semibold mb-3 text-blue-400">Technical Indicators</h3>
                    <div class="space-y-2">
                        <div class="flex justify-between">
                            <span class="text-gray-400">RSI (14):</span>
                            <span class="${this.getRSIColor(indicators.rsi)}">${indicators.rsi?.toFixed(2) || 'N/A'}</span>
                        </div>
                        <div class="flex justify-between">
                            <span class="text-gray-400">MACD:</span>
                            <span>${indicators.macd_line?.toFixed(4) || 'N/A'}</span>
                        </div>
                        <div class="flex justify-between">
                            <span class="text-gray-400">SMA 50:</span>
                            <span>$${this.formatNumber(indicators.sma50) || 'N/A'}</span>
                        </div>
                        <div class="flex justify-between">
                            <span class="text-gray-400">SMA 200:</span>
                            <span>$${this.formatNumber(indicators.sma200) || 'N/A'}</span>
                        </div>
                    </div>
                </div>
                
                <div>
                    <h3 class="text-lg font-semibold mb-3 text-green-400">Trading Signals</h3>
                    <div class="space-y-2">
                        <div class="flex justify-between">
                            <span class="text-gray-400">Trend:</span>
                            <span class="${this.getSignalColor(signals.trend_signal)}">${signals.trend_signal || 'N/A'}</span>
                        </div>
                        <div class="flex justify-between">
                            <span class="text-gray-400">RSI Signal:</span>
                            <span class="${this.getSignalColor(signals.rsi_signal)}">${signals.rsi_signal || 'N/A'}</span>
                        </div>
                        <div class="flex justify-between">
                            <span class="text-gray-400">Fear & Greed:</span>
                            <span class="text-yellow-400">${fearGreed.value || 'N/A'} (${fearGreed.classification || 'N/A'})</span>
                        </div>
                    </div>
                    
                    ${signals.candlestick_patterns && signals.candlestick_patterns.length > 0 ? `
                        <h4 class="text-md font-semibold mt-4 mb-2 text-yellow-400">Candlestick Patterns</h4>
                        <div class="space-y-1">
                            ${signals.candlestick_patterns.slice(0, 3).map(pattern => 
                                `<div class="text-sm text-gray-300">• ${pattern}</div>`
                            ).join('')}
                        </div>
                    ` : ''}
                </div>
                
                <div>
                    <h3 class="text-lg font-semibold mb-3 text-purple-400">Market Data</h3>
                    <div class="space-y-2">
                        <div class="flex justify-between">
                            <span class="text-gray-400">Volume Status:</span>
                            <span class="text-white">${volumeAnalysis.volume_status || 'N/A'}</span>
                        </div>
                        <div class="flex justify-between">
                            <span class="text-gray-400">Volume Ratio:</span>
                            <span class="text-white">${volumeAnalysis.volume_ratio ? volumeAnalysis.volume_ratio + 'x' : 'N/A'}</span>
                        </div>
                        ${this.formatOnChainData(onchainData, this.currentSymbol)}
                    </div>
                </div>
            </div>
        `;
    }
    
    updateFibonacciLevels(data) {
        const container = document.getElementById('fibonacciLevels');
        const levels = data.fibonacci_levels || {};
        
        container.innerHTML = Object.entries(levels).map(([level, price]) => `
            <div class="bg-gray-700 rounded-lg p-4 text-center ${
                level === data.nearest_level ? 'border-2 border-yellow-400' : ''
            }">
                <div class="text-sm text-gray-400">${level.replace('level_', '').replace('_', '.')}</div>
                <div class="text-lg font-semibold">${this.formatNumber(price, 4)}</div>
                ${level === data.nearest_level ? '<div class="text-xs text-yellow-400 mt-1">NEAREST</div>' : ''}
            </div>
        `).join('');
    }
    
    updateRecentAlerts(alerts) {
        const container = document.getElementById('recentAlerts');
        
        if (!alerts || alerts.length === 0) {
            container.innerHTML = '<p class="text-gray-400 text-sm">No recent alerts</p>';
            return;
        }
        
        container.innerHTML = alerts.slice(0, 5).map(alert => `
            <div class="bg-gray-700 rounded-lg p-3">
                <div class="flex items-center justify-between">
                    <span class="text-sm">${alert.message}</span>
                    <span class="text-xs text-gray-400">${this.formatDate(alert.timestamp)}</span>
                </div>
            </div>
        `).join('');
    }
    
    async createAlert() {
        const alertType = document.getElementById('alertType').value;
        const condition = document.getElementById('alertCondition').value;
        const value = parseFloat(document.getElementById('alertValue').value);
        
        if (!value) {
            this.showError('Please enter a valid value');
            return;
        }
        
        try {
            const response = await fetch('/api/alerts/create', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    symbol: this.currentSymbol,
                    alert_type: alertType,
                    condition: condition,
                    value: value,
                    user_id: 'web_user'
                })
            });
            
            const result = await response.json();
            
            if (response.ok) {
                this.showSuccess('Alert created successfully!');
                document.getElementById('alertValue').value = '';
                this.loadActiveAlerts();
            } else {
                throw new Error(result.error);
            }
        } catch (error) {
            console.error('Error creating alert:', error);
            this.showError('Failed to create alert');
        }
    }
    
    async loadActiveAlerts() {
        try {
            const response = await fetch('/api/alerts/user/web_user');
            const data = await response.json();
            
            if (response.ok) {
                this.updateActiveAlerts(data.alerts);
            }
        } catch (error) {
            console.error('Error loading active alerts:', error);
        }
    }
    
    updateActiveAlerts(alerts) {
        const container = document.getElementById('activeAlerts');
        
        if (!alerts || alerts.length === 0) {
            container.innerHTML = '<p class="text-gray-400 text-sm">No active alerts</p>';
            return;
        }
        
        container.innerHTML = alerts.filter(alert => alert.is_active).map(alert => `
            <div class="flex items-center justify-between bg-gray-700 rounded p-2">
                <div class="flex-1">
                    <div class="text-sm">${alert.symbol}</div>
                    <div class="text-xs text-gray-400">${alert.condition_type} $${alert.target_price}</div>
                </div>
                <button onclick="dashboard.deleteAlert(${alert.id})" class="text-red-400 hover:text-red-300">
                    <i class="fas fa-trash text-sm"></i>
                </button>
            </div>
        `).join('');
    }
    
    updateAlertConditions(alertType) {
        const conditionSelect = document.getElementById('alertCondition');
        
        if (alertType === 'PERCENTAGE') {
            conditionSelect.innerHTML = `
                <option value="GAIN">Gain</option>
                <option value="LOSS">Loss</option>
            `;
        } else if (alertType === 'VOLUME') {
            conditionSelect.innerHTML = `
                <option value="SPIKE">Spike Above</option>
            `;
        } else {
            conditionSelect.innerHTML = `
                <option value="ABOVE">Above</option>
                <option value="BELOW">Below</option>
            `;
        }
    }
    
    async deleteAlert(alertId) {
        try {
            const response = await fetch(`/api/alerts/${alertId}`, {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ user_id: 'web_user' })
            });
            
            if (response.ok) {
                this.showSuccess('Alert deleted');
                this.loadActiveAlerts();
            } else {
                throw new Error('Failed to delete alert');
            }
        } catch (error) {
            console.error('Error deleting alert:', error);
            this.showError('Failed to delete alert');
        }
    }
    
    startAutoRefresh() {
        // Refresh realtime data every 30 seconds
        setInterval(() => {
            this.loadRealtimeData();
        }, 30000);
        
        // Refresh analysis every 5 minutes
        setInterval(() => {
            this.loadAnalysis();
        }, 300000);
    }
    
    async refreshAllData() {
        const btn = document.getElementById('refreshBtn');
        const icon = btn.querySelector('i');
        
        icon.classList.add('fa-spin');
        
        try {
            await this.loadInitialData();
            this.showSuccess('Data refreshed successfully!');
        } catch (error) {
            this.showError('Failed to refresh data');
        } finally {
            icon.classList.remove('fa-spin');
        }
    }
    
    toggleTheme() {
        this.isDarkMode = !this.isDarkMode;
        const icon = document.querySelector('#themeToggle i');
        
        if (this.isDarkMode) {
            icon.className = 'fas fa-sun';
            document.body.className = 'bg-gray-900 text-white min-h-screen';
        } else {
            icon.className = 'fas fa-moon';
            document.body.className = 'bg-white text-gray-900 min-h-screen';
        }
    }
    
    // Utility functions
    formatNumber(num, decimals = 2) {
        if (!num) return '0';
        return parseFloat(num).toLocaleString('en-US', {
            minimumFractionDigits: decimals,
            maximumFractionDigits: decimals
        });
    }
    
    formatDate(dateString) {
        return new Date(dateString).toLocaleString('en-US', {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    }
    
    formatOnChainData(onchainData, symbol) {
        if (!onchainData || onchainData.error) {
            return '<div class="text-sm text-gray-500">On-chain data not available</div>';
        }
        
        let html = '';
        
        if (symbol.includes('BTC')) {
            html += `
                <div class="flex justify-between">
                    <span class="text-gray-400">Hash Rate:</span>
                    <span class="text-white">${this.formatNumber(onchainData.network_hash_rate || 0, 0)}</span>
                </div>
                <div class="flex justify-between">
                    <span class="text-gray-400">Mempool:</span>
                    <span class="text-white">${onchainData.mempool_transactions || 0} txs</span>
                </div>
            `;
        } else if (symbol.includes('ETH')) {
            html += `
                <div class="flex justify-between">
                    <span class="text-gray-400">Gas (Fast):</span>
                    <span class="text-white">${onchainData.fast_gas_price || 0} gwei</span>
                </div>
                <div class="flex justify-between">
                    <span class="text-gray-400">Total Nodes:</span>
                    <span class="text-white">${this.formatNumber(onchainData.total_nodes || 0, 0)}</span>
                </div>
            `;
        } else {
            html += `
                <div class="flex justify-between">
                    <span class="text-gray-400">Market Cap:</span>
                    <span class="text-white">$${this.formatNumber(onchainData.market_cap || 0, 0)}</span>
                </div>
            `;
        }
        
        return html;
    }
    
    getRSIColor(rsi) {
        if (!rsi) return 'text-gray-400';
        if (rsi > 70) return 'text-red-400';
        if (rsi < 30) return 'text-green-400';
        return 'text-yellow-400';
    }
    
    getSignalColor(signal) {
        if (!signal) return 'text-gray-400';
        if (signal.includes('Bullish') || signal.includes('Uptrend') || signal.includes('Oversold')) {
            return 'text-green-400';
        }
        if (signal.includes('Bearish') || signal.includes('Downtrend') || signal.includes('Overbought')) {
            return 'text-red-400';
        }
        return 'text-yellow-400';
    }
    
    showLoading(show) {
        const overlay = document.getElementById('loadingOverlay');
        overlay.style.display = show ? 'flex' : 'none';
    }
    
    showSuccess(message) {
        this.showNotification(message, 'success');
    }
    
    showError(message) {
        this.showNotification(message, 'error');
    }
    
    showNotification(message, type) {
        const notification = document.createElement('div');
        notification.className = `fixed top-4 right-4 p-4 rounded-lg z-50 ${
            type === 'success' ? 'bg-green-600' : 'bg-red-600'
        } text-white`;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.remove();
        }, 3000);
    }
}

class AlertManager {
    constructor() {
        this.alerts = [];
    }
    
    add(alert) {
        this.alerts.push(alert);
    }
    
    remove(id) {
        this.alerts = this.alerts.filter(alert => alert.id !== id);
    }
    
    getActive() {
        return this.alerts.filter(alert => alert.active);
    }
}

// Initialize dashboard when page loads
const dashboard = new CryptoDashboard();
