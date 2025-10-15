// MCX Live Trading Dashboard JavaScript
class TradingDashboard {
    constructor() {
        this.currentCommodity = 'GOLD';
        this.currentTimeframe = '1h';
        this.currentDateRange = '1d';
        this.priceChart = null;
        this.candlestickChart = null;
        this.updateInterval = null;
        this.marketDataInterval = null;
        this.showTrendLines = true;
        this.showSupportResistance = true;
        
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.startDataUpdates();
        this.updatePositionCalculator();
        this.loadInitialData();
        this.initializeTooltips();
    }
    
    initializeTooltips() {
        // Initialize Bootstrap tooltips
        var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }

    setupEventListeners() {
        // Position calculator inputs
        document.getElementById('quantity-input').addEventListener('input', () => {
            this.updatePositionCalculator();
        });
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (event) => {
            // Ctrl/Cmd + R for force refresh
            if ((event.ctrlKey || event.metaKey) && event.key === 'r') {
                event.preventDefault(); // Prevent browser refresh
                this.forceRefreshData();
            }
            
            // F5 for force refresh
            if (event.key === 'F5') {
                event.preventDefault(); // Prevent browser refresh
                this.forceRefreshData();
            }
        });
    }

    startDataUpdates() {
        // Update data immediately
        this.updateAllData();
        
        // Set up interval for regular updates (every 2 minutes)
        this.updateInterval = setInterval(() => {
            this.updateAllData();
        }, 120000); // 2 minutes

        // Update market status every 30 seconds
        this.marketDataInterval = setInterval(() => {
            this.updateMarketStatus();
        }, 30000); // 30 seconds
    }

    async updateAllData(forceRefresh = false) {
        try {
            if (forceRefresh) {
                console.log('Force refreshing all data...');
            }
            
            await Promise.all([
                this.updateMarketData(forceRefresh),
                this.updateTradingSignals(),
                this.updatePerformance(),
                this.updatePriceChart(),
                this.updateCandlestickChart(),
                this.updateMarketAnalysis()
            ]);
            
            this.updateLastUpdateTime();
        } catch (error) {
            console.error('Error updating data:', error);
            this.showError('Failed to update data. Please refresh the page.');
        }
    }

    async updateMarketData(forceRefresh = false) {
        try {
            const url = forceRefresh ? 
                `/api/market-data/${this.currentCommodity}?force=${Date.now()}` : 
                `/api/market-data/${this.currentCommodity}`;
                
            const response = await fetch(url);
            if (!response.ok) throw new Error('Failed to fetch market data');
            
            const data = await response.json();
            this.displayMarketData(data);
            
        } catch (error) {
            console.error('Error fetching market data:', error);
        }
    }

    displayMarketData(data) {
        const livePrice = data.live_price;
        
        // Update price display
        document.getElementById('current-price').textContent = `₹${livePrice.close.toLocaleString('en-IN')}`;
        
        // Update price change
        const changeElement = document.getElementById('price-change');
        const changeAmount = document.getElementById('change-amount');
        const changePercent = document.getElementById('change-percent');
        
        changeAmount.textContent = `₹${livePrice.change.toLocaleString('en-IN')}`;
        changePercent.textContent = `(${livePrice.change_pct.toFixed(2)}%)`;
        
        // Set color based on change
        if (livePrice.change > 0) {
            changeElement.className = 'mt-2 change-positive';
        } else if (livePrice.change < 0) {
            changeElement.className = 'mt-2 change-negative';
        } else {
            changeElement.className = 'mt-2';
        }
        
        // Update futures information
        document.getElementById('futures-name').textContent = livePrice.name;
        document.getElementById('futures-symbol').textContent = livePrice.symbol;
        document.getElementById('contract-size').textContent = livePrice.contract_size;
        document.getElementById('expiry').textContent = livePrice.expiry;
        
        // Update other market data
        document.getElementById('lot-size').textContent = livePrice.lot_size.toLocaleString('en-IN');
        document.getElementById('unit').textContent = 'grams';
        document.getElementById('volume').textContent = livePrice.volume.toLocaleString('en-IN');
        
        // Update position calculator with contract details
        document.getElementById('price-input').value = livePrice.close;
        document.getElementById('lot-size-display').textContent = livePrice.lot_size + ' grams';
        document.getElementById('contract-size-display').textContent = livePrice.contract_size;
        document.getElementById('expiry-display').textContent = livePrice.expiry;
        document.getElementById('margin-percent').textContent = (livePrice.margin * 100).toFixed(1) + '%';
        
        this.updatePositionCalculator();
    }

    async updateTradingSignals() {
        try {
            const response = await fetch(`/api/signals/${this.currentCommodity}/${this.currentTimeframe}`);
            if (!response.ok) throw new Error('Failed to fetch trading signals');
            
            const data = await response.json();
            this.displayTradingSignals(data);
            this.displayMarketAnalysis(data.market_analysis);
            
        } catch (error) {
            console.error('Error fetching trading signals:', error);
        }
    }

    displayTradingSignals(data) {
        const container = document.getElementById('current-signals-container');
        
        if (data.signals.length === 0) {
            container.innerHTML = `
                <div class="alert alert-info alert-custom">
                    <i class="fas fa-info-circle me-2"></i>
                    No trading signals found above confidence threshold.
                </div>
            `;
            return;
        }
        
        let signalsHtml = '';
        
        data.signals.forEach((signal, index) => {
            const confidenceClass = this.getConfidenceClass(signal.confidence);
            
            signalsHtml += `
                <div class="signal-card ${confidenceClass}">
                    <div class="card">
                        <div class="card-body">
                            <div class="row align-items-center">
                                <div class="col-md-4">
                                    <h6 class="mb-1">${signal.strategy_name}</h6>
                                    <small class="text-muted">Pattern: ${signal.pattern}</small>
                                </div>
                                <div class="col-md-2 text-center">
                                    <span class="confidence-badge ${confidenceClass}">
                                        ${(signal.confidence * 100).toFixed(1)}%
                                    </span>
                                    <br>
                                    <small class="text-muted">${signal.confidence_level}</small>
                                </div>
                                <div class="col-md-2 text-center">
                                    <span class="badge bg-${signal.risk_level === 'LOW RISK' ? 'success' : signal.risk_level === 'MODERATE RISK' ? 'warning' : 'danger'}">
                                        ${signal.risk_level}
                                    </span>
                                </div>
                                <div class="col-md-4">
                                    <p class="mb-1">${signal.recommendation}</p>
                                    <div class="row">
                                        <div class="col-6">
                                            <small class="text-muted">Historical: ${(signal.breakdown.historical * 100).toFixed(1)}%</small><br>
                                            <small class="text-muted">Market: ${(signal.breakdown.market_conditions * 100).toFixed(1)}%</small>
                                        </div>
                                        <div class="col-6">
                                            <small class="text-muted">Pattern: ${(signal.breakdown.pattern_strength * 100).toFixed(1)}%</small><br>
                                            <small class="text-muted">Risk: ${(signal.breakdown.risk_conditions * 100).toFixed(1)}%</small>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        });
        
        // Add recommendation summary
        const recommendationHtml = `
            <div class="alert alert-${data.recommendation.action === 'ENTER' ? 'success' : 'info'} alert-custom">
                <h6><i class="fas fa-lightbulb me-2"></i>Trading Recommendation</h6>
                <strong>Action:</strong> ${data.recommendation.action}<br>
                <strong>Reason:</strong> ${data.recommendation.reason}<br>
                <strong>Position Sizing:</strong> ${data.recommendation.position_sizing}
            </div>
        `;
        
        container.innerHTML = recommendationHtml + signalsHtml;
    }

    displayMarketAnalysis(analysis) {
        document.getElementById('market-regime').textContent = analysis.regime;
        document.getElementById('trend-strength').textContent = analysis.trend_strength;
        document.getElementById('volatility').textContent = analysis.volatility;
        document.getElementById('volume-level').textContent = analysis.volume_level;
        
        document.getElementById('rsi-value').textContent = analysis.rsi.toFixed(1);
        document.getElementById('adx-value').textContent = analysis.adx.toFixed(1);
        document.getElementById('atr-value').textContent = analysis.atr_pct.toFixed(2) + '%';
        
        // Update enhanced market analysis
        document.getElementById('support-level').textContent = '₹' + (analysis.support || 0).toLocaleString('en-IN');
        document.getElementById('resistance-level').textContent = '₹' + (analysis.resistance || 0).toLocaleString('en-IN');
        
        // Update market sentiment
        document.getElementById('bullish-percent').textContent = (analysis.bullish_percent || 50) + '%';
        document.getElementById('neutral-percent').textContent = (analysis.neutral_percent || 30) + '%';
        document.getElementById('bearish-percent').textContent = (analysis.bearish_percent || 20) + '%';
    }
    
    async updateMarketAnalysis() {
        try {
            // This would fetch enhanced market analysis data
            // For now, we'll use simulated data
            const analysis = {
                regime: 'BULLISH',
                trend_strength: 'STRONG',
                volatility: 'HIGH',
                volume_level: 'ABOVE_AVERAGE',
                rsi: 65.5,
                adx: 28.3,
                atr_pct: 1.8,
                support: 118500,
                resistance: 121200,
                bullish_percent: 65,
                neutral_percent: 25,
                bearish_percent: 10
            };
            
            this.displayMarketAnalysis(analysis);
        } catch (error) {
            console.error('Error updating market analysis:', error);
        }
    }
    
    async updateCandlestickChart() {
        try {
            const response = await fetch(`/api/chart-data/${this.currentCommodity}/${this.currentTimeframe}`);
            if (!response.ok) throw new Error('Failed to fetch candlestick data');
            
            const data = await response.json();
            this.renderCandlestickChart(data);
            
        } catch (error) {
            console.error('Error updating candlestick chart:', error);
        }
    }
    
    renderCandlestickChart(data) {
        const ctx = document.getElementById('candlestick-chart').getContext('2d');
        
        // Destroy existing chart
        if (this.candlestickChart) {
            this.candlestickChart.destroy();
        }
        
        // Prepare candlestick data
        const ohlcData = data.ohlc || [];
        
        // Create candlestick-like data using bar chart
        const datasets = [{
            label: 'OHLC',
            data: ohlcData.map(item => ({
                x: new Date(item.timestamp),
                o: item.open,
                h: item.high,
                l: item.low,
                c: item.close
            })),
            backgroundColor: ohlcData.map(item => 
                item.close >= item.open ? 'rgba(46, 204, 113, 0.8)' : 'rgba(231, 76, 60, 0.8)'
            ),
            borderColor: ohlcData.map(item => 
                item.close >= item.open ? '#27ae60' : '#e74c3c'
            ),
            borderWidth: 1
        }];
        
        this.candlestickChart = new Chart(ctx, {
            type: 'bar',
            data: {
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    x: {
                        type: 'time',
                        time: {
                            unit: this.currentTimeframe === '1h' ? 'hour' : 'day'
                        },
                        title: {
                            display: true,
                            text: 'Time'
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: 'Price (₹)'
                        },
                        ticks: {
                            callback: function(value) {
                                return '₹' + value.toLocaleString('en-IN');
                            }
                        }
                    }
                }
            }
        });
    }

    async updatePerformance() {
        try {
            const response = await fetch(`/api/performance/${this.currentCommodity}`);
            if (!response.ok) throw new Error('Failed to fetch performance data');
            
            const data = await response.json();
            this.displayPerformance(data);
            
        } catch (error) {
            console.error('Error fetching performance:', error);
        }
    }

    displayPerformance(data) {
        // Use current timeframe data or combine if available
        const timeframeData = data[this.currentTimeframe] || Object.values(data)[0] || {};
        
        document.getElementById('total-trades').textContent = timeframeData.total_trades || 0;
        document.getElementById('win-rate').textContent = (timeframeData.win_rate || 0).toFixed(1) + '%';
        document.getElementById('total-pnl').textContent = `₹${(timeframeData.total_pnl || 0).toLocaleString('en-IN')}`;
    }

    async updatePriceChart() {
        try {
            const response = await fetch(`/api/chart-data/${this.currentCommodity}/${this.currentTimeframe}`);
            if (!response.ok) throw new Error('Failed to fetch chart data');
            
            const data = await response.json();
            this.renderPriceChart(data);
            
        } catch (error) {
            console.error('Error updating chart:', error);
        }
    }

    renderPriceChart(data) {
        const ctx = document.getElementById('price-chart').getContext('2d');
        
        // Destroy existing chart
        if (this.priceChart) {
            this.priceChart.destroy();
        }
        
        // Prepare chart data
        const ohlcData = data.ohlc || [];
        const labels = ohlcData.map(item => new Date(item.timestamp).toLocaleTimeString());
        const prices = ohlcData.map(item => item.close);
        
        this.priceChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: `${this.currentCommodity} Price (₹)`,
                    data: prices,
                    borderColor: '#3498db',
                    backgroundColor: 'rgba(52, 152, 219, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true,
                        position: 'top'
                    }
                },
                scales: {
                    x: {
                        display: true,
                        title: {
                            display: true,
                            text: 'Time'
                        }
                    },
                    y: {
                        display: true,
                        title: {
                            display: true,
                            text: 'Price (₹)'
                        },
                        ticks: {
                            callback: function(value) {
                                return '₹' + value.toLocaleString('en-IN');
                            }
                        }
                    }
                },
                interaction: {
                    intersect: false,
                    mode: 'index'
                }
            }
        });
    }

    updatePositionCalculator() {
        const quantity = parseInt(document.getElementById('quantity-input').value) || 1;
        const price = parseFloat(document.getElementById('price-input').value) || 0;
        const lotSize = parseInt(document.getElementById('lot-size-display').textContent) || 100;
        const marginPercent = parseFloat(document.getElementById('margin-percent').textContent) || 5.0;
        
        if (price > 0) {
            // Calculate position value using lot size
            const totalQuantity = quantity * lotSize; // Total grams
            const positionValue = (price / 10) * totalQuantity; // Price per 10 grams * total grams / 10
            const marginRequired = positionValue * (marginPercent / 100);
            
            document.getElementById('position-value').textContent = `₹${positionValue.toLocaleString('en-IN')}`;
            document.getElementById('margin-required').textContent = `₹${marginRequired.toLocaleString('en-IN')}`;
            
            // Also try API calculation as fallback
            fetch('/api/position-calculator', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    commodity: this.currentCommodity,
                    quantity: quantity,
                    price: price,
                    lot_size: lotSize,
                    margin_percent: marginPercent
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    console.error('Position calculation error:', data.error);
                    return;
                }
                
                // Update with API results if available
                if (data.position_value) {
                    document.getElementById('position-value').textContent = `₹${data.position_value.toLocaleString('en-IN')}`;
                }
                if (data.margin_required) {
                    document.getElementById('margin-required').textContent = `₹${data.margin_required.toLocaleString('en-IN')}`;
                }
            })
            .catch(error => {
                console.error('Error calculating position:', error);
            });
        }
    }

    async updateMarketStatus() {
        try {
            const response = await fetch('/api/market-status');
            if (!response.ok) throw new Error('Failed to fetch market status');
            
            const data = await response.json();
            
            const indicator = document.getElementById('market-indicator');
            if (data.market_open) {
                indicator.textContent = 'MARKET OPEN';
                indicator.className = 'badge bg-success';
            } else {
                indicator.textContent = 'MARKET CLOSED';
                indicator.className = 'badge bg-danger';
            }
            
        } catch (error) {
            console.error('Error fetching market status:', error);
        }
    }

    updateLastUpdateTime() {
        const now = new Date();
        document.getElementById('last-update').textContent = now.toLocaleTimeString();
        
        // Calculate next update time
        const nextUpdate = new Date(now.getTime() + 120000); // 2 minutes from now
        document.getElementById('next-update').textContent = nextUpdate.toLocaleTimeString();
    }
    
    async forceRefreshData() {
        const refreshBtn = document.getElementById('refresh-btn');
        const refreshIcon = document.getElementById('refresh-icon');
        const refreshText = document.getElementById('refresh-text');
        
        // Disable button and show loading state
        refreshBtn.disabled = true;
        refreshIcon.classList.add('spinning');
        refreshText.textContent = 'Refreshing...';
        
        try {
            console.log('Force refreshing dashboard data...');
            
            // Force refresh all data
            await this.updateAllData(true);
            
            // Show success feedback
            refreshText.textContent = 'Refreshed!';
            refreshIcon.classList.remove('spinning');
            refreshIcon.classList.add('fa-check');
            
            // Reset button after 2 seconds
            setTimeout(() => {
                refreshBtn.disabled = false;
                refreshIcon.classList.remove('fa-check');
                refreshText.textContent = 'Refresh';
            }, 2000);
            
        } catch (error) {
            console.error('Error during force refresh:', error);
            
            // Show error feedback
            refreshText.textContent = 'Error!';
            refreshIcon.classList.remove('spinning');
            refreshIcon.classList.add('fa-exclamation-triangle');
            
            // Reset button after 3 seconds
            setTimeout(() => {
                refreshBtn.disabled = false;
                refreshIcon.classList.remove('fa-exclamation-triangle');
                refreshIcon.classList.add('fa-sync-alt');
                refreshText.textContent = 'Refresh';
            }, 3000);
        }
    }

    getConfidenceClass(confidence) {
        if (confidence >= 0.8) return 'confidence-very-high';
        if (confidence >= 0.7) return 'confidence-high';
        if (confidence >= 0.6) return 'confidence-medium';
        if (confidence >= 0.5) return 'confidence-low';
        return 'confidence-very-low';
    }

    showError(message) {
        const container = document.getElementById('current-signals-container');
        container.innerHTML = `
            <div class="alert alert-danger alert-custom">
                <i class="fas fa-exclamation-triangle me-2"></i>
                ${message}
            </div>
        `;
    }
    
    async updatePastSignals() {
        try {
            const container = document.getElementById('past-signals-container');
            
            // Show loading state
            container.innerHTML = `
                <div class="loading">
                    <div class="spinner"></div>
                    <p>Loading past trading signals...</p>
                </div>
            `;
            
            // Fetch past signals data
            const response = await fetch(`/api/past-signals/${this.currentCommodity}/${this.currentTimeframe}`);
            if (!response.ok) throw new Error('Failed to fetch past signals');
            
            const data = await response.json();
            this.displayPastSignals(data);
            
        } catch (error) {
            console.error('Error updating past signals:', error);
            const container = document.getElementById('past-signals-container');
            container.innerHTML = `
                <div class="alert alert-danger alert-custom">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    Error loading past signals: ${error.message}
                </div>
            `;
        }
    }
    
    displayPastSignals(data) {
        const container = document.getElementById('past-signals-container');
        const signals = data.signals || [];
        const summary = data.summary || {};
        
        if (signals.length === 0) {
            container.innerHTML = `
                <div class="alert alert-info alert-custom">
                    <i class="fas fa-info-circle me-2"></i>
                    No past signals found for the selected timeframe.
                </div>
            `;
            return;
        }
        
        // Create summary section
        const summaryHtml = `
            <div class="past-signals-summary mb-3">
                <div class="row">
                    <div class="col-md-3">
                        <div class="stat-card">
                            <div class="stat-number">${summary.total_signals || 0}</div>
                            <div class="stat-label">Total Signals</div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="stat-card">
                            <div class="stat-number text-success">${summary.winning_signals || 0}</div>
                            <div class="stat-label">Wins</div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="stat-card">
                            <div class="stat-number text-danger">${summary.losing_signals || 0}</div>
                            <div class="stat-label">Losses</div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="stat-card">
                            <div class="stat-number ${summary.total_pnl >= 0 ? 'text-success' : 'text-danger'}">
                                ₹${(summary.total_pnl || 0).toLocaleString('en-IN')}
                            </div>
                            <div class="stat-label">Total PnL</div>
                        </div>
                    </div>
                </div>
                <div class="row mt-2">
                    <div class="col-12 text-center">
                        <span class="badge ${summary.win_rate >= 50 ? 'bg-success' : 'bg-warning'} fs-6">
                            Win Rate: ${(summary.win_rate || 0).toFixed(1)}%
                        </span>
                    </div>
                </div>
            </div>
        `;
        
        // Create signals table
        const signalsHtml = signals.slice(0, 20).map(signal => {
            const outcomeClass = signal.outcome === 'WIN' ? 'text-success' : 
                               signal.outcome === 'LOSS' ? 'text-danger' : 'text-warning';
            const pnlClass = signal.pnl >= 0 ? 'text-success' : 'text-danger';
            
            return `
                <tr>
                    <td>
                        <small class="text-muted">${signal.timestamp}</small>
                    </td>
                    <td>
                        <strong>${signal.strategy_name}</strong>
                        <br><small class="text-muted">${signal.pattern}</small>
                    </td>
                    <td class="text-center">
                        <span class="badge ${signal.outcome === 'WIN' ? 'bg-success' : 
                                         signal.outcome === 'LOSS' ? 'bg-danger' : 'bg-warning'}">
                            ${signal.outcome}
                        </span>
                    </td>
                    <td class="text-end">
                        <strong>₹${signal.entry_price.toLocaleString('en-IN')}</strong>
                        <br><small class="text-muted">→ ₹${signal.exit_price.toLocaleString('en-IN')}</small>
                    </td>
                    <td class="text-end ${pnlClass}">
                        <strong>₹${signal.pnl.toLocaleString('en-IN')}</strong>
                        <br><small>(${signal.pnl_percent.toFixed(2)}%)</small>
                    </td>
                    <td class="text-center">
                        <small class="text-muted">${signal.hold_bars} bars</small>
                        <br><small class="text-muted">${signal.exit_reason}</small>
                    </td>
                    <td class="text-center">
                        <span class="badge ${signal.confidence >= 0.7 ? 'bg-success' : 
                                         signal.confidence >= 0.5 ? 'bg-warning' : 'bg-danger'}">
                            ${(signal.confidence * 100).toFixed(0)}%
                        </span>
                    </td>
                </tr>
            `;
        }).join('');
        
        container.innerHTML = `
            ${summaryHtml}
            <div class="table-responsive">
                <table class="table table-striped table-hover">
                    <thead class="table-dark">
                        <tr>
                            <th>Date/Time</th>
                            <th>Strategy</th>
                            <th class="text-center">Outcome</th>
                            <th class="text-end">Entry → Exit</th>
                            <th class="text-end">PnL</th>
                            <th class="text-center">Hold Time</th>
                            <th class="text-center">Confidence</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${signalsHtml}
                    </tbody>
                </table>
            </div>
            ${signals.length > 20 ? `
                <div class="text-center mt-3">
                    <small class="text-muted">Showing first 20 signals of ${signals.length} total</small>
                </div>
            ` : ''}
        `;
    }

    loadInitialData() {
        this.updateAllData();
        this.updateMarketStatus();
    }

    destroy() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
        }
        if (this.marketDataInterval) {
            clearInterval(this.marketDataInterval);
        }
        if (this.priceChart) {
            this.priceChart.destroy();
        }
    }
}

// Global functions for commodity and timeframe selection
function selectCommodity(commodity) {
    // Update active button
    document.querySelectorAll('.btn-commodity').forEach(btn => {
        btn.classList.remove('active');
    });
    document.querySelector(`[onclick="selectCommodity('${commodity}')"]`).classList.add('active');
    
    // Show/hide timeframe buttons based on commodity
    const timeframeButtons = document.querySelectorAll('[onclick^="selectTimeframe"]');
    
    timeframeButtons.forEach(btn => {
        const onclickStr = btn.onclick.toString();
        const match = onclickStr.match(/selectTimeframe\('([^']+)'\)/);
        
        if (match) {
            const timeframe = match[1];
            
            if (commodity === 'GOLD') {
                // Gold: Show all 3 timeframes (1h, 4h, 1d)
                btn.style.display = 'inline-block';
                btn.style.visibility = 'visible';
            } else if (commodity === 'SILVER') {
                // Silver: Show only 4h and 1d
                if (timeframe === '1h') {
                    btn.style.display = 'none';
                } else {
                    btn.style.display = 'inline-block';
                    btn.style.visibility = 'visible';
                }
            }
        }
    });
    
    // If switching to Silver and 1h was selected, switch to 4h
    if (commodity === 'SILVER' && dashboard.currentTimeframe === '1h') {
        selectTimeframe('4h');
    }
    
    // Update dashboard
    dashboard.currentCommodity = commodity;
    dashboard.updateAllData();
}

function selectTimeframe(timeframe) {
    // Update active button for timeframe
    document.querySelectorAll('.btn-timeframe').forEach(btn => {
        if (btn.onclick && btn.onclick.toString().includes('selectTimeframe')) {
            btn.classList.remove('active');
        }
    });
    document.querySelector(`[onclick="selectTimeframe('${timeframe}')"]`).classList.add('active');
    
    // Update dashboard
    dashboard.currentTimeframe = timeframe;
    dashboard.updateAllData();
}

function selectDateRange(dateRange) {
    // Update active button for date range
    document.querySelectorAll('.btn-timeframe').forEach(btn => {
        if (btn.onclick && btn.onclick.toString().includes('selectDateRange')) {
            btn.classList.remove('active');
        }
    });
    document.querySelector(`[onclick="selectDateRange('${dateRange}')"]`).classList.add('active');
    
    // Update dashboard
    dashboard.currentDateRange = dateRange;
    dashboard.updateAllData();
}

function updateCustomDateRange() {
    const startDate = document.getElementById('start-date').value;
    const endDate = document.getElementById('end-date').value;
    
    if (startDate && endDate) {
        dashboard.currentDateRange = 'custom';
        dashboard.updateAllData();
    }
}

function toggleTrendLines() {
    dashboard.showTrendLines = document.getElementById('show-trend-lines').checked;
    dashboard.updatePriceChart();
}

function toggleSupportResistance() {
    dashboard.showSupportResistance = document.getElementById('show-support-resistance').checked;
    dashboard.updatePriceChart();
}

function showSignalTab(tab) {
    // Update active button
    document.querySelectorAll('.btn-outline-primary').forEach(btn => {
        btn.classList.remove('active');
    });
    event.target.classList.add('active');
    
    // Show/hide containers
    if (tab === 'current') {
        document.getElementById('current-signals-container').style.display = 'block';
        document.getElementById('past-signals-container').style.display = 'none';
    } else {
        document.getElementById('current-signals-container').style.display = 'none';
        document.getElementById('past-signals-container').style.display = 'block';
        dashboard.updatePastSignals();
    }
}

function forceRefreshData() {
    if (dashboard) {
        dashboard.forceRefreshData();
    } else {
        console.error('Dashboard not initialized');
    }
}

// Initialize dashboard when page loads
let dashboard;
document.addEventListener('DOMContentLoaded', function() {
    dashboard = new TradingDashboard();
    
    // Ensure all timeframe buttons are visible initially
    const timeframeButtons = document.querySelectorAll('[onclick^="selectTimeframe"]');
    timeframeButtons.forEach(btn => {
        btn.style.display = 'inline-block';
        btn.style.visibility = 'visible';
    });
    
    // Initialize timeframe visibility based on default commodity (GOLD)
    setTimeout(() => {
        selectCommodity('GOLD');
    }, 100);
});

// Cleanup on page unload
window.addEventListener('beforeunload', function() {
    if (dashboard) {
        dashboard.destroy();
    }
});
