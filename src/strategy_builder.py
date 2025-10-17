"""
Strategy Builder
Combines patterns and indicators to create trading strategies
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Callable, Optional
from utils import get_logger

logger = get_logger(__name__)

class StrategyBuilder:
    """
    Build trading strategies by combining patterns with indicator filters
    
    Example:
    --------
    strategy = StrategyBuilder(df)
    strategy.add_pattern('pattern_inside_bar')
    strategy.add_trend_filter('ema20 > ema50')
    strategy.add_momentum_filter('rsi_14 >= 55')
    strategy.add_strength_filter('adx_14 >= 20')
    
    entry_signal = strategy.get_entry_signal()
    """
    
    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.conditions = []
        self.description = []
        
    def add_condition(self, condition: pd.Series, description: str):
        """Add a condition to the strategy"""
        self.conditions.append(condition)
        self.description.append(description)
        return self
    
    def add_pattern(self, pattern_column: str):
        """Add a pattern condition"""
        if pattern_column not in self.df.columns:
            raise ValueError(f"Pattern column '{pattern_column}' not found in dataframe")
        
        condition = self.df[pattern_column] == 1
        self.add_condition(condition, f"Pattern: {pattern_column}")
        return self
    
    def add_trend_filter(self, condition_str: str):
        """
        Add a trend filter using string expression
        
        Examples:
        ---------
        'ema20 > ema50'
        'close > ema_20'
        'trend_ema_bull_short == 1'
        """
        try:
            condition = self.df.eval(condition_str)
            self.add_condition(condition, f"Trend: {condition_str}")
        except Exception as e:
            raise ValueError(f"Invalid trend filter '{condition_str}': {str(e)}")
        return self
    
    def add_momentum_filter(self, condition_str: str):
        """
        Add a momentum filter
        
        Examples:
        ---------
        'rsi_14 >= 55'
        'rsi_14 < 70'
        'macd > macd_signal'
        """
        try:
            condition = self.df.eval(condition_str)
            self.add_condition(condition, f"Momentum: {condition_str}")
        except Exception as e:
            raise ValueError(f"Invalid momentum filter '{condition_str}': {str(e)}")
        return self
    
    def add_strength_filter(self, condition_str: str):
        """
        Add a strength filter (ADX, trend strength)
        
        Examples:
        ---------
        'adx_14 >= 20'
        'adx_14 < 50'
        """
        try:
            condition = self.df.eval(condition_str)
            self.add_condition(condition, f"Strength: {condition_str}")
        except Exception as e:
            raise ValueError(f"Invalid strength filter '{condition_str}': {str(e)}")
        return self
    
    def add_volatility_filter(self, condition_str: str):
        """
        Add a volatility filter (ATR)
        
        Examples:
        ---------
        'atr_pct_14 >= 0.5'
        'atr_pct_14 <= 2.0'
        """
        try:
            condition = self.df.eval(condition_str)
            self.add_condition(condition, f"Volatility: {condition_str}")
        except Exception as e:
            raise ValueError(f"Invalid volatility filter '{condition_str}': {str(e)}")
        return self
    
    def add_proximity_filter(self, condition_str: str):
        """
        Add a proximity filter (distance from EMAs)
        
        Examples:
        ---------
        'dist_ema20 <= 1.5'
        'abs(close - ema_20) <= atr_14 * 2'
        """
        try:
            condition = self.df.eval(condition_str)
            self.add_condition(condition, f"Proximity: {condition_str}")
        except Exception as e:
            raise ValueError(f"Invalid proximity filter '{condition_str}': {str(e)}")
        return self
    
    def add_volume_filter(self, condition_str: str):
        """
        Add a volume filter
        
        Examples:
        ---------
        'volume_ratio >= 1.2'
        'Volume > volume_sma_20'
        """
        try:
            condition = self.df.eval(condition_str)
            self.add_condition(condition, f"Volume: {condition_str}")
        except Exception as e:
            raise ValueError(f"Invalid volume filter '{condition_str}': {str(e)}")
        return self
    
    def add_custom_filter(self, condition: pd.Series, description: str):
        """Add a custom condition"""
        self.add_condition(condition, f"Custom: {description}")
        return self
    
    def get_entry_signal(self) -> pd.Series:
        """
        Get final entry signal by combining all conditions
        
        Returns:
        --------
        pd.Series with boolean entry signals
        """
        if len(self.conditions) == 0:
            raise ValueError("No conditions added to strategy")
        
        # Combine all conditions with AND logic
        signal = self.conditions[0]
        for condition in self.conditions[1:]:
            signal = signal & condition
        
        return signal
    
    def get_description(self) -> str:
        """Get strategy description"""
        if len(self.description) == 0:
            return "Empty strategy"
        
        return " AND ".join(self.description)
    
    def count_signals(self) -> int:
        """Count number of entry signals"""
        return self.get_entry_signal().sum()
    
    def reset(self):
        """Reset strategy conditions"""
        self.conditions = []
        self.description = []
        return self


def create_pattern_strategy(
    df: pd.DataFrame,
    pattern: str,
    trend_condition: Optional[str] = None,
    rsi_min: Optional[float] = None,
    rsi_max: Optional[float] = None,
    adx_min: Optional[float] = None,
    atr_min: Optional[float] = None,
    atr_max: Optional[float] = None,
    ema_proximity: Optional[float] = None,
    volume_min: Optional[float] = None
) -> Callable:
    """
    Create a pattern-based strategy with indicator filters
    
    Parameters:
    -----------
    df : pd.DataFrame
        DataFrame with features
    pattern : str
        Pattern column name (e.g., 'pattern_inside_bar')
    trend_condition : str, optional
        Trend filter (e.g., 'ema20 > ema50')
    rsi_min : float, optional
        Minimum RSI value
    rsi_max : float, optional
        Maximum RSI value
    adx_min : float, optional
        Minimum ADX value
    atr_min : float, optional
        Minimum ATR percentage
    atr_max : float, optional
        Maximum ATR percentage
    ema_proximity : float, optional
        Maximum distance from EMA20 in ATR multiples
    volume_min : float, optional
        Minimum volume ratio
        
    Returns:
    --------
    Callable that returns entry signal
    """
    def entry_condition(df_input: pd.DataFrame) -> pd.Series:
        strategy = StrategyBuilder(df_input)
        
        # Add pattern
        strategy.add_pattern(pattern)
        
        # Add filters
        if trend_condition:
            strategy.add_trend_filter(trend_condition)
        
        if rsi_min is not None:
            strategy.add_momentum_filter(f'rsi_14 >= {rsi_min}')
        
        if rsi_max is not None:
            strategy.add_momentum_filter(f'rsi_14 <= {rsi_max}')
        
        if adx_min is not None:
            strategy.add_strength_filter(f'adx_14 >= {adx_min}')
        
        if atr_min is not None:
            strategy.add_volatility_filter(f'atr_pct_14 >= {atr_min}')
        
        if atr_max is not None:
            strategy.add_volatility_filter(f'atr_pct_14 <= {atr_max}')
        
        if ema_proximity is not None:
            strategy.add_proximity_filter(f'dist_ema20 <= {ema_proximity}')
        
        if volume_min is not None:
            strategy.add_volume_filter(f'volume_ratio >= {volume_min}')
        
        return strategy.get_entry_signal()
    
    return entry_condition


def get_default_patterns() -> List[str]:
    """Get list of primary patterns to test"""
    return [
        'pattern_inside_bar',
        'pattern_bullish_engulfing',
        'pattern_bullish_pin',
        'pattern_hammer',
        'pattern_morning_star',
        'pattern_three_white_soldiers',
        'pattern_breakout_20',
        'pattern_breakout_10',
        'pattern_range_expansion',
        'pattern_outside_bar',
        'pattern_harami_bull',
        'pattern_tweezer_bottom',
        'pattern_marubozu_bull'
    ]


def get_bearish_patterns() -> List[str]:
    """Get list of bearish patterns"""
    return [
        'pattern_bearish_engulfing',
        'pattern_bearish_pin',
        'pattern_shooting_star',
        'pattern_evening_star',
        'pattern_three_black_crows',
        'pattern_breakdown_20',
        'pattern_breakdown_10',
        'pattern_harami_bear',
        'pattern_tweezer_top',
        'pattern_marubozu_bear'
    ]


if __name__ == "__main__":
    # Example usage
    print("Strategy Builder Module")
    print("Use this module to create pattern + indicator strategies")





