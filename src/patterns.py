"""
Candlestick Pattern Detection Module
Detects all major candlestick patterns across multiple timeframes
"""
import pandas as pd
import numpy as np
from typing import Dict

def detect_inside_bar(df: pd.DataFrame) -> pd.Series:
    """
    Inside Bar: Current bar's high/low completely within previous bar's range
    Indicates consolidation, often precedes breakout
    
    Returns:
    --------
    pd.Series with 1 for inside bar, 0 otherwise
    """
    inside = (
        (df['high'] < df['high'].shift(1)) & 
        (df['low'] > df['low'].shift(1))
    ).astype(int)
    
    return inside

def detect_outside_bar(df: pd.DataFrame) -> pd.Series:
    """
    Outside Bar (Engulfing Range): Current bar completely engulfs previous bar
    Indicates volatility expansion and potential reversal/continuation
    
    Returns:
    --------
    pd.Series with 1 for outside bar, 0 otherwise
    """
    outside = (
        (df['high'] > df['high'].shift(1)) & 
        (df['low'] < df['low'].shift(1))
    ).astype(int)
    
    return outside

def detect_bullish_engulfing(df: pd.DataFrame) -> pd.Series:
    """
    Bullish Engulfing: Bullish candle completely engulfs previous bearish candle
    Strong bullish reversal signal
    
    Returns:
    --------
    pd.Series with 1 for bullish engulfing, 0 otherwise
    """
    prev_bearish = df['close'].shift(1) < df['open'].shift(1)
    curr_bullish = df['close'] > df['open']
    
    engulfing = (
        prev_bearish &
        curr_bullish &
        (df['open'] <= df['close'].shift(1)) &
        (df['close'] >= df['open'].shift(1))
    ).astype(int)
    
    return engulfing

def detect_bearish_engulfing(df: pd.DataFrame) -> pd.Series:
    """
    Bearish Engulfing: Bearish candle completely engulfs previous bullish candle
    Strong bearish reversal signal
    """
    prev_bullish = df['close'].shift(1) > df['open'].shift(1)
    curr_bearish = df['close'] < df['open']
    
    engulfing = (
        prev_bullish &
        curr_bearish &
        (df['open'] >= df['close'].shift(1)) &
        (df['close'] <= df['open'].shift(1))
    ).astype(int)
    
    return engulfing

def detect_hammer(df: pd.DataFrame, body_ratio: float = 0.3, wick_ratio: float = 2.0) -> pd.Series:
    """
    Hammer: Small body at top, long lower wick
    Bullish reversal pattern (rejection of lower prices)
    
    Parameters:
    -----------
    body_ratio : float
        Maximum body size as fraction of total range
    wick_ratio : float
        Minimum ratio of lower wick to body
    """
    body = abs(df['close'] - df['open'])
    total_range = df['high'] - df['low']
    lower_wick = df[['open', 'close']].min(axis=1) - df['low']
    upper_wick = df['high'] - df[['open', 'close']].max(axis=1)
    
    hammer = (
        (body / total_range <= body_ratio) &
        (lower_wick / (body + 1e-10) >= wick_ratio) &
        (upper_wick < body)
    ).astype(int)
    
    return hammer

def detect_shooting_star(df: pd.DataFrame, body_ratio: float = 0.3, wick_ratio: float = 2.0) -> pd.Series:
    """
    Shooting Star: Small body at bottom, long upper wick
    Bearish reversal pattern (rejection of higher prices)
    """
    body = abs(df['close'] - df['open'])
    total_range = df['high'] - df['low']
    lower_wick = df[['open', 'close']].min(axis=1) - df['low']
    upper_wick = df['high'] - df[['open', 'close']].max(axis=1)
    
    shooting_star = (
        (body / total_range <= body_ratio) &
        (upper_wick / (body + 1e-10) >= wick_ratio) &
        (lower_wick < body)
    ).astype(int)
    
    return shooting_star

def detect_doji(df: pd.DataFrame, body_threshold: float = 0.1) -> pd.Series:
    """
    Doji: Open and close nearly equal
    Indicates indecision, potential reversal
    
    Parameters:
    -----------
    body_threshold : float
        Maximum body size as fraction of total range
    """
    body = abs(df['close'] - df['open'])
    total_range = df['high'] - df['low']
    
    doji = (body / (total_range + 1e-10) <= body_threshold).astype(int)
    
    return doji

def detect_pin_bar(df: pd.DataFrame, wick_ratio: float = 0.66) -> pd.Series:
    """
    Pin Bar: Long wick on one side (either direction)
    Indicates rejection of price level
    
    Parameters:
    -----------
    wick_ratio : float
        Minimum wick length as fraction of total range
    """
    total_range = df['high'] - df['low']
    lower_wick = df[['open', 'close']].min(axis=1) - df['low']
    upper_wick = df['high'] - df[['open', 'close']].max(axis=1)
    
    pin_bar = (
        ((lower_wick / (total_range + 1e-10)) >= wick_ratio) |
        ((upper_wick / (total_range + 1e-10)) >= wick_ratio)
    ).astype(int)
    
    return pin_bar

def detect_bullish_pin_bar(df: pd.DataFrame, wick_ratio: float = 0.66) -> pd.Series:
    """Bullish Pin Bar: Long lower wick (rejection of lower prices)"""
    total_range = df['high'] - df['low']
    lower_wick = df[['open', 'close']].min(axis=1) - df['low']
    
    bullish_pin = ((lower_wick / (total_range + 1e-10)) >= wick_ratio).astype(int)
    
    return bullish_pin

def detect_bearish_pin_bar(df: pd.DataFrame, wick_ratio: float = 0.66) -> pd.Series:
    """Bearish Pin Bar: Long upper wick (rejection of higher prices)"""
    total_range = df['high'] - df['low']
    upper_wick = df['high'] - df[['open', 'close']].max(axis=1)
    
    bearish_pin = ((upper_wick / (total_range + 1e-10)) >= wick_ratio).astype(int)
    
    return bearish_pin

def detect_marubozu_bullish(df: pd.DataFrame, wick_threshold: float = 0.05) -> pd.Series:
    """
    Bullish Marubozu: Large bullish candle with little to no wicks
    Strong bullish continuation
    """
    body = df['close'] - df['open']
    total_range = df['high'] - df['low']
    
    marubozu = (
        (body > 0) &
        (body / (total_range + 1e-10) >= (1 - wick_threshold))
    ).astype(int)
    
    return marubozu

def detect_marubozu_bearish(df: pd.DataFrame, wick_threshold: float = 0.05) -> pd.Series:
    """
    Bearish Marubozu: Large bearish candle with little to no wicks
    Strong bearish continuation
    """
    body = df['open'] - df['close']
    total_range = df['high'] - df['low']
    
    marubozu = (
        (body > 0) &
        (body / (total_range + 1e-10) >= (1 - wick_threshold))
    ).astype(int)
    
    return marubozu

def detect_morning_star(df: pd.DataFrame) -> pd.Series:
    """
    Morning Star: 3-bar bullish reversal pattern
    1. Large bearish candle
    2. Small-bodied candle (gap down)
    3. Large bullish candle
    """
    # Bar 1: Bearish
    bar1_bearish = df['close'].shift(2) < df['open'].shift(2)
    bar1_body = abs(df['close'].shift(2) - df['open'].shift(2))
    
    # Bar 2: Small body
    bar2_body = abs(df['close'].shift(1) - df['open'].shift(1))
    bar2_small = bar2_body < bar1_body * 0.3
    
    # Bar 3: Bullish
    bar3_bullish = df['close'] > df['open']
    bar3_body = abs(df['close'] - df['open'])
    
    # Pattern
    morning_star = (
        bar1_bearish &
        bar2_small &
        bar3_bullish &
        (bar3_body > bar1_body * 0.5)
    ).astype(int)
    
    return morning_star

def detect_evening_star(df: pd.DataFrame) -> pd.Series:
    """
    Evening Star: 3-bar bearish reversal pattern
    1. Large bullish candle
    2. Small-bodied candle (gap up)
    3. Large bearish candle
    """
    # Bar 1: Bullish
    bar1_bullish = df['close'].shift(2) > df['open'].shift(2)
    bar1_body = abs(df['close'].shift(2) - df['open'].shift(2))
    
    # Bar 2: Small body
    bar2_body = abs(df['close'].shift(1) - df['open'].shift(1))
    bar2_small = bar2_body < bar1_body * 0.3
    
    # Bar 3: Bearish
    bar3_bearish = df['close'] < df['open']
    bar3_body = abs(df['close'] - df['open'])
    
    # Pattern
    evening_star = (
        bar1_bullish &
        bar2_small &
        bar3_bearish &
        (bar3_body > bar1_body * 0.5)
    ).astype(int)
    
    return evening_star

def detect_three_white_soldiers(df: pd.DataFrame) -> pd.Series:
    """
    Three White Soldiers: 3 consecutive bullish candles with higher closes
    Strong bullish continuation
    """
    bullish_1 = df['close'].shift(2) > df['open'].shift(2)
    bullish_2 = df['close'].shift(1) > df['open'].shift(1)
    bullish_3 = df['close'] > df['open']
    
    higher_closes = (
        (df['close'] > df['close'].shift(1)) &
        (df['close'].shift(1) > df['close'].shift(2))
    )
    
    pattern = (bullish_1 & bullish_2 & bullish_3 & higher_closes).astype(int)
    
    return pattern

def detect_three_black_crows(df: pd.DataFrame) -> pd.Series:
    """
    Three Black Crows: 3 consecutive bearish candles with lower closes
    Strong bearish continuation
    """
    bearish_1 = df['close'].shift(2) < df['open'].shift(2)
    bearish_2 = df['close'].shift(1) < df['open'].shift(1)
    bearish_3 = df['close'] < df['open']
    
    lower_closes = (
        (df['close'] < df['close'].shift(1)) &
        (df['close'].shift(1) < df['close'].shift(2))
    )
    
    pattern = (bearish_1 & bearish_2 & bearish_3 & lower_closes).astype(int)
    
    return pattern

def detect_tweezer_bottom(df: pd.DataFrame, tolerance: float = 0.001) -> pd.Series:
    """
    Tweezer Bottom: Two candles with similar lows
    Bullish reversal pattern
    
    Parameters:
    -----------
    tolerance : float
        Maximum price difference as fraction of price
    """
    low_diff = abs(df['low'] - df['low'].shift(1))
    similar_lows = (low_diff / df['low'] <= tolerance)
    
    # First candle bearish, second bullish
    reversal = (
        (df['close'].shift(1) < df['open'].shift(1)) &
        (df['close'] > df['open'])
    )
    
    pattern = (similar_lows & reversal).astype(int)
    
    return pattern

def detect_tweezer_top(df: pd.DataFrame, tolerance: float = 0.001) -> pd.Series:
    """
    Tweezer Top: Two candles with similar highs
    Bearish reversal pattern
    """
    high_diff = abs(df['high'] - df['high'].shift(1))
    similar_highs = (high_diff / df['high'] <= tolerance)
    
    # First candle bullish, second bearish
    reversal = (
        (df['close'].shift(1) > df['open'].shift(1)) &
        (df['close'] < df['open'])
    )
    
    pattern = (similar_highs & reversal).astype(int)
    
    return pattern

def detect_harami_bullish(df: pd.DataFrame) -> pd.Series:
    """
    Bullish Harami: Small bullish candle within previous large bearish candle
    Potential bullish reversal
    """
    prev_bearish = df['close'].shift(1) < df['open'].shift(1)
    prev_large = abs(df['close'].shift(1) - df['open'].shift(1)) > abs(df['close'] - df['open']) * 2
    
    curr_bullish = df['close'] > df['open']
    curr_within = (
        (df['open'] >= df['close'].shift(1)) &
        (df['close'] <= df['open'].shift(1))
    )
    
    pattern = (prev_bearish & prev_large & curr_bullish & curr_within).astype(int)
    
    return pattern

def detect_harami_bearish(df: pd.DataFrame) -> pd.Series:
    """
    Bearish Harami: Small bearish candle within previous large bullish candle
    Potential bearish reversal
    """
    prev_bullish = df['close'].shift(1) > df['open'].shift(1)
    prev_large = abs(df['close'].shift(1) - df['open'].shift(1)) > abs(df['close'] - df['open']) * 2
    
    curr_bearish = df['close'] < df['open']
    curr_within = (
        (df['open'] <= df['close'].shift(1)) &
        (df['close'] >= df['open'].shift(1))
    )
    
    pattern = (prev_bullish & prev_large & curr_bearish & curr_within).astype(int)
    
    return pattern

def detect_breakout_bar(df: pd.DataFrame, lookback: int = 20) -> pd.Series:
    """
    Breakout Bar: Current close breaks above recent high
    Strong bullish momentum
    
    Parameters:
    -----------
    lookback : int
        Number of bars to look back for high/low
    """
    recent_high = df['high'].shift(1).rolling(window=lookback).max()
    
    breakout = (df['close'] > recent_high).astype(int)
    
    return breakout

def detect_breakdown_bar(df: pd.DataFrame, lookback: int = 20) -> pd.Series:
    """
    Breakdown Bar: Current close breaks below recent low
    Strong bearish momentum
    """
    recent_low = df['low'].shift(1).rolling(window=lookback).min()
    
    breakdown = (df['close'] < recent_low).astype(int)
    
    return breakdown

def detect_range_expansion(df: pd.DataFrame, period: int = 20, threshold: float = 1.5) -> pd.Series:
    """
    Range Expansion: Current bar range significantly larger than average
    Indicates volatility increase
    
    Parameters:
    -----------
    period : int
        Period for average range calculation
    threshold : float
        Multiplier of average range to trigger signal
    """
    bar_range = df['high'] - df['low']
    avg_range = bar_range.rolling(window=period).mean()
    
    expansion = (bar_range > avg_range.shift(1) * threshold).astype(int)
    
    return expansion

def detect_all_patterns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Detect all candlestick patterns and add to dataframe
    
    Parameters:
    -----------
    df : pd.DataFrame
        OHLC dataframe
        
    Returns:
    --------
    pd.DataFrame with all pattern columns added
    """
    df = df.copy()
    
    # Single-bar patterns
    df['pattern_inside_bar'] = detect_inside_bar(df)
    df['pattern_outside_bar'] = detect_outside_bar(df)
    df['pattern_doji'] = detect_doji(df)
    df['pattern_hammer'] = detect_hammer(df)
    df['pattern_shooting_star'] = detect_shooting_star(df)
    df['pattern_pin_bar'] = detect_pin_bar(df)
    df['pattern_bullish_pin'] = detect_bullish_pin_bar(df)
    df['pattern_bearish_pin'] = detect_bearish_pin_bar(df)
    df['pattern_marubozu_bull'] = detect_marubozu_bullish(df)
    df['pattern_marubozu_bear'] = detect_marubozu_bearish(df)
    
    # Two-bar patterns
    df['pattern_bullish_engulfing'] = detect_bullish_engulfing(df)
    df['pattern_bearish_engulfing'] = detect_bearish_engulfing(df)
    df['pattern_tweezer_bottom'] = detect_tweezer_bottom(df)
    df['pattern_tweezer_top'] = detect_tweezer_top(df)
    df['pattern_harami_bull'] = detect_harami_bullish(df)
    df['pattern_harami_bear'] = detect_harami_bearish(df)
    
    # Three-bar patterns
    df['pattern_morning_star'] = detect_morning_star(df)
    df['pattern_evening_star'] = detect_evening_star(df)
    df['pattern_three_white_soldiers'] = detect_three_white_soldiers(df)
    df['pattern_three_black_crows'] = detect_three_black_crows(df)
    
    # Breakout patterns
    df['pattern_breakout_20'] = detect_breakout_bar(df, 20)
    df['pattern_breakdown_20'] = detect_breakdown_bar(df, 20)
    df['pattern_breakout_10'] = detect_breakout_bar(df, 10)
    df['pattern_breakdown_10'] = detect_breakdown_bar(df, 10)
    
    # Range patterns
    df['pattern_range_expansion'] = detect_range_expansion(df, 20, 1.5)
    
    return df

def get_pattern_summary(df: pd.DataFrame) -> Dict[str, int]:
    """
    Get summary statistics of pattern occurrences
    
    Returns:
    --------
    Dict with pattern names and occurrence counts
    """
    pattern_cols = [col for col in df.columns if col.startswith('pattern_')]
    
    summary = {}
    for col in pattern_cols:
        pattern_name = col.replace('pattern_', '')
        count = df[col].sum()
        summary[pattern_name] = int(count)
    
    return summary



