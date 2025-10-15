"""
Technical Indicators Module
Implements all technical indicators used in the trading framework
"""
import pandas as pd
import numpy as np
from typing import Tuple

def calculate_ema(series: pd.Series, period: int) -> pd.Series:
    """Calculate Exponential Moving Average"""
    return series.ewm(span=period, adjust=False).mean()

def calculate_sma(series: pd.Series, period: int) -> pd.Series:
    """Calculate Simple Moving Average"""
    return series.rolling(window=period).mean()

def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """
    Calculate Relative Strength Index
    
    Parameters:
    -----------
    series : pd.Series
        Price series (typically close)
    period : int
        RSI period (default 14)
        
    Returns:
    --------
    pd.Series with RSI values
    """
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi

def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    Calculate Average True Range
    
    Parameters:
    -----------
    df : pd.DataFrame
        OHLC dataframe
    period : int
        ATR period
        
    Returns:
    --------
    pd.Series with ATR values
    """
    high = df['high']
    low = df['low']
    close = df['close']
    
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    
    return atr

def calculate_adx(df: pd.DataFrame, period: int = 14) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Calculate Average Directional Index (ADX), +DI, -DI
    
    Parameters:
    -----------
    df : pd.DataFrame
        OHLC dataframe
    period : int
        ADX period
        
    Returns:
    --------
    Tuple of (ADX, +DI, -DI) as pd.Series
    """
    high = df['high']
    low = df['low']
    close = df['close']
    
    # Calculate +DM and -DM
    up_move = high.diff()
    down_move = -low.diff()
    
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
    
    plus_dm = pd.Series(plus_dm, index=df.index)
    minus_dm = pd.Series(minus_dm, index=df.index)
    
    # Calculate ATR
    atr = calculate_atr(df, period)
    
    # Calculate smoothed +DM and -DM
    plus_dm_smooth = plus_dm.rolling(window=period).mean()
    minus_dm_smooth = minus_dm.rolling(window=period).mean()
    
    # Calculate +DI and -DI
    plus_di = 100 * (plus_dm_smooth / atr)
    minus_di = 100 * (minus_dm_smooth / atr)
    
    # Calculate DX
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    
    # Calculate ADX
    adx = dx.rolling(window=period).mean()
    
    return adx, plus_di, minus_di

def calculate_bollinger_bands(series: pd.Series, period: int = 20, std_dev: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Calculate Bollinger Bands
    
    Returns:
    --------
    Tuple of (middle_band, upper_band, lower_band)
    """
    middle = series.rolling(window=period).mean()
    std = series.rolling(window=period).std()
    
    upper = middle + (std * std_dev)
    lower = middle - (std * std_dev)
    
    return middle, upper, lower

def calculate_macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Calculate MACD
    
    Returns:
    --------
    Tuple of (macd_line, signal_line, histogram)
    """
    ema_fast = calculate_ema(series, fast)
    ema_slow = calculate_ema(series, slow)
    
    macd_line = ema_fast - ema_slow
    signal_line = calculate_ema(macd_line, signal)
    histogram = macd_line - signal_line
    
    return macd_line, signal_line, histogram

def calculate_stochastic(df: pd.DataFrame, k_period: int = 14, d_period: int = 3) -> Tuple[pd.Series, pd.Series]:
    """
    Calculate Stochastic Oscillator
    
    Returns:
    --------
    Tuple of (%K, %D)
    """
    low_min = df['low'].rolling(window=k_period).min()
    high_max = df['high'].rolling(window=k_period).max()
    
    k = 100 * (df['close'] - low_min) / (high_max - low_min)
    d = k.rolling(window=d_period).mean()
    
    return k, d

def calculate_obv(df: pd.DataFrame) -> pd.Series:
    """
    Calculate On-Balance Volume
    """
    obv = (np.sign(df['close'].diff()) * df['Volume']).fillna(0).cumsum()
    return obv

def calculate_vwap(df: pd.DataFrame) -> pd.Series:
    """
    Calculate Volume Weighted Average Price (intraday)
    Note: Typically resets each day, but here calculated cumulatively
    """
    typical_price = (df['high'] + df['low'] + df['close']) / 3
    vwap = (typical_price * df['Volume']).cumsum() / df['Volume'].cumsum()
    return vwap

def calculate_supertrend(df: pd.DataFrame, period: int = 10, multiplier: float = 3.0) -> Tuple[pd.Series, pd.Series]:
    """
    Calculate Supertrend indicator
    
    Returns:
    --------
    Tuple of (supertrend, direction)
    direction: 1 for uptrend, -1 for downtrend
    """
    atr = calculate_atr(df, period)
    hl_avg = (df['high'] + df['low']) / 2
    
    upper_band = hl_avg + (multiplier * atr)
    lower_band = hl_avg - (multiplier * atr)
    
    supertrend = pd.Series(index=df.index, dtype=float)
    direction = pd.Series(index=df.index, dtype=int)
    
    for i in range(len(df)):
        if i == 0:
            supertrend.iloc[i] = lower_band.iloc[i]
            direction.iloc[i] = 1
        else:
            if df['close'].iloc[i] > supertrend.iloc[i-1]:
                supertrend.iloc[i] = lower_band.iloc[i]
                direction.iloc[i] = 1
            else:
                supertrend.iloc[i] = upper_band.iloc[i]
                direction.iloc[i] = -1
                
            # Adjust bands
            if direction.iloc[i] == 1:
                if lower_band.iloc[i] < supertrend.iloc[i-1]:
                    supertrend.iloc[i] = supertrend.iloc[i-1]
            else:
                if upper_band.iloc[i] > supertrend.iloc[i-1]:
                    supertrend.iloc[i] = supertrend.iloc[i-1]
    
    return supertrend, direction

def add_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add all technical indicators to dataframe
    
    Parameters:
    -----------
    df : pd.DataFrame
        OHLC dataframe
        
    Returns:
    --------
    pd.DataFrame with all indicators added
    """
    df = df.copy()
    
    # Moving Averages
    df['ema_5'] = calculate_ema(df['close'], 5)
    df['ema_10'] = calculate_ema(df['close'], 10)
    df['ema_20'] = calculate_ema(df['close'], 20)
    df['ema_50'] = calculate_ema(df['close'], 50)
    df['ema_100'] = calculate_ema(df['close'], 100)
    df['ema_200'] = calculate_ema(df['close'], 200)
    
    df['sma_20'] = calculate_sma(df['close'], 20)
    df['sma_50'] = calculate_sma(df['close'], 50)
    df['sma_200'] = calculate_sma(df['close'], 200)
    
    # RSI (multiple periods)
    df['rsi_7'] = calculate_rsi(df['close'], 7)
    df['rsi_14'] = calculate_rsi(df['close'], 14)
    df['rsi_21'] = calculate_rsi(df['close'], 21)
    
    # ATR
    df['atr_7'] = calculate_atr(df, 7)
    df['atr_14'] = calculate_atr(df, 14)
    df['atr_21'] = calculate_atr(df, 21)
    
    # ATR as percentage
    df['atr_pct_7'] = (df['atr_7'] / df['close']) * 100
    df['atr_pct_14'] = (df['atr_14'] / df['close']) * 100
    df['atr_pct_21'] = (df['atr_21'] / df['close']) * 100
    
    # ADX
    df['adx_14'], df['plus_di_14'], df['minus_di_14'] = calculate_adx(df, 14)
    df['adx_20'], df['plus_di_20'], df['minus_di_20'] = calculate_adx(df, 20)
    
    # Bollinger Bands
    df['bb_middle_20'], df['bb_upper_20'], df['bb_lower_20'] = calculate_bollinger_bands(df['close'], 20, 2.0)
    
    # MACD
    df['macd'], df['macd_signal'], df['macd_hist'] = calculate_macd(df['close'])
    
    # Stochastic
    df['stoch_k'], df['stoch_d'] = calculate_stochastic(df, 14, 3)
    
    # Volume indicators
    df['obv'] = calculate_obv(df)
    df['volume_sma_20'] = df['Volume'].rolling(window=20).mean()
    df['volume_ratio'] = df['Volume'] / df['volume_sma_20']
    
    # Supertrend
    df['supertrend_10_3'], df['supertrend_dir'] = calculate_supertrend(df, 10, 3.0)
    
    # Distance from EMAs (for proximity filters)
    df['dist_ema20'] = abs(df['close'] - df['ema_20']) / df['atr_14']
    df['dist_ema50'] = abs(df['close'] - df['ema_50']) / df['atr_14']
    
    return df



