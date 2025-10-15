#!/usr/bin/env python3
"""
Gold 1H Comprehensive Optimization
Process raw data and optimize 5 selected patterns for live MCX trading
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
from src.feature_engineering import FeatureEngineer
from src.optimizer import PatternOptimizer

logger = get_logger(__name__)

# Selected patterns for Gold 1H optimization (high-frequency, high-probability)
SELECTED_1H_PATTERNS = [
    'pattern_hammer',           # Reversal at support - high frequency
    'pattern_breakout_10',      # Momentum breakout - volume driver  
    'pattern_doji',             # Indecision before breakout - precision
    'pattern_inside_bar',       # Consolidation before move - balanced
    'pattern_bullish_engulfing' # Strong reversal - quality
]

def process_gold_1h_data():
    """Process raw Gold 1H data into features"""
    
    logger.info(f"\n{'='*70}")
    logger.info("PROCESSING GOLD 1H RAW DATA")
    logger.info(f"{'='*70}\n")
    
    raw_file = Path("data/raw/1h/gold_1H.csv")
    processed_file = Path("data/processed/gold_1h_features.csv")
    
    if not raw_file.exists():
        logger.error(f"Raw file not found: {raw_file}")
        return False
    
    if processed_file.exists():
        logger.info(f"Features already exist: {processed_file}")
        return True
    
    logger.info("Loading raw Gold 1H data...")
    try:
        df = pd.read_csv(raw_file)
        logger.info(f"Loaded {len(df)} raw bars")
        logger.info(f"Date range: {df.iloc[0]['time']} to {df.iloc[-1]['time']}")
        
        # Process features
        logger.info("Processing features...")
        engineer = FeatureEngineer()
        df_features = engineer.process_dataframe(df)
        
        # Save processed data
        df_features.to_csv(processed_file, index=False)
        logger.info(f"✅ Saved features to: {processed_file}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error processing data: {str(e)}")
        return False

def analyze_pattern_availability(df: pd.DataFrame, patterns: List[str]) -> List[str]:
    """Check which patterns exist and have sufficient occurrences"""
    
    logger.info(f"\n{'='*70}")
    logger.info("PATTERN AVAILABILITY ANALYSIS")
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
        elif count < 20:
            logger.warning(f"⚠️  {pattern}: {count} occurrences ({pct:.2f}%) - TOO FEW")
        elif count < 50:
            logger.info(f"⚠️  {pattern}: {count} occurrences ({pct:.2f}%) - LOW")
        else:
            logger.info(f"✅ {pattern}: {count} occurrences ({pct:.2f}%) - GOOD")
            valid_patterns.append(pattern)
    
    logger.info(f"\nValid patterns for optimization: {len(valid_patterns)}/{len(patterns)}")
    return valid_patterns

def optimize_gold_1h_patterns(patterns: List[str]):
    """Optimize selected Gold 1H patterns"""
    
    logger.info(f"\n{'='*70}")
    logger.info("GOLD 1H PATTERN OPTIMIZATION")
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
    logger.info(f"# OPTIMIZATION COMPLETE")
    logger.info(f"# Total time: {elapsed/60:.1f} minutes")
    logger.info(f"# Successful: {len(all_results)}/{len(valid_patterns)}")
    logger.info(f"{'#'*70}\n")
    
    return all_results

def analyze_gold_1h_results(all_results: Dict):
    """Analyze Gold 1H optimization results"""
    
    if len(all_results) == 0:
        logger.warning("No results to analyze!")
        return
    
    logger.info(f"\n{'='*70}")
    logger.info("GOLD 1H OPTIMIZATION ANALYSIS")
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
    logger.info("📊 TOP PATTERNS BY PERFORMANCE:\n")
    
    # Top by trade frequency (1H should have high frequency)
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
    
    # Save summary
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path("reports/optimization/gold/1h")
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_file = output_dir / f"_SUMMARY_{timestamp}.csv"
    summary_df.to_csv(summary_file, index=False)
    logger.info(f"\n✅ Summary saved to: {summary_file}")
    
    return summary_df

def main():
    """Main execution"""
    
    logger.info(f"\n{'#'*70}")
    logger.info(f"# GOLD 1H COMPREHENSIVE OPTIMIZATION")
    logger.info(f"# Patterns: {len(SELECTED_1H_PATTERNS)}")
    logger.info(f"{'#'*70}\n")
    
    # Step 1: Process raw data
    if not process_gold_1h_data():
        logger.error("Failed to process raw data!")
        return
    
    # Step 2: Optimize patterns
    all_results = optimize_gold_1h_patterns(SELECTED_1H_PATTERNS)
    
    # Step 3: Analyze results
    if len(all_results) > 0:
        summary_df = analyze_gold_1h_results(all_results)
    
    logger.info("\n✅ GOLD 1H OPTIMIZATION COMPLETE!")

if __name__ == "__main__":
    main()
