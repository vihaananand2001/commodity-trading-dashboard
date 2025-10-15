#!/usr/bin/env python3
"""
Gold 1D Long Signal Generator
Implements the 3 optimized strategies for Gold 1D Long trading

Usage:
------
# Check for signals today
python signal_generator_gold_1d.py

# Check specific date
python signal_generator_gold_1d.py --date 2025-09-30

# Generate historical signals for validation
python signal_generator_gold_1d.py --validate
"""

import sys
import argparse
from datetime import datetime
from pathlib import Path
import pandas as pd

from utils import load_features, get_logger
from strategy_builder import StrategyBuilder

logger = get_logger(__name__)

# =============================================================================
# STRATEGY DEFINITIONS (From Optimization Results)
# =============================================================================

def strategy_1_range_expansion(df: pd.DataFrame) -> pd.Series:
    """
    STRATEGY #1: Range Expansion (PRIMARY)
    
    Performance: 40 trades, 70% WR, 2.86 PF, 13.69% DD
    """
    strategy = StrategyBuilder(df)
    
    # Pattern
    strategy.add_pattern('pattern_range_expansion')
    
    # Filters
    strategy.add_momentum_filter('rsi_14 >= 45')
    strategy.add_strength_filter('adx_14 >= 18')
    strategy.add_volatility_filter('atr_pct_14 >= 0.8')
    strategy.add_volatility_filter('atr_pct_14 <= 1.8')
    strategy.add_proximity_filter('dist_ema20 <= 1.0')
    strategy.add_volume_filter('volume_ratio >= 1.0')
    
    return strategy.get_entry_signal()

def strategy_2_inside_bar(df: pd.DataFrame) -> pd.Series:
    """
    STRATEGY #2: Inside Bar (ALTERNATIVE)
    
    Performance: 37 trades, 56.8% WR, 1.91 PF, 14.06% DD
    """
    strategy = StrategyBuilder(df)
    
    # Pattern
    strategy.add_pattern('pattern_inside_bar')
    
    # Filters
    strategy.add_momentum_filter('rsi_14 >= 45')
    strategy.add_strength_filter('adx_14 >= 28')  # Higher ADX
    strategy.add_volatility_filter('atr_pct_14 >= 0.9')
    strategy.add_volatility_filter('atr_pct_14 <= 1.8')
    strategy.add_proximity_filter('dist_ema20 <= 2.0')  # More flexible
    strategy.add_volume_filter('volume_ratio >= 0.8')
    
    return strategy.get_entry_signal()

def strategy_3_breakout_10(df: pd.DataFrame) -> pd.Series:
    """
    STRATEGY #3: Breakout 10 (CONSERVATIVE)
    
    Performance: 29 trades, 62.1% WR, 2.21 PF, 13.80% DD
    """
    strategy = StrategyBuilder(df)
    
    # Pattern
    strategy.add_pattern('pattern_breakout_10')
    
    # Filters
    strategy.add_trend_filter('price_above_ema20 == 1')  # Trend required
    strategy.add_momentum_filter('rsi_14 >= 40')
    strategy.add_strength_filter('adx_14 >= 18')
    strategy.add_volatility_filter('atr_pct_14 >= 0.5')
    strategy.add_volatility_filter('atr_pct_14 <= 2.5')
    strategy.add_proximity_filter('dist_ema20 <= 1.2')
    strategy.add_volume_filter('volume_ratio >= 1.0')
    
    return strategy.get_entry_signal()

# =============================================================================
# SIGNAL GENERATOR
# =============================================================================

def calculate_trade_levels(row: pd.Series, stop_atr: float = 1.2, tp_atr: float = 1.5) -> dict:
    """Calculate entry, stop loss, and take profit levels"""
    entry = row['close']
    atr = row['atr_14']
    
    stop_loss = entry - (stop_atr * atr)
    take_profit = entry + (tp_atr * atr)
    risk = entry - stop_loss
    reward = take_profit - entry
    
    return {
        'entry': entry,
        'stop_loss': stop_loss,
        'take_profit': take_profit,
        'risk': risk,
        'reward': reward,
        'risk_reward': reward / risk if risk > 0 else 0
    }

def check_signals(date: str = None, validate: bool = False):
    """
    Check for trading signals
    
    Parameters:
    -----------
    date : str, optional
        Specific date to check (format: YYYY-MM-DD)
    validate : bool
        Generate all historical signals for validation
    """
    logger.info("="*80)
    logger.info("GOLD 1D LONG - SIGNAL GENERATOR")
    logger.info("="*80)
    
    # Load data
    logger.info("\nLoading Gold 1D data...")
    df = load_features('gold', '1d')
    logger.info(f"Loaded {len(df)} bars from {df['time'].min()} to {df['time'].max()}")
    
    # Generate signals for all strategies
    logger.info("\nGenerating signals...")
    df['signal_range_expansion'] = strategy_1_range_expansion(df)
    df['signal_inside_bar'] = strategy_2_inside_bar(df)
    df['signal_breakout_10'] = strategy_3_breakout_10(df)
    
    # Count total signals
    total_signals_1 = df['signal_range_expansion'].sum()
    total_signals_2 = df['signal_inside_bar'].sum()
    total_signals_3 = df['signal_breakout_10'].sum()
    
    logger.info(f"  Strategy #1 (Range Expansion): {total_signals_1} signals")
    logger.info(f"  Strategy #2 (Inside Bar):      {total_signals_2} signals")
    logger.info(f"  Strategy #3 (Breakout 10):     {total_signals_3} signals")
    
    if validate:
        # Show all historical signals
        logger.info("\n" + "="*80)
        logger.info("HISTORICAL SIGNALS VALIDATION")
        logger.info("="*80)
        
        for strategy_col, strategy_name in [
            ('signal_range_expansion', 'Range Expansion'),
            ('signal_inside_bar', 'Inside Bar'),
            ('signal_breakout_10', 'Breakout 10')
        ]:
            signals = df[df[strategy_col] == True]
            
            if len(signals) > 0:
                logger.info(f"\n{strategy_name}: {len(signals)} signals")
                logger.info("-" * 80)
                
                for idx, row in signals.head(10).iterrows():
                    levels = calculate_trade_levels(row)
                    logger.info(f"  {row['time'].strftime('%Y-%m-%d')}: "
                              f"Entry={levels['entry']:.2f}, "
                              f"SL={levels['stop_loss']:.2f}, "
                              f"TP={levels['take_profit']:.2f}")
                
                if len(signals) > 10:
                    logger.info(f"  ... and {len(signals) - 10} more signals")
        
        return
    
    # Check specific date or latest
    if date:
        check_date = pd.to_datetime(date)
        df_check = df[df['time'] == check_date]
        
        if len(df_check) == 0:
            logger.error(f"\nDate {date} not found in data")
            logger.info(f"Available range: {df['time'].min()} to {df['time'].max()}")
            return
    else:
        # Check latest bar
        df_check = df.tail(1)
        check_date = df_check.iloc[0]['time']
    
    logger.info("\n" + "="*80)
    logger.info(f"CHECKING SIGNALS FOR: {check_date.strftime('%Y-%m-%d %A')}")
    logger.info("="*80)
    
    row = df_check.iloc[0]
    
    # Display market data
    logger.info(f"\n📊 Market Data:")
    logger.info(f"   Open:   ₹{row['open']:,.2f}")
    logger.info(f"   High:   ₹{row['high']:,.2f}")
    logger.info(f"   Low:    ₹{row['low']:,.2f}")
    logger.info(f"   Close:  ₹{row['close']:,.2f}")
    logger.info(f"   Volume: {row['Volume']:,.0f}")
    
    logger.info(f"\n📈 Indicators:")
    logger.info(f"   RSI(14):  {row['rsi_14']:.2f}")
    logger.info(f"   ADX(14):  {row['adx_14']:.2f}")
    logger.info(f"   ATR(14):  ₹{row['atr_14']:.2f} ({row['atr_pct_14']:.2f}%)")
    logger.info(f"   EMA(20):  ₹{row['ema_20']:,.2f}")
    logger.info(f"   EMA(50):  ₹{row['ema_50']:,.2f}")
    logger.info(f"   Vol Ratio: {row['volume_ratio']:.2f}x")
    
    # Check each strategy
    signals_found = []
    
    logger.info("\n" + "="*80)
    logger.info("SIGNAL CHECK:")
    logger.info("="*80)
    
    # Strategy #1: Range Expansion
    if row['signal_range_expansion']:
        signals_found.append('Range Expansion')
        levels = calculate_trade_levels(row)
        
        logger.info("\n🚨 STRATEGY #1: RANGE EXPANSION SIGNAL!")
        logger.info("   Status: PRIMARY STRATEGY ⭐")
        logger.info(f"   Expected Performance: 40 trades/yr, 70% WR, 2.86 PF")
        logger.info(f"\n   📍 Trade Levels:")
        logger.info(f"      Entry:       ₹{levels['entry']:,.2f}")
        logger.info(f"      Stop Loss:   ₹{levels['stop_loss']:,.2f}")
        logger.info(f"      Take Profit: ₹{levels['take_profit']:,.2f}")
        logger.info(f"      Risk:        ₹{levels['risk']:,.2f}")
        logger.info(f"      Reward:      ₹{levels['reward']:,.2f}")
        logger.info(f"      R:R Ratio:   {levels['risk_reward']:.2f}")
        logger.info(f"\n   ⏰ Max Hold: 5 days (exit by {(check_date + pd.Timedelta(days=5)).strftime('%Y-%m-%d')})")
    else:
        logger.info("\n⚪ Strategy #1 (Range Expansion): No signal")
    
    # Strategy #2: Inside Bar
    if row['signal_inside_bar']:
        signals_found.append('Inside Bar')
        levels = calculate_trade_levels(row)
        
        logger.info("\n🚨 STRATEGY #2: INSIDE BAR SIGNAL!")
        logger.info("   Status: ALTERNATIVE STRATEGY")
        logger.info(f"   Expected Performance: 37 trades/yr, 56.8% WR, 1.91 PF")
        logger.info(f"\n   📍 Trade Levels:")
        logger.info(f"      Entry:       ₹{levels['entry']:,.2f}")
        logger.info(f"      Stop Loss:   ₹{levels['stop_loss']:,.2f}")
        logger.info(f"      Take Profit: ₹{levels['take_profit']:,.2f}")
        logger.info(f"      Risk:        ₹{levels['risk']:,.2f}")
        logger.info(f"      Reward:      ₹{levels['reward']:,.2f}")
        logger.info(f"\n   ⏰ Max Hold: 5 days")
    else:
        logger.info("⚪ Strategy #2 (Inside Bar): No signal")
    
    # Strategy #3: Breakout 10
    if row['signal_breakout_10']:
        signals_found.append('Breakout 10')
        levels = calculate_trade_levels(row)
        
        logger.info("\n🚨 STRATEGY #3: BREAKOUT 10 SIGNAL!")
        logger.info("   Status: CONSERVATIVE STRATEGY")
        logger.info(f"   Expected Performance: 29 trades/yr, 62.1% WR, 2.21 PF")
        logger.info(f"\n   📍 Trade Levels:")
        logger.info(f"      Entry:       ₹{levels['entry']:,.2f}")
        logger.info(f"      Stop Loss:   ₹{levels['stop_loss']:,.2f}")
        logger.info(f"      Take Profit: ₹{levels['take_profit']:,.2f}")
        logger.info(f"      Risk:        ₹{levels['risk']:,.2f}")
        logger.info(f"      Reward:      ₹{levels['reward']:,.2f}")
        logger.info(f"\n   ⏰ Max Hold: 5 days")
    else:
        logger.info("⚪ Strategy #3 (Breakout 10): No signal")
    
    # Summary
    logger.info("\n" + "="*80)
    if len(signals_found) > 0:
        logger.info(f"✅ {len(signals_found)} SIGNAL(S) DETECTED: {', '.join(signals_found)}")
        logger.info("="*80)
        logger.info("\n💡 ACTION REQUIRED:")
        logger.info("   1. Review the trade levels above")
        logger.info("   2. Calculate position size based on your risk tolerance")
        logger.info("   3. Place entry order for next trading session")
        logger.info("   4. Set stop loss and take profit orders immediately")
        logger.info("   5. Mark calendar for time exit (Day 5)")
        
        if len(signals_found) > 1:
            logger.info(f"\n⚠️  Multiple signals detected!")
            logger.info(f"   Recommended: Use Strategy #1 (Range Expansion) as priority")
    else:
        logger.info("✋ NO SIGNALS TODAY")
        logger.info("="*80)
        logger.info("\n   Wait for next trading day")
    
    logger.info("\n")

def generate_trade_log():
    """Generate a trade log for the 3 strategies"""
    logger.info("="*80)
    logger.info("GENERATING TRADE LOG FOR ALL STRATEGIES")
    logger.info("="*80)
    
    df = load_features('gold', '1d')
    
    # Generate signals
    df['signal_1'] = strategy_1_range_expansion(df)
    df['signal_2'] = strategy_2_inside_bar(df)
    df['signal_3'] = strategy_3_breakout_10(df)
    
    # Create trade log
    trades = []
    
    for idx, row in df.iterrows():
        if row['signal_1'] or row['signal_2'] or row['signal_3']:
            levels = calculate_trade_levels(row)
            
            strategies = []
            if row['signal_1']:
                strategies.append('Range_Expansion')
            if row['signal_2']:
                strategies.append('Inside_Bar')
            if row['signal_3']:
                strategies.append('Breakout_10')
            
            trades.append({
                'date': row['time'],
                'strategies': '|'.join(strategies),
                'entry': levels['entry'],
                'stop_loss': levels['stop_loss'],
                'take_profit': levels['take_profit'],
                'risk': levels['risk'],
                'reward': levels['reward'],
                'rsi': row['rsi_14'],
                'adx': row['adx_14'],
                'atr_pct': row['atr_pct_14']
            })
    
    trades_df = pd.DataFrame(trades)
    
    # Save
    output_path = Path('models') / 'gold_1d_long_trade_log.csv'
    trades_df.to_csv(output_path, index=False)
    
    logger.info(f"\n✅ Trade log saved to: {output_path}")
    logger.info(f"   Total signal days: {len(trades_df)}")
    logger.info(f"   Date range: {trades_df['date'].min()} to {trades_df['date'].max()}")
    
    # Show stats
    logger.info(f"\n📊 Signal Distribution:")
    logger.info(f"   Range Expansion:  {df['signal_1'].sum()} signals")
    logger.info(f"   Inside Bar:       {df['signal_2'].sum()} signals")
    logger.info(f"   Breakout 10:      {df['signal_3'].sum()} signals")
    
    # Show recent signals
    logger.info(f"\n📅 Last 5 Signals:")
    logger.info("-" * 80)
    for _, trade in trades_df.tail(5).iterrows():
        logger.info(f"   {trade['date'].strftime('%Y-%m-%d')}: "
                   f"{trade['strategies']:30s} Entry=₹{trade['entry']:,.0f} "
                   f"SL=₹{trade['stop_loss']:,.0f} TP=₹{trade['take_profit']:,.0f}")
    
    logger.info("\n" + "="*80)

def main():
    parser = argparse.ArgumentParser(description="Gold 1D Long Signal Generator")
    parser.add_argument('--date', type=str, help='Specific date to check (YYYY-MM-DD)')
    parser.add_argument('--validate', action='store_true', help='Generate historical signals')
    parser.add_argument('--trade-log', action='store_true', help='Generate complete trade log')
    
    args = parser.parse_args()
    
    try:
        if args.trade_log:
            generate_trade_log()
        elif args.validate:
            check_signals(validate=True)
        else:
            check_signals(date=args.date)
    
    except FileNotFoundError as e:
        logger.error(f"\n❌ Error: {str(e)}")
        logger.error("Please run feature engineering first:")
        logger.error("  python src/main.py --build-features --commodity gold --timeframe 1d")
    except Exception as e:
        logger.error(f"\n❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()



