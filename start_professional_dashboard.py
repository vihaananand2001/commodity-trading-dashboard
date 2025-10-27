#!/usr/bin/env python3
"""
Start Professional Trading Dashboard
Professional JP Morgan-style dashboard with market overview and live signals
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from professional_dashboard import app, logger

if __name__ == '__main__':
    logger.info("Starting Professional Trading Dashboard...")
    logger.info("Dashboard will be available at: http://localhost:5001")
    logger.info("Features:")
    logger.info("- Professional homepage with market overview")
    logger.info("- Live USD/INR, Gold, Silver, Copper prices")
    logger.info("- Market sentiment analysis")
    logger.info("- Trading signals across all commodities")
    logger.info("- Individual commodity analysis pages")
    logger.info("- Professional styling without emojis")
    
    # Run Flask app
    app.run(debug=True, host='0.0.0.0', port=5001)

