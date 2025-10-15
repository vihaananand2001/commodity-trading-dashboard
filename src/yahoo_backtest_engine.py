#!/usr/bin/env python3
"""
Yahoo Finance Backtest Engine
Performs backtests using live Yahoo Finance data instead of downloaded historical data
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple, Optional
import yaml
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

from src.yahoo_finance_fetcher import YahooFinanceFetcher
from src.backtest_engine import BacktestEngine, Trade
from src.utils import get_logger

logger = get_logger(__name__)

class YahooBacktestEngine:
    """
    Backtest engine that uses Yahoo Finance data for live backtesting
    """
    
    def __init__(self):
        self.yahoo_fetcher = YahooFinanceFetcher()
        
    def get_yahoo_data_with_features(self, commodity: str, timeframe: str, 
                                   period: str = '1y') -> pd.DataFrame:
        """
        Get Yahoo Finance data and calculate basic technical indicators
        """
        try:
            # Map timeframe to interval
            interval_map = {
                '1h': '1h',
                '4h': '1h',  # We'll resample 1h data to 4h
                '1d': '1d'
            }
            
            interval = interval_map.get(timeframe, '1d')
            
            # Get data from Yahoo Finance
            df = self.yahoo_fetcher.get_historical_data(commodity, period, interval)
            
            if df.empty:
                logger.warning(f"No Yahoo Finance data available for {commodity} {timeframe}")
                return pd.DataFrame()
            
            # Ensure datetime index
            df.index = pd.to_datetime(df.index)
            df = df.sort_index()
            
            # Rename columns to lowercase for consistency
            df.columns = df.columns.str.lower()
            
            # Resample to 4h if needed
            if timeframe == '4h' and interval == '1h':
                df = df.resample('4H').agg({
                    'open': 'first',
                    'high': 'max',
                    'low': 'min',
                    'close': 'last',
                    'volume': 'sum'
                }).dropna()
            
            # Calculate basic technical indicators
            df = self._calculate_technical_indicators(df)
            
            # Calculate simple pattern detection
            df = self._calculate_simple_patterns(df)
            
            logger.info(f"Yahoo Finance data for {commodity} {timeframe}: {len(df)} records from {df.index[0]} to {df.index[-1]}")
            return df
            
        except Exception as e:
            logger.error(f"Error getting Yahoo Finance data: {e}")
            return pd.DataFrame()
    
    def _calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate basic technical indicators for Yahoo Finance data."""
        try:
            # Simple Moving Averages
            df['sma_20'] = df['close'].rolling(window=20).mean()
            df['sma_50'] = df['close'].rolling(window=50).mean()
            
            # Exponential Moving Averages
            df['ema_20'] = df['close'].ewm(span=20).mean()
            df['ema_50'] = df['close'].ewm(span=50).mean()
            
            # RSI
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df['rsi_14'] = 100 - (100 / (1 + rs))
            
            # ATR
            high_low = df['high'] - df['low']
            high_close = np.abs(df['high'] - df['close'].shift())
            low_close = np.abs(df['low'] - df['close'].shift())
            ranges = pd.concat([high_low, high_close, low_close], axis=1)
            true_range = ranges.max(axis=1)
            df['atr'] = true_range.rolling(window=14).mean()
            df['atr_pct'] = (df['atr'] / df['close']) * 100
            
            # ADX (simplified)
            df['adx_14'] = 20  # Placeholder - would need more complex calculation
            
            # Volume indicators
            df['volume_sma'] = df['volume'].rolling(window=20).mean()
            df['volume_ratio'] = df['volume'] / df['volume_sma']
            
            return df
            
        except Exception as e:
            logger.error(f"Error calculating technical indicators: {e}")
            return df
    
    def _calculate_simple_patterns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate simple pattern detection for Yahoo Finance data."""
        try:
            # Doji pattern
            df['pattern_doji'] = ((abs(df['open'] - df['close']) / (df['high'] - df['low'])) < 0.1).astype(int)
            
            # Hammer pattern (simplified)
            body = abs(df['close'] - df['open'])
            lower_shadow = df[['open', 'close']].min(axis=1) - df['low']
            upper_shadow = df['high'] - df[['open', 'close']].max(axis=1)
            
            df['pattern_hammer'] = (
                (lower_shadow > 2 * body) & 
                (upper_shadow < body) & 
                (df['close'] > df['open'])
            ).astype(int)
            
            # Breakout patterns (simplified)
            df['high_20'] = df['high'].rolling(window=20).max()
            df['low_20'] = df['low'].rolling(window=20).min()
            
            df['pattern_breakout_10'] = (df['close'] > df['high'].shift(1) * 1.001).astype(int)
            df['pattern_breakout_20'] = (df['close'] > df['high_20'].shift(1)).astype(int)
            
            # Range expansion (simplified)
            df['range'] = df['high'] - df['low']
            df['range_sma'] = df['range'].rolling(window=10).mean()
            df['pattern_range_expansion'] = (df['range'] > df['range_sma'] * 1.5).astype(int)
            
            # Inside bar
            df['inside_bar'] = (
                (df['high'] < df['high'].shift(1)) & 
                (df['low'] > df['low'].shift(1))
            ).astype(int)
            df['pattern_inside_bar'] = df['inside_bar']
            
            return df
            
        except Exception as e:
            logger.error(f"Error calculating patterns: {e}")
            return df
    
    def load_trading_rules(self, commodity: str, timeframe: str) -> Dict[str, Any]:
        """Load trading rules from YAML files."""
        try:
            rules_file = Path(f"models/{commodity}_{timeframe}_long_rules.yaml")
            
            if not rules_file.exists():
                logger.warning(f"Trading rules not found: {rules_file}")
                return {}
            
            with open(rules_file, 'r') as f:
                rules = yaml.safe_load(f)
            
            logger.info(f"Loaded trading rules for {commodity} {timeframe}")
            return rules
            
        except Exception as e:
            logger.error(f"Error loading trading rules for {commodity} {timeframe}: {e}")
            return {}
    
    def run_yahoo_backtest(self, commodity: str, timeframe: str, 
                          period: str = '1y') -> Dict[str, Any]:
        """
        Run backtest using Yahoo Finance data
        """
        try:
            logger.info(f"Starting Yahoo Finance backtest for {commodity} {timeframe} ({period})")
            
            # Get Yahoo Finance data with features
            df = self.get_yahoo_data_with_features(commodity, timeframe, period)
            
            if df.empty:
                return {
                    'error': f'No Yahoo Finance data available for {commodity} {timeframe}',
                    'trades': [],
                    'performance': {}
                }
            
            # Load trading rules
            rules = self.load_trading_rules(commodity, timeframe)
            
            if not rules:
                return {
                    'error': f'No trading rules found for {commodity} {timeframe}',
                    'trades': [],
                    'performance': {}
                }
            
            # Extract strategies from rules
            strategies = []
            for key, value in rules.items():
                if key.startswith('strategy_') and key != 'strategy_metadata':
                    strategies.append(value)
            
            all_trades = []
            
            for strategy in strategies:
                try:
                    # Run backtest for this strategy
                    strategy_trades = self._run_strategy_backtest(df, strategy, commodity, timeframe)
                    all_trades.extend(strategy_trades)
                    
                except Exception as e:
                    logger.error(f"Error running backtest for strategy {strategy.get('name', 'Unknown')}: {e}")
                    continue
            
            # Calculate performance metrics
            performance = self._calculate_performance_metrics(all_trades, df)
            
            # Sort trades by entry time
            all_trades.sort(key=lambda x: x.entry_time)
            
            logger.info(f"Yahoo Finance backtest completed: {len(all_trades)} trades, {performance.get('win_rate', 0):.1f}% win rate")
            
            return {
                'commodity': commodity,
                'timeframe': timeframe,
                'period': period,
                'data_source': 'Yahoo Finance',
                'data_points': len(df),
                'date_range': f"{df.index[0].strftime('%Y-%m-%d')} to {df.index[-1].strftime('%Y-%m-%d')}",
                'trades': all_trades,
                'performance': performance,
                'strategies_tested': len(strategies)
            }
            
        except Exception as e:
            logger.error(f"Error running Yahoo Finance backtest: {e}")
            return {
                'error': str(e),
                'trades': [],
                'performance': {}
            }
    
    def _run_strategy_backtest(self, df: pd.DataFrame, strategy: Dict, 
                              commodity: str, timeframe: str) -> List[Trade]:
        """Run backtest for a single strategy on Yahoo Finance data."""
        try:
            pattern_name = strategy['pattern']
            pattern_col = f"pattern_{pattern_name}"  # Yahoo Finance data already has pattern_ prefix
            
            if pattern_col not in df.columns:
                logger.warning(f"Pattern column {pattern_col} not found in Yahoo Finance data")
                return []
            
            # Get entry conditions
            filters = strategy['entry_conditions']['filters']
            exit_rules = strategy['exit_rules']
            
            # Create entry conditions (simplified for Yahoo Finance data)
            conditions = df[pattern_col] == 1
            
            # Apply basic filters
            if 'rsi_min' in filters and 'rsi_14' in df.columns:
                conditions &= df['rsi_14'] >= filters['rsi_min']
            if 'rsi_max' in filters and 'rsi_14' in df.columns:
                conditions &= df['rsi_14'] <= filters['rsi_max']
            
            # Apply trend filter if specified
            if 'trend_filter' in strategy['entry_conditions'] and strategy['entry_conditions']['trend_filter'] == 'uptrend':
                if 'ema_20' in df.columns and 'ema_50' in df.columns:
                    conditions &= df['ema_20'] > df['ema_50']
            
            # Find signal points
            signal_points = df[conditions]
            
            if signal_points.empty:
                logger.info(f"No signals found for strategy {strategy['name']}")
                return []
            
            trades = []
            
            for timestamp, row in signal_points.iterrows():
                try:
                    # Create trade object (using the correct Trade class structure)
                    trade = Trade(
                        entry_idx=df.index.get_loc(timestamp),
                        entry_time=timestamp,
                        entry_price=row['close'],
                        direction='long',
                        stop_loss=row['close'] * (1 - strategy['exit_rules'].get('stop_loss_pct', 2.0) / 100),
                        take_profit=row['close'] * (1 + strategy['exit_rules'].get('take_profit_pct', 4.0) / 100)
                    )
                    
                    # Simulate trade outcome
                    trade = self._simulate_trade_outcome(trade, df, exit_rules)
                    
                    if trade.exit_price is not None:  # Trade was closed
                        trades.append(trade)
                        
                except Exception as e:
                    logger.error(f"Error processing trade at {timestamp}: {e}")
                    continue
            
            logger.info(f"Strategy {strategy['name']}: {len(trades)} completed trades")
            return trades
            
        except Exception as e:
            logger.error(f"Error running strategy backtest: {e}")
            return []
    
    def _simulate_trade_outcome(self, trade: Trade, df: pd.DataFrame, 
                               exit_rules: Dict) -> Trade:
        """Simulate the outcome of a trade using Yahoo Finance data."""
        try:
            # Get exit parameters
            max_hold_bars = exit_rules.get('max_hold_bars', 10)
            entry_idx = trade.entry_idx
            entry_price = trade.entry_price
            stop_loss_price = trade.stop_loss
            take_profit_price = trade.take_profit
            
            # Simulate the trade forward
            for i in range(1, min(max_hold_bars + 1, len(df) - entry_idx)):
                current_idx = entry_idx + i
                if current_idx >= len(df):
                    break
                
                current_bar = df.iloc[current_idx]
                high = current_bar['high']
                low = current_bar['low']
                close = current_bar['close']
                
                # Check for stop loss hit
                if low <= stop_loss_price:
                    trade.exit_idx = current_idx
                    trade.exit_time = df.index[current_idx]
                    trade.exit_price = stop_loss_price
                    trade.pnl = stop_loss_price - entry_price
                    trade.pnl_pct = (trade.pnl / entry_price) * 100
                    trade.bars_held = i
                    trade.exit_reason = 'Stop Loss'
                    break
                
                # Check for take profit hit
                if high >= take_profit_price:
                    trade.exit_idx = current_idx
                    trade.exit_time = df.index[current_idx]
                    trade.exit_price = take_profit_price
                    trade.pnl = take_profit_price - entry_price
                    trade.pnl_pct = (trade.pnl / entry_price) * 100
                    trade.bars_held = i
                    trade.exit_reason = 'Take Profit'
                    break
            
            # If max hold bars reached, exit at close
            if trade.exit_price is None:
                final_idx = entry_idx + max_hold_bars
                if final_idx < len(df):
                    trade.exit_idx = final_idx
                    trade.exit_time = df.index[final_idx]
                    trade.exit_price = df.iloc[final_idx]['close']
                    trade.pnl = trade.exit_price - entry_price
                    trade.pnl_pct = (trade.pnl / entry_price) * 100
                    trade.bars_held = max_hold_bars
                    trade.exit_reason = 'Time Exit'
            
            return trade
            
        except Exception as e:
            logger.error(f"Error simulating trade outcome: {e}")
            return trade
    
    def _calculate_performance_metrics(self, trades: List[Trade], df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate performance metrics for Yahoo Finance backtest."""
        try:
            if not trades:
                return {
                    'total_trades': 0,
                    'winning_trades': 0,
                    'losing_trades': 0,
                    'win_rate': 0,
                    'total_pnl': 0,
                    'avg_pnl': 0,
                    'profit_factor': 0,
                    'max_drawdown_pct': 0,
                    'sharpe_ratio': 0
                }
            
            total_trades = len(trades)
            winning_trades = len([t for t in trades if t.pnl > 0])
            losing_trades = len([t for t in trades if t.pnl < 0])
            
            total_pnl = sum([t.pnl for t in trades])
            avg_pnl = total_pnl / total_trades if total_trades > 0 else 0
            
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            
            # Profit factor
            gross_profit = sum([t.pnl for t in trades if t.pnl > 0])
            gross_loss = abs(sum([t.pnl for t in trades if t.pnl < 0]))
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf') if gross_profit > 0 else 0
            
            # Calculate cumulative PnL for drawdown
            cumulative_pnl = np.cumsum([t.pnl for t in trades])
            running_max = np.maximum.accumulate(cumulative_pnl)
            drawdown = running_max - cumulative_pnl
            max_drawdown = np.max(drawdown) if len(drawdown) > 0 else 0
            max_drawdown_pct = (max_drawdown / np.max(running_max) * 100) if np.max(running_max) > 0 else 0
            
            # Sharpe ratio (simplified)
            returns = [t.pnl_pct for t in trades if t.pnl_pct is not None]
            sharpe_ratio = np.mean(returns) / np.std(returns) if len(returns) > 1 and np.std(returns) > 0 else 0
            
            return {
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'win_rate': win_rate,
                'total_pnl': total_pnl,
                'avg_pnl': avg_pnl,
                'profit_factor': profit_factor,
                'max_drawdown_pct': max_drawdown_pct,
                'sharpe_ratio': sharpe_ratio
            }
            
        except Exception as e:
            logger.error(f"Error calculating performance metrics: {e}")
            return {}

if __name__ == "__main__":
    # Test the Yahoo Finance backtest engine
    engine = YahooBacktestEngine()
    
    print("🚀 Testing Yahoo Finance Backtest Engine")
    print("=" * 50)
    
    # Test Gold 1D
    print("\n📊 Testing Gold 1D (1 year):")
    result = engine.run_yahoo_backtest('GOLD', '1d', '1y')
    
    if 'error' in result:
        print(f"❌ Error: {result['error']}")
    else:
        print(f"✅ Data Points: {result['data_points']}")
        print(f"✅ Date Range: {result['date_range']}")
        print(f"✅ Total Trades: {result['performance']['total_trades']}")
        print(f"✅ Win Rate: {result['performance']['win_rate']:.1f}%")
        print(f"✅ Total PnL: ₹{result['performance']['total_pnl']:,.2f}")
        print(f"✅ Profit Factor: {result['performance']['profit_factor']:.2f}")
    
    # Test Silver 1D
    print("\n📊 Testing Silver 1D (1 year):")
    result = engine.run_yahoo_backtest('SILVER', '1d', '1y')
    
    if 'error' in result:
        print(f"❌ Error: {result['error']}")
    else:
        print(f"✅ Data Points: {result['data_points']}")
        print(f"✅ Date Range: {result['date_range']}")
        print(f"✅ Total Trades: {result['performance']['total_trades']}")
        print(f"✅ Win Rate: {result['performance']['win_rate']:.1f}%")
        print(f"✅ Total PnL: ₹{result['performance']['total_pnl']:,.2f}")
        print(f"✅ Profit Factor: {result['performance']['profit_factor']:.2f}")
