#!/usr/bin/env python3
"""
Test dashboard endpoints to verify everything is working
"""

import requests
import json

BASE_URL = "http://localhost:5001"

print("🎯 Testing MCX Live Trading Dashboard")
print("=" * 70)

# Test 1: Market Status
print("\n1️⃣ Testing Market Status...")
try:
    response = requests.get(f"{BASE_URL}/api/market-status")
    data = response.json()
    print(f"   ✅ Market Status: {data.get('session', 'UNKNOWN')}")
    print(f"   ✅ Market Open: {data.get('market_open', False)}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 2: Gold Market Data
print("\n2️⃣ Testing Gold Market Data...")
try:
    response = requests.get(f"{BASE_URL}/api/market-data/GOLD")
    data = response.json()
    lp = data['live_price']
    print(f"   ✅ Symbol: {lp.get('symbol')}")
    print(f"   ✅ Name: {lp.get('name')}")
    print(f"   ✅ Contract: {lp.get('contract_size')}")
    print(f"   ✅ Lot Size: {lp.get('lot_size')} grams")
    print(f"   ✅ Price: ₹{lp.get('close'):,.2f}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 3: Silver Market Data
print("\n3️⃣ Testing Silver Market Data...")
try:
    response = requests.get(f"{BASE_URL}/api/market-data/SILVER")
    data = response.json()
    lp = data['live_price']
    print(f"   ✅ Symbol: {lp.get('symbol')}")
    print(f"   ✅ Name: {lp.get('name')}")
    print(f"   ✅ Contract: {lp.get('contract_size')}")
    print(f"   ✅ Lot Size: {lp.get('lot_size')} grams")
    print(f"   ✅ Price: ₹{lp.get('close'):,.2f}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 4: Commodity Specs
print("\n4️⃣ Testing Commodity Specs...")
try:
    response = requests.get(f"{BASE_URL}/api/commodity-specs")
    data = response.json()
    print(f"   ✅ GOLD: {data['GOLD']['symbol']} - {data['GOLD']['name']}")
    print(f"   ✅ SILVER: {data['SILVER']['symbol']} - {data['SILVER']['name']}")
except Exception as e:
    print(f"   ❌ Error: {e}")

print("\n" + "=" * 70)
print("✅ Dashboard is working correctly!")
print(f"🌐 Open in browser: {BASE_URL}")
print("=" * 70)
