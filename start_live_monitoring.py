#!/usr/bin/env python3
"""
Start Live Pattern Monitoring
Simple script to start continuous live pattern monitoring
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.live_pattern_monitor import LivePatternMonitor
from src.utils import get_logger

logger = get_logger(__name__)

def main():
    print("🚀 Starting Live Pattern Monitoring")
    print("=" * 50)
    print("This will continuously monitor Yahoo Finance data for trading patterns")
    print("and generate real-time trading signals based on your optimized strategies.")
    print("=" * 50)
    
    # Create monitor with 10-minute update interval (more frequent for demo)
    monitor = LivePatternMonitor(update_interval_minutes=10)
    
    try:
        # Start monitoring
        monitor.start_monitoring()
        
        print("✅ Live monitoring started!")
        print("📊 Monitoring:")
        print("   • GOLD: 1D, 4H, 1H timeframes")
        print("   • SILVER: 1D, 4H, 1H timeframes")
        print("🔄 Update interval: 10 minutes")
        print("📁 Logs saved to: logs/live_monitoring/")
        print("\n🎯 Your trading strategies are now running continuously!")
        print("📈 Patterns and signals will be detected and logged automatically.")
        print("\nPress Ctrl+C to stop monitoring...")
        
        # Keep running and show periodic updates
        import time
        from datetime import datetime
        
        while True:
            time.sleep(300)  # Check every 5 minutes
            
            # Show recent activity
            recent_signals = monitor.get_recent_signals(hours=1)
            if recent_signals:
                print(f"\n🚨 {len(recent_signals)} new signals in the last hour:")
                for signal in recent_signals[-3:]:  # Show last 3 signals
                    print(f"   • {signal['strategy_name']} - {signal['pattern']} "
                          f"at ₹{signal['entry_price']:,.2f}")
    
    except KeyboardInterrupt:
        print("\n🛑 Stopping live monitoring...")
        monitor.stop_monitoring()
        print("✅ Live monitoring stopped.")
    
    except Exception as e:
        logger.error(f"Error in live monitoring: {e}")
        print(f"❌ Error: {e}")
        monitor.stop_monitoring()

if __name__ == "__main__":
    main()
