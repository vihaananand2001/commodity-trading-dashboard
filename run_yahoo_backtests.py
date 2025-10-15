#!/usr/bin/env python3
"""
Yahoo Finance Backtesting Script
Runs backtests on live Yahoo Finance data for all commodities and timeframes
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.yahoo_backtest_engine import YahooBacktestEngine
from src.utils import get_logger
import pandas as pd
from datetime import datetime

logger = get_logger(__name__)

def run_comprehensive_yahoo_backtests():
    """Run Yahoo Finance backtests for all commodities and timeframes."""
    
    print("🚀 Yahoo Finance Live Backtesting")
    print("=" * 60)
    print(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📊 Data Source: Yahoo Finance (Live)")
    print("=" * 60)
    
    engine = YahooBacktestEngine()
    
    # Define test configurations
    test_configs = [
        # Gold tests
        {'commodity': 'GOLD', 'timeframe': '1d', 'period': '1y', 'description': 'Gold 1D (1 year)'},
        {'commodity': 'GOLD', 'timeframe': '4h', 'period': '90d', 'description': 'Gold 4H (90 days)'},
        {'commodity': 'GOLD', 'timeframe': '1h', 'period': '30d', 'description': 'Gold 1H (30 days)'},
        
        # Silver tests  
        {'commodity': 'SILVER', 'timeframe': '1d', 'period': '1y', 'description': 'Silver 1D (1 year)'},
        {'commodity': 'SILVER', 'timeframe': '4h', 'period': '90d', 'description': 'Silver 4H (90 days)'},
        {'commodity': 'SILVER', 'timeframe': '1h', 'period': '30d', 'description': 'Silver 1H (30 days)'},
    ]
    
    results = []
    
    for config in test_configs:
        print(f"\n📊 Testing {config['description']}:")
        print("-" * 40)
        
        try:
            result = engine.run_yahoo_backtest(
                config['commodity'], 
                config['timeframe'], 
                config['period']
            )
            
            if 'error' in result:
                print(f"❌ Error: {result['error']}")
                continue
            
            # Extract key metrics
            performance = result['performance']
            
            print(f"✅ Data Points: {result['data_points']}")
            print(f"✅ Date Range: {result['date_range']}")
            print(f"✅ Total Trades: {performance['total_trades']}")
            print(f"✅ Win Rate: {performance['win_rate']:.1f}%")
            print(f"✅ Total PnL: ₹{performance['total_pnl']:,.2f}")
            print(f"✅ Profit Factor: {performance['profit_factor']:.2f}")
            print(f"✅ Max Drawdown: {performance['max_drawdown_pct']:.1f}%")
            print(f"✅ Sharpe Ratio: {performance['sharpe_ratio']:.2f}")
            
            # Store results for summary
            results.append({
                'commodity': config['commodity'],
                'timeframe': config['timeframe'],
                'period': config['period'],
                'data_points': result['data_points'],
                'total_trades': performance['total_trades'],
                'win_rate': performance['win_rate'],
                'total_pnl': performance['total_pnl'],
                'profit_factor': performance['profit_factor'],
                'max_drawdown_pct': performance['max_drawdown_pct'],
                'sharpe_ratio': performance['sharpe_ratio']
            })
            
            # Show sample trades if available
            trades = result['trades']
            if trades:
                print(f"📈 Sample Trades:")
                for i, trade in enumerate(trades[:3]):  # Show first 3 trades
                    print(f"   {i+1}. {trade.entry_time.strftime('%Y-%m-%d')} - "
                          f"{trade.strategy_name} - "
                          f"{'WIN' if trade.pnl > 0 else 'LOSS'} - "
                          f"₹{trade.pnl:,.2f} ({trade.pnl_pct:.2f}%)")
                
                if len(trades) > 3:
                    print(f"   ... and {len(trades) - 3} more trades")
            
        except Exception as e:
            print(f"❌ Error running backtest: {e}")
            logger.error(f"Error running backtest for {config['description']}: {e}")
    
    # Summary report
    print("\n" + "=" * 60)
    print("📋 YAHOO FINANCE BACKTEST SUMMARY")
    print("=" * 60)
    
    if results:
        df_results = pd.DataFrame(results)
        
        print(f"\n📊 Overall Performance:")
        print(f"   Total Tests: {len(results)}")
        print(f"   Total Trades: {df_results['total_trades'].sum()}")
        print(f"   Average Win Rate: {df_results['win_rate'].mean():.1f}%")
        print(f"   Total PnL: ₹{df_results['total_pnl'].sum():,.2f}")
        print(f"   Average Profit Factor: {df_results['profit_factor'].mean():.2f}")
        
        print(f"\n🏆 Best Performing:")
        best_pnl = df_results.loc[df_results['total_pnl'].idxmax()]
        print(f"   Best PnL: {best_pnl['commodity']} {best_pnl['timeframe']} - ₹{best_pnl['total_pnl']:,.2f}")
        
        best_winrate = df_results.loc[df_results['win_rate'].idxmax()]
        print(f"   Best Win Rate: {best_winrate['commodity']} {best_winrate['timeframe']} - {best_winrate['win_rate']:.1f}%")
        
        best_pf = df_results.loc[df_results['profit_factor'].idxmax()]
        print(f"   Best Profit Factor: {best_pf['commodity']} {best_pf['timeframe']} - {best_pf['profit_factor']:.2f}")
        
        print(f"\n📈 Detailed Results:")
        print(df_results.to_string(index=False, float_format='%.2f'))
        
        # Save results to CSV
        output_file = f"yahoo_backtest_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        df_results.to_csv(output_file, index=False)
        print(f"\n💾 Results saved to: {output_file}")
        
    else:
        print("❌ No successful backtests completed")
    
    print("\n🎉 Yahoo Finance backtesting completed!")
    return results

if __name__ == "__main__":
    run_comprehensive_yahoo_backtests()
