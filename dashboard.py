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

def get_usd_inr_rate():
    """Get live USD/INR exchange rate"""
    try:
        # Try to get USD/INR directly using yfinance
        import yfinance as yf
        usd_inr_ticker = yf.Ticker('USDINR=X')
        usd_inr_data = usd_inr_ticker.history(period='2d')
        if not usd_inr_data.empty:
            rate = float(usd_inr_data['Close'].iloc[-1])
            logger.info(f"Fetched USD/INR rate: {rate}")
            return rate
        
        # Fallback: try Yahoo Finance fetcher if available
        if hasattr(yahoo_fetcher, 'get_usd_inr_rate'):
            rate = yahoo_fetcher.get_usd_inr_rate()
            logger.info(f"Fetched USD/INR rate from fetcher: {rate}")
            return rate
            
        logger.warning("Could not fetch USD/INR rate, using default")
        return 83.0
    except Exception as e:
        logger.error(f"Error fetching USD/INR: {e}")
        return 83.0  # Default fallback

def convert_ounce_to_grams(price_per_ounce, usd_inr_rate):
    """Convert price per ounce to price per gram in INR using MCX conversion factor"""
    # MCX uses troy ounces: 1 troy ounce = 31.1035 grams
    # Formula: (Future price in USD for troy ounce / 31.1035) * live USD to INR rate
    price_per_gram_inr = (price_per_ounce / 31.1035) * usd_inr_rate
    return price_per_gram_inr

def get_live_commodity_data(commodity):
    """Get live commodity data with proper conversion"""
    try:
        usd_inr_rate = get_usd_inr_rate()
        
        if commodity == 'GOLD':
            # Use MCX data fetcher for Indian Gold prices (no conversion needed)
            try:
                # Check if mcx_fetcher is properly initialized
                if hasattr(mcx_fetcher, 'get_live_price'):
                    mcx_data = mcx_fetcher.get_live_price('GOLD')
                    logger.info(f"MCX Gold data: {mcx_data}")
                    
                    if mcx_data and mcx_data.get('close', 0) > 0:
                        # MCX Gold prices are already in INR per gram
                        price_per_gram = mcx_data.get('close', 0)
                        price_per_10g = price_per_gram * 10  # Convert to per 10 grams
                        
                        logger.info(f"Using MCX Gold price: ₹{price_per_10g:,.2f} per 10g")
                        
                        return {
                            'close': price_per_10g,
                            'change': mcx_data.get('change', 0) * 10,
                            'change_percent': mcx_data.get('change_pct', 0),
                            'volume': mcx_data.get('volume', 0),
                            'symbol': 'GOLD',
                            'name': 'Gold (₹/10g) - MCX',
                            'usd_inr_rate': usd_inr_rate,
                            'source': 'MCX',
                            'contract_size': mcx_data.get('contract_size', '100 grams')
                        }
                    else:
                        logger.warning("MCX data returned empty or zero price")
                else:
                    logger.warning("MCX fetcher does not have get_live_price method")
            except Exception as e:
                logger.error(f"Error fetching MCX Gold data: {e}")
            
            # Fallback: Try Yahoo Finance fetcher
            try:
                gold_data = yahoo_fetcher.get_live_price('GOLD')
                price_inr = gold_data.get('close', 0)
                if price_inr > 0:
                    # The price is already in INR per gram, convert to per 10 grams
                    price_per_10g = price_inr * 10
                    return {
                        'close': price_per_10g,
                        'change': gold_data.get('change', 0) * 10,
                        'change_percent': gold_data.get('change_pct', 0),
                        'volume': gold_data.get('volume', 0),
                        'symbol': 'GOLD',
                        'name': 'Gold (₹/10g) - Yahoo',
                        'usd_inr_rate': usd_inr_rate,
                        'source': 'Yahoo Finance'
                    }
            except:
                pass
            
            # Final fallback: Get gold data directly using yfinance
            try:
                import yfinance as yf
                gold_ticker = yf.Ticker('GC=F')
                gold_data_raw = gold_ticker.history(period='2d')
                if not gold_data_raw.empty:
                    latest_data = gold_data_raw.iloc[-1]
                    prev_data = gold_data_raw.iloc[-2] if len(gold_data_raw) > 1 else latest_data
                    
                    price_per_ounce_usd = float(latest_data['Close'])
                    # Use MCX conversion: (price_per_troy_ounce / 31.1035) * usd_inr_rate
                    price_per_gram_inr = (price_per_ounce_usd / 31.1035) * usd_inr_rate
                    price_per_10g = price_per_gram_inr * 10
                    
                    change_per_ounce = float(latest_data['Close'] - prev_data['Close'])
                    change_per_gram = (change_per_ounce / 31.1035) * usd_inr_rate
                    change_per_10g = change_per_gram * 10
                    
                    return {
                        'close': price_per_10g,
                        'change': change_per_10g,
                        'change_percent': float((latest_data['Close'] - prev_data['Close']) / prev_data['Close'] * 100),
                        'volume': int(latest_data['Volume']),
                        'symbol': 'GOLD',
                        'name': 'Gold (₹/10g) - Converted',
                        'usd_inr_rate': usd_inr_rate,
                        'source': 'Yahoo Finance (Converted)'
                    }
            except Exception as e:
                logger.error(f"Error fetching gold data: {e}")
        
        elif commodity == 'SILVER':
            # Try Yahoo Finance fetcher first, then fallback to direct yfinance
            try:
                silver_data = yahoo_fetcher.get_live_price('SILVER')
                price_inr = silver_data.get('close', 0)
                if price_inr > 0:
                    # The price is already in INR per gram, convert to per kg
                    price_per_kg = price_inr * 1000
                    return {
                        'close': price_per_kg,
                        'change': silver_data.get('change', 0) * 1000,
                        'change_percent': silver_data.get('change_pct', 0),
                        'volume': silver_data.get('volume', 0),
                        'symbol': 'SILVER',
                        'name': 'Silver (₹/kg)',
                        'usd_inr_rate': usd_inr_rate
                    }
            except:
                pass
            
            # Fallback: Get silver data directly using yfinance
            try:
                import yfinance as yf
                silver_ticker = yf.Ticker('SI=F')
                silver_data_raw = silver_ticker.history(period='2d')
                if not silver_data_raw.empty:
                    latest_data = silver_data_raw.iloc[-1]
                    prev_data = silver_data_raw.iloc[-2] if len(silver_data_raw) > 1 else latest_data
                    
                    price_per_ounce_usd = float(latest_data['Close'])
                    # Use MCX conversion: (price_per_troy_ounce / 31.1035) * usd_inr_rate
                    price_per_gram_inr = (price_per_ounce_usd / 31.1035) * usd_inr_rate
                    price_per_kg = price_per_gram_inr * 1000
                    
                    change_per_ounce = float(latest_data['Close'] - prev_data['Close'])
                    change_per_gram = (change_per_ounce / 31.1035) * usd_inr_rate
                    change_per_kg = change_per_gram * 1000
                    
                    return {
                        'close': price_per_kg,
                        'change': change_per_kg,
                        'change_percent': float((latest_data['Close'] - prev_data['Close']) / prev_data['Close'] * 100),
                        'volume': int(latest_data['Volume']),
                        'symbol': 'SILVER',
                        'name': 'Silver (₹/kg)',
                        'usd_inr_rate': usd_inr_rate
                    }
            except Exception as e:
                logger.error(f"Error fetching silver data: {e}")
        
        elif commodity == 'COPPER':
            # For copper, we'll use a fallback approach since it's not in the predefined symbols
            # Try to get copper data using yfinance directly
            try:
                import yfinance as yf
                copper_ticker = yf.Ticker('HG=F')
                copper_data_raw = copper_ticker.history(period='2d')
                if not copper_data_raw.empty:
                    latest_data = copper_data_raw.iloc[-1]
                    prev_data = copper_data_raw.iloc[-2] if len(copper_data_raw) > 1 else latest_data
                    
                    copper_data = {
                        'close': float(latest_data['Close']),
                        'change': float(latest_data['Close'] - prev_data['Close']),
                        'change_percent': float((latest_data['Close'] - prev_data['Close']) / prev_data['Close'] * 100),
                        'volume': int(latest_data['Volume'])
                    }
                else:
                    copper_data = {'close': 0, 'change': 0, 'change_percent': 0, 'volume': 0}
            except Exception as e:
                logger.error(f"Error fetching copper data: {e}")
                copper_data = {'close': 0, 'change': 0, 'change_percent': 0, 'volume': 0}
            
            price_per_pound = copper_data.get('close', 0)
            if price_per_pound > 0:
                # Convert to INR per kg
                # 1 pound = 0.453592 kg
                price_per_kg_usd = price_per_pound / 0.453592
                price_per_kg_inr = price_per_kg_usd * usd_inr_rate
                
                return {
                    'close': price_per_kg_inr,
                    'change': copper_data.get('change', 0) * usd_inr_rate / 0.453592,
                    'change_percent': copper_data.get('change_percent', 0),
                    'volume': copper_data.get('volume', 0),
                    'symbol': 'COPPER',
                    'name': 'Copper (₹/kg)',
                    'usd_price_per_pound': price_per_pound,
                    'usd_inr_rate': usd_inr_rate
                }
        
        # Fallback
        return {
            'close': 0, 'change': 0, 'change_percent': 0, 'volume': 0,
            'symbol': commodity, 'name': commodity, 'usd_inr_rate': usd_inr_rate
        }
        
    except Exception as e:
        logger.error(f"Error getting live data for {commodity}: {e}")
        return {
            'close': 0, 'change': 0, 'change_percent': 0, 'volume': 0,
            'symbol': commodity, 'name': commodity, 'usd_inr_rate': 83.0
        }

def update_market_data():
    """Update market data cache with live data and proper conversions."""
    global market_data_cache, last_update_time
    
    while True:
        try:
            current_time = datetime.now()
            logger.info("Updating market data with live prices...")
            
            # Update cache for all commodities
            for commodity in ['GOLD', 'SILVER', 'COPPER']:
                try:
                    live_price = get_live_commodity_data(commodity)
                    
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
                    logger.info(f"Updated {commodity}: ₹{live_price.get('close', 0):,.2f} (USD/INR: {live_price.get('usd_inr_rate', 0):.2f})")
                    
                except Exception as e:
                    logger.error(f"Error updating {commodity}: {e}")
            
            logger.info("Market data updated with live prices and conversions")
            time.sleep(30)  # Update every 30 seconds
            
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

@app.route('/api/scalping/gold')
def get_gold_scalping_data():
    """Get Gold scalping data using Indian MCX prices."""
    try:
        from src.gold_scalping_strategy import GoldScalpingStrategy
        
        strategy = GoldScalpingStrategy()
        
        # Get market data
        market_data = strategy.get_market_data()
        
        # Get performance summary
        performance = strategy.get_performance_summary()
        
        # Get recent trades
        recent_trades = strategy.trades[-5:] if strategy.trades else []
        
        return jsonify({
            'market_data': market_data,
            'performance': performance,
            'recent_trades': recent_trades,
            'strategy_params': {
                'stop_loss_points': strategy.stop_loss_points,
                'take_profit_points': strategy.take_profit_points,
                'max_hold_minutes': strategy.max_hold_minutes,
                'position_size': strategy.position_size
            },
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting scalping data: {e}")
        return jsonify({'error': str(e)}), 500

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
            overview['usd_inr'] = get_usd_inr_rate()
        except:
            overview['usd_inr'] = 83.0
        
        # Get all commodity data with proper conversions
        for commodity in ['GOLD', 'SILVER', 'COPPER']:
            try:
                live_price = get_live_commodity_data(commodity)
                overview['commodities'][commodity] = {
                    'price': live_price.get('close', 0),
                    'change': live_price.get('change', 0),
                    'change_percent': live_price.get('change_percent', 0),
                    'volume': live_price.get('volume', 0),
                    'symbol': live_price.get('symbol', ''),
                    'name': live_price.get('name', commodity),
                    'usd_inr_rate': live_price.get('usd_inr_rate', 83.0)
                }
            except Exception as e:
                logger.warning(f"Could not get data for {commodity}: {e}")
                overview['commodities'][commodity] = {
                    'price': 0, 'change': 0, 'change_percent': 0, 'volume': 0, 'symbol': '', 'name': commodity, 'usd_inr_rate': 83.0
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
    # Force initial cache update with live data and conversions
    logger.info("Forcing initial cache update with live data and conversions...")
    current_time = datetime.now()
    
    for commodity in ['GOLD', 'SILVER', 'COPPER']:
        try:
            live_price = get_live_commodity_data(commodity)
            historical_1h = yahoo_fetcher.get_historical_data(commodity, '1d', '1h')
            historical_4h = yahoo_fetcher.get_historical_data(commodity, '5d', '4h')
            
            market_data_cache[commodity] = {
                'live_price': live_price,
                'historical_1h': historical_1h.to_dict('records') if not historical_1h.empty else [],
                'historical_4h': historical_4h.to_dict('records') if not historical_4h.empty else [],
                'last_update': current_time.isoformat()
            }
            last_update_time[commodity] = current_time
            logger.info(f"Initial cache updated for {commodity}: {live_price.get('name', commodity)} = ₹{live_price.get('close', 0):,.2f} (USD/INR: {live_price.get('usd_inr_rate', 0):.2f})")
        except Exception as e:
            logger.error(f"Error initializing {commodity}: {e}")
    
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
