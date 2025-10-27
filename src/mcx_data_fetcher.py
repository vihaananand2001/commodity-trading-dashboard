#!/usr/bin/env python3
"""
MCX Live Data Fetcher
Fetches real-time data from Indian MCX commodity markets
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import json
from typing import Dict, List, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')

import logging

# Create logger without dependency on utils
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class MCXDataFetcher:
    """
    Fetches live data from MCX commodity markets.
    For demo purposes, we'll simulate live data based on historical patterns.
    In production, this would connect to real MCX data feeds.
    """
    
    def __init__(self):
        """Initialize MCX data fetcher."""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # MCX commodity specifications
        self.commodity_specs = {
            'GOLD': {
                'symbol': 'GOLDM',
                'name': 'GOLD MINI',
                'expiry': '2025-12-05',
                'lot_size': 100,  # grams (Mini contract)
                'tick_size': 1.0,  # INR per gram
                'margin': 0.05,    # 5% margin
                'currency': 'INR',
                'unit': 'grams',
                'contract_size': '100 grams'
            },
            'SILVER': {
                'symbol': 'SILVERM',
                'name': 'SILVER MINI',
                'expiry': '2025-12-05',
                'lot_size': 5000,  # grams (Mini contract)
                'tick_size': 1.0,   # INR per gram
                'margin': 0.05,     # 5% margin
                'currency': 'INR',
                'unit': 'grams',
                'contract_size': '5 kg'
            },
            'COPPER': {
                'symbol': 'COPPERM',
                'name': 'COPPER MINI',
                'expiry': '2025-12-05',
                'lot_size': 1000,  # kg (Mini contract)
                'tick_size': 0.05,  # INR per kg
                'margin': 0.05,     # 5% margin
                'currency': 'INR',
                'unit': 'kg',
                'contract_size': '1 tonne'
            }
        }
        
        # Base prices for simulation (realistic MCX prices as of Oct 2025)
        self.base_prices = {
            'GOLD': 125620.0,   # INR per 10 grams (December futures realistic price)
            'SILVER': 145000.0, # INR per kg (December futures realistic price)
            'COPPER': 850.0     # INR per kg (December futures realistic price)
        }
        
        # Last update time
        self.last_update = {}
        
    def get_live_price(self, commodity: str) -> Dict[str, any]:
        """
        Get live price data for a commodity.
        
        Args:
            commodity: Commodity symbol (GOLD, SILVER)
            
        Returns:
            Dictionary with live price data
        """
        try:
            # In production, this would fetch from real MCX API
            # For demo, we'll simulate realistic price movements
            
            current_time = datetime.now()
            base_price = self.base_prices.get(commodity, 0)
            
            # Simulate realistic price movements
            if commodity == 'GOLD':
                # Gold price simulation with realistic volatility
                time_factor = (current_time.hour + current_time.minute / 60.0) / 24.0
                volatility = np.random.normal(0, 200)  # ±200 INR volatility for Gold
                trend = np.sin(time_factor * 2 * np.pi) * 300  # Daily trend
                price_change = volatility + trend
                current_price = base_price + price_change
            elif commodity == 'SILVER':
                # Silver price simulation (more volatile than gold)
                time_factor = (current_time.hour + current_time.minute / 60.0) / 24.0
                volatility = np.random.normal(0, 500)  # ±500 INR volatility for Silver
                trend = np.sin(time_factor * 2 * np.pi) * 800  # Daily trend
                price_change = volatility + trend
                current_price = base_price + price_change
            else:  # COPPER
                # Copper price simulation
                time_factor = (current_time.hour + current_time.minute / 60.0) / 24.0
                volatility = np.random.normal(0, 5)  # ±5 INR volatility for Copper
                trend = np.sin(time_factor * 2 * np.pi) * 10  # Daily trend
                price_change = volatility + trend
                current_price = base_price + price_change
            
            # Ensure price is positive and realistic
            current_price = max(current_price, base_price * 0.95)
            
            # Update base price occasionally to simulate market movement
            if commodity not in self.last_update or (current_time - self.last_update[commodity]).seconds > 300:  # Every 5 minutes
                self.base_prices[commodity] = current_price
                self.last_update[commodity] = current_time
            
            # Generate OHLC data
            high = current_price + np.random.uniform(10, 50)
            low = current_price - np.random.uniform(10, 50)
            open_price = current_price + np.random.uniform(-20, 20)
            close = current_price
            
            # Calculate volume (simulated)
            volume = np.random.randint(1000, 5000)
            
            price_data = {
                'symbol': self.commodity_specs[commodity]['symbol'],
                'name': self.commodity_specs[commodity]['name'],
                'expiry': self.commodity_specs[commodity]['expiry'],
                'contract_size': self.commodity_specs[commodity]['contract_size'],
                'timestamp': current_time.isoformat(),
                'open': round(open_price, 2),
                'high': round(high, 2),
                'low': round(low, 2),
                'close': round(close, 2),
                'volume': volume,
                'change': round(close - open_price, 2),
                'change_pct': round(((close - open_price) / open_price) * 100, 2),
                'lot_size': self.commodity_specs[commodity]['lot_size'],
                'tick_size': self.commodity_specs[commodity]['tick_size'],
                'margin': self.commodity_specs[commodity]['margin'],
                'currency': 'INR'
            }
            
            logger.debug(f"Live price for {commodity}: ₹{close:,.2f}")
            return price_data
            
        except Exception as e:
            logger.error(f"Error fetching live price for {commodity}: {e}")
            return {}
    
    def get_historical_data(self, commodity: str, timeframe: str = '1h', bars: int = 100) -> pd.DataFrame:
        """
        Get historical data for a commodity.
        
        Args:
            commodity: Commodity symbol (GOLD, SILVER)
            timeframe: Timeframe (1h, 4h, 1d)
            bars: Number of bars to fetch
            
        Returns:
            DataFrame with OHLCV data
        """
        try:
            # In production, this would fetch from real data source
            # For demo, we'll generate realistic historical data
            
            current_time = datetime.now()
            
            # Calculate time intervals
            if timeframe == '1h':
                interval = timedelta(hours=1)
            elif timeframe == '4h':
                interval = timedelta(hours=4)
            elif timeframe == '1d':
                interval = timedelta(days=1)
            else:
                interval = timedelta(hours=1)
            
            # Generate historical data
            data = []
            base_price = self.base_prices.get(commodity, 65000.0)
            
            for i in range(bars):
                timestamp = current_time - (bars - i - 1) * interval
                
                # Generate realistic OHLC data
                if i == 0:
                    price = base_price
                else:
                    # Price follows random walk with trend
                    price_change = np.random.normal(0, 50 if commodity == 'GOLD' else 100)
                    price = data[-1]['close'] + price_change
                
                # Generate OHLC from close price
                close = price
                high = close + np.random.uniform(10, 100)
                low = close - np.random.uniform(10, 100)
                open_price = low + np.random.uniform(0, high - low)
                
                # Generate volume
                volume = np.random.randint(1000, 5000)
                
                data.append({
                    'timestamp': timestamp,
                    'open': round(open_price, 2),
                    'high': round(high, 2),
                    'low': round(low, 2),
                    'close': round(close, 2),
                    'volume': volume
                })
            
            df = pd.DataFrame(data)
            df.set_index('timestamp', inplace=True)
            
            logger.debug(f"Generated {len(df)} historical bars for {commodity} {timeframe}")
            return df
            
        except Exception as e:
            logger.error(f"Error fetching historical data for {commodity}: {e}")
            return pd.DataFrame()
    
    def calculate_position_value(self, commodity: str, quantity: int, price: float) -> Dict[str, float]:
        """
        Calculate position value and margin requirements.
        
        Args:
            commodity: Commodity symbol
            quantity: Number of lots
            price: Current price
            
        Returns:
            Dictionary with position calculations
        """
        try:
            specs = self.commodity_specs.get(commodity, {})
            if not specs:
                return {}
            
            lot_size = specs['lot_size']
            margin_rate = specs['margin']
            
            # Calculate position value
            position_value = quantity * lot_size * price
            
            # Calculate margin required
            margin_required = position_value * margin_rate
            
            # Calculate tick value (minimum price movement value)
            tick_size = specs['tick_size']
            tick_value = quantity * lot_size * tick_size
            
            return {
                'commodity': commodity,
                'quantity': quantity,
                'lot_size': lot_size,
                'price': price,
                'position_value': position_value,
                'margin_required': margin_required,
                'tick_value': tick_value,
                'currency': 'INR'
            }
            
        except Exception as e:
            logger.error(f"Error calculating position value: {e}")
            return {}
    
    def get_market_status(self) -> Dict[str, any]:
        """Get current market status."""
        current_time = datetime.now()
        
        # MCX trading hours (approximate)
        # Normal trading: 9:00 AM - 11:30 PM (Monday to Friday)
        # Extended hours: 9:00 AM - 11:55 PM (Monday to Friday)
        
        hour = current_time.hour
        minute = current_time.minute
        weekday = current_time.weekday()  # 0 = Monday, 6 = Sunday
        
        # Check if market is open
        is_weekday = weekday < 5  # Monday to Friday
        is_trading_hours = (9 <= hour < 23) or (hour == 23 and minute <= 55)
        
        market_open = is_weekday and is_trading_hours
        
        # Determine session
        if hour < 10:
            session = "PRE_OPEN"
        elif hour < 11:
            session = "OPENING"
        elif hour < 15:
            session = "MORNING"
        elif hour < 18:
            session = "AFTERNOON"
        elif hour < 23:
            session = "EVENING"
        else:
            session = "CLOSING"
        
        return {
            'market_open': market_open,
            'session': session,
            'current_time': current_time.isoformat(),
            'next_open': self._get_next_open_time(current_time),
            'next_close': self._get_next_close_time(current_time)
        }
    
    def _get_next_open_time(self, current_time: datetime) -> str:
        """Get next market open time."""
        if current_time.weekday() < 5:  # Weekday
            if current_time.hour < 9:
                next_open = current_time.replace(hour=9, minute=0, second=0, microsecond=0)
            else:
                next_open = current_time + timedelta(days=1)
                next_open = next_open.replace(hour=9, minute=0, second=0, microsecond=0)
        else:  # Weekend
            days_until_monday = 7 - current_time.weekday()
            next_open = current_time + timedelta(days=days_until_monday)
            next_open = next_open.replace(hour=9, minute=0, second=0, microsecond=0)
        
        return next_open.isoformat()
    
    def _get_next_close_time(self, current_time: datetime) -> str:
        """Get next market close time."""
        if current_time.weekday() < 5 and current_time.hour < 23:  # Weekday and before close
            next_close = current_time.replace(hour=23, minute=55, second=0, microsecond=0)
        else:  # Weekend or after close
            days_until_monday = 7 - current_time.weekday()
            next_close = current_time + timedelta(days=days_until_monday)
            next_close = next_close.replace(hour=23, minute=55, second=0, microsecond=0)
        
        return next_close.isoformat()

def main():
    """Test MCX data fetcher."""
    logger.info("Testing MCX Data Fetcher")
    
    fetcher = MCXDataFetcher()
    
    # Test live prices
    for commodity in ['GOLD', 'SILVER']:
        price_data = fetcher.get_live_price(commodity)
        logger.info(f"{commodity} Live Price: ₹{price_data.get('close', 0):,.2f}")
        
        # Test position calculation
        position = fetcher.calculate_position_value(commodity, 1, price_data.get('close', 0))
        logger.info(f"1 Lot Position Value: ₹{position.get('position_value', 0):,.2f}")
        logger.info(f"Margin Required: ₹{position.get('margin_required', 0):,.2f}")
    
    # Test market status
    market_status = fetcher.get_market_status()
    logger.info(f"Market Status: {'OPEN' if market_status['market_open'] else 'CLOSED'}")
    logger.info(f"Current Session: {market_status['session']}")

if __name__ == "__main__":
    main()
