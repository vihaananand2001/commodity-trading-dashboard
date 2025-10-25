#!/usr/bin/env python3
"""
Professional Commodity Trading Dashboard
JP Morgan-style professional dashboard with market overview and live signals
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
except ImportError as e:
    print(f"Warning: Could not import some modules: {e}")
    # Create dummy classes for testing
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
try:
    from src.utils import get_logger
except ImportError:
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

# Market data cache
market_data_cache = {}
last_update_time = {}
usd_inr_price = 0.0

def get_usd_inr_price():
    """Get USD/INR exchange rate"""
    try:
        # Using Yahoo Finance for USD/INR
        usd_inr_data = yahoo_fetcher.get_live_price('USDINR=X')
        return usd_inr_data.get('close', 83.0)  # Default fallback
    except Exception as e:
        logger.error(f"Error fetching USD/INR: {e}")
        return 83.0  # Default fallback

def update_market_data():
    """Update market data cache with all commodities and USD/INR"""
    global market_data_cache, last_update_time, usd_inr_price
    
    while True:
        try:
            current_time = datetime.now()
            
            # Get USD/INR rate
            usd_inr_price = get_usd_inr_price()
            
            # Update all commodities
            commodities = ['GOLD', 'SILVER', 'COPPER']
            
            for commodity in commodities:
                try:
                    # Get live price data
                    live_price = yahoo_fetcher.get_live_price(commodity)
                    
                    # Get historical data for analysis
                    historical_1h = yahoo_fetcher.get_historical_data(commodity, '1d', '1h')
                    historical_4h = yahoo_fetcher.get_historical_data(commodity, '5d', '4h')
                    
                    # Update cache
                    market_data_cache[commodity] = {
                        'live_price': live_price,
                        'historical_1h': historical_1h.to_dict('records') if not historical_1h.empty else [],
                        'historical_4h': historical_4h.to_dict('records') if not historical_4h.empty else [],
                        'last_update': current_time.isoformat()
                    }
                    
                    last_update_time[commodity] = current_time
                    logger.info(f"Updated {commodity}: ₹{live_price.get('close', 0):,.2f}")
                    
                except Exception as e:
                    logger.error(f"Error updating {commodity}: {e}")
            
            logger.info(f"Market data updated. USD/INR: {usd_inr_price:.2f}")
            time.sleep(30)  # Update every 30 seconds
            
        except Exception as e:
            logger.error(f"Error updating market data: {e}")
            time.sleep(60)  # Retry in 1 minute on error

@app.route('/')
def homepage():
    """Professional homepage with market overview"""
    return render_template('professional_homepage.html')

@app.route('/commodity/<commodity>/<timeframe>')
def commodity_page(commodity, timeframe):
    """Individual commodity page"""
    return render_template('commodity_detail.html', 
                         commodity=commodity.upper(), 
                         timeframe=timeframe)

@app.route('/api/market-overview')
def get_market_overview():
    """Get comprehensive market overview for homepage"""
    try:
        overview = {
            'usd_inr': usd_inr_price,
            'commodities': {},
            'signals': {},
            'market_sentiment': {},
            'last_update': datetime.now().isoformat()
        }
        
        # Get all commodity data
        for commodity in ['GOLD', 'SILVER', 'COPPER']:
            if commodity in market_data_cache:
                data = market_data_cache[commodity]
                live_price = data['live_price']
                
                overview['commodities'][commodity] = {
                    'price': live_price.get('close', 0),
                    'change': live_price.get('change', 0),
                    'change_percent': live_price.get('change_percent', 0),
                    'volume': live_price.get('volume', 0),
                    'symbol': live_price.get('symbol', ''),
                    'name': live_price.get('name', commodity)
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

@app.route('/api/commodity-data/<commodity>')
def get_commodity_data(commodity):
    """Get detailed data for a specific commodity"""
    try:
        commodity = commodity.upper()
        
        if commodity not in ['GOLD', 'SILVER', 'COPPER']:
            return jsonify({'error': 'Commodity not found'}), 404
        
        # Get live price data
        live_price = yahoo_fetcher.get_live_price(commodity)
        historical_1h = yahoo_fetcher.get_historical_data(commodity, '1d', '1h')
        historical_4h = yahoo_fetcher.get_historical_data(commodity, '5d', '4h')
        
        response_data = {
            'live_price': live_price,
            'historical_1h': historical_1h.to_dict('records') if not historical_1h.empty else [],
            'historical_4h': historical_4h.to_dict('records') if not historical_4h.empty else [],
            'usd_inr': usd_inr_price,
            'last_update': datetime.now().isoformat()
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error getting commodity data for {commodity}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/signals/<commodity>/<timeframe>')
def get_trading_signals(commodity, timeframe):
    """Get trading signals for a specific commodity and timeframe"""
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

@app.route('/api/chart-data/<commodity>/<timeframe>')
def get_chart_data(commodity, timeframe):
    """Get chart data for visualization"""
    try:
        commodity = commodity.upper()
        timeframe = timeframe.lower()
        
        if commodity not in ['GOLD', 'SILVER', 'COPPER']:
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

def start_data_updater():
    """Start the background data updater thread"""
    # Force initial cache update
    logger.info("Initializing market data cache...")
    current_time = datetime.now()
    
    # Get USD/INR
    global usd_inr_price
    usd_inr_price = get_usd_inr_price()
    
    # Initialize all commodities
    for commodity in ['GOLD', 'SILVER', 'COPPER']:
        try:
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
            logger.info(f"Initialized {commodity}: ₹{live_price.get('close', 0):,.2f}")
        except Exception as e:
            logger.error(f"Error initializing {commodity}: {e}")
    
    # Start background thread
    updater_thread = threading.Thread(target=update_market_data, daemon=True)
    updater_thread.start()
    logger.info("Market data updater started")

if __name__ == '__main__':
    logger.info("Starting Professional Trading Dashboard...")
    
    # Start background data updater
    start_data_updater()
    
    # Run Flask app
    app.run(debug=True, host='0.0.0.0', port=5001)
