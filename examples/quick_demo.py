"""
Quick Demo: Testing a simple pattern strategy

This example shows how to:
1. Load feature-engineered data
2. Build a pattern-based strategy
3. Run a backtest
4. Analyze results
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from utils import load_features, get_logger
from strategy_builder import StrategyBuilder
from backtest_engine import simple_backtest
import pandas as pd

logger = get_logger(__name__)

def demo_simple_strategy():
    """
    Demo: Inside Bar + Trend + Momentum strategy for Gold 4H
    """
    logger.info("="*70)
    logger.info("DEMO: Inside Bar Strategy for Gold 4H")
    logger.info("="*70)
    
    # Load data
    logger.info("\n1. Loading feature-engineered data...")
    try:
        df = load_features('gold', '4h')
        logger.info(f"   Loaded {len(df)} bars from {df['time'].min()} to {df['time'].max()}")
    except FileNotFoundError:
        logger.error("\n   ERROR: Features not found!")
        logger.error("   Please run feature engineering first:")
        logger.error("   python src/main.py --build-features --commodity gold --timeframe 4h")
        return
    
    # Build strategy
    logger.info("\n2. Building strategy...")
    logger.info("   Pattern: Inside Bar")
    logger.info("   Trend Filter: EMA20 > EMA50 (bullish trend)")
    logger.info("   Momentum: RSI >= 55")
    logger.info("   Strength: ADX >= 20")
    logger.info("   Volatility: ATR% between 0.5% and 2.0%")
    
    strategy = StrategyBuilder(df)
    strategy.add_pattern('pattern_inside_bar')
    strategy.add_trend_filter('ema_20 > ema_50')
    strategy.add_momentum_filter('rsi_14 >= 55')
    strategy.add_strength_filter('adx_14 >= 20')
    strategy.add_volatility_filter('atr_pct_14 >= 0.5')
    strategy.add_volatility_filter('atr_pct_14 <= 2.0')
    
    entry_signal = strategy.get_entry_signal()
    signal_count = entry_signal.sum()
    
    logger.info(f"\n   Strategy generates {signal_count} entry signals")
    
    if signal_count == 0:
        logger.warning("   No entry signals! Try relaxing filters.")
        return
    
    # Run backtest
    logger.info("\n3. Running backtest...")
    logger.info("   Stop Loss: 2.0 ATR")
    logger.info("   Take Profit: 2.5 ATR")
    logger.info("   Max Hold: 10 bars")
    
    trades, summary = simple_backtest(
        df=df,
        entry_condition=lambda df: entry_signal,
        direction='long',
        stop_loss_atr=2.0,
        take_profit_atr=2.5,
        max_hold_bars=10,
        verbose=False
    )
    
    # Display results
    logger.info("\n4. Results:")
    logger.info("   " + "="*60)
    logger.info(f"   Total Trades:        {summary['total_trades']}")
    logger.info(f"   Winning Trades:      {summary['winning_trades']}")
    logger.info(f"   Losing Trades:       {summary['losing_trades']}")
    logger.info(f"   Win Rate:            {summary['win_rate']:.2f}%")
    logger.info(f"   Profit Factor:       {summary['profit_factor']:.2f}")
    logger.info(f"   Total PnL:           {summary['total_pnl']:.2f}")
    logger.info(f"   Avg PnL per Trade:   {summary['avg_pnl_per_trade']:.2f}")
    logger.info(f"   Avg Win:             {summary['avg_win']:.2f}")
    logger.info(f"   Avg Loss:            {summary['avg_loss']:.2f}")
    logger.info(f"   Max Drawdown:        {summary['max_dd_pct']:.2f}%")
    logger.info(f"   Avg Bars Held:       {summary['avg_bars_held']:.1f}")
    logger.info("   " + "="*60)
    
    # Exit reasons
    logger.info("\n5. Exit Reasons:")
    for reason, count in summary['exit_reasons'].items():
        pct = (count / summary['total_trades']) * 100
        logger.info(f"   {reason:20s}: {count:3d} ({pct:5.1f}%)")
    
    # Show first few trades
    if len(trades) > 0:
        logger.info("\n6. Sample Trades (first 5):")
        logger.info("   " + "-"*130)
        logger.info(f"   {'Entry Time':<20} {'Entry':<8} {'Exit Time':<20} {'Exit':<8} {'Reason':<15} {'PnL':<10} {'PnL%':<8} {'Bars':<5}")
        logger.info("   " + "-"*130)
        
        for i in range(min(5, len(trades))):
            trade = trades.iloc[i]
            logger.info(
                f"   {str(trade['entry_time']):<20} "
                f"{trade['entry_price']:<8.2f} "
                f"{str(trade['exit_time']):<20} "
                f"{trade['exit_price']:<8.2f} "
                f"{trade['exit_reason']:<15} "
                f"{trade['pnl']:<10.2f} "
                f"{trade['pnl_pct']:<8.2f} "
                f"{trade['bars_held']:<5.0f}"
            )
    
    # Evaluation
    logger.info("\n7. Evaluation:")
    
    meets_objectives = True
    
    if summary['profit_factor'] >= 1.25:
        logger.info("   ✓ Profit Factor >= 1.25")
    else:
        logger.info("   ✗ Profit Factor < 1.25")
        meets_objectives = False
    
    if summary['win_rate'] >= 60:
        logger.info("   ✓ Win Rate >= 60%")
    else:
        logger.info("   ✗ Win Rate < 60%")
        meets_objectives = False
    
    if summary['max_dd_pct'] <= 15:
        logger.info("   ✓ Drawdown <= 15%")
    else:
        logger.info("   ✗ Drawdown > 15%")
        meets_objectives = False
    
    if summary['total_trades'] >= 20:
        logger.info("   ✓ Sufficient trades (>= 20)")
    else:
        logger.info("   ! Low trade count (< 20)")
    
    if meets_objectives:
        logger.info("\n   🎉 Strategy meets all objectives!")
    else:
        logger.info("\n   📊 Strategy needs optimization")
        logger.info("   Tip: Run optimizer to find better parameters")
        logger.info("   python src/main.py --optimize-all --commodity gold --timeframe 4h --direction long")
    
    logger.info("\n" + "="*70)

def demo_pattern_comparison():
    """
    Demo: Compare multiple patterns on the same data
    """
    logger.info("\n" + "="*70)
    logger.info("DEMO: Pattern Comparison for Silver 4H")
    logger.info("="*70)
    
    try:
        df = load_features('silver', '4h')
    except FileNotFoundError:
        logger.error("Features not found. Run feature engineering first.")
        return
    
    patterns_to_test = [
        'pattern_inside_bar',
        'pattern_bullish_engulfing',
        'pattern_hammer',
        'pattern_bullish_pin',
        'pattern_breakout_20'
    ]
    
    results = []
    
    logger.info("\nTesting patterns with basic filters...")
    
    for pattern in patterns_to_test:
        # Simple strategy: pattern + trend
        strategy = StrategyBuilder(df)
        strategy.add_pattern(pattern)
        strategy.add_trend_filter('ema_20 > ema_50')
        
        entry_signal = strategy.get_entry_signal()
        
        if entry_signal.sum() == 0:
            logger.info(f"\n{pattern}: No signals")
            continue
        
        trades, summary = simple_backtest(
            df=df,
            entry_condition=lambda df, sig=entry_signal: sig,
            direction='long',
            stop_loss_atr=2.0,
            take_profit_atr=2.5,
            verbose=False
        )
        
        results.append({
            'pattern': pattern.replace('pattern_', ''),
            'trades': summary['total_trades'],
            'win_rate': summary['win_rate'],
            'profit_factor': summary['profit_factor'],
            'max_dd': summary['max_dd_pct'],
            'total_pnl': summary['total_pnl']
        })
    
    if len(results) > 0:
        results_df = pd.DataFrame(results)
        results_df = results_df.sort_values('profit_factor', ascending=False)
        
        logger.info("\n" + "="*100)
        logger.info(f"{'Pattern':<25} {'Trades':<8} {'Win%':<8} {'PF':<8} {'DD%':<8} {'Total PnL':<12}")
        logger.info("="*100)
        
        for _, row in results_df.iterrows():
            logger.info(
                f"{row['pattern']:<25} "
                f"{row['trades']:<8.0f} "
                f"{row['win_rate']:<8.1f} "
                f"{row['profit_factor']:<8.2f} "
                f"{row['max_dd']:<8.2f} "
                f"{row['total_pnl']:<12.2f}"
            )
        
        logger.info("="*100)
        
        best = results_df.iloc[0]
        logger.info(f"\n🏆 Best Pattern: {best['pattern']} (PF={best['profit_factor']:.2f}, WR={best['win_rate']:.1f}%)")
    
    logger.info("\n" + "="*70)

if __name__ == "__main__":
    print("\n")
    print("╔════════════════════════════════════════════════════════════════╗")
    print("║        Commodity Trading Framework - Quick Demo               ║")
    print("╚════════════════════════════════════════════════════════════════╝")
    print("\n")
    
    # Run demos
    demo_simple_strategy()
    
    # Uncomment to run pattern comparison
    # demo_pattern_comparison()
    
    print("\n")
    print("="*70)
    print("Demo complete!")
    print("\nNext steps:")
    print("  1. Modify parameters in the demo code above")
    print("  2. Run full optimization: python src/main.py --optimize-all --commodity gold --timeframe 4h")
    print("  3. Build your own strategies using StrategyBuilder")
    print("="*70)
    print("\n")




