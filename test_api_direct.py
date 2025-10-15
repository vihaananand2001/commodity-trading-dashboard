#!/usr/bin/env python3
"""
Test API endpoint directly
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the dashboard components
from src.mcx_data_fetcher import MCXDataFetcher
import json
from datetime import datetime

print("=== Testing API Endpoint Logic ===")

# Simulate the API endpoint logic
commodity = 'GOLD'
fresh_mcx_fetcher = MCXDataFetcher()
live_price = fresh_mcx_fetcher.get_live_price(commodity)

print(f"Fresh MCX fetcher commodity specs: {fresh_mcx_fetcher.commodity_specs.get(commodity, 'NOT FOUND')}")
print(f"Live price data keys: {list(live_price.keys())}")
print(f"Live price symbol: {live_price.get('symbol')}")
print(f"Live price name: {live_price.get('name')}")
print(f"Live price lot_size: {live_price.get('lot_size')}")
print(f"Live price contract_size: {live_price.get('contract_size')}")

# Create the response structure like the API
response_data = {
    'live_price': live_price,
    'historical_1h': [],  # Simplified for testing
    'historical_4h': [],  # Simplified for testing
    'last_update': datetime.now().isoformat()
}

print(f"\nResponse data live_price keys: {list(response_data['live_price'].keys())}")
print(f"Response symbol: {response_data['live_price'].get('symbol')}")
print(f"Response name: {response_data['live_price'].get('name')}")
print(f"Response lot_size: {response_data['live_price'].get('lot_size')}")

print("\n=== Test Complete ===")
