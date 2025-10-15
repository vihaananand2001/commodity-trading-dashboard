#!/usr/bin/env python3
"""
Minimal Flask test for MCX data
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, jsonify
from src.mcx_data_fetcher import MCXDataFetcher

app = Flask(__name__)

@app.route('/test-mcx')
def test_mcx():
    """Test MCX fetcher directly in Flask."""
    fetcher = MCXDataFetcher()
    data = fetcher.get_live_price('GOLD')
    return jsonify(data)

if __name__ == '__main__':
    print("Starting minimal Flask test...")
    print("Test URL: http://localhost:5002/test-mcx")
    app.run(debug=True, port=5002)
