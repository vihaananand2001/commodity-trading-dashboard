#!/usr/bin/env python3
"""
Test MCX fetcher in dashboard context
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Test the exact same import as dashboard
from src.mcx_data_fetcher import MCXDataFetcher

print("=== Testing MCX Fetcher in Dashboard Context ===")

# Create instance
fetcher = MCXDataFetcher()

print(f"Commodity specs: {fetcher.commodity_specs}")

# Test Gold
gold_data = fetcher.get_live_price('GOLD')
print(f"\nGold data keys: {list(gold_data.keys())}")
print(f"Gold symbol: {gold_data.get('symbol')}")
print(f"Gold name: {gold_data.get('name')}")
print(f"Gold lot_size: {gold_data.get('lot_size')}")
print(f"Gold contract_size: {gold_data.get('contract_size')}")

# Test Silver
silver_data = fetcher.get_live_price('SILVER')
print(f"\nSilver data keys: {list(silver_data.keys())}")
print(f"Silver symbol: {silver_data.get('symbol')}")
print(f"Silver name: {silver_data.get('name')}")
print(f"Silver lot_size: {silver_data.get('lot_size')}")
print(f"Silver contract_size: {silver_data.get('contract_size')}")

print("\n=== Test Complete ===")
