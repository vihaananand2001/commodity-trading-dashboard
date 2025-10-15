"""
Backtesting Engine
Comprehensive backtesting system with SL/TP, time-based exits, and performance metrics
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Callable, Optional, Tuple
from dataclasses import dataclass
from utils import get_logger, create_summary_stats

logger = get_logger(__name__)

@dataclass
class Trade:
    """Represents a single trade"""
    entry_idx: int
    entry_time: pd.Timestamp
    entry_price: float
    direction: str  # 'long' or 'short'
    stop_loss: float
    take_profit: float
    exit_idx: Optional[int] = None
    exit_time: Optional[pd.Timestamp] = None
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None
    bars_held: Optional[int] = None
    mae: Optional[float] = None  # Maximum Adverse Excursion
    mfe: Optional[float] = None  # Maximum Favorable Excursion

class BacktestEngine:
    """
    Universal backtesting engine for pattern-based strategies
    
    Parameters:
    -----------
    df : pd.DataFrame
        DataFrame with OHLC and features
    entry_conditions : callable
        Function that takes df and returns boolean Series for entries
    direction : str
        'long' or 'short'
    stop_loss_atr : float
        Stop loss in ATR multiples
    take_profit_atr : float
        Take profit in ATR multiples
    max_hold_bars : int
        Maximum bars to hold trade (None for no limit)
    breakeven_at_tp1 : bool
        Move SL to breakeven at TP1 (half of TP)
    atr_column : str
        ATR column to use for SL/TP calculation
    """
    
    def __init__(
        self,
        df: pd.DataFrame,
        entry_conditions: Callable,
        direction: str = 'long',
        stop_loss_atr: float = 2.0,
        take_profit_atr: float = 3.0,
        max_hold_bars: Optional[int] = None,
        breakeven_at_tp1: bool = False,
        atr_column: str = 'atr_14'
    ):
        self.df = df.copy().reset_index(drop=True)
        self.entry_conditions = entry_conditions
        self.direction = direction.lower()
        self.stop_loss_atr = stop_loss_atr
        self.take_profit_atr = take_profit_atr
        self.max_hold_bars = max_hold_bars
        self.breakeven_at_tp1 = breakeven_at_tp1
        self.atr_column = atr_column
        
        self.trades: List[Trade] = []
        self.in_trade = False
        self.current_trade: Optional[Trade] = None
        
    def calculate_stop_and_target(self, idx: int) -> Tuple[float, float]:
        """Calculate stop loss and take profit levels"""
        entry_price = self.df.loc[idx, 'close']
        atr = self.df.loc[idx, self.atr_column]
        
        if self.direction == 'long':
            stop_loss = entry_price - (self.stop_loss_atr * atr)
            take_profit = entry_price + (self.take_profit_atr * atr)
        else:  # short
            stop_loss = entry_price + (self.stop_loss_atr * atr)
            take_profit = entry_price - (self.take_profit_atr * atr)
            
        return stop_loss, take_profit
    
    def check_exit(self, idx: int) -> Tuple[bool, Optional[str], Optional[float]]:
        """
        Check if current trade should be exited
        
        Returns:
        --------
        Tuple of (should_exit, exit_reason, exit_price)
        """
        if not self.in_trade or self.current_trade is None:
            return False, None, None
        
        high = self.df.loc[idx, 'high']
        low = self.df.loc[idx, 'low']
        close = self.df.loc[idx, 'close']
        
        bars_held = idx - self.current_trade.entry_idx
        
        # Check time-based exit
        if self.max_hold_bars is not None and bars_held >= self.max_hold_bars:
            return True, 'time_exit', close
        
        if self.direction == 'long':
            # Check stop loss
            if low <= self.current_trade.stop_loss:
                return True, 'stop_loss', self.current_trade.stop_loss
            
            # Check take profit
            if high >= self.current_trade.take_profit:
                return True, 'take_profit', self.current_trade.take_profit
            
            # Check breakeven
            if self.breakeven_at_tp1:
                tp1 = self.current_trade.entry_price + (
                    (self.current_trade.take_profit - self.current_trade.entry_price) / 2
                )
                if high >= tp1 and self.current_trade.stop_loss < self.current_trade.entry_price:
                    self.current_trade.stop_loss = self.current_trade.entry_price
                    
        else:  # short
            # Check stop loss
            if high >= self.current_trade.stop_loss:
                return True, 'stop_loss', self.current_trade.stop_loss
            
            # Check take profit
            if low <= self.current_trade.take_profit:
                return True, 'take_profit', self.current_trade.take_profit
            
            # Check breakeven
            if self.breakeven_at_tp1:
                tp1 = self.current_trade.entry_price - (
                    (self.current_trade.entry_price - self.current_trade.take_profit) / 2
                )
                if low <= tp1 and self.current_trade.stop_loss > self.current_trade.entry_price:
                    self.current_trade.stop_loss = self.current_trade.entry_price
        
        return False, None, None
    
    def calculate_mae_mfe(self, trade: Trade) -> Tuple[float, float]:
        """Calculate Maximum Adverse and Favorable Excursion"""
        if trade.exit_idx is None:
            return 0.0, 0.0
        
        trade_slice = self.df.loc[trade.entry_idx:trade.exit_idx]
        
        if self.direction == 'long':
            # MAE: worst drawdown (lowest low relative to entry)
            mae = ((trade_slice['low'].min() - trade.entry_price) / trade.entry_price) * 100
            # MFE: best profit (highest high relative to entry)
            mfe = ((trade_slice['high'].max() - trade.entry_price) / trade.entry_price) * 100
        else:  # short
            # MAE: worst drawdown (highest high relative to entry)
            mae = ((trade.entry_price - trade_slice['high'].max()) / trade.entry_price) * 100
            # MFE: best profit (lowest low relative to entry)
            mfe = ((trade.entry_price - trade_slice['low'].min()) / trade.entry_price) * 100
        
        return mae, mfe
    
    def run(self) -> pd.DataFrame:
        """
        Run the backtest
        
        Returns:
        --------
        pd.DataFrame with trade results
        """
        logger.info(f"Running backtest ({self.direction}) with {len(self.df)} bars...")
        
        # Get entry signals
        entry_signals = self.entry_conditions(self.df)
        
        # Ensure entry_signals is a Series with same index as df
        if not isinstance(entry_signals, pd.Series):
            entry_signals = pd.Series(entry_signals, index=self.df.index)
        
        logger.info(f"Found {entry_signals.sum()} potential entry signals")
        
        # Main loop
        for idx in range(len(self.df)):
            # Check for exit if in trade
            if self.in_trade:
                should_exit, exit_reason, exit_price = self.check_exit(idx)
                
                if should_exit and self.current_trade is not None:
                    # Close trade
                    self.current_trade.exit_idx = idx
                    self.current_trade.exit_time = self.df.loc[idx, 'time']
                    self.current_trade.exit_price = exit_price
                    self.current_trade.exit_reason = exit_reason
                    self.current_trade.bars_held = idx - self.current_trade.entry_idx
                    
                    # Calculate PnL
                    if self.direction == 'long':
                        self.current_trade.pnl = exit_price - self.current_trade.entry_price
                    else:
                        self.current_trade.pnl = self.current_trade.entry_price - exit_price
                    
                    self.current_trade.pnl_pct = (
                        self.current_trade.pnl / self.current_trade.entry_price
                    ) * 100
                    
                    # Calculate MAE/MFE
                    mae, mfe = self.calculate_mae_mfe(self.current_trade)
                    self.current_trade.mae = mae
                    self.current_trade.mfe = mfe
                    
                    # Store trade
                    self.trades.append(self.current_trade)
                    
                    # Reset state
                    self.in_trade = False
                    self.current_trade = None
            
            # Check for new entry if not in trade
            if not self.in_trade and entry_signals.iloc[idx]:
                # Enter trade
                stop_loss, take_profit = self.calculate_stop_and_target(idx)
                
                self.current_trade = Trade(
                    entry_idx=idx,
                    entry_time=self.df.loc[idx, 'time'],
                    entry_price=self.df.loc[idx, 'close'],
                    direction=self.direction,
                    stop_loss=stop_loss,
                    take_profit=take_profit
                )
                
                self.in_trade = True
        
        # Close any open trade at end
        if self.in_trade and self.current_trade is not None:
            idx = len(self.df) - 1
            self.current_trade.exit_idx = idx
            self.current_trade.exit_time = self.df.loc[idx, 'time']
            self.current_trade.exit_price = self.df.loc[idx, 'close']
            self.current_trade.exit_reason = 'end_of_data'
            self.current_trade.bars_held = idx - self.current_trade.entry_idx
            
            if self.direction == 'long':
                self.current_trade.pnl = (
                    self.current_trade.exit_price - self.current_trade.entry_price
                )
            else:
                self.current_trade.pnl = (
                    self.current_trade.entry_price - self.current_trade.exit_price
                )
            
            self.current_trade.pnl_pct = (
                self.current_trade.pnl / self.current_trade.entry_price
            ) * 100
            
            mae, mfe = self.calculate_mae_mfe(self.current_trade)
            self.current_trade.mae = mae
            self.current_trade.mfe = mfe
            
            self.trades.append(self.current_trade)
        
        logger.info(f"Backtest complete: {len(self.trades)} trades executed")
        
        # Convert to DataFrame
        return self.trades_to_dataframe()
    
    def trades_to_dataframe(self) -> pd.DataFrame:
        """Convert trades list to DataFrame"""
        if len(self.trades) == 0:
            return pd.DataFrame()
        
        trades_data = []
        for trade in self.trades:
            trades_data.append({
                'entry_time': trade.entry_time,
                'entry_price': trade.entry_price,
                'exit_time': trade.exit_time,
                'exit_price': trade.exit_price,
                'direction': trade.direction,
                'stop_loss': trade.stop_loss,
                'take_profit': trade.take_profit,
                'exit_reason': trade.exit_reason,
                'pnl': trade.pnl,
                'pnl_pct': trade.pnl_pct,
                'bars_held': trade.bars_held,
                'mae': trade.mae,
                'mfe': trade.mfe
            })
        
        return pd.DataFrame(trades_data)
    
    def get_summary(self) -> Dict:
        """Get performance summary"""
        trades_df = self.trades_to_dataframe()
        
        if len(trades_df) == 0:
            return {
                'total_trades': 0,
                'win_rate': 0.0,
                'profit_factor': 0.0,
                'max_dd_pct': 0.0,
                'total_pnl': 0.0
            }
        
        summary = create_summary_stats(trades_df)
        
        # Add additional metrics
        summary['avg_bars_held'] = trades_df['bars_held'].mean()
        summary['avg_mae'] = trades_df['mae'].mean()
        summary['avg_mfe'] = trades_df['mfe'].mean()
        
        # Exit reason breakdown
        exit_reasons = trades_df['exit_reason'].value_counts().to_dict()
        summary['exit_reasons'] = exit_reasons
        
        return summary

def simple_backtest(
    df: pd.DataFrame,
    entry_condition: Callable,
    direction: str = 'long',
    stop_loss_atr: float = 2.0,
    take_profit_atr: float = 3.0,
    max_hold_bars: Optional[int] = None,
    verbose: bool = True
) -> Tuple[pd.DataFrame, Dict]:
    """
    Simple backtest wrapper
    
    Returns:
    --------
    Tuple of (trades_df, summary_dict)
    """
    engine = BacktestEngine(
        df=df,
        entry_conditions=entry_condition,
        direction=direction,
        stop_loss_atr=stop_loss_atr,
        take_profit_atr=take_profit_atr,
        max_hold_bars=max_hold_bars
    )
    
    trades_df = engine.run()
    summary = engine.get_summary()
    
    if verbose and len(trades_df) > 0:
        logger.info(f"\n{'='*60}")
        logger.info(f"BACKTEST SUMMARY ({direction.upper()})")
        logger.info(f"{'='*60}")
        logger.info(f"Total Trades:     {summary['total_trades']}")
        logger.info(f"Win Rate:         {summary['win_rate']:.2f}%")
        logger.info(f"Profit Factor:    {summary['profit_factor']:.2f}")
        logger.info(f"Total PnL:        {summary['total_pnl']:.2f}")
        logger.info(f"Avg PnL/Trade:    {summary['avg_pnl_per_trade']:.2f}")
        logger.info(f"Max DD:           {summary['max_dd_pct']:.2f}%")
        logger.info(f"Avg Bars Held:    {summary['avg_bars_held']:.1f}")
        logger.info(f"{'='*60}\n")
    
    return trades_df, summary




