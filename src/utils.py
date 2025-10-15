"""
Utility functions for the commodity trading framework
"""
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def get_logger(name: str):
    """Get a logger instance"""
    return logging.getLogger(name)

def load_ohlc_data(commodity: str, timeframe: str, data_dir: str = "data/raw") -> pd.DataFrame:
    """
    Load OHLC data for a given commodity and timeframe
    
    Parameters:
    -----------
    commodity : str
        One of ['gold', 'silver', 'copper']
    timeframe : str
        One of ['1h', '4h', '1d']
    data_dir : str
        Base directory for raw data
        
    Returns:
    --------
    pd.DataFrame with columns: time, open, high, low, close, Volume
    """
    logger = get_logger(__name__)
    
    commodity = commodity.lower()
    timeframe = timeframe.lower()
    
    file_map = {
        ('gold', '1h'): 'gold_1H.csv',
        ('gold', '4h'): 'gold_4H.csv',
        ('gold', '1d'): 'gold_1D.csv',
        ('silver', '1h'): 'silver_1H.csv',
        ('silver', '4h'): 'silver_4H.csv',
        ('silver', '1d'): 'silver_1D.csv',
        ('copper', '1h'): 'copper_1H.csv',
        ('copper', '4h'): 'copper_4H.csv',
        ('copper', '1d'): 'copper_1D.csv',
    }
    
    if (commodity, timeframe) not in file_map:
        raise ValueError(f"Invalid commodity '{commodity}' or timeframe '{timeframe}'")
    
    file_name = file_map[(commodity, timeframe)]
    file_path = Path(data_dir) / timeframe / file_name
    
    if not file_path.exists():
        raise FileNotFoundError(f"Data file not found: {file_path}")
    
    logger.info(f"Loading {commodity.upper()} {timeframe.upper()} data from {file_path}")
    
    df = pd.read_csv(file_path)
    df['time'] = pd.to_datetime(df['time'])
    df = df.sort_values('time').reset_index(drop=True)
    
    logger.info(f"Loaded {len(df)} bars from {df['time'].min()} to {df['time'].max()}")
    
    return df

def save_features(df: pd.DataFrame, commodity: str, timeframe: str, output_dir: str = "data/processed"):
    """
    Save feature-engineered dataframe
    
    Parameters:
    -----------
    df : pd.DataFrame
        DataFrame with features
    commodity : str
        Commodity name
    timeframe : str
        Timeframe
    output_dir : str
        Output directory
    """
    logger = get_logger(__name__)
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    file_name = f"{commodity.lower()}_{timeframe.lower()}_features.csv"
    file_path = output_path / file_name
    
    df.to_csv(file_path, index=False)
    logger.info(f"Saved features to {file_path} ({len(df)} rows, {len(df.columns)} columns)")

def load_features(commodity: str, timeframe: str, data_dir: str = "data/processed") -> pd.DataFrame:
    """Load feature-engineered data"""
    file_name = f"{commodity.lower()}_{timeframe.lower()}_features.csv"
    file_path = Path(data_dir) / file_name
    
    if not file_path.exists():
        raise FileNotFoundError(f"Features file not found: {file_path}. Run feature engineering first.")
    
    df = pd.read_csv(file_path)
    df['time'] = pd.to_datetime(df['time'])
    
    return df

def calculate_returns(df: pd.DataFrame, price_col: str = 'close') -> pd.Series:
    """Calculate percentage returns"""
    return df[price_col].pct_change() * 100

def calculate_atr_percent(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculate ATR as percentage of close price"""
    from indicators import calculate_atr
    atr = calculate_atr(df, period)
    return (atr / df['close']) * 100

def create_summary_stats(results: pd.DataFrame) -> Dict:
    """
    Create summary statistics from backtest results
    
    Parameters:
    -----------
    results : pd.DataFrame
        Backtest results with trade data
        
    Returns:
    --------
    Dict with summary statistics
    """
    if len(results) == 0:
        return {
            'total_trades': 0,
            'win_rate': 0.0,
            'profit_factor': 0.0,
            'avg_win': 0.0,
            'avg_loss': 0.0,
            'max_dd_pct': 0.0,
            'total_pnl': 0.0
        }
    
    winners = results[results['pnl'] > 0]
    losers = results[results['pnl'] < 0]
    
    total_wins = winners['pnl'].sum() if len(winners) > 0 else 0
    total_losses = abs(losers['pnl'].sum()) if len(losers) > 0 else 0
    
    profit_factor = total_wins / total_losses if total_losses > 0 else (float('inf') if total_wins > 0 else 0)
    
    # Calculate drawdown
    equity_curve = results['pnl'].cumsum()
    running_max = equity_curve.expanding().max()
    drawdown = equity_curve - running_max
    max_dd = drawdown.min()
    
    # Calculate max DD as percentage of peak
    peak_at_max_dd = running_max[drawdown.idxmin()] if len(drawdown) > 0 else 1
    max_dd_pct = abs(max_dd / peak_at_max_dd * 100) if peak_at_max_dd != 0 else 0
    
    return {
        'total_trades': len(results),
        'winning_trades': len(winners),
        'losing_trades': len(losers),
        'win_rate': len(winners) / len(results) * 100 if len(results) > 0 else 0,
        'profit_factor': profit_factor,
        'avg_win': winners['pnl'].mean() if len(winners) > 0 else 0,
        'avg_loss': losers['pnl'].mean() if len(losers) > 0 else 0,
        'max_dd': max_dd,
        'max_dd_pct': max_dd_pct,
        'total_pnl': results['pnl'].sum(),
        'avg_pnl_per_trade': results['pnl'].mean()
    }

def get_all_commodities() -> List[str]:
    """Return list of all commodities"""
    return ['gold', 'silver', 'copper']

def get_all_timeframes() -> List[str]:
    """Return list of all timeframes"""
    return ['1h', '4h', '1d']

def get_all_combinations() -> List[Tuple[str, str]]:
    """Return all commodity-timeframe combinations"""
    return [(c, t) for c in get_all_commodities() for t in get_all_timeframes()]



