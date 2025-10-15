#!/usr/bin/env python3
"""
Startup script for MCX Live Trading Dashboard
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.utils import get_logger

logger = get_logger(__name__)

def main():
    """Start the dashboard with proper error handling."""
    try:
        logger.info("Starting MCX Live Trading Dashboard...")
        
        # Import and run dashboard
        from dashboard import app, initialize_traders, start_data_updater
        
        # Initialize traders and start data updater
        initialize_traders()
        start_data_updater()
        
        logger.info("Dashboard components initialized successfully")
        logger.info("Starting Flask application on http://localhost:5001")
        
        # Run Flask app
        app.run(debug=False, host='0.0.0.0', port=5001, use_reloader=False)
        
    except Exception as e:
        logger.error(f"Error starting dashboard: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
