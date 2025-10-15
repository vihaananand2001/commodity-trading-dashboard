#!/usr/bin/env python3
"""
Test Flask import exactly as dashboard does
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import exactly as dashboard does
from src.mcx_data_fetcher import MCXDataFetcher

print("=== Testing Flask Import ===")

# Test 1: Check the module location
import inspect
print(f"MCX fetcher module location: {inspect.getfile(MCXDataFetcher)}")

# Test 2: Create instance and check specs
fetcher = MCXDataFetcher()
print(f"\nGOLD specs from fetcher.commodity_specs:")
print(fetcher.commodity_specs['GOLD'])

# Test 3: Get live price
data = fetcher.get_live_price('GOLD')
print(f"\nLive price data:")
print(f"  Symbol: {data.get('symbol')}")
print(f"  Name: {data.get('name')}")
print(f"  Lot Size: {data.get('lot_size')}")
print(f"  Contract: {data.get('contract_size')}")

print("\n=== Test Complete ===")

