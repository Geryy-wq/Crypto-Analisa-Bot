class CryptoDashboard {
    constructor() {
        this.currentSymbol = 'BTC/USDT';
        this.currentTimeframe = '1d';
        this.isDarkMode = true;
        this.alerts = [];
        this.isLoading = false;

        this.init();
    }

    async init() {
        this.setupEventListeners();
        await this.loadInitialData();
        this.startAutoRefresh();
    }

    setupEventListeners() {
        // Symbol selector
        document.getElementById('symbolSelect').addEventListener('change', (e) => {
            this.currentSymbol = e.target.value;
            this.loadAnalysis();
        });

        // Timeframe selector
        document.getElementById('timeframeSelect').addEventListener('change', (e) => {
            this.currentTimeframe = e.target.value;
            this.loadAnalysis();
        });

        // Refresh button
        document.getElementById('refreshBtn').addEventListener('click', () => {
            this.refreshAllData();
        });

        // Theme toggle
        document.getElementById('themeToggle').addEventListener('click', () => {
            this.toggleTheme();
        });

        // Alert form
        document.getElementById('alertForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.createAlert();
        });

        // Alert type selector
        document.getElementById('alertType').addEventListener('change', (e) => {
            this.updateAlertFields(e.target.value);
        });
    }

    async loadInitialData() {
        this.showLoading();
        try {
            await Promise.all([
                this.loadAnalysis(),
                this.loadRealtimeData(),
                this.loadUserAlerts()
            ]);
        } catch (error) {
            this.showError('Failed to load initial data');
            console.error('Initial data loading error:', error);
        } finally {
            this.hideLoading();
        }
    }

    async loadAnalysis() {
        try {
            const response = await fetch(`/api/analyze?symbol=${this.currentSymbol}&timeframe=${this.currentTimeframe}`);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);

            const data = await response.json();
            this.renderAnalysis(data);
        } catch (error) {
            console.error('Analysis loading error:', error);
            this.showError('Failed to load analysis data');
        }
    }

    async loadRealtimeData() {
        try {
            const response = await fetch(`/api/realtime/${this.currentSymbol}`);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);

            const data = await response.json();
            this.renderRealtimeData(data);
        } catch (error) {
            console.error('Realtime data loading error:', error);
            this.showError('Failed to load realtime data');
        }
    }

    async loadUserAlerts() {
        try {
            const response = await fetch('/api/alerts/user/web_user');
            if (!response.ok) throw new Error(`HTTP ${response.status}`);

            const data = await response.json();
            this.alerts = data.alerts || [];
            this.renderAlerts();
        } catch (error) {
            console.error('Alerts loading error:', error);
            this.showError('Failed to load alerts');
        }
    }

    renderAnalysis(data) {
        const container = document.getElementById('analysisData');
        const indicators = data.technical_indicators || {};
        const signals = data.signals || {};
        const fibonacci = data.fibonacci_levels || {};
        const pivot = data.pivot_points || {};
        const supportResistance = data.support_resistance || {};

        container.innerHTML = `
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
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
                            <span class="${this.getTrendColor(signals.trend_signal)}">${signals.trend_signal || 'N/A'}</span>
                        </div>
                        <div class="flex justify-between">
                            <span class="text-gray-400">RSI Signal:</span>
                            <span>${signals.rsi_signal || 'N/A'}</span>
                        </div>
                    </div>
                </div>

                <div>
                    <h3 class="text-lg font-semibold mb-3 text-purple-400">Pivot Points</h3>
                    <div class="space-y-2">
                        <div class="flex justify-between">
                            <span class="text-gray-400">Pivot:</span>
                            <span>$${this.formatNumber(pivot.pivot) || 'N/A'}</span>
                        </div>
                        <div class="flex justify-between">
                            <span class="text-gray-400">R1:</span>
                            <span class="text-red-400">$${this.formatNumber(pivot.resistance_1) || 'N/A'}</span>
                        </div>
                        <div class="flex justify-between">
                            <span class="text-gray-400">S1:</span>
                            <span class="text-green-400">$${this.formatNumber(pivot.support_1) || 'N/A'}</span>
                        </div>
                    </div>
                </div>

                <div>
                    <h3 class="text-lg font-semibold mb-3 text-orange-400">Support & Resistance</h3>
                    <div class="space-y-2">
                        ${supportResistance.nearest_resistance ? `
                        <div class="flex justify-between">
                            <span class="text-gray-400">🔴 Nearest R:</span>
                            <span class="text-red-400">$${this.formatNumber(supportResistance.nearest_resistance)}</span>
                        </div>
                        ` : ''}
                        ${supportResistance.nearest_support ? `
                        <div class="flex justify-between">
                            <span class="text-gray-400">🟢 Nearest S:</span>
                            <span class="text-green-400">$${this.formatNumber(supportResistance.nearest_support)}</span>
                        </div>
                        ` : ''}
                        ${supportResistance.current_price ? `
                        <div class="flex justify-between">
                            <span class="text-gray-400">Current:</span>
                            <span class="text-white">$${this.formatNumber(supportResistance.current_price)}</span>
                        </div>
                        ` : ''}
                    </div>
                </div>
            </div>

            <div class="mt-6 grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div>
                    <h3 class="text-lg font-semibold mb-3 text-yellow-400">Fibonacci Levels</h3>
                    <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
                        ${Object.entries(fibonacci).map(([level, price]) => `
                            <div class="text-center">
                                <div class="text-gray-400 text-sm">${level.replace('level_', '')}</div>
                                <div class="font-mono">$${this.formatNumber(price)}</div>
                            </div>
                        `).join('')}
                    </div>
                </div>

                <div>
                    <h3 class="text-lg font-semibold mb-3 text-cyan-400">Key S/R Levels</h3>
                    <div class="space-y-3">
                        ${supportResistance.resistance_levels && supportResistance.resistance_levels.length > 0 ? `
                        <div>
                            <div class="text-red-400 text-sm font-semibold mb-1">🔴 Resistance Levels:</div>
                            ${supportResistance.resistance_levels.map(level => `
                                <div class="text-red-300 text-sm">$${this.formatNumber(level)}</div>
                            `).join('')}
                        </div>
                        ` : ''}
                        
                        ${supportResistance.support_levels && supportResistance.support_levels.length > 0 ? `
                        <div>
                            <div class="text-green-400 text-sm font-semibold mb-1">🟢 Support Levels:</div>
                            ${supportResistance.support_levels.map(level => `
                                <div class="text-green-300 text-sm">$${this.formatNumber(level)}</div>
                            `).join('')}
                        </div>
                        ` : ''}
                    </div>
                </div>
            </div>
        `;
    }

    renderRealtimeData(data) {
        const container = document.getElementById('realtimeData');
        const changeClass = data.change_24h >= 0 ? 'text-green-400' : 'text-red-400';
        const changeIcon = data.change_24h >= 0 ? '↗' : '↘';

        container.innerHTML = `
            <div class="grid grid-cols-1 md:grid-cols-4 gap-6">
                <div class="text-center">
                    <div class="text-gray-400 text-sm">Current Price</div>
                    <div class="text-2xl font-bold">$${this.formatNumber(data.price, 4)}</div>
                </div>
                <div class="text-center">
                    <div class="text-gray-400 text-sm">24h Change</div>
                    <div class="text-xl font-bold ${changeClass}">
                        ${changeIcon} ${data.change_24h?.toFixed(2) || '0.00'}%
                    </div>
                </div>
                <div class="text-center">
                    <div class="text-gray-400 text-sm">24h Volume</div>
                    <div class="text-lg font-bold">$${this.formatNumber(data.volume_24h, 0)}</div>
                </div>
                <div class="text-center">
                    <div class="text-gray-400 text-sm">Spread</div>
                    <div class="text-lg font-bold">
                        ${data.bid && data.ask ? '$' + this.formatNumber(data.ask - data.bid, 4) : 'N/A'}
                    </div>
                </div>
            </div>
        `;
    }

    renderAlerts() {
        const container = document.getElementById('alertsList');

        if (!this.alerts.length) {
            container.innerHTML = '<div class="text-gray-400 text-center py-4">No alerts found</div>';
            return;
        }

        container.innerHTML = this.alerts.map(alert => `
            <div class="bg-gray-700 p-4 rounded-lg flex justify-between items-center">
                <div>
                    <div class="font-semibold">${alert.symbol}</div>
                    <div class="text-sm text-gray-400">
                        ${alert.alert_type} ${alert.condition_type} ${alert.target_price || alert.percentage_change || alert.volume_threshold}
                    </div>
                    <div class="text-xs text-gray-500">${this.formatDate(alert.created_at)}</div>
                </div>
                <div class="flex items-center space-x-2">
                    <span class="px-2 py-1 text-xs rounded ${alert.is_active ? 'bg-green-600' : 'bg-gray-600'}">
                        ${alert.is_active ? 'Active' : 'Triggered'}
                    </span>
                    <button onclick="dashboard.deleteAlert(${alert.id})" 
                            class="text-red-400 hover:text-red-300">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
        `).join('');
    }

    updateAlertFields(alertType) {
        const conditionGroup = document.getElementById('conditionGroup');
        const valueGroup = document.getElementById('valueGroup');
        const conditionSelect = document.getElementById('alertCondition');
        const valueInput = document.getElementById('alertValue');

        if (alertType === 'PRICE') {
            conditionGroup.style.display = 'block';
            conditionSelect.innerHTML = `
                <option value="ABOVE">Above</option>
                <option value="BELOW">Below</option>
            `;
            valueInput.placeholder = 'Enter target price';
        } else if (alertType === 'PERCENTAGE') {
            conditionGroup.style.display = 'block';
            conditionSelect.innerHTML = `
                <option value="GAIN">Gain</option>
                <option value="LOSS">Loss</option>
            `;
            valueInput.placeholder = 'Enter percentage (e.g., 5 for 5%)';
        } else if (alertType === 'VOLUME') {
            conditionGroup.style.display = 'none';
            valueInput.placeholder = 'Enter volume threshold';
        }
    }

    async createAlert() {
        const formData = new FormData(document.getElementById('alertForm'));
        const alertData = {
            symbol: formData.get('symbol'),
            alert_type: formData.get('alert_type'),
            condition: formData.get('condition'),
            value: parseFloat(formData.get('value')),
            user_id: 'web_user'
        };

        try {
            const response = await fetch('/api/alerts/create', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(alertData)
            });

            if (!response.ok) throw new Error('Failed to create alert');

            const result = await response.json();
            this.showSuccess('Alert created successfully!');
            document.getElementById('alertForm').reset();
            await this.loadUserAlerts();
        } catch (error) {
            console.error('Create alert error:', error);
            this.showError('Failed to create alert');
        }
    }

    async deleteAlert(alertId) {
        if (!confirm('Are you sure you want to delete this alert?')) return;

        try {
            const response = await fetch(`/api/alerts/${alertId}`, {
                method: 'DELETE',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_id: 'web_user' })
            });

            if (!response.ok) throw new Error('Failed to delete alert');

            this.showSuccess('Alert deleted successfully!');
            await this.loadUserAlerts();
        } catch (error) {
            console.error('Delete alert error:', error);
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

    getRSIColor(rsi) {
        if (!rsi) return 'text-gray-400';
        if (rsi > 70) return 'text-red-400';
        if (rsi < 30) return 'text-green-400';
        return 'text-yellow-400';
    }

    getTrendColor(trend) {
        if (!trend) return 'text-gray-400';
        if (trend.includes('Uptrend')) return 'text-green-400';
        if (trend.includes('Downtrend')) return 'text-red-400';
        return 'text-yellow-400';
    }

    showLoading() {
        this.isLoading = true;
        document.getElementById('loadingIndicator').classList.remove('hidden');
    }

    hideLoading() {
        this.isLoading = false;
        document.getElementById('loadingIndicator').classList.add('hidden');
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
        }, 5000);
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new CryptoDashboard();
});