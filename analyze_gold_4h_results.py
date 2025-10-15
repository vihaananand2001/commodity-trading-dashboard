#!/usr/bin/env python3
"""
Analyze Gold 4H Optimization Results
Generate comprehensive summary of completed patterns
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, List

from src.utils import get_logger

logger = get_logger(__name__)

def analyze_gold_4h_results():
    """Analyze all completed Gold 4H optimization results"""
    
    logger.info(f"\n{'='*70}")
    logger.info("GOLD 4H OPTIMIZATION RESULTS ANALYSIS")
    logger.info(f"{'='*70}\n")
    
    # Directory with results
    results_dir = Path("reports/optimization/gold/4h")
    
    # Find all optimization files
    opt_files = list(results_dir.glob("*_long_optimization.csv"))
    
    if len(opt_files) == 0:
        logger.warning("No optimization files found!")
        return
    
    logger.info(f"Found {len(opt_files)} completed optimization files\n")
    
    # Analyze each file
    all_results = {}
    pattern_summaries = []
    
    for opt_file in sorted(opt_files):
        pattern_name = opt_file.stem.replace("_long_optimization", "")
        
        try:
            df = pd.read_csv(opt_file)
            
            if len(df) == 0:
                logger.warning(f"❌ {pattern_name}: No results")
                continue
            
            # Get top 3 results
            top_3 = df.head(3)
            
            all_results[pattern_name] = df
            
            # Summary stats
            summary = {
                'pattern': pattern_name,
                'total_strategies': len(df),
                'top_trades': df.iloc[0]['trades'],
                'top_win_rate': df.iloc[0]['win_rate'],
                'top_profit_factor': df.iloc[0]['profit_factor'],
                'top_pnl': df.iloc[0]['total_pnl'],
                'top_dd': df.iloc[0]['max_dd_pct'],
                'avg_trades': df['trades'].mean(),
                'avg_win_rate': df['win_rate'].mean(),
                'avg_profit_factor': df['profit_factor'].mean(),
                'max_pnl': df['total_pnl'].max(),
                'min_dd': df['max_dd_pct'].min(),
                'file_size_kb': opt_file.stat().st_size / 1024
            }
            
            pattern_summaries.append(summary)
            
            logger.info(f"✅ {pattern_name:25s} | "
                       f"Strategies: {len(df):4d} | "
                       f"Top: {df.iloc[0]['trades']:3.0f} trades, "
                       f"{df.iloc[0]['win_rate']:5.1f}% WR, "
                       f"PF {df.iloc[0]['profit_factor']:5.2f}, "
                       f"${df.iloc[0]['total_pnl']:7,.0f} PnL")
        
        except Exception as e:
            logger.error(f"❌ Error analyzing {pattern_name}: {str(e)}")
            continue
    
    if len(pattern_summaries) == 0:
        logger.warning("No valid results to analyze!")
        return
    
    # Create summary DataFrame
    summary_df = pd.DataFrame(pattern_summaries)
    
    # Sort by different criteria
    logger.info(f"\n{'='*70}")
    logger.info("TOP PATTERNS BY DIFFERENT CRITERIA")
    logger.info(f"{'='*70}\n")
    
    # Top by total strategies
    logger.info("📊 MOST STRATEGIES FOUND:")
    top_strategies = summary_df.nlargest(5, 'total_strategies')
    for _, row in top_strategies.iterrows():
        logger.info(f"  {row['pattern']:25s}: {row['total_strategies']:3.0f} strategies")
    
    # Top by best single strategy performance
    logger.info("\n🏆 BEST SINGLE STRATEGIES:")
    best_single = summary_df.nlargest(5, 'top_pnl')
    for _, row in best_single.iterrows():
        logger.info(f"  {row['pattern']:25s}: ${row['top_pnl']:8,.0f} PnL, "
                   f"{row['top_trades']:3.0f} trades, "
                   f"{row['top_win_rate']:5.1f}% WR")
    
    # Top by high win rate
    high_wr = summary_df[summary_df['top_win_rate'] >= 70].nlargest(5, 'top_win_rate')
    if len(high_wr) > 0:
        logger.info("\n🎯 HIGH WIN RATE (70%+):")
        for _, row in high_wr.iterrows():
            logger.info(f"  {row['pattern']:25s}: {row['top_win_rate']:5.1f}% WR, "
                       f"{row['top_trades']:3.0f} trades, "
                       f"${row['top_pnl']:8,.0f} PnL")
    
    # Top by high profit factor
    high_pf = summary_df[summary_df['top_profit_factor'] >= 3.0].nlargest(5, 'top_profit_factor')
    if len(high_pf) > 0:
        logger.info("\n💰 HIGH PROFIT FACTOR (3.0+):")
        for _, row in high_pf.iterrows():
            logger.info(f"  {row['pattern']:25s}: PF {row['top_profit_factor']:5.2f}, "
                       f"{row['top_trades']:3.0f} trades, "
                       f"${row['top_pnl']:8,.0f} PnL")
    
    # Top by low drawdown
    low_dd = summary_df.nsmallest(5, 'min_dd')
    logger.info("\n🛡️  LOWEST DRAWDOWN:")
    for _, row in low_dd.iterrows():
        logger.info(f"  {row['pattern']:25s}: {row['min_dd']:5.2f}% DD, "
                   f"{row['top_trades']:3.0f} trades, "
                   f"${row['top_pnl']:8,.0f} PnL")
    
    # Detailed analysis of top patterns
    logger.info(f"\n{'='*70}")
    logger.info("DETAILED ANALYSIS - TOP 5 PATTERNS")
    logger.info(f"{'='*70}\n")
    
    # Sort by combination of factors
    summary_df['composite_score'] = (
        summary_df['top_pnl'] / 1000 +  # PnL weight
        summary_df['top_win_rate'] +    # Win rate weight
        summary_df['top_profit_factor'] * 10 +  # PF weight
        -summary_df['min_dd']           # Drawdown penalty
    )
    
    top_5 = summary_df.nlargest(5, 'composite_score')
    
    for i, (_, row) in enumerate(top_5.iterrows(), 1):
        logger.info(f"\n{i}. {row['pattern'].upper()}")
        logger.info(f"   Best Strategy: {row['top_trades']:.0f} trades, "
                   f"{row['top_win_rate']:.1f}% WR, "
                   f"PF {row['top_profit_factor']:.2f}, "
                   f"${row['top_pnl']:,.0f} PnL, "
                   f"{row['min_dd']:.2f}% DD")
        logger.info(f"   Total Strategies: {row['total_strategies']:.0f}")
        logger.info(f"   Avg Performance: {row['avg_trades']:.1f} trades, "
                   f"{row['avg_win_rate']:.1f}% WR, "
                   f"PF {row['avg_profit_factor']:.2f}")
        
        # Show top 3 parameter sets
        if row['pattern'] in all_results:
            df = all_results[row['pattern']]
            logger.info("   Top 3 Parameter Sets:")
            for j in range(min(3, len(df))):
                r = df.iloc[j]
                logger.info(f"     {j+1}. SL:{r['stop_loss_atr']:.1f}, "
                           f"TP:{r['take_profit_atr']:.1f}, "
                           f"Hold:{r['max_hold_bars']:.0f}, "
                           f"RSI:{r.get('rsi_min', 'N/A')}, "
                           f"ADX:{r.get('adx_min', 'N/A')}")
    
    # Strategy recommendations
    logger.info(f"\n{'='*70}")
    logger.info("STRATEGY RECOMMENDATIONS FOR LIVE MCX")
    logger.info(f"{'='*70}\n")
    
    logger.info("🎯 RECOMMENDED FOR LIVE TRADING:")
    
    # High frequency + good performance
    high_freq = summary_df[summary_df['top_trades'] >= 100]
    if len(high_freq) > 0:
        logger.info("\n📈 HIGH FREQUENCY (100+ trades):")
        for _, row in high_freq.nlargest(3, 'top_pnl').iterrows():
            logger.info(f"  • {row['pattern']:25s}: {row['top_trades']:.0f} trades, "
                       f"${row['top_pnl']:,.0f} PnL, "
                       f"{row['top_win_rate']:.1f}% WR")
    
    # Conservative (low DD + good WR)
    conservative = summary_df[
        (summary_df['min_dd'] <= 15) & 
        (summary_df['top_win_rate'] >= 60)
    ]
    if len(conservative) > 0:
        logger.info("\n🛡️  CONSERVATIVE (Low DD + High WR):")
        for _, row in conservative.nlargest(3, 'top_pnl').iterrows():
            logger.info(f"  • {row['pattern']:25s}: {row['min_dd']:.1f}% DD, "
                       f"{row['top_win_rate']:.1f}% WR, "
                       f"${row['top_pnl']:,.0f} PnL")
    
    # Aggressive (high PnL)
    aggressive = summary_df.nlargest(3, 'max_pnl')
    logger.info("\n🚀 AGGRESSIVE (Highest PnL Potential):")
    for _, row in aggressive.iterrows():
        logger.info(f"  • {row['pattern']:25s}: ${row['max_pnl']:,.0f} PnL, "
                   f"{row['top_trades']:.0f} trades, "
                   f"{row['top_win_rate']:.1f}% WR")
    
    # Save summary
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    summary_file = results_dir / f"_ANALYSIS_SUMMARY_{timestamp}.csv"
    summary_df.to_csv(summary_file, index=False)
    logger.info(f"\n✅ Analysis summary saved to: {summary_file}")
    
    return summary_df, all_results

if __name__ == "__main__":
    analyze_gold_4h_results()
