#!/usr/bin/env python3
"""
Live Pattern Monitor
Continuously monitors live Yahoo Finance data for trading patterns and signals
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import threading
from typing import Dict, List, Any
import json
from pathlib import Path

from src.yahoo_finance_fetcher import YahooFinanceFetcher
from src.yahoo_backtest_engine import YahooBacktestEngine
from src.utils import get_logger

logger = get_logger(__name__)

class LivePatternMonitor:
    """
    Continuously monitors live data for trading patterns and generates signals
    """
    
    def __init__(self, update_interval_minutes: int = 15):
        self.update_interval = update_interval_minutes * 60  # Convert to seconds
        self.yahoo_fetcher = YahooFinanceFetcher()
        self.backtest_engine = YahooBacktestEngine()
        self.running = False
        self.signals_log = []
        self.pattern_log = []
        
        # Create logs directory
        self.logs_dir = Path("logs/live_monitoring")
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Load existing signals if any
        self._load_existing_signals()
    
    def _load_existing_signals(self):
        """Load existing signals from log files."""
        try:
            signals_file = self.logs_dir / "live_signals.json"
            if signals_file.exists():
                with open(signals_file, 'r') as f:
                    self.signals_log = json.load(f)
                logger.info(f"Loaded {len(self.signals_log)} existing signals")
        except Exception as e:
            logger.error(f"Error loading existing signals: {e}")
    
    def _save_signals(self):
        """Save signals to log file."""
        try:
            signals_file = self.logs_dir / "live_signals.json"
            with open(signals_file, 'w') as f:
                json.dump(self.signals_log, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving signals: {e}")
    
    def _detect_live_patterns(self, commodity: str, timeframe: str) -> List[Dict]:
        """Detect patterns in the most recent data points."""
        try:
            # Get recent data (last 30 days for 1D, last 7 days for 4H, last 2 days for 1H)
            period_map = {'1d': '30d', '4h': '7d', '1h': '2d'}
            period = period_map.get(timeframe, '30d')
            
            # Get Yahoo Finance data with features
            df = self.backtest_engine.get_yahoo_data_with_features(commodity, timeframe, period)
            
            if df.empty:
                return []
            
            # Focus on the last few data points for live detection
            recent_data = df.tail(10)  # Last 10 bars
            
            detected_patterns = []
            
            # Check for patterns in the most recent bars
            for timestamp, row in recent_data.iterrows():
                patterns_found = []
                
                # Check each pattern column
                for col in df.columns:
                    if col.startswith('pattern_') and row[col] == 1:
                        pattern_name = col.replace('pattern_', '')
                        patterns_found.append(pattern_name)
                
                if patterns_found:
                    detected_patterns.append({
                        'timestamp': timestamp.isoformat(),
                        'commodity': commodity,
                        'timeframe': timeframe,
                        'patterns': patterns_found,
                        'price': float(row['close']),
                        'volume': float(row['volume']) if 'volume' in row else 0,
                        'rsi': float(row.get('rsi_14', 50)) if 'rsi_14' in row else 50,
                        'atr_pct': float(row.get('atr_pct', 1.0)) if 'atr_pct' in row else 1.0
                    })
            
            return detected_patterns
            
        except Exception as e:
            logger.error(f"Error detecting live patterns for {commodity} {timeframe}: {e}")
            return []
    
    def _check_trading_signals(self, commodity: str, timeframe: str) -> List[Dict]:
        """Check for trading signals based on detected patterns and trading rules."""
        try:
            # Load trading rules
            rules = self.backtest_engine.load_trading_rules(commodity, timeframe)
            
            if not rules:
                return []
            
            # Get recent data
            period_map = {'1d': '30d', '4h': '7d', '1h': '2d'}
            period = period_map.get(timeframe, '30d')
            df = self.backtest_engine.get_yahoo_data_with_features(commodity, timeframe, period)
            
            if df.empty:
                return []
            
            signals = []
            
            # Extract strategies from rules
            for key, strategy in rules.items():
                if key.startswith('strategy_') and key != 'strategy_metadata':
                    pattern_name = strategy['pattern']
                    pattern_col = f"pattern_{pattern_name}"
                    
                    if pattern_col not in df.columns:
                        continue
                    
                    # Check the most recent bar for this pattern
                    recent_data = df.tail(1)
                    if recent_data.empty:
                        continue
                    
                    row = recent_data.iloc[0]
                    timestamp = recent_data.index[0]
                    
                    # Check if pattern is detected
                    if row[pattern_col] == 1:
                        # Apply filters from strategy
                        filters = strategy['entry_conditions']['filters']
                        signal_valid = True
                        
                        # Apply basic filters
                        if 'rsi_min' in filters and 'rsi_14' in row:
                            if row['rsi_14'] < filters['rsi_min']:
                                signal_valid = False
                        
                        if 'rsi_max' in filters and 'rsi_14' in row:
                            if row['rsi_14'] > filters['rsi_max']:
                                signal_valid = False
                        
                        if signal_valid:
                            signal = {
                                'timestamp': timestamp.isoformat(),
                                'commodity': commodity,
                                'timeframe': timeframe,
                                'strategy_name': strategy['name'],
                                'pattern': pattern_name,
                                'entry_price': float(row['close']),
                                'direction': 'LONG',
                                'rsi': float(row.get('rsi_14', 50)) if 'rsi_14' in row else 50,
                                'atr_pct': float(row.get('atr_pct', 1.0)) if 'atr_pct' in row else 1.0,
                                'volume': float(row.get('volume', 0)) if 'volume' in row else 0,
                                'stop_loss_pct': strategy['exit_rules'].get('stop_loss_pct', 2.0),
                                'take_profit_pct': strategy['exit_rules'].get('take_profit_pct', 4.0),
                                'max_hold_bars': strategy['exit_rules'].get('max_hold_bars', 10),
                                'signal_id': f"{commodity}_{timeframe}_{pattern_name}_{int(timestamp.timestamp())}"
                            }
                            signals.append(signal)
            
            return signals
            
        except Exception as e:
            logger.error(f"Error checking trading signals for {commodity} {timeframe}: {e}")
            return []
    
    def _process_commodity_timeframe(self, commodity: str, timeframe: str):
        """Process one commodity-timeframe combination."""
        try:
            logger.info(f"Processing {commodity} {timeframe}...")
            
            # Detect patterns
            patterns = self._detect_live_patterns(commodity, timeframe)
            
            # Check for trading signals
            signals = self._check_trading_signals(commodity, timeframe)
            
            # Log new patterns
            for pattern in patterns:
                pattern['detected_at'] = datetime.now().isoformat()
                self.pattern_log.append(pattern)
                logger.info(f"🔍 Pattern detected: {pattern['patterns']} in {commodity} {timeframe} at ₹{pattern['price']:,.2f}")
            
            # Log new signals
            for signal in signals:
                # Check if this signal was already logged
                existing_signals = [s for s in self.signals_log if s.get('signal_id') == signal['signal_id']]
                if not existing_signals:
                    signal['detected_at'] = datetime.now().isoformat()
                    self.signals_log.append(signal)
                    
                    logger.info(f"🚨 TRADING SIGNAL: {signal['strategy_name']} - {signal['pattern']} "
                              f"in {commodity} {timeframe} at ₹{signal['entry_price']:,.2f}")
                    logger.info(f"   📊 Entry: ₹{signal['entry_price']:,.2f} | "
                              f"SL: {signal['stop_loss_pct']:.1f}% | "
                              f"TP: {signal['take_profit_pct']:.1f}% | "
                              f"RSI: {signal['rsi']:.1f}")
            
            # Save signals periodically
            if len(self.signals_log) % 10 == 0:  # Save every 10 new signals
                self._save_signals()
                
        except Exception as e:
            logger.error(f"Error processing {commodity} {timeframe}: {e}")
    
    def _monitoring_loop(self):
        """Main monitoring loop."""
        logger.info("🔄 Starting live pattern monitoring loop...")
        
        # Define commodities and timeframes to monitor
        monitoring_configs = [
            ('GOLD', '1d'),
            ('GOLD', '4h'), 
            ('GOLD', '1h'),
            ('SILVER', '1d'),
            ('SILVER', '4h'),
            ('SILVER', '1h')
        ]
        
        while self.running:
            try:
                start_time = datetime.now()
                
                # Process each commodity-timeframe combination
                for commodity, timeframe in monitoring_configs:
                    if not self.running:  # Check if we should stop
                        break
                    
                    self._process_commodity_timeframe(commodity, timeframe)
                    
                    # Small delay between processing different commodities
                    time.sleep(2)
                
                # Calculate processing time
                processing_time = (datetime.now() - start_time).total_seconds()
                logger.info(f"✅ Monitoring cycle completed in {processing_time:.1f}s. "
                          f"Next update in {self.update_interval/60:.1f} minutes.")
                
                # Save all signals
                self._save_signals()
                
                # Wait for next update
                time.sleep(self.update_interval)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(60)  # Wait 1 minute before retrying
    
    def start_monitoring(self):
        """Start the live monitoring in a separate thread."""
        if self.running:
            logger.warning("Monitoring is already running!")
            return
        
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
        
        logger.info(f"🚀 Live pattern monitoring started!")
        logger.info(f"   📊 Update interval: {self.update_interval/60:.1f} minutes")
        logger.info(f"   📁 Logs directory: {self.logs_dir}")
        logger.info(f"   🎯 Monitoring: GOLD & SILVER across 1D, 4H, 1H timeframes")
    
    def stop_monitoring(self):
        """Stop the live monitoring."""
        if not self.running:
            logger.warning("Monitoring is not running!")
            return
        
        self.running = False
        logger.info("🛑 Stopping live pattern monitoring...")
        
        # Save final signals
        self._save_signals()
        
        logger.info("✅ Live pattern monitoring stopped.")
    
    def get_recent_signals(self, hours: int = 24) -> List[Dict]:
        """Get signals from the last N hours."""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        cutoff_str = cutoff_time.isoformat()
        
        recent_signals = []
        for signal in self.signals_log:
            if signal.get('detected_at', '') > cutoff_str:
                recent_signals.append(signal)
        
        return recent_signals
    
    def get_pattern_summary(self) -> Dict[str, Any]:
        """Get a summary of detected patterns and signals."""
        total_patterns = len(self.pattern_log)
        total_signals = len(self.signals_log)
        
        # Count patterns by commodity
        pattern_counts = {}
        for pattern in self.pattern_log:
            commodity = pattern.get('commodity', 'Unknown')
            pattern_counts[commodity] = pattern_counts.get(commodity, 0) + 1
        
        # Count signals by strategy
        signal_counts = {}
        for signal in self.signals_log:
            strategy = signal.get('strategy_name', 'Unknown')
            signal_counts[strategy] = signal_counts.get(strategy, 0) + 1
        
        return {
            'total_patterns': total_patterns,
            'total_signals': total_signals,
            'pattern_counts_by_commodity': pattern_counts,
            'signal_counts_by_strategy': signal_counts,
            'monitoring_active': self.running,
            'last_update': datetime.now().isoformat()
        }

def main():
    """Main function to run live monitoring."""
    print("🚀 Live Pattern Monitor")
    print("=" * 50)
    
    # Create monitor with 15-minute update interval
    monitor = LivePatternMonitor(update_interval_minutes=15)
    
    try:
        # Start monitoring
        monitor.start_monitoring()
        
        print("✅ Live monitoring started!")
        print("📊 Monitoring GOLD & SILVER across 1D, 4H, 1H timeframes")
        print("🔄 Update interval: 15 minutes")
        print("📁 Logs saved to: logs/live_monitoring/")
        print("\nPress Ctrl+C to stop monitoring...")
        
        # Keep running until interrupted
        while True:
            time.sleep(60)  # Check every minute
            
            # Print summary every hour
            if datetime.now().minute == 0:
                summary = monitor.get_pattern_summary()
                print(f"\n📊 Hourly Summary ({datetime.now().strftime('%H:%M')}):")
                print(f"   Patterns detected: {summary['total_patterns']}")
                print(f"   Trading signals: {summary['total_signals']}")
                if summary['pattern_counts_by_commodity']:
                    for commodity, count in summary['pattern_counts_by_commodity'].items():
                        print(f"   {commodity} patterns: {count}")
    
    except KeyboardInterrupt:
        print("\n🛑 Stopping live monitoring...")
        monitor.stop_monitoring()
        print("✅ Live monitoring stopped.")
    
    except Exception as e:
        logger.error(f"Error in main monitoring loop: {e}")
        monitor.stop_monitoring()

if __name__ == "__main__":
    main()
