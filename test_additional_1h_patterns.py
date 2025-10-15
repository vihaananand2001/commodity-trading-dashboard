#!/usr/bin/env python3
"""
Test 2 Additional Gold 1H Patterns
Focus on high-frequency patterns that work well on 1H timeframe
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

from src.utils import get_logger, load_features
from src.optimizer import PatternOptimizer

logger = get_logger(__name__)

# Additional patterns to test (high-frequency, momentum-based)
ADDITIONAL_1H_PATTERNS = [
    'pattern_breakout_20',      # 20-bar breakout - higher timeframe momentum
    'pattern_outside_bar'       # Outside bar - volatility expansion
]

def analyze_pattern_availability(df: pd.DataFrame, patterns: List[str]) -> List[str]:
    """Check which patterns exist and have sufficient occurrences"""
    
    logger.info(f"\n{'='*70}")
    logger.info("ADDITIONAL 1H PATTERN AVAILABILITY ANALYSIS")
    logger.info(f"{'='*70}\n")
    
    valid_patterns = []
    
    for pattern in patterns:
        if pattern not in df.columns:
            logger.warning(f"❌ {pattern}: Not in dataframe")
            continue
        
        count = df[pattern].sum()
        pct = (count / len(df)) * 100
        
        if count == 0:
            logger.warning(f"❌ {pattern}: 0 occurrences")
        elif count < 100:
            logger.warning(f"⚠️  {pattern}: {count} occurrences ({pct:.2f}%) - TOO FEW")
        elif count < 300:
            logger.info(f"⚠️  {pattern}: {count} occurrences ({pct:.2f}%) - MODERATE")
        else:
            logger.info(f"✅ {pattern}: {count} occurrences ({pct:.2f}%) - EXCELLENT")
            valid_patterns.append(pattern)
    
    logger.info(f"\nValid patterns for optimization: {len(valid_patterns)}/{len(patterns)}")
    return valid_patterns

def optimize_additional_patterns(patterns: List[str]):
    """Optimize additional Gold 1H patterns"""
    
    logger.info(f"\n{'='*70}")
    logger.info("ADDITIONAL GOLD 1H PATTERN OPTIMIZATION")
    logger.info(f"{'='*70}\n")
    
    # Load data
    logger.info("Loading Gold 1H features...")
    df = load_features('gold', '1h')
    logger.info(f"Loaded {len(df)} bars")
    logger.info(f"Date range: {df['time'].iloc[0]} to {df['time'].iloc[-1]}")
    
    # Check pattern availability
    valid_patterns = analyze_pattern_availability(df, patterns)
    
    if len(valid_patterns) == 0:
        logger.error("No valid patterns found for optimization!")
        return {}
    
    # Run optimization for each pattern
    all_results = {}
    start_time = time.time()
    
    for i, pattern in enumerate(valid_patterns, 1):
        logger.info(f"\n[{i}/{len(valid_patterns)}] Optimizing: {pattern}")
        logger.info("-" * 70)
        
        try:
            optimizer = PatternOptimizer(
                commodity='gold',
                timeframe='1h',
                pattern=pattern,
                direction='long'
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
    logger.info(f"# ADDITIONAL OPTIMIZATION COMPLETE")
    logger.info(f"# Total time: {elapsed/60:.1f} minutes")
    logger.info(f"# Successful: {len(all_results)}/{len(valid_patterns)}")
    logger.info(f"{'#'*70}\n")
    
    return all_results

def analyze_additional_results(all_results: Dict):
    """Analyze additional Gold 1H optimization results"""
    
    if len(all_results) == 0:
        logger.warning("No results to analyze!")
        return
    
    logger.info(f"\n{'='*70}")
    logger.info("ADDITIONAL GOLD 1H OPTIMIZATION ANALYSIS")
    logger.info(f"{'='*70}\n")
    
    summary_data = []
    
    for pattern, results_df in all_results.items():
        if len(results_df) == 0:
            continue
        
        # Get top result
        top = results_df.iloc[0]
        
        summary_data.append({
            'pattern': pattern.replace('pattern_', ''),
            'total_strategies': len(results_df),
            'top_trades': top['trades'],
            'top_win_rate': top['win_rate'],
            'top_profit_factor': top['profit_factor'],
            'top_pnl': top['total_pnl'],
            'top_dd': top['max_dd_pct'],
            'avg_trades': results_df['trades'].mean(),
            'avg_win_rate': results_df['win_rate'].mean(),
            'avg_profit_factor': results_df['profit_factor'].mean(),
            'max_pnl': results_df['total_pnl'].max(),
            'min_dd': results_df['max_dd_pct'].min()
        })
    
    summary_df = pd.DataFrame(summary_data)
    
    # Sort by different criteria
    logger.info("📊 ADDITIONAL PATTERNS BY PERFORMANCE:\n")
    
    # Top by trade frequency
    logger.info("🚀 HIGH FREQUENCY (Most Trades):")
    top_freq = summary_df.nlargest(3, 'top_trades')
    for _, row in top_freq.iterrows():
        logger.info(f"  {row['pattern']:25s}: {row['top_trades']:4.0f} trades, "
                   f"${row['top_pnl']:8,.0f} PnL, "
                   f"{row['top_win_rate']:5.1f}% WR")
    
    # Top by win rate
    logger.info("\n🎯 HIGH WIN RATE:")
    top_wr = summary_df.nlargest(3, 'top_win_rate')
    for _, row in top_wr.iterrows():
        logger.info(f"  {row['pattern']:25s}: {row['top_win_rate']:5.1f}% WR, "
                   f"{row['top_trades']:4.0f} trades, "
                   f"${row['top_pnl']:8,.0f} PnL")
    
    # Top by profit factor
    logger.info("\n💰 HIGH PROFIT FACTOR:")
    top_pf = summary_df.nlargest(3, 'top_profit_factor')
    for _, row in top_pf.iterrows():
        logger.info(f"  {row['pattern']:25s}: PF {row['top_profit_factor']:5.2f}, "
                   f"{row['top_trades']:4.0f} trades, "
                   f"${row['top_pnl']:8,.0f} PnL")
    
    # Top by total PnL
    logger.info("\n💎 HIGHEST PnL:")
    top_pnl = summary_df.nlargest(3, 'top_pnl')
    for _, row in top_pnl.iterrows():
        logger.info(f"  {row['pattern']:25s}: ${row['top_pnl']:8,.0f} PnL, "
                   f"{row['top_trades']:4.0f} trades, "
                   f"{row['top_win_rate']:5.1f}% WR")
    
    # Compare with existing results
    logger.info(f"\n{'='*70}")
    logger.info("COMPARISON WITH EXISTING 1H STRATEGIES")
    logger.info(f"{'='*70}\n")
    
    logger.info("📈 EXISTING TOP STRATEGIES:")
    logger.info("  breakout_10              :   10 trades,  80.0% WR, $3,068 PnL, 6.5% DD")
    logger.info("  doji                     :   14 trades,  64.3% WR, $1,341 PnL, 14.8% DD")
    
    logger.info("\n🆕 NEW STRATEGIES:")
    for _, row in summary_df.iterrows():
        logger.info(f"  {row['pattern']:25s}: {row['top_trades']:4.0f} trades, "
                   f"{row['top_win_rate']:5.1f}% WR, "
                   f"${row['top_pnl']:8,.0f} PnL, "
                   f"{row['top_dd']:5.1f}% DD")
    
    # Strategy recommendations
    logger.info(f"\n{'='*70}")
    logger.info("UPDATED STRATEGY RECOMMENDATIONS")
    logger.info(f"{'='*70}\n")
    
    # High frequency
    high_freq = summary_df[summary_df['top_trades'] >= 10]
    if len(high_freq) > 0:
        logger.info("📈 HIGH FREQUENCY SCALPING (10+ trades):")
        for _, row in high_freq.nlargest(3, 'top_pnl').iterrows():
            logger.info(f"  • {row['pattern']:25s}: {row['top_trades']:.0f} trades, "
                       f"${row['top_pnl']:,.0f} PnL, "
                       f"{row['top_win_rate']:.1f}% WR, "
                       f"{row['top_dd']:.1f}% DD")
    
    # Conservative
    conservative = summary_df[
        (summary_df['top_dd'] <= 15) & 
        (summary_df['top_win_rate'] >= 60)
    ]
    if len(conservative) > 0:
        logger.info("\n🛡️  CONSERVATIVE SCALPING (Low DD + High WR):")
        for _, row in conservative.nlargest(3, 'top_pnl').iterrows():
            logger.info(f"  • {row['pattern']:25s}: {row['top_dd']:.1f}% DD, "
                       f"{row['top_win_rate']:.1f}% WR, "
                       f"${row['top_pnl']:,.0f} PnL")
    
    # Save summary
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path("reports/optimization/gold/1h")
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_file = output_dir / f"_ADDITIONAL_SUMMARY_{timestamp}.csv"
    summary_df.to_csv(summary_file, index=False)
    logger.info(f"\n✅ Additional summary saved to: {summary_file}")
    
    return summary_df

def main():
    """Main execution"""
    
    logger.info(f"\n{'#'*70}")
    logger.info(f"# ADDITIONAL GOLD 1H PATTERN TESTING")
    logger.info(f"# Testing Patterns: {len(ADDITIONAL_1H_PATTERNS)}")
    logger.info(f"{'#'*70}\n")
    
    # Optimize additional patterns
    all_results = optimize_additional_patterns(ADDITIONAL_1H_PATTERNS)
    
    # Analyze results
    if len(all_results) > 0:
        summary_df = analyze_additional_results(all_results)
    
    logger.info("\n✅ ADDITIONAL GOLD 1H TESTING COMPLETE!")

if __name__ == "__main__":
    main()
