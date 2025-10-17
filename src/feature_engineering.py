"""
Feature Engineering Pipeline
Combines patterns, indicators, and market context for all commodities and timeframes
"""
import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Tuple
import sys

from utils import load_ohlc_data, save_features, get_logger, get_all_combinations
from indicators import add_all_indicators
from patterns import detect_all_patterns, get_pattern_summary

logger = get_logger(__name__)

def add_market_context(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add market context features like time of day, day of week, etc.
    
    Parameters:
    -----------
    df : pd.DataFrame
        DataFrame with 'time' column
        
    Returns:
    --------
    pd.DataFrame with market context features
    """
    df = df.copy()
    
    # Time-based features
    df['hour'] = df['time'].dt.hour
    df['day_of_week'] = df['time'].dt.dayofweek  # 0=Monday, 6=Sunday
    df['day_of_month'] = df['time'].dt.day
    df['month'] = df['time'].dt.month
    df['quarter'] = df['time'].dt.quarter
    
    # Session indicators (IST timezone assumed)
    # MCX Gold/Silver trading hours: 09:00 - 23:30 IST
    df['is_morning_session'] = ((df['hour'] >= 9) & (df['hour'] < 13)).astype(int)
    df['is_afternoon_session'] = ((df['hour'] >= 13) & (df['hour'] < 17)).astype(int)
    df['is_evening_session'] = ((df['hour'] >= 17) & (df['hour'] < 21)).astype(int)
    df['is_night_session'] = ((df['hour'] >= 21) | (df['hour'] < 9)).astype(int)
    
    return df

def add_price_action_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add raw price action features
    
    Returns:
    --------
    pd.DataFrame with price action features
    """
    df = df.copy()
    
    # Candle characteristics
    df['body'] = abs(df['close'] - df['open'])
    df['upper_wick'] = df['high'] - df[['open', 'close']].max(axis=1)
    df['lower_wick'] = df[['open', 'close']].min(axis=1) - df['low']
    df['total_range'] = df['high'] - df['low']
    
    # Body as percentage of range
    df['body_pct'] = df['body'] / (df['total_range'] + 1e-10)
    df['upper_wick_pct'] = df['upper_wick'] / (df['total_range'] + 1e-10)
    df['lower_wick_pct'] = df['lower_wick'] / (df['total_range'] + 1e-10)
    
    # Candle direction
    df['is_bullish'] = (df['close'] > df['open']).astype(int)
    df['is_bearish'] = (df['close'] < df['open']).astype(int)
    
    # Price changes
    df['close_change'] = df['close'].pct_change() * 100
    df['close_change_abs'] = abs(df['close_change'])
    
    # High/Low relative to previous close
    df['high_vs_prev_close'] = (df['high'] / df['close'].shift(1) - 1) * 100
    df['low_vs_prev_close'] = (df['low'] / df['close'].shift(1) - 1) * 100
    
    # Gaps
    df['gap_up'] = ((df['low'] > df['high'].shift(1))).astype(int)
    df['gap_down'] = ((df['high'] < df['low'].shift(1))).astype(int)
    df['gap_size'] = df['open'] - df['close'].shift(1)
    df['gap_size_pct'] = (df['gap_size'] / df['close'].shift(1)) * 100
    
    # Range expansion/contraction
    df['range_change'] = df['total_range'].pct_change() * 100
    df['range_vs_avg_20'] = df['total_range'] / df['total_range'].rolling(20).mean()
    
    # Consecutive bars
    df['consecutive_bull'] = (df['is_bullish'] * 
                              (df['is_bullish'].groupby((df['is_bullish'] != df['is_bullish'].shift()).cumsum()).cumcount() + 1))
    df['consecutive_bear'] = (df['is_bearish'] * 
                              (df['is_bearish'].groupby((df['is_bearish'] != df['is_bearish'].shift()).cumsum()).cumcount() + 1))
    
    return df

def add_trend_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add trend identification features
    
    Returns:
    --------
    pd.DataFrame with trend features
    """
    df = df.copy()
    
    # EMA trend conditions
    df['trend_ema_bull_short'] = (df['ema_20'] > df['ema_50']).astype(int)
    df['trend_ema_bull_long'] = (df['ema_50'] > df['ema_200']).astype(int)
    df['trend_ema_bear_short'] = (df['ema_20'] < df['ema_50']).astype(int)
    df['trend_ema_bear_long'] = (df['ema_50'] < df['ema_200']).astype(int)
    
    # Price vs EMAs
    df['price_above_ema20'] = (df['close'] > df['ema_20']).astype(int)
    df['price_above_ema50'] = (df['close'] > df['ema_50']).astype(int)
    df['price_above_ema200'] = (df['close'] > df['ema_200']).astype(int)
    
    # EMA slopes (rate of change)
    df['ema20_slope'] = df['ema_20'].pct_change(periods=5) * 100
    df['ema50_slope'] = df['ema_50'].pct_change(periods=10) * 100
    
    # Higher highs, higher lows
    df['higher_high'] = (df['high'] > df['high'].shift(1)).astype(int)
    df['higher_low'] = (df['low'] > df['low'].shift(1)).astype(int)
    df['lower_high'] = (df['high'] < df['high'].shift(1)).astype(int)
    df['lower_low'] = (df['low'] < df['low'].shift(1)).astype(int)
    
    return df

def add_momentum_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add momentum-based features
    
    Returns:
    --------
    pd.DataFrame with momentum features
    """
    df = df.copy()
    
    # RSI zones
    df['rsi14_oversold'] = (df['rsi_14'] < 30).astype(int)
    df['rsi14_overbought'] = (df['rsi_14'] > 70).astype(int)
    df['rsi14_bullish'] = (df['rsi_14'] > 50).astype(int)
    df['rsi14_bearish'] = (df['rsi_14'] < 50).astype(int)
    
    # RSI momentum
    df['rsi14_rising'] = (df['rsi_14'] > df['rsi_14'].shift(1)).astype(int)
    df['rsi14_falling'] = (df['rsi_14'] < df['rsi_14'].shift(1)).astype(int)
    
    # MACD signals
    df['macd_bullish'] = (df['macd'] > df['macd_signal']).astype(int)
    df['macd_bearish'] = (df['macd'] < df['macd_signal']).astype(int)
    df['macd_cross_up'] = ((df['macd'] > df['macd_signal']) & 
                           (df['macd'].shift(1) <= df['macd_signal'].shift(1))).astype(int)
    df['macd_cross_down'] = ((df['macd'] < df['macd_signal']) & 
                             (df['macd'].shift(1) >= df['macd_signal'].shift(1))).astype(int)
    
    # Stochastic
    df['stoch_oversold'] = (df['stoch_k'] < 20).astype(int)
    df['stoch_overbought'] = (df['stoch_k'] > 80).astype(int)
    
    return df

def add_volatility_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add volatility-based features
    
    Returns:
    --------
    pd.DataFrame with volatility features
    """
    df = df.copy()
    
    # ATR zones
    df['atr14_high'] = (df['atr_pct_14'] > df['atr_pct_14'].rolling(50).quantile(0.75)).astype(int)
    df['atr14_low'] = (df['atr_pct_14'] < df['atr_pct_14'].rolling(50).quantile(0.25)).astype(int)
    
    # ADX trend strength
    df['adx14_trending'] = (df['adx_14'] > 25).astype(int)
    df['adx14_strong'] = (df['adx_14'] > 40).astype(int)
    df['adx14_weak'] = (df['adx_14'] < 20).astype(int)
    
    # Directional movement
    df['di_bullish'] = (df['plus_di_14'] > df['minus_di_14']).astype(int)
    df['di_bearish'] = (df['plus_di_14'] < df['minus_di_14']).astype(int)
    
    # Bollinger Band position
    df['bb_upper_touch'] = (df['close'] >= df['bb_upper_20']).astype(int)
    df['bb_lower_touch'] = (df['close'] <= df['bb_lower_20']).astype(int)
    df['bb_position'] = (df['close'] - df['bb_lower_20']) / (df['bb_upper_20'] - df['bb_lower_20'])
    
    return df

def build_features(commodity: str, timeframe: str, save: bool = True) -> pd.DataFrame:
    """
    Complete feature engineering pipeline for a commodity-timeframe pair
    
    Parameters:
    -----------
    commodity : str
        Commodity name (gold, silver, copper)
    timeframe : str
        Timeframe (1h, 4h, 1d)
    save : bool
        Whether to save the results
        
    Returns:
    --------
    pd.DataFrame with all features
    """
    logger.info(f"\n{'='*60}")
    logger.info(f"Building features for {commodity.upper()} {timeframe.upper()}")
    logger.info(f"{'='*60}")
    
    # Load raw data
    df = load_ohlc_data(commodity, timeframe)
    logger.info(f"Loaded {len(df)} bars")
    
    # Add all feature categories
    logger.info("Adding technical indicators...")
    df = add_all_indicators(df)
    
    logger.info("Detecting candlestick patterns...")
    df = detect_all_patterns(df)
    
    logger.info("Adding market context...")
    df = add_market_context(df)
    
    logger.info("Adding price action features...")
    df = add_price_action_features(df)
    
    logger.info("Adding trend features...")
    df = add_trend_features(df)
    
    logger.info("Adding momentum features...")
    df = add_momentum_features(df)
    
    logger.info("Adding volatility features...")
    df = add_volatility_features(df)
    
    # Get pattern summary
    pattern_summary = get_pattern_summary(df)
    logger.info(f"\nPattern occurrences:")
    for pattern, count in sorted(pattern_summary.items(), key=lambda x: x[1], reverse=True):
        if count > 0:
            pct = (count / len(df)) * 100
            logger.info(f"  {pattern:30s}: {count:5d} ({pct:5.2f}%)")
    
    # Save if requested
    if save:
        save_features(df, commodity, timeframe)
    
    logger.info(f"\nFinal dataset: {len(df)} rows, {len(df.columns)} columns")
    logger.info(f"Date range: {df['time'].min()} to {df['time'].max()}")
    
    return df

def build_all_features():
    """
    Build features for all commodity-timeframe combinations
    """
    logger.info(f"\n{'#'*60}")
    logger.info(f"# BUILDING FEATURES FOR ALL COMMODITIES AND TIMEFRAMES")
    logger.info(f"{'#'*60}\n")
    
    combinations = get_all_combinations()
    
    results = {}
    for commodity, timeframe in combinations:
        try:
            df = build_features(commodity, timeframe, save=True)
            results[(commodity, timeframe)] = {
                'success': True,
                'rows': len(df),
                'columns': len(df.columns)
            }
        except Exception as e:
            logger.error(f"Error processing {commodity} {timeframe}: {str(e)}")
            results[(commodity, timeframe)] = {
                'success': False,
                'error': str(e)
            }
    
    # Summary
    logger.info(f"\n{'='*60}")
    logger.info("FEATURE ENGINEERING SUMMARY")
    logger.info(f"{'='*60}")
    
    for (commodity, timeframe), result in results.items():
        if result['success']:
            logger.info(f"✓ {commodity:7s} {timeframe:3s}: {result['rows']:6d} rows, {result['columns']:4d} columns")
        else:
            logger.error(f"✗ {commodity:7s} {timeframe:3s}: {result['error']}")
    
    logger.info(f"\n{'#'*60}")
    logger.info("# FEATURE ENGINEERING COMPLETE")
    logger.info(f"{'#'*60}\n")

if __name__ == "__main__":
    # Can run this directly to build all features
    build_all_features()





