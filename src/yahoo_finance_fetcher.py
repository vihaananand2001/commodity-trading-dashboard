#!/usr/bin/env python3
"""
Yahoo Finance Data Fetcher for Gold and Silver
Fetches real-time commodity data from Yahoo Finance
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils import get_logger

logger = get_logger(__name__)

class YahooFinanceFetcher:
    """
    Fetches live Gold and Silver data from Yahoo Finance
    """
    
    def __init__(self):
        self.session = requests.Session()
        
        # Retry strategy for robust API calls
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Yahoo Finance ticker symbols for commodities
        self.ticker_symbols = {
            'GOLD': {
                'yahoo_symbol': 'GC=F',  # Gold Futures
                'name': 'Gold Futures',
                'currency': 'USD',
                'unit': 'per troy ounce',
                'mcx_contract': {
                    'symbol': 'GOLD',
                    'name': 'GOLD',
                    'contract_size': '1 kg',
                    'lot_size': 1000,
                    'tick_size': 1.0,
                    'margin': 0.05,
                    'expiry': '2025-12-05'
                }
            },
            'SILVER': {
                'yahoo_symbol': 'SI=F',  # Silver Futures  
                'name': 'Silver Futures',
                'currency': 'USD',
                'unit': 'per troy ounce',
                'mcx_contract': {
                    'symbol': 'SILVER',
                    'name': 'SILVER',
                    'contract_size': '30 kg',
                    'lot_size': 30000,
                    'tick_size': 1.0,
                    'margin': 0.05,
                    'expiry': '2025-12-05'
                }
            },
            'GOLD_INDIA': {
                'yahoo_symbol': 'GOLDINR=X',  # Gold in INR
                'name': 'Gold INR',
                'currency': 'INR',
                'unit': 'per 10 grams',
                'mcx_contract': {
                    'symbol': 'GOLDINR',
                    'name': 'GOLD INR',
                    'contract_size': '10 grams',
                    'lot_size': 10,
                    'tick_size': 1.0,
                    'margin': 0.05,
                    'expiry': '2025-12-05'
                }
            }
        }
        
        # USD to INR conversion rate (we'll fetch this live)
        self.usd_to_inr_rate = 83.0  # Default rate, will be updated
        
    def get_usd_inr_rate(self) -> float:
        """Get current USD to INR exchange rate from Yahoo Finance"""
        try:
            ticker = yf.Ticker("USDINR=X")
            data = ticker.history(period="1d")
            if not data.empty:
                self.usd_to_inr_rate = float(data['Close'].iloc[-1])
                logger.info(f"USD/INR rate updated: {self.usd_to_inr_rate}")
            return self.usd_to_inr_rate
        except Exception as e:
            logger.warning(f"Could not fetch USD/INR rate: {e}. Using default: {self.usd_to_inr_rate}")
            return self.usd_to_inr_rate
    
    def get_live_price(self, commodity: str) -> Dict[str, Any]:
        """
        Get live price data for a commodity from Yahoo Finance
        
        Args:
            commodity: Commodity symbol (GOLD, SILVER, GOLD_INDIA)
            
        Returns:
            Dictionary with live price data
        """
        try:
            if commodity not in self.ticker_symbols:
                raise ValueError(f"Unknown commodity: {commodity}")
            
            symbol_info = self.ticker_symbols[commodity]
            ticker = yf.Ticker(symbol_info['yahoo_symbol'])
            
            # Get the latest data
            data = ticker.history(period="2d")  # Get 2 days to ensure we have recent data
            
            if data.empty:
                raise ValueError(f"No data available for {symbol_info['yahoo_symbol']}")
            
            # Get the most recent data
            latest_data = data.iloc[-1]
            prev_data = data.iloc[-2] if len(data) > 1 else latest_data
            
            # Calculate price in INR if needed
            current_price = float(latest_data['Close'])
            if symbol_info['currency'] == 'USD' and commodity != 'GOLD_INDIA':
                # Convert USD to INR for Gold and Silver futures
                usd_inr_rate = self.get_usd_inr_rate()
                current_price = current_price * usd_inr_rate
                
                # Convert from per troy ounce to per 10 grams for Gold, per kg for Silver
                if commodity == 'GOLD':
                    # 1 troy ounce = 31.1035 grams, so 10 grams = 0.3215 troy ounces
                    current_price = current_price * 0.3215
                elif commodity == 'SILVER':
                    # 1 troy ounce = 31.1035 grams, so 1 kg = 32.1507 troy ounces  
                    current_price = current_price * 32.1507
            
            # Calculate change
            prev_price = float(prev_data['Close'])
            if symbol_info['currency'] == 'USD' and commodity != 'GOLD_INDIA':
                usd_inr_rate = self.get_usd_inr_rate()
                prev_price = prev_price * usd_inr_rate
                if commodity == 'GOLD':
                    prev_price = prev_price * 0.3215
                elif commodity == 'SILVER':
                    prev_price = prev_price * 32.1507
            
            price_change = current_price - prev_price
            change_percent = (price_change / prev_price) * 100 if prev_price != 0 else 0
            
            # Get volume
            volume = int(latest_data['Volume']) if not pd.isna(latest_data['Volume']) else 0
            
            # Get MCX contract details
            mcx_contract = symbol_info['mcx_contract']
            
            # Create response data
            price_data = {
                'symbol': mcx_contract['symbol'],
                'name': mcx_contract['name'],
                'source': 'Yahoo Finance',
                'currency': 'INR',
                'timestamp': datetime.now().isoformat(),
                'open': round(float(latest_data['Open']), 2),
                'high': round(float(latest_data['High']), 2), 
                'low': round(float(latest_data['Low']), 2),
                'close': round(current_price, 2),
                'volume': volume,
                'change': round(price_change, 2),
                'change_pct': round(change_percent, 2),
                'unit': 'grams',
                'yahoo_symbol': symbol_info['yahoo_symbol'],
                # MCX contract details
                'contract_size': mcx_contract['contract_size'],
                'lot_size': mcx_contract['lot_size'],
                'tick_size': mcx_contract['tick_size'],
                'margin': mcx_contract['margin'],
                'expiry': mcx_contract['expiry']
            }
            
            logger.info(f"Fetched {commodity} price from Yahoo Finance: ₹{current_price:,.2f}")
            return price_data
            
        except Exception as e:
            logger.error(f"Error fetching {commodity} price from Yahoo Finance: {e}")
            return {}
    
    def get_historical_data(self, commodity: str, period: str = "1mo", interval: str = "1d") -> pd.DataFrame:
        """
        Get historical data for a commodity
        
        Args:
            commodity: Commodity symbol
            period: Data period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
            interval: Data interval (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)
            
        Returns:
            DataFrame with historical data
        """
        try:
            if commodity not in self.ticker_symbols:
                raise ValueError(f"Unknown commodity: {commodity}")
            
            symbol_info = self.ticker_symbols[commodity]
            ticker = yf.Ticker(symbol_info['yahoo_symbol'])
            
            data = ticker.history(period=period, interval=interval)
            
            if data.empty:
                logger.warning(f"No historical data available for {symbol_info['yahoo_symbol']}")
                return pd.DataFrame()
            
            # Convert USD to INR if needed
            if symbol_info['currency'] == 'USD' and commodity != 'GOLD_INDIA':
                usd_inr_rate = self.get_usd_inr_rate()
                
                for col in ['Open', 'High', 'Low', 'Close']:
                    data[col] = data[col] * usd_inr_rate
                    
                    # Convert units
                    if commodity == 'GOLD':
                        data[col] = data[col] * 0.3215  # per 10 grams
                    elif commodity == 'SILVER':
                        data[col] = data[col] * 32.1507  # per kg
            
            logger.info(f"Fetched {len(data)} historical records for {commodity}")
            return data
            
        except Exception as e:
            logger.error(f"Error fetching historical data for {commodity}: {e}")
            return pd.DataFrame()
    
    def get_multiple_prices(self, commodities: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Get live prices for multiple commodities
        
        Args:
            commodities: List of commodity symbols
            
        Returns:
            Dictionary with price data for each commodity
        """
        results = {}
        for commodity in commodities:
            try:
                results[commodity] = self.get_live_price(commodity)
                time.sleep(0.1)  # Small delay to avoid rate limiting
            except Exception as e:
                logger.error(f"Error fetching {commodity}: {e}")
                results[commodity] = {}
        
        return results
    
    def test_connection(self) -> bool:
        """
        Test if Yahoo Finance connection is working
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            # Test with Gold futures
            test_data = self.get_live_price('GOLD')
            return bool(test_data and 'close' in test_data)
        except Exception as e:
            logger.error(f"Yahoo Finance connection test failed: {e}")
            return False

if __name__ == "__main__":
    # Test the Yahoo Finance fetcher
    logger.info("Testing Yahoo Finance Data Fetcher...")
    
    fetcher = YahooFinanceFetcher()
    
    # Test connection
    if fetcher.test_connection():
        logger.info("✅ Yahoo Finance connection successful!")
        
        # Test Gold
        print("\n=== GOLD ===")
        gold_data = fetcher.get_live_price('GOLD')
        if gold_data:
            print(f"Symbol: {gold_data.get('symbol')}")
            print(f"Name: {gold_data.get('name')}")
            print(f"Price: ₹{gold_data.get('close'):,.2f}")
            print(f"Change: ₹{gold_data.get('change'):,.2f} ({gold_data.get('change_pct'):.2f}%)")
            print(f"Volume: {gold_data.get('volume'):,}")
        
        # Test Silver
        print("\n=== SILVER ===")
        silver_data = fetcher.get_live_price('SILVER')
        if silver_data:
            print(f"Symbol: {silver_data.get('symbol')}")
            print(f"Name: {silver_data.get('name')}")
            print(f"Price: ₹{silver_data.get('close'):,.2f}")
            print(f"Change: ₹{silver_data.get('change'):,.2f} ({silver_data.get('change_pct'):.2f}%)")
            print(f"Volume: {silver_data.get('volume'):,}")
        
        # Test Gold India
        print("\n=== GOLD INDIA ===")
        gold_india_data = fetcher.get_live_price('GOLD_INDIA')
        if gold_india_data:
            print(f"Symbol: {gold_india_data.get('symbol')}")
            print(f"Name: {gold_india_data.get('name')}")
            print(f"Price: ₹{gold_india_data.get('close'):,.2f}")
            print(f"Change: ₹{gold_india_data.get('change'):,.2f} ({gold_india_data.get('change_pct'):.2f}%)")
            
    else:
        logger.error("❌ Yahoo Finance connection failed!")
