#!/usr/bin/env python3
"""
Dashboard Data Service
Integrates historical data, trading rules, and signal generation for the dashboard
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple, Optional
import yaml
import warnings
warnings.filterwarnings('ignore')

from src.utils import get_logger, load_features
from src.backtest_engine import BacktestEngine
from src.strategy_builder import create_pattern_strategy
from src.simple_confidence_scorer import SimpleConfidenceScorer
from src.yahoo_finance_fetcher import YahooFinanceFetcher

logger = get_logger(__name__)

class DashboardDataService:
    """
    Comprehensive data service for the dashboard that integrates:
    - Historical data from CSV files
    - Trading rules from YAML files
    - Signal generation using optimized strategies
    - Trend analysis and technical indicators
    """
    
    def __init__(self):
        self.data_cache = {}
        self.strategy_cache = {}
        self.yahoo_fetcher = YahooFinanceFetcher()
        self.confidence_scorer = None
        
    def load_historical_data(self, commodity: str, timeframe: str) -> pd.DataFrame:
        """Load historical data with features from processed CSV files."""
        try:
            cache_key = f"{commodity}_{timeframe}"
            
            if cache_key in self.data_cache:
                return self.data_cache[cache_key]
            
            # Load features data
            df = load_features(commodity, timeframe)
            
            if df.empty:
                logger.warning(f"No data found for {commodity} {timeframe}")
                return pd.DataFrame()
            
            # Ensure datetime index
            if not isinstance(df.index, pd.DatetimeIndex):
                df.index = pd.to_datetime(df.index)
            
            # Sort by date
            df = df.sort_index()
            
            # Cache the data
            self.data_cache[cache_key] = df
            
            logger.info(f"Loaded {len(df)} records for {commodity} {timeframe}")
            return df
            
        except Exception as e:
            logger.error(f"Error loading historical data for {commodity} {timeframe}: {e}")
            return pd.DataFrame()
    
    def load_trading_rules(self, commodity: str, timeframe: str) -> Dict[str, Any]:
        """Load trading rules from YAML files."""
        try:
            cache_key = f"{commodity}_{timeframe}"
            
            if cache_key in self.strategy_cache:
                return self.strategy_cache[cache_key]
            
            rules_file = Path(f"models/{commodity}_{timeframe}_long_rules.yaml")
            
            if not rules_file.exists():
                logger.warning(f"Trading rules not found: {rules_file}")
                return {}
            
            with open(rules_file, 'r') as f:
                rules = yaml.safe_load(f)
            
            # Cache the rules
            self.strategy_cache[cache_key] = rules
            
            logger.info(f"Loaded trading rules for {commodity} {timeframe}")
            return rules
            
        except Exception as e:
            logger.error(f"Error loading trading rules for {commodity} {timeframe}: {e}")
            return {}
    
    def generate_trading_signals(self, commodity: str, timeframe: str, 
                               lookback_days: int = 30) -> List[Dict[str, Any]]:
        """Generate trading signals using optimized strategies."""
        try:
            # Load data and rules
            df = self.load_historical_data(commodity, timeframe)
            rules = self.load_trading_rules(commodity, timeframe)
            
            if df.empty or not rules:
                return []
            
            # Get recent data for signal generation
            recent_data = df.tail(lookback_days * self._get_bars_per_day(timeframe))
            
            signals = []
            
            # Extract strategies from rules
            strategies = []
            for key, value in rules.items():
                if key.startswith('strategy_') and key != 'strategy_metadata':
                    strategies.append(value)
            
            for strategy in strategies:
                try:
                    # Get pattern column name
                    pattern_name = strategy['pattern']
                    pattern_col = f"pattern_{pattern_name}"
                    
                    if pattern_col not in recent_data.columns:
                        logger.warning(f"Pattern column {pattern_col} not found in data")
                        continue
                    
                    # Apply filters to find signal points
                    filters = strategy['entry_conditions']['filters']
                    
                    # Create filter conditions
                    conditions = recent_data[pattern_col] == 1  # Pattern detected
                    
                    # Apply additional filters (more lenient for demo)
                    if 'rsi_min' in filters and 'rsi_14' in recent_data.columns:
                        # Relax RSI filter slightly
                        rsi_min = max(filters['rsi_min'] - 10, 20)
                        conditions &= recent_data['rsi_14'] >= rsi_min
                    if 'rsi_max' in filters and 'rsi_14' in recent_data.columns:
                        # Relax RSI filter slightly
                        rsi_max = min(filters['rsi_max'] + 10, 80)
                        conditions &= recent_data['rsi_14'] <= rsi_max
                    if 'adx_min' in filters and 'adx_14' in recent_data.columns:
                        # Relax ADX filter
                        adx_min = max(filters['adx_min'] - 5, 10)
                        conditions &= recent_data['adx_14'] >= adx_min
                    if 'atr_pct_min' in filters and 'atr_pct' in recent_data.columns:
                        # Relax ATR filter
                        atr_min = max(filters['atr_pct_min'] - 0.3, 0.2)
                        conditions &= recent_data['atr_pct'] >= atr_min
                    if 'atr_pct_max' in filters and 'atr_pct' in recent_data.columns:
                        # Relax ATR filter
                        atr_max = min(filters['atr_pct_max'] + 0.5, 5.0)
                        conditions &= recent_data['atr_pct'] <= atr_max
                    if 'ema_proximity' in filters and 'ema_20' in recent_data.columns:
                        # Relax EMA proximity filter
                        ema_proximity_pct = min(filters['ema_proximity'] + 1.0, 5.0)
                        conditions &= abs(recent_data['close'] - recent_data['ema_20']) / recent_data['ema_20'] <= ema_proximity_pct / 100
                    if 'volume_min' in filters and 'volume' in recent_data.columns:
                        # Relax volume filter
                        volume_min = max(filters['volume_min'] * 0.5, 0.1)
                        conditions &= recent_data['volume'] >= volume_min
                    
                    # Apply trend filter if specified
                    if 'trend_filter' in strategy['entry_conditions'] and strategy['entry_conditions']['trend_filter'] == 'uptrend':
                        if 'ema_20' in recent_data.columns and 'ema_50' in recent_data.columns:
                            conditions &= recent_data['ema_20'] > recent_data['ema_50']
                    
                    # Find signal points
                    signal_points = recent_data[conditions]
                    
                    for timestamp, row in signal_points.iterrows():
                        # Calculate confidence score
                        confidence = self._calculate_signal_confidence(strategy, row)
                        
                        signal = {
                            'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S') if hasattr(timestamp, 'strftime') else str(timestamp),
                            'strategy_name': strategy['name'],
                            'pattern': strategy['pattern'],
                            'confidence': confidence,
                            'confidence_level': self._get_confidence_level(confidence),
                            'risk_level': self._get_risk_level(strategy),
                            'recommendation': self._get_recommendation(confidence),
                            'breakdown': self._get_confidence_breakdown(strategy, row),
                            'entry_price': float(row['close']),
                            'direction': 'LONG'
                        }
                        
                        signals.append(signal)
                
                except Exception as e:
                    logger.error(f"Error generating signals for strategy {strategy.get('name', 'Unknown')}: {e}")
                    continue
            
            # Sort by timestamp (most recent first)
            signals.sort(key=lambda x: x['timestamp'], reverse=True)
            
            logger.info(f"Generated {len(signals)} signals for {commodity} {timeframe}")
            return signals
            
        except Exception as e:
            logger.error(f"Error generating trading signals: {e}")
            return []
    
    def get_chart_data(self, commodity: str, timeframe: str, 
                      period: str = '1m') -> Dict[str, Any]:
        """Get formatted chart data for visualization."""
        try:
            df = self.load_historical_data(commodity, timeframe)
            
            if df.empty:
                return {'ohlc': [], 'volume': [], 'indicators': {}}
            
            # Get data for the specified period
            if period == '1d':
                chart_data = df.tail(24)  # Last 24 bars
            elif period == '1w':
                chart_data = df.tail(168)  # Last week
            elif period == '1m':
                chart_data = df.tail(720)  # Last month
            elif period == '3m':
                chart_data = df.tail(2160)  # Last 3 months
            else:
                chart_data = df.tail(100)  # Default
            
            # Format OHLC data
            ohlc_data = []
            volume_data = []
            
            for timestamp, row in chart_data.iterrows():
                ohlc_data.append({
                    'timestamp': timestamp.isoformat(),
                    'open': float(row['open']),
                    'high': float(row['high']),
                    'low': float(row['low']),
                    'close': float(row['close'])
                })
                
                volume_data.append({
                    'timestamp': timestamp.isoformat(),
                    'volume': float(row.get('volume', 0))
                })
            
            # Calculate technical indicators
            indicators = self._calculate_technical_indicators(chart_data)
            
            return {
                'ohlc': ohlc_data,
                'volume': volume_data,
                'indicators': indicators,
                'trend_lines': self._calculate_trend_lines(chart_data),
                'support_resistance': self._calculate_support_resistance(chart_data)
            }
            
        except Exception as e:
            logger.error(f"Error getting chart data: {e}")
            return {'ohlc': [], 'volume': [], 'indicators': {}}
    
    def get_market_analysis(self, commodity: str, timeframe: str) -> Dict[str, Any]:
        """Get comprehensive market analysis."""
        try:
            df = self.load_historical_data(commodity, timeframe)
            
            if df.empty:
                return self._get_default_analysis()
            
            # Get recent data for analysis
            recent_data = df.tail(50)
            
            # Calculate market regime
            regime = self._calculate_market_regime(recent_data)
            
            # Calculate trend strength
            trend_strength = self._calculate_trend_strength(recent_data)
            
            # Calculate volatility
            volatility = self._calculate_volatility(recent_data)
            
            # Calculate volume level
            volume_level = self._calculate_volume_level(recent_data)
            
            # Get latest technical indicators
            latest = recent_data.iloc[-1]
            
            analysis = {
                'regime': regime,
                'trend_strength': trend_strength,
                'volatility': volatility,
                'volume_level': volume_level,
                'rsi': float(latest.get('rsi_14', 50)),
                'adx': float(latest.get('adx_14', 20)),
                'atr_pct': float(latest.get('atr_pct', 1.0)),
                'support': float(recent_data['low'].tail(20).min()),
                'resistance': float(recent_data['high'].tail(20).max()),
                'bullish_percent': self._calculate_bullish_percent(recent_data),
                'neutral_percent': 30.0,  # Placeholder
                'bearish_percent': self._calculate_bearish_percent(recent_data)
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error getting market analysis: {e}")
            return self._get_default_analysis()
    
    def get_performance_metrics(self, commodity: str, timeframe: str) -> Dict[str, Any]:
        """Get performance metrics for the strategies."""
        try:
            rules = self.load_trading_rules(commodity, timeframe)
            
            if not rules:
                return {'total_trades': 0, 'win_rate': 0, 'total_pnl': 0}
            
            # Extract performance from strategies
            total_trades = 0
            total_pnl = 0
            win_rates = []
            
            for key, value in rules.items():
                if key.startswith('strategy_'):
                    performance = value.get('performance', {})
                    total_trades += performance.get('trades', 0)
                    total_pnl += performance.get('total_pnl', 0)
                    win_rates.append(performance.get('win_rate', 0))
            
            avg_win_rate = np.mean(win_rates) if win_rates else 0
            
            return {
                'total_trades': total_trades,
                'win_rate': avg_win_rate,
                'total_pnl': total_pnl
            }
            
        except Exception as e:
            logger.error(f"Error getting performance metrics: {e}")
            return {'total_trades': 0, 'win_rate': 0, 'total_pnl': 0}
    
    def get_past_signals(self, commodity: str, timeframe: str, lookback_days: int = 90) -> List[Dict[str, Any]]:
        """Get historical trading signals with their outcomes."""
        try:
            # Load data and rules
            df = self.load_historical_data(commodity, timeframe)
            rules = self.load_trading_rules(commodity, timeframe)
            
            if df.empty or not rules:
                return []
            
            # Get historical data for past signals
            historical_data = df.tail(lookback_days * self._get_bars_per_day(timeframe))
            
            past_signals = []
            
            # Extract strategies from rules
            strategies = []
            for key, value in rules.items():
                if key.startswith('strategy_') and key != 'strategy_metadata':
                    strategies.append(value)
            
            for strategy in strategies:
                try:
                    # Get pattern column name
                    pattern_name = strategy['pattern']
                    pattern_col = f"pattern_{pattern_name}"
                    
                    if pattern_col not in historical_data.columns:
                        logger.warning(f"Pattern column {pattern_col} not found in data")
                        continue
                    
                    # Apply filters to find signal points
                    filters = strategy['entry_conditions']['filters']
                    
                    # Create filter conditions
                    conditions = historical_data[pattern_col] == 1  # Pattern detected
                    
                    # Apply additional filters (more lenient for historical data)
                    if 'rsi_min' in filters and 'rsi_14' in historical_data.columns:
                        rsi_min = max(filters['rsi_min'] - 10, 20)
                        conditions &= historical_data['rsi_14'] >= rsi_min
                    if 'rsi_max' in filters and 'rsi_14' in historical_data.columns:
                        rsi_max = min(filters['rsi_max'] + 10, 80)
                        conditions &= historical_data['rsi_14'] <= rsi_max
                    if 'adx_min' in filters and 'adx_14' in historical_data.columns:
                        adx_min = max(filters['adx_min'] - 5, 10)
                        conditions &= historical_data['adx_14'] >= adx_min
                    if 'atr_pct_min' in filters and 'atr_pct' in historical_data.columns:
                        atr_min = max(filters['atr_pct_min'] - 0.3, 0.2)
                        conditions &= historical_data['atr_pct'] >= atr_min
                    if 'atr_pct_max' in filters and 'atr_pct' in historical_data.columns:
                        atr_max = min(filters['atr_pct_max'] + 0.5, 5.0)
                        conditions &= historical_data['atr_pct'] <= atr_max
                    if 'ema_proximity' in filters and 'ema_20' in historical_data.columns:
                        ema_proximity_pct = min(filters['ema_proximity'] + 1.0, 5.0)
                        conditions &= abs(historical_data['close'] - historical_data['ema_20']) / historical_data['ema_20'] <= ema_proximity_pct / 100
                    if 'volume_min' in filters and 'volume' in historical_data.columns:
                        volume_min = max(filters['volume_min'] * 0.5, 0.1)
                        conditions &= historical_data['volume'] >= volume_min
                    
                    # Apply trend filter if specified
                    if 'trend_filter' in strategy['entry_conditions'] and strategy['entry_conditions']['trend_filter'] == 'uptrend':
                        if 'ema_20' in historical_data.columns and 'ema_50' in historical_data.columns:
                            conditions &= historical_data['ema_20'] > historical_data['ema_50']
                    
                    # Find signal points
                    signal_points = historical_data[conditions]
                    
                    for timestamp, row in signal_points.iterrows():
                        # Calculate trade outcome
                        outcome = self._calculate_trade_outcome(strategy, timestamp, historical_data)
                        
                        signal = {
                            'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S') if hasattr(timestamp, 'strftime') else str(timestamp),
                            'strategy_name': strategy['name'],
                            'pattern': strategy['pattern'],
                            'entry_price': float(row['close']),
                            'direction': 'LONG',
                            'confidence': self._calculate_signal_confidence(strategy, row),
                            'outcome': outcome['result'],  # WIN, LOSS, or BREAKEVEN
                            'exit_price': outcome['exit_price'],
                            'pnl': outcome['pnl'],
                            'pnl_percent': outcome['pnl_percent'],
                            'hold_bars': outcome['hold_bars'],
                            'exit_reason': outcome['exit_reason']
                        }
                        
                        past_signals.append(signal)
                
                except Exception as e:
                    logger.error(f"Error generating past signals for strategy {strategy.get('name', 'Unknown')}: {e}")
                    continue
            
            # Sort by timestamp (most recent first)
            past_signals.sort(key=lambda x: x['timestamp'], reverse=True)
            
            logger.info(f"Generated {len(past_signals)} past signals for {commodity} {timeframe}")
            return past_signals
            
        except Exception as e:
            logger.error(f"Error getting past signals: {e}")
            return []
    
    def _calculate_trade_outcome(self, strategy: Dict, entry_timestamp: pd.Timestamp, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate the outcome of a historical trade."""
        try:
            # Get entry conditions from strategy
            exit_rules = strategy.get('exit_rules', {})
            
            # Find entry index
            entry_idx = df.index.get_loc(entry_timestamp)
            entry_price = df.iloc[entry_idx]['close']
            
            # Get exit parameters
            stop_loss_pct = exit_rules.get('stop_loss_pct', 2.0)
            take_profit_pct = exit_rules.get('take_profit_pct', 4.0)
            max_hold_bars = exit_rules.get('max_hold_bars', 10)
            
            # Calculate stop loss and take profit levels
            stop_loss_price = entry_price * (1 - stop_loss_pct / 100)
            take_profit_price = entry_price * (1 + take_profit_pct / 100)
            
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
                    return {
                        'result': 'LOSS',
                        'exit_price': stop_loss_price,
                        'pnl': stop_loss_price - entry_price,
                        'pnl_percent': (stop_loss_price - entry_price) / entry_price * 100,
                        'hold_bars': i,
                        'exit_reason': 'Stop Loss'
                    }
                
                # Check for take profit hit
                if high >= take_profit_price:
                    return {
                        'result': 'WIN',
                        'exit_price': take_profit_price,
                        'pnl': take_profit_price - entry_price,
                        'pnl_percent': (take_profit_price - entry_price) / entry_price * 100,
                        'hold_bars': i,
                        'exit_reason': 'Take Profit'
                    }
            
            # If max hold bars reached, exit at close
            final_idx = entry_idx + max_hold_bars
            if final_idx < len(df):
                exit_price = df.iloc[final_idx]['close']
                pnl = exit_price - entry_price
                pnl_percent = (pnl / entry_price) * 100
                
                result = 'WIN' if pnl > 0 else 'LOSS' if pnl < 0 else 'BREAKEVEN'
                
                return {
                    'result': result,
                    'exit_price': exit_price,
                    'pnl': pnl,
                    'pnl_percent': pnl_percent,
                    'hold_bars': max_hold_bars,
                    'exit_reason': 'Time Exit'
                }
            
            # Fallback if we can't simulate the trade
            return {
                'result': 'UNKNOWN',
                'exit_price': entry_price,
                'pnl': 0.0,
                'pnl_percent': 0.0,
                'hold_bars': 0,
                'exit_reason': 'Unknown'
            }
            
        except Exception as e:
            logger.error(f"Error calculating trade outcome: {e}")
            return {
                'result': 'ERROR',
                'exit_price': entry_price,
                'pnl': 0.0,
                'pnl_percent': 0.0,
                'hold_bars': 0,
                'exit_reason': 'Error'
            }
    
    def _get_bars_per_day(self, timeframe: str) -> int:
        """Get number of bars per day for a timeframe."""
        if timeframe == '1h':
            return 24
        elif timeframe == '4h':
            return 6
        elif timeframe == '1d':
            return 1
        else:
            return 24
    
    def _calculate_signal_confidence(self, strategy: Dict, row: pd.Series) -> float:
        """Calculate confidence score for a signal."""
        try:
            performance = strategy.get('performance', {})
            win_rate = performance.get('win_rate', 50) / 100
            profit_factor = min(performance.get('profit_factor', 1.0) / 3.0, 1.0)
            
            # Base confidence from strategy performance
            base_confidence = (win_rate * 0.6 + profit_factor * 0.4)
            
            # Adjust based on current market conditions
            rsi = row.get('rsi_14', 50)
            if 30 <= rsi <= 70:
                base_confidence *= 1.1  # Good RSI range
            else:
                base_confidence *= 0.9  # Extreme RSI
            
            return min(max(base_confidence, 0.0), 1.0)
            
        except Exception as e:
            logger.error(f"Error calculating signal confidence: {e}")
            return 0.5
    
    def _get_confidence_level(self, confidence: float) -> str:
        """Get confidence level string."""
        if confidence >= 0.8:
            return "VERY HIGH"
        elif confidence >= 0.7:
            return "HIGH"
        elif confidence >= 0.6:
            return "MEDIUM"
        elif confidence >= 0.5:
            return "LOW"
        else:
            return "VERY LOW"
    
    def _get_risk_level(self, strategy: Dict) -> str:
        """Get risk level from strategy."""
        performance = strategy.get('performance', {})
        max_dd = performance.get('max_drawdown_pct', 20)
        
        if max_dd < 5:
            return "LOW RISK"
        elif max_dd < 15:
            return "MODERATE RISK"
        else:
            return "HIGH RISK"
    
    def _get_recommendation(self, confidence: float) -> str:
        """Get trading recommendation."""
        if confidence >= 0.8:
            return "Strong signal - High probability of success"
        elif confidence >= 0.7:
            return "Good signal - Favorable conditions"
        elif confidence >= 0.6:
            return "Moderate signal - Proceed with caution"
        elif confidence >= 0.5:
            return "Weak signal - Consider skipping"
        else:
            return "Very weak signal - Avoid trade"
    
    def _get_confidence_breakdown(self, strategy: Dict, row: pd.Series) -> Dict[str, float]:
        """Get confidence breakdown for display."""
        performance = strategy.get('performance', {})
        
        # Historical performance score
        hist_score = (performance.get('win_rate', 50) / 100) * 0.6 + \
                    min(performance.get('profit_factor', 1.0) / 3.0, 1.0) * 0.4
        
        # Market conditions score
        rsi = row.get('rsi_14', 50)
        market_score = 1.0 if 30 <= rsi <= 70 else 0.7
        
        # Pattern strength (simplified)
        pattern_score = 1.0 if row.get(strategy['pattern'], 0) == 1 else 0.0
        
        # Risk conditions
        max_dd = performance.get('max_drawdown_pct', 20)
        risk_score = max(0.0, 1.0 - (max_dd / 50.0))
        
        return {
            'historical_performance': hist_score,
            'market_conditions': market_score,
            'pattern_strength': pattern_score,
            'risk_conditions': risk_score
        }
    
    def _calculate_technical_indicators(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate technical indicators for charts."""
        try:
            if df.empty:
                return {}
            
            latest = df.iloc[-1]
            
            return {
                'ema_20': float(latest.get('ema_20', latest['close'])),
                'ema_50': float(latest.get('ema_50', latest['close'])),
                'rsi': float(latest.get('rsi_14', 50)),
                'macd': float(latest.get('macd', 0)),
                'bollinger_upper': float(latest.get('bb_upper', latest['close'])),
                'bollinger_lower': float(latest.get('bb_lower', latest['close']))
            }
        except Exception as e:
            logger.error(f"Error calculating technical indicators: {e}")
            return {}
    
    def _calculate_trend_lines(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate trend lines for the chart."""
        try:
            if len(df) < 20:
                return {}
            
            # Simple trend line calculation
            recent_highs = df['high'].tail(10)
            recent_lows = df['low'].tail(10)
            
            return {
                'trend_up': float(recent_highs.max()),
                'trend_down': float(recent_lows.min()),
                'trend_middle': float(df['close'].tail(10).mean())
            }
        except Exception as e:
            logger.error(f"Error calculating trend lines: {e}")
            return {}
    
    def _calculate_support_resistance(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calculate support and resistance levels."""
        try:
            if len(df) < 20:
                return {'support': 0, 'resistance': 0}
            
            recent_data = df.tail(20)
            
            return {
                'support': float(recent_data['low'].min()),
                'resistance': float(recent_data['high'].max())
            }
        except Exception as e:
            logger.error(f"Error calculating support/resistance: {e}")
            return {'support': 0, 'resistance': 0}
    
    def _calculate_market_regime(self, df: pd.DataFrame) -> str:
        """Calculate market regime."""
        try:
            if len(df) < 10:
                return "NEUTRAL"
            
            # Simple regime detection based on trend
            recent_returns = df['close'].pct_change().tail(10).mean()
            
            if recent_returns > 0.001:  # 0.1% positive
                return "BULLISH"
            elif recent_returns < -0.001:  # 0.1% negative
                return "BEARISH"
            else:
                return "NEUTRAL"
        except Exception as e:
            logger.error(f"Error calculating market regime: {e}")
            return "NEUTRAL"
    
    def _calculate_trend_strength(self, df: pd.DataFrame) -> str:
        """Calculate trend strength."""
        try:
            if len(df) < 10:
                return "WEAK"
            
            # Use ADX if available
            if 'adx_14' in df.columns:
                latest_adx = df['adx_14'].iloc[-1]
                if latest_adx > 25:
                    return "STRONG"
                elif latest_adx > 15:
                    return "MODERATE"
                else:
                    return "WEAK"
            
            # Fallback to price movement
            price_change = abs(df['close'].pct_change().tail(10).mean())
            if price_change > 0.005:  # 0.5%
                return "STRONG"
            elif price_change > 0.002:  # 0.2%
                return "MODERATE"
            else:
                return "WEAK"
        except Exception as e:
            logger.error(f"Error calculating trend strength: {e}")
            return "WEAK"
    
    def _calculate_volatility(self, df: pd.DataFrame) -> str:
        """Calculate volatility level."""
        try:
            if len(df) < 10:
                return "LOW"
            
            # Use ATR if available
            if 'atr_pct' in df.columns:
                latest_atr = df['atr_pct'].iloc[-1]
                if latest_atr > 2.0:
                    return "HIGH"
                elif latest_atr > 1.0:
                    return "MODERATE"
                else:
                    return "LOW"
            
            # Fallback to price volatility
            volatility = df['close'].pct_change().std()
            if volatility > 0.02:  # 2%
                return "HIGH"
            elif volatility > 0.01:  # 1%
                return "MODERATE"
            else:
                return "LOW"
        except Exception as e:
            logger.error(f"Error calculating volatility: {e}")
            return "MODERATE"
    
    def _calculate_volume_level(self, df: pd.DataFrame) -> str:
        """Calculate volume level."""
        try:
            if 'volume' not in df.columns or len(df) < 10:
                return "NORMAL"
            
            recent_volume = df['volume'].tail(10).mean()
            avg_volume = df['volume'].mean()
            
            if recent_volume > avg_volume * 1.5:
                return "ABOVE_AVERAGE"
            elif recent_volume < avg_volume * 0.5:
                return "BELOW_AVERAGE"
            else:
                return "NORMAL"
        except Exception as e:
            logger.error(f"Error calculating volume level: {e}")
            return "NORMAL"
    
    def _calculate_bullish_percent(self, df: pd.DataFrame) -> float:
        """Calculate bullish percentage."""
        try:
            if len(df) < 10:
                return 50.0
            
            # Count bullish vs bearish bars
            bullish_bars = (df['close'] > df['open']).sum()
            total_bars = len(df)
            
            return (bullish_bars / total_bars) * 100
        except Exception as e:
            logger.error(f"Error calculating bullish percent: {e}")
            return 50.0
    
    def _calculate_bearish_percent(self, df: pd.DataFrame) -> float:
        """Calculate bearish percentage."""
        try:
            if len(df) < 10:
                return 50.0
            
            # Count bearish vs bullish bars
            bearish_bars = (df['close'] < df['open']).sum()
            total_bars = len(df)
            
            return (bearish_bars / total_bars) * 100
        except Exception as e:
            logger.error(f"Error calculating bearish percent: {e}")
            return 50.0
    
    def _get_default_analysis(self) -> Dict[str, Any]:
        """Get default analysis when data is not available."""
        return {
            'regime': 'NEUTRAL',
            'trend_strength': 'MODERATE',
            'volatility': 'MODERATE',
            'volume_level': 'NORMAL',
            'rsi': 50.0,
            'adx': 20.0,
            'atr_pct': 1.0,
            'support': 0.0,
            'resistance': 0.0,
            'bullish_percent': 50.0,
            'neutral_percent': 30.0,
            'bearish_percent': 20.0
        }

if __name__ == "__main__":
    # Test the data service
    service = DashboardDataService()
    
    # Test Gold 1D data
    print("Testing Dashboard Data Service...")
    
    # Test historical data loading
    df = service.load_historical_data('gold', '1d')
    print(f"Gold 1D data: {len(df)} records")
    
    # Test trading rules
    rules = service.load_trading_rules('gold', '1d')
    print(f"Gold 1D rules: {len([k for k in rules.keys() if k.startswith('strategy_')])} strategies")
    
    # Test signal generation
    signals = service.generate_trading_signals('gold', '1d')
    print(f"Generated signals: {len(signals)}")
    
    # Test chart data
    chart_data = service.get_chart_data('gold', '1d')
    print(f"Chart data: {len(chart_data['ohlc'])} OHLC points")
    
    # Test market analysis
    analysis = service.get_market_analysis('gold', '1d')
    print(f"Market analysis: {analysis['regime']} regime")
