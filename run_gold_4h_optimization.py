#!/usr/bin/env python3
"""
Gold 4H Comprehensive Optimization
Run optimization for ALL patterns to find complementary strategies to Gold 1D
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import time
from typing import List, Dict

from src.utils import load_features, get_logger
from src.optimizer import PatternOptimizer

logger = get_logger(__name__)

# All available patterns
ALL_PATTERNS = [
    'pattern_inside_bar',
    'pattern_outside_bar',
    'pattern_doji',
    'pattern_hammer',
    'pattern_shooting_star',
    'pattern_pin_bar',
    'pattern_bullish_pin',
    'pattern_bearish_pin',
    'pattern_marubozu_bull',
    'pattern_marubozu_bear',
    'pattern_bullish_engulfing',
    'pattern_bearish_engulfing',
    'pattern_tweezer_bottom',
    'pattern_tweezer_top',
    'pattern_harami_bull',
    'pattern_harami_bear',
    'pattern_morning_star',
    'pattern_evening_star',
    'pattern_three_white_soldiers',
    'pattern_three_black_crows',
    'pattern_breakout_20',
    'pattern_breakdown_20',
    'pattern_breakout_10',
    'pattern_breakdown_10',
    'pattern_range_expansion'
]

def check_pattern_availability(df: pd.DataFrame, patterns: List[str]) -> List[str]:
    """Check which patterns exist and have occurrences"""
    valid_patterns = []
    
    logger.info(f"\n{'='*70}")
    logger.info("PATTERN AVAILABILITY CHECK")
    logger.info(f"{'='*70}")
    
    for pattern in patterns:
        if pattern not in df.columns:
            logger.warning(f"❌ {pattern}: Not in dataframe")
            continue
        
        count = df[pattern].sum()
        pct = (count / len(df)) * 100
        
        if count == 0:
            logger.warning(f"❌ {pattern}: 0 occurrences")
        elif count < 10:
            logger.warning(f"⚠️  {pattern}: {count} occurrences ({pct:.2f}%) - TOO FEW")
        else:
            logger.info(f"✅ {pattern}: {count} occurrences ({pct:.2f}%)")
            valid_patterns.append(pattern)
    
    logger.info(f"\nValid patterns: {len(valid_patterns)}/{len(patterns)}")
    return valid_patterns

def optimize_all_patterns(
    commodity: str = 'gold',
    timeframe: str = '4h',
    direction: str = 'long',
    patterns: List[str] = None,
    skip_existing: bool = True
):
    """
    Optimize all patterns for a given commodity-timeframe combination
    
    Parameters:
    -----------
    commodity : str
        Commodity name
    timeframe : str
        Timeframe
    direction : str
        'long' or 'short'
    patterns : List[str]
        List of patterns to optimize (None = all)
    skip_existing : bool
        Skip patterns with existing optimization files
    """
    
    logger.info(f"\n{'#'*70}")
    logger.info(f"# GOLD 4H COMPREHENSIVE OPTIMIZATION")
    logger.info(f"# Direction: {direction.upper()}")
    logger.info(f"{'#'*70}\n")
    
    # Load data
    logger.info("Loading Gold 4H features...")
    df = load_features(commodity, timeframe)
    logger.info(f"Loaded {len(df)} bars ({df['time'].iloc[0]} to {df['time'].iloc[-1]})\n")
    
    # Check pattern availability
    if patterns is None:
        patterns = ALL_PATTERNS
    
    valid_patterns = check_pattern_availability(df, patterns)
    
    if len(valid_patterns) == 0:
        logger.error("No valid patterns found!")
        return {}
    
    # Check for existing optimization files
    output_dir = Path("reports/optimization") / commodity / timeframe
    
    patterns_to_optimize = []
    skipped_patterns = []
    
    for pattern in valid_patterns:
        pattern_clean = pattern.replace('pattern_', '')
        opt_file = output_dir / f"{pattern_clean}_{direction}_optimization.csv"
        
        if skip_existing and opt_file.exists():
            skipped_patterns.append(pattern)
            logger.info(f"⏭️  Skipping {pattern} - already optimized")
        else:
            patterns_to_optimize.append(pattern)
    
    if len(skipped_patterns) > 0:
        logger.info(f"\nSkipped {len(skipped_patterns)} already optimized patterns")
    
    if len(patterns_to_optimize) == 0:
        logger.info("\n✅ All patterns already optimized!")
        return load_existing_results(commodity, timeframe, direction)
    
    logger.info(f"\n{'='*70}")
    logger.info(f"OPTIMIZING {len(patterns_to_optimize)} PATTERNS")
    logger.info(f"{'='*70}\n")
    
    # Run optimization for each pattern
    all_results = {}
    start_time = time.time()
    
    for i, pattern in enumerate(patterns_to_optimize, 1):
        logger.info(f"\n[{i}/{len(patterns_to_optimize)}] Optimizing: {pattern}")
        logger.info("-" * 70)
        
        try:
            optimizer = PatternOptimizer(
                commodity=commodity,
                timeframe=timeframe,
                pattern=pattern,
                direction=direction
            )
            
            results_df = optimizer.optimize(use_multiprocessing=True)
            
            if len(results_df) > 0:
                optimizer.save_results()
                all_results[pattern] = results_df
                logger.info(f"✅ {pattern}: {len(results_df)} valid strategies found")
            else:
                logger.warning(f"⚠️  {pattern}: No valid strategies found")
        
        except Exception as e:
            logger.error(f"❌ Error optimizing {pattern}: {str(e)}")
            continue
    
    elapsed = time.time() - start_time
    logger.info(f"\n{'#'*70}")
    logger.info(f"# OPTIMIZATION COMPLETE")
    logger.info(f"# Total time: {elapsed/60:.1f} minutes")
    logger.info(f"# Successful: {len(all_results)}/{len(patterns_to_optimize)}")
    logger.info(f"{'#'*70}\n")
    
    return all_results

def load_existing_results(commodity: str, timeframe: str, direction: str) -> Dict:
    """Load existing optimization results"""
    output_dir = Path("reports/optimization") / commodity / timeframe
    all_results = {}
    
    for opt_file in output_dir.glob(f"*_{direction}_optimization.csv"):
        pattern_name = opt_file.stem.replace(f"_{direction}_optimization", "")
        pattern_full = f"pattern_{pattern_name}"
        
        try:
            df = pd.read_csv(opt_file)
            if len(df) > 0:
                all_results[pattern_full] = df
                logger.info(f"✅ Loaded {pattern_full}: {len(df)} results")
        except Exception as e:
            logger.error(f"❌ Error loading {opt_file}: {str(e)}")
    
    return all_results

def create_summary_report(all_results: Dict, commodity: str, timeframe: str, direction: str):
    """Create comprehensive summary report"""
    
    if len(all_results) == 0:
        logger.warning("No results to summarize")
        return
    
    logger.info(f"\n{'='*70}")
    logger.info("OPTIMIZATION SUMMARY - TOP STRATEGIES")
    logger.info(f"{'='*70}\n")
    
    summary_data = []
    
    for pattern, results_df in all_results.items():
        if len(results_df) == 0:
            continue
        
        # Get top result
        top = results_df.iloc[0]
        
        summary_data.append({
            'pattern': pattern.replace('pattern_', ''),
            'trades': top['trades'],
            'win_rate': top['win_rate'],
            'profit_factor': top['profit_factor'],
            'max_dd_pct': top['max_dd_pct'],
            'total_pnl': top['total_pnl'],
            'avg_pnl_per_trade': top['avg_pnl_per_trade'],
            'avg_bars_held': top.get('avg_bars_held', 0),
            'stop_loss_atr': top['stop_loss_atr'],
            'take_profit_atr': top['take_profit_atr'],
            'max_hold_bars': top['max_hold_bars']
        })
    
    summary_df = pd.DataFrame(summary_data)
    
    # Sort by: trades (desc), PF (desc), win rate (desc)
    summary_df = summary_df.sort_values(
        ['trades', 'profit_factor', 'win_rate'],
        ascending=[False, False, False]
    ).reset_index(drop=True)
    
    # Print top 10
    logger.info("TOP 10 STRATEGIES (by trade count):\n")
    
    for i, row in summary_df.head(10).iterrows():
        logger.info(f"{i+1:2d}. {row['pattern']:25s} | "
                   f"Trades: {row['trades']:4.0f} | "
                   f"WR: {row['win_rate']:5.1f}% | "
                   f"PF: {row['profit_factor']:5.2f} | "
                   f"PnL: ${row['total_pnl']:8,.2f} | "
                   f"DD: {row['max_dd_pct']:5.2f}%")
    
    # Save summary
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path("reports/optimization") / commodity / timeframe
    summary_file = output_dir / f"_SUMMARY_{direction}_{timestamp}.csv"
    
    summary_df.to_csv(summary_file, index=False)
    logger.info(f"\n✅ Summary saved to: {summary_file}")
    
    # Strategy recommendations
    logger.info(f"\n{'='*70}")
    logger.info("STRATEGY RECOMMENDATIONS")
    logger.info(f"{'='*70}\n")
    
    # High frequency (trades >= 100)
    high_freq = summary_df[summary_df['trades'] >= 100]
    if len(high_freq) > 0:
        logger.info("📈 HIGH FREQUENCY STRATEGIES (100+ trades):")
        for _, row in high_freq.head(3).iterrows():
            logger.info(f"  • {row['pattern']:25s}: {row['trades']:.0f} trades, "
                       f"{row['win_rate']:.1f}% WR, PF {row['profit_factor']:.2f}")
    
    # High win rate (WR >= 65%)
    high_wr = summary_df[summary_df['win_rate'] >= 65]
    if len(high_wr) > 0:
        logger.info("\n🎯 HIGH WIN RATE STRATEGIES (65%+):")
        for _, row in high_wr.head(3).iterrows():
            logger.info(f"  • {row['pattern']:25s}: {row['win_rate']:.1f}% WR, "
                       f"{row['trades']:.0f} trades, PF {row['profit_factor']:.2f}")
    
    # High profit factor (PF >= 2.5)
    high_pf = summary_df[summary_df['profit_factor'] >= 2.5]
    if len(high_pf) > 0:
        logger.info("\n💰 HIGH PROFIT FACTOR STRATEGIES (2.5+):")
        for _, row in high_pf.head(3).iterrows():
            logger.info(f"  • {row['pattern']:25s}: PF {row['profit_factor']:.2f}, "
                       f"{row['trades']:.0f} trades, {row['win_rate']:.1f}% WR")
    
    # Low drawdown (DD <= 10%)
    low_dd = summary_df[summary_df['max_dd_pct'] <= 10]
    if len(low_dd) > 0:
        logger.info("\n🛡️  LOW DRAWDOWN STRATEGIES (10% or less):")
        for _, row in low_dd.head(3).iterrows():
            logger.info(f"  • {row['pattern']:25s}: {row['max_dd_pct']:.2f}% DD, "
                       f"{row['trades']:.0f} trades, {row['win_rate']:.1f}% WR")
    
    return summary_df

def main():
    """Main execution"""
    
    # Optimize all patterns for Gold 4H Long
    all_results = optimize_all_patterns(
        commodity='gold',
        timeframe='4h',
        direction='long',
        patterns=None,  # All patterns
        skip_existing=True  # Skip already optimized
    )
    
    # Create summary report
    if len(all_results) > 0:
        summary_df = create_summary_report(all_results, 'gold', '4h', 'long')
    
    logger.info("\n✅ OPTIMIZATION COMPLETE!")

if __name__ == "__main__":
    main()

