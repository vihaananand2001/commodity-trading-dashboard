#!/usr/bin/env python3
"""
Live Trading Dashboard for MCX Commodity Markets
Real-time dashboard with ML confidence scoring and position sizing
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, render_template, jsonify, request
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import threading
import time
from typing import Dict, List, Any
import warnings
warnings.filterwarnings('ignore')

try:
    from src.mcx_data_fetcher import MCXDataFetcher
    from src.yahoo_finance_fetcher import YahooFinanceFetcher
    from src.simple_confidence_scorer import SimpleConfidenceScorer
    from src.dashboard_data_service import DashboardDataService
    from src.live_trading_integration import LiveTradingIntegration
    from src.utils import get_logger
except ImportError as e:
    print(f"Warning: Could not import some modules: {e}")
    # Create dummy classes for deployment
    class MCXDataFetcher:
        def get_live_price(self, commodity): return {'close': 0, 'change': 0, 'change_percent': 0}
        def get_historical_data(self, commodity, period, interval): return pd.DataFrame()
    class YahooFinanceFetcher:
        def get_live_price(self, commodity): return {'close': 0, 'change': 0, 'change_percent': 0}
        def get_historical_data(self, commodity, period, interval): return pd.DataFrame()
    class SimpleConfidenceScorer:
        def __init__(self, *args, **kwargs): pass
    class DashboardDataService:
        def generate_trading_signals(self, commodity, timeframe): return []
        def get_market_analysis(self, commodity, timeframe): return {}
        def get_chart_data(self, commodity, timeframe, days): return {}
    class LiveTradingIntegration:
        def __init__(self, *args, **kwargs): pass
    import logging
    def get_logger(name):
        return logging.getLogger(name)

logger = get_logger(__name__)

app = Flask(__name__)

# Global instances
mcx_fetcher = MCXDataFetcher()
yahoo_fetcher = YahooFinanceFetcher()
data_service = DashboardDataService()
live_traders = {}
confidence_scorers = {}

# Data source configuration
USE_YAHOO_FINANCE = True  # Set to True for real data, False for simulated data

# Market data cache
market_data_cache = {}
last_update_time = {}

def initialize_traders():
    """Initialize live traders and confidence scorers for each commodity."""
    commodities = ['GOLD', 'SILVER']
    timeframes = ['1h', '4h']
    
    for commodity in commodities:
        live_traders[commodity] = {}
        confidence_scorers[commodity] = {}
        
        for timeframe in timeframes:
            try:
                # Initialize live trader
                live_traders[commodity][timeframe] = LiveTradingIntegration(
                    commodity.lower(), timeframe, 'long'
                )
                
                # Initialize confidence scorer
                confidence_scorers[commodity][timeframe] = SimpleConfidenceScorer(
                    commodity.lower(), timeframe, 'long'
                )
                
                logger.info(f"Initialized trader for {commodity} {timeframe}")
                
            except Exception as e:
                logger.error(f"Error initializing {commodity} {timeframe}: {e}")

def update_market_data():
    """Update market data cache."""
    global market_data_cache, last_update_time
    
    while True:
        try:
            current_time = datetime.now()
            
            # Use Yahoo Finance for real data or MCX fetcher for simulated data
            if USE_YAHOO_FINANCE:
                logger.info("Background thread using Yahoo Finance for real-time data")
                for commodity in ['GOLD', 'SILVER']:
                    # Get live price data from Yahoo Finance
                    live_price = yahoo_fetcher.get_live_price(commodity)
                    logger.info(f"Background thread {commodity} Yahoo data: ₹{live_price.get('close', 0):,.2f}")
                    
                    # Get historical data for analysis
                    historical_1h = yahoo_fetcher.get_historical_data(commodity, '1d', '1h')
                    historical_4h = yahoo_fetcher.get_historical_data(commodity, '5d', '4h')
            else:
                # Use simulated MCX data
                fresh_fetcher = MCXDataFetcher()
                logger.info(f"Background thread using simulated MCX data")
                for commodity in ['GOLD', 'SILVER']:
                    # Get live price data
                    live_price = fresh_fetcher.get_live_price(commodity)
                    logger.info(f"Background thread {commodity} simulated data: symbol={live_price.get('symbol')}, name={live_price.get('name')}, lot_size={live_price.get('lot_size')}")
                    
                    # Get historical data for analysis
                    historical_1h = fresh_fetcher.get_historical_data(commodity, '1h', 100)
                    historical_4h = fresh_fetcher.get_historical_data(commodity, '4h', 100)
                
            # Update cache for all commodities
            for commodity in ['GOLD', 'SILVER']:
                if USE_YAHOO_FINANCE:
                    live_price = yahoo_fetcher.get_live_price(commodity)
                    historical_1h = yahoo_fetcher.get_historical_data(commodity, '1d', '1h')
                    historical_4h = yahoo_fetcher.get_historical_data(commodity, '5d', '4h')
                else:
                    fresh_fetcher = MCXDataFetcher()
                    live_price = fresh_fetcher.get_live_price(commodity)
                    historical_1h = fresh_fetcher.get_historical_data(commodity, '1h', 100)
                    historical_4h = fresh_fetcher.get_historical_data(commodity, '4h', 100)
                
                # Update cache
                market_data_cache[commodity] = {
                    'live_price': live_price,
                    'historical_1h': historical_1h.to_dict('records') if not historical_1h.empty else [],
                    'historical_4h': historical_4h.to_dict('records') if not historical_4h.empty else [],
                    'last_update': current_time.isoformat()
                }
                
                last_update_time[commodity] = current_time
            
            logger.info("Market data updated with fresh MCX specs")
            time.sleep(30)  # Update every 30 seconds for now
            
        except Exception as e:
            logger.error(f"Error updating market data: {e}")
            time.sleep(60)  # Retry in 1 minute on error

@app.route('/')
def index():
    """Professional homepage with market overview."""
    try:
        return render_template('professional_homepage.html')
    except Exception as e:
        logger.error(f"Error loading professional homepage: {e}")
        # Fallback to basic dashboard
        return render_template('dashboard.html')

@app.route('/test')
def test_route():
    """Test route to verify dashboard is working."""
    return jsonify({
        'status': 'success',
        'message': 'Professional Trading Dashboard is running',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/commodity/<commodity>/<timeframe>')
def commodity_page(commodity, timeframe):
    """Individual commodity page."""
    return render_template('commodity_detail.html', 
                         commodity=commodity.upper(), 
                         timeframe=timeframe)

@app.route('/api/market-overview')
def get_market_overview():
    """Get comprehensive market overview for homepage."""
    try:
        overview = {
            'usd_inr': 83.0,  # Default fallback
            'commodities': {},
            'signals': {},
            'market_sentiment': {},
            'last_update': datetime.now().isoformat()
        }
        
        # Get USD/INR rate
        try:
            usd_inr_data = yahoo_fetcher.get_live_price('USDINR=X')
            overview['usd_inr'] = usd_inr_data.get('close', 83.0)
        except:
            overview['usd_inr'] = 83.0
        
        # Get all commodity data
        for commodity in ['GOLD', 'SILVER', 'COPPER']:
            try:
                live_price = yahoo_fetcher.get_live_price(commodity)
                overview['commodities'][commodity] = {
                    'price': live_price.get('close', 0),
                    'change': live_price.get('change', 0),
                    'change_percent': live_price.get('change_percent', 0),
                    'volume': live_price.get('volume', 0),
                    'symbol': live_price.get('symbol', ''),
                    'name': live_price.get('name', commodity)
                }
            except Exception as e:
                logger.warning(f"Could not get data for {commodity}: {e}")
                overview['commodities'][commodity] = {
                    'price': 0, 'change': 0, 'change_percent': 0, 'volume': 0, 'symbol': '', 'name': commodity
                }
        
        # Get signals for all commodities and timeframes
        for commodity in ['GOLD', 'SILVER']:
            overview['signals'][commodity] = {}
            for timeframe in ['1h', '4h', '1d']:
                try:
                    signals = data_service.generate_trading_signals(commodity.lower(), timeframe)
                    overview['signals'][commodity][timeframe] = signals[:3]  # Top 3 signals
                except Exception as e:
                    logger.warning(f"Could not get signals for {commodity} {timeframe}: {e}")
                    overview['signals'][commodity][timeframe] = []
        
        # Calculate market sentiment
        total_signals = 0
        bullish_signals = 0
        bearish_signals = 0
        
        for commodity_signals in overview['signals'].values():
            for timeframe_signals in commodity_signals.values():
                for signal in timeframe_signals:
                    total_signals += 1
                    if signal.get('direction', '').upper() == 'LONG':
                        bullish_signals += 1
                    elif signal.get('direction', '').upper() == 'SHORT':
                        bearish_signals += 1
        
        if total_signals > 0:
            overview['market_sentiment'] = {
                'bullish_percent': (bullish_signals / total_signals) * 100,
                'bearish_percent': (bearish_signals / total_signals) * 100,
                'neutral_percent': 100 - ((bullish_signals + bearish_signals) / total_signals) * 100,
                'total_signals': total_signals
            }
        else:
            overview['market_sentiment'] = {
                'bullish_percent': 50,
                'bearish_percent': 50,
                'neutral_percent': 0,
                'total_signals': 0
            }
        
        return jsonify(overview)
        
    except Exception as e:
        logger.error(f"Error getting market overview: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/market-data/<commodity>')
def get_market_data(commodity):
    """Get market data for a specific commodity."""
    try:
        commodity = commodity.upper()
        
        if commodity not in ['GOLD', 'SILVER']:
            return jsonify({'error': 'Commodity not found'}), 404
        
        # Force Yahoo Finance for real data
        logger.info(f"=== FORCING YAHOO FINANCE FOR {commodity} ===")
        live_price = yahoo_fetcher.get_live_price(commodity)
        logger.info(f"Yahoo Finance data for {commodity}: {live_price}")
        
        # Get historical data (1 month for demo)
        historical_1h = yahoo_fetcher.get_historical_data(commodity, '1d', '1h')
        historical_4h = yahoo_fetcher.get_historical_data(commodity, '5d', '4h')
        
        response_data = {
            'live_price': live_price,
            'historical_1h': historical_1h.to_dict('records') if not historical_1h.empty else [],
            'historical_4h': historical_4h.to_dict('records') if not historical_4h.empty else [],
            'last_update': datetime.now().isoformat()
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error getting market data for {commodity}: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/signals/<commodity>/<timeframe>')
def get_trading_signals(commodity, timeframe):
    """Get trading signals for a specific commodity and timeframe."""
    try:
        commodity = commodity.upper()
        
        if commodity not in ['GOLD', 'SILVER']:
            return jsonify({'error': 'Commodity not found'}), 404
            
        if timeframe not in ['1h', '4h', '1d']:
            return jsonify({'error': 'Timeframe not supported'}), 404
        
        # Use data service to get actual trading signals
        commodity_key = commodity.lower()
        signals = data_service.generate_trading_signals(commodity_key, timeframe)
        
        # Get market analysis
        market_analysis = data_service.get_market_analysis(commodity_key, timeframe)
        
        # Generate recommendation based on signals
        if signals:
            avg_confidence = np.mean([s['confidence'] for s in signals])
            if avg_confidence >= 0.7:
                action = "ENTER"
                reason = f"High confidence signals detected (avg: {avg_confidence:.2f})"
                position_sizing = "Standard position size"
            elif avg_confidence >= 0.6:
                action = "CONSIDER"
                reason = f"Moderate confidence signals detected (avg: {avg_confidence:.2f})"
                position_sizing = "Reduced position size"
            else:
                action = "WAIT"
                reason = f"Low confidence signals (avg: {avg_confidence:.2f})"
                position_sizing = "Avoid or very small position"
        else:
            action = "WAIT"
            reason = "No high-confidence signals detected"
            position_sizing = "Monitor for better opportunities"
        
        recommendation = {
            'action': action,
            'reason': reason,
            'position_sizing': position_sizing
        }
        
        response_data = {
            'signals': signals,
            'market_analysis': market_analysis,
            'recommendation': recommendation,
            'timestamp': datetime.now().isoformat()
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error getting signals for {commodity} {timeframe}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/position-calculator', methods=['POST'])
def calculate_position():
    """Calculate position size and margin requirements."""
    try:
        data = request.json
        commodity = data.get('commodity', 'GOLD').upper()
        quantity = int(data.get('quantity', 1))
        price = float(data.get('price', 0))
        
        if price <= 0:
            return jsonify({'error': 'Invalid price'}), 400
        
        # Calculate position value
        fresh_fetcher = MCXDataFetcher()
        position_data = fresh_fetcher.calculate_position_value(commodity, quantity, price)
        
        if not position_data:
            return jsonify({'error': 'Error calculating position'}), 500
        
        return jsonify(position_data)
        
    except Exception as e:
        logger.error(f"Error calculating position: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/market-status')
def get_market_status():
    """Get current market status."""
    try:
        fresh_fetcher = MCXDataFetcher()
        market_status = fresh_fetcher.get_market_status()
        return jsonify(market_status)
        
    except Exception as e:
        logger.error(f"Error getting market status: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/commodity-specs')
def get_commodity_specs():
    """Get commodity specifications."""
    try:
        fresh_fetcher = MCXDataFetcher()
        return jsonify(fresh_fetcher.commodity_specs)
        
    except Exception as e:
        logger.error(f"Error getting commodity specs: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/chart-data/<commodity>/<timeframe>')
def get_chart_data(commodity, timeframe):
    """Get chart data for visualization."""
    try:
        commodity = commodity.upper()
        timeframe = timeframe.lower()
        
        if commodity not in ['GOLD', 'SILVER']:
            return jsonify({'error': 'Commodity not found'}), 404
            
        if timeframe not in ['1h', '4h', '1d']:
            return jsonify({'error': 'Timeframe not supported'}), 404
        
        # Use data service to get chart data
        commodity_key = commodity.lower()
        chart_data = data_service.get_chart_data(commodity_key, timeframe, '1m')  # Last month
        
        return jsonify(chart_data)
        
    except Exception as e:
        logger.error(f"Error getting chart data: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/past-signals/<commodity>/<timeframe>')
def get_past_signals(commodity, timeframe):
    """Get past trading signals with outcomes."""
    try:
        commodity = commodity.upper()
        timeframe = timeframe.lower()
        
        if commodity not in ['GOLD', 'SILVER']:
            return jsonify({'error': 'Commodity not found'}), 404
            
        if timeframe not in ['1h', '4h', '1d']:
            return jsonify({'error': 'Timeframe not supported'}), 404
        
        # Use data service to get past signals
        commodity_key = commodity.lower()
        past_signals = data_service.get_past_signals(commodity_key, timeframe, lookback_days=90)
        
        # Calculate summary statistics
        total_signals = len(past_signals)
        winning_signals = len([s for s in past_signals if s['outcome'] == 'WIN'])
        losing_signals = len([s for s in past_signals if s['outcome'] == 'LOSS'])
        total_pnl = sum([s['pnl'] for s in past_signals])
        
        win_rate = (winning_signals / total_signals * 100) if total_signals > 0 else 0
        
        response_data = {
            'signals': past_signals,
            'summary': {
                'total_signals': total_signals,
                'winning_signals': winning_signals,
                'losing_signals': losing_signals,
                'win_rate': win_rate,
                'total_pnl': total_pnl
            },
            'timestamp': datetime.now().isoformat()
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error getting past signals: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/debug-data-source')
def debug_data_source():
    """Debug data source configuration."""
    try:
        yahoo_data = yahoo_fetcher.get_live_price('GOLD')
        mcx_data = mcx_fetcher.get_live_price('GOLD')
        
        return jsonify({
            'use_yahoo_finance': USE_YAHOO_FINANCE,
            'yahoo_data': yahoo_data,
            'mcx_data': mcx_data,
            'yahoo_symbol': yahoo_data.get('symbol'),
            'mcx_symbol': mcx_data.get('symbol'),
            'yahoo_price': yahoo_data.get('close'),
            'mcx_price': mcx_data.get('close')
        })
        
    except Exception as e:
        logger.error(f"Error in debug data source: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/performance/<commodity>')
def get_performance(commodity):
    """Get trading performance for a commodity."""
    try:
        commodity = commodity.upper()
        
        # Get performance from data service
        commodity_key = commodity.lower()
        performance_data = {}
        
        # Get performance for different timeframes
        for timeframe in ['1d', '4h', '1h']:
            try:
                metrics = data_service.get_performance_metrics(commodity_key, timeframe)
                performance_data[timeframe] = metrics
            except Exception as e:
                logger.warning(f"Could not get performance for {commodity} {timeframe}: {e}")
                performance_data[timeframe] = {'total_trades': 0, 'win_rate': 0, 'total_pnl': 0}
        
        return jsonify(performance_data)
        
    except Exception as e:
        logger.error(f"Error getting performance for {commodity}: {e}")
        return jsonify({'error': str(e)}), 500

def start_data_updater():
    """Start the background data updater thread."""
    # Force initial cache update with Yahoo Finance
    logger.info("Forcing initial cache update with Yahoo Finance...")
    current_time = datetime.now()
    
    for commodity in ['GOLD', 'SILVER']:
        live_price = yahoo_fetcher.get_live_price(commodity)
        historical_1h = yahoo_fetcher.get_historical_data(commodity, '1d', '1h')
        historical_4h = yahoo_fetcher.get_historical_data(commodity, '5d', '4h')
        
        market_data_cache[commodity] = {
            'live_price': live_price,
            'historical_1h': historical_1h.to_dict('records') if not historical_1h.empty else [],
            'historical_4h': historical_4h.to_dict('records') if not historical_4h.empty else [],
            'last_update': current_time.isoformat()
        }
        last_update_time[commodity] = current_time
        logger.info(f"Initial cache updated for {commodity}: symbol={live_price.get('symbol')}, name={live_price.get('name')}, price=₹{live_price.get('close', 0):,.2f}")
    
    # Start background thread
    updater_thread = threading.Thread(target=update_market_data, daemon=True)
    updater_thread.start()
    logger.info("Market data updater started")

if __name__ == '__main__':
    logger.info("Starting Professional Trading Dashboard...")
    
    # Initialize traders and scorers
    initialize_traders()
    
    # Start background data updater
    start_data_updater()
    
    # Get port from environment variable (for Render deployment)
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') != 'production'
    
    # Run Flask app
    app.run(debug=debug, host='0.0.0.0', port=port)
