"""
Strategy Optimizer
Grid search optimization for pattern-based strategies with multiprocessing support
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from itertools import product
from multiprocessing import Pool, cpu_count
import time
from pathlib import Path

from utils import load_features, get_logger, create_summary_stats
from backtest_engine import BacktestEngine
from strategy_builder import create_pattern_strategy, get_default_patterns
from config import get_config

logger = get_logger(__name__)

# Global variables for multiprocessing worker initialization
_worker_df = None
_worker_pattern = None
_worker_direction = None

def _worker_init(df: pd.DataFrame, pattern: str, direction: str):
    """Initialize worker process with shared data"""
    global _worker_df, _worker_pattern, _worker_direction
    _worker_df = df
    _worker_pattern = pattern
    _worker_direction = direction

def _evaluate_combination(params: Dict) -> Tuple[Optional[Dict], Optional[Dict]]:
    """
    Evaluate a single parameter combination
    
    Returns:
    --------
    Tuple of (result_dict, diagnostic_dict)
    result_dict: If strategy passes filters, else None
    diagnostic_dict: Reason for failure if applicable
    """
    global _worker_df, _worker_pattern, _worker_direction
    
    try:
        # Build entry condition
        entry_func = create_pattern_strategy(
            df=_worker_df,
            pattern=_worker_pattern,
            trend_condition=params.get('trend_condition'),
            rsi_min=params.get('rsi_min'),
            rsi_max=params.get('rsi_max'),
            adx_min=params.get('adx_min'),
            atr_min=params.get('atr_min'),
            atr_max=params.get('atr_max'),
            ema_proximity=params.get('ema_proximity'),
            volume_min=params.get('volume_min')
        )
        
        # Run backtest
        engine = BacktestEngine(
            df=_worker_df,
            entry_conditions=entry_func,
            direction=_worker_direction,
            stop_loss_atr=params['stop_loss_atr'],
            take_profit_atr=params['take_profit_atr'],
            max_hold_bars=params.get('max_hold_bars')
        )
        
        trades_df = engine.run()
        
        if len(trades_df) == 0:
            return None, {
                'params': params,
                'why': 'no_trades',
                'trades': 0
            }
        
        # Calculate metrics
        summary = engine.get_summary()
        
        # Check filters
        config = get_config()
        min_trades = config.get('filters.min_trades', 10)
        min_pf = config.get('objectives.min_profit_factor', 1.25)
        max_dd = config.get('objectives.max_drawdown_pct', 15.0)
        
        if summary['total_trades'] < min_trades:
            return None, {
                'params': params,
                'why': 'insufficient_trades',
                'trades': summary['total_trades']
            }
        
        if summary['profit_factor'] < min_pf:
            return None, {
                'params': params,
                'why': 'pf_fail',
                'pf': summary['profit_factor'],
                'trades': summary['total_trades']
            }
        
        if summary['max_dd_pct'] > max_dd:
            return None, {
                'params': params,
                'why': 'dd_fail',
                'dd': summary['max_dd_pct'],
                'trades': summary['total_trades']
            }
        
        # Passed all filters - return result
        result = {
            **params,
            'trades': summary['total_trades'],
            'win_rate': summary['win_rate'],
            'profit_factor': summary['profit_factor'],
            'max_dd_pct': summary['max_dd_pct'],
            'total_pnl': summary['total_pnl'],
            'avg_pnl_per_trade': summary['avg_pnl_per_trade'],
            'avg_bars_held': summary['avg_bars_held'],
            'avg_mae': summary['avg_mae'],
            'avg_mfe': summary['avg_mfe']
        }
        
        return result, None
        
    except Exception as e:
        return None, {
            'params': params,
            'why': 'error',
            'error': str(e)
        }

class PatternOptimizer:
    """
    Optimize pattern-based strategies across parameter space
    
    Parameters:
    -----------
    commodity : str
        Commodity name (gold, silver, copper)
    timeframe : str
        Timeframe (1h, 4h, 1d)
    pattern : str
        Pattern to optimize
    direction : str
        'long' or 'short'
    """
    
    def __init__(
        self,
        commodity: str,
        timeframe: str,
        pattern: str,
        direction: str = 'long'
    ):
        self.commodity = commodity.lower()
        self.timeframe = timeframe.lower()
        self.pattern = pattern
        self.direction = direction.lower()
        
        # Load configuration
        self.config = get_config()
        
        # Load data
        logger.info(f"Loading features for {commodity} {timeframe}...")
        self.df = load_features(commodity, timeframe)
        
        # Verify pattern exists
        if pattern not in self.df.columns:
            raise ValueError(f"Pattern '{pattern}' not found in dataframe")
        
        # Check if pattern occurs
        pattern_count = self.df[pattern].sum()
        logger.info(f"Pattern '{pattern}' occurs {pattern_count} times ({pattern_count/len(self.df)*100:.2f}%)")
        
        if pattern_count == 0:
            raise ValueError(f"Pattern '{pattern}' never occurs in the data")
        
        self.results = []
        self.diagnostics = []
        
    def generate_parameter_grid(self) -> List[Dict]:
        """
        Generate parameter combinations to test
        
        Returns:
        --------
        List of parameter dictionaries
        """
        opt_config = self.config.get_optimization_params()
        
        # Get parameter ranges
        stop_loss_range = opt_config.get('stop_loss_atr_range', [1.5, 2.0, 2.5])
        take_profit_range = opt_config.get('take_profit_atr_range', [2.0, 2.5, 3.0])
        max_hold_bars_range = opt_config.get('max_hold_bars_range', [None, 10, 15])
        
        rsi_min_range = opt_config.get('rsi_min_range', [None, 50, 55, 60])
        adx_min_range = opt_config.get('adx_min_range', [None, 20, 25])
        
        atr_min_range = opt_config.get('atr_pct_min_range', [None, 0.5, 0.8])
        atr_max_range = opt_config.get('atr_pct_max_range', [None, 1.5, 2.0])
        
        ema_proximity_range = opt_config.get('ema_proximity_range', [None, 1.5, 2.0])
        volume_ratio_range = opt_config.get('volume_ratio_range', [None, 1.0, 1.2])
        
        # Trend conditions based on direction
        if self.direction == 'long':
            trend_conditions = self.config.get('trend_conditions.bullish', [None, 'ema_20 > ema_50'])
        else:
            trend_conditions = self.config.get('trend_conditions.bearish', [None, 'ema_20 < ema_50'])
        
        # Generate all combinations (iterator for memory efficiency)
        combinations_iterator = product(
            stop_loss_range,
            take_profit_range,
            max_hold_bars_range,
            trend_conditions,
            rsi_min_range,
            adx_min_range,
            atr_min_range,
            atr_max_range,
            ema_proximity_range,
            volume_ratio_range
        )
        
        # Get max combinations limit
        max_combos = self.config.get('filters.max_combinations', 50000)
        
        # Convert to list of dicts with filtering (limit early for efficiency)
        param_grid = []
        total_checked = 0
        
        for combo in combinations_iterator:
            total_checked += 1
            
            params = {
                'stop_loss_atr': combo[0],
                'take_profit_atr': combo[1],
                'max_hold_bars': combo[2],
                'trend_condition': combo[3],
                'rsi_min': combo[4],
                'adx_min': combo[5],
                'atr_min': combo[6],
                'atr_max': combo[7],
                'ema_proximity': combo[8],
                'volume_min': combo[9]
            }
            
            # Filter out invalid combinations (e.g., atr_min > atr_max)
            if params['atr_min'] is not None and params['atr_max'] is not None:
                if params['atr_min'] >= params['atr_max']:
                    continue
            
            # Filter out RSI >= 70 (overbought)
            if params['rsi_min'] is not None and params['rsi_min'] >= 70:
                continue
            
            param_grid.append(params)
            
            # Stop early if we have enough valid combinations
            if len(param_grid) >= max_combos * 2:  # Get 2x, then sample
                break
        
        logger.info(f"Generated {len(param_grid)} valid parameter combinations (checked {total_checked} total)")
        
        # Randomly sample if we have too many
        if len(param_grid) > max_combos:
            logger.info(f"Randomly sampling {max_combos} combinations from {len(param_grid)}")
            indices = np.random.choice(len(param_grid), size=max_combos, replace=False)
            param_grid = [param_grid[i] for i in indices]
        
        return param_grid
    
    def optimize(self, use_multiprocessing: bool = True) -> pd.DataFrame:
        """
        Run optimization
        
        Parameters:
        -----------
        use_multiprocessing : bool
            Whether to use multiprocessing
            
        Returns:
        --------
        pd.DataFrame with optimization results
        """
        logger.info(f"\n{'='*70}")
        logger.info(f"OPTIMIZING: {self.commodity.upper()} {self.timeframe.upper()} - {self.pattern}")
        logger.info(f"Direction: {self.direction.upper()}")
        logger.info(f"{'='*70}")
        
        param_grid = self.generate_parameter_grid()
        
        if len(param_grid) == 0:
            logger.error("No parameter combinations to test")
            return pd.DataFrame()
        
        start_time = time.time()
        
        if use_multiprocessing:
            num_processes = self.config.get('optimization.num_processes')
            if num_processes is None:
                num_processes = cpu_count()
            
            chunk_size = self.config.get('optimization.chunk_size', 64)
            
            logger.info(f"Using multiprocessing with {num_processes} processes")
            logger.info(f"Testing {len(param_grid)} combinations...")
            
            with Pool(
                processes=num_processes,
                initializer=_worker_init,
                initargs=(self.df, self.pattern, self.direction)
            ) as pool:
                results = pool.map(_evaluate_combination, param_grid, chunksize=chunk_size)
            
            # Separate results and diagnostics
            for result, diag in results:
                if result is not None:
                    self.results.append(result)
                if diag is not None:
                    self.diagnostics.append(diag)
        
        else:
            # Sequential processing
            logger.info(f"Running sequential optimization...")
            logger.info(f"Testing {len(param_grid)} combinations...")
            
            _worker_init(self.df, self.pattern, self.direction)
            
            for i, params in enumerate(param_grid):
                if i % 100 == 0:
                    logger.info(f"Progress: {i}/{len(param_grid)} ({i/len(param_grid)*100:.1f}%)")
                
                result, diag = _evaluate_combination(params)
                
                if result is not None:
                    self.results.append(result)
                if diag is not None:
                    self.diagnostics.append(diag)
        
        elapsed = time.time() - start_time
        
        logger.info(f"\nOptimization complete in {elapsed:.1f} seconds")
        logger.info(f"Tested: {len(param_grid)} combinations")
        logger.info(f"Passed filters: {len(self.results)}")
        
        if len(self.results) == 0:
            logger.warning("No combinations passed filters")
            self._print_diagnostic_summary()
            return pd.DataFrame()
        
        # Convert to DataFrame and sort
        results_df = pd.DataFrame(self.results)
        
        # Sort by: trades (desc), PF (desc), Win Rate (desc), DD (asc)
        results_df = results_df.sort_values(
            ['trades', 'profit_factor', 'win_rate', 'max_dd_pct'],
            ascending=[False, False, False, True]
        ).reset_index(drop=True)
        
        logger.info(f"\nTop 3 Results:")
        for i in range(min(3, len(results_df))):
            row = results_df.iloc[i]
            logger.info(f"  {i+1}. Trades={row['trades']:.0f}, PF={row['profit_factor']:.2f}, "
                       f"WR={row['win_rate']:.1f}%, DD={row['max_dd_pct']:.2f}%")
        
        return results_df
    
    def _print_diagnostic_summary(self):
        """Print summary of why combinations failed"""
        if len(self.diagnostics) == 0:
            return
        
        diag_df = pd.DataFrame(self.diagnostics)
        
        logger.info("\nDiagnostic Summary:")
        reason_counts = diag_df['why'].value_counts()
        
        for reason, count in reason_counts.items():
            pct = count / len(self.diagnostics) * 100
            logger.info(f"  {reason:20s}: {count:6d} ({pct:5.1f}%)")
    
    def save_results(self, output_dir: str = "reports/optimization"):
        """Save optimization results"""
        if len(self.results) == 0:
            logger.warning("No results to save")
            return
        
        output_path = Path(output_dir) / self.commodity / self.timeframe
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Save results
        results_df = pd.DataFrame(self.results)
        pattern_clean = self.pattern.replace('pattern_', '')
        filename = f"{pattern_clean}_{self.direction}_optimization.csv"
        filepath = output_path / filename
        
        results_df.to_csv(filepath, index=False)
        logger.info(f"Saved results to {filepath}")
        
        # Save diagnostics
        if len(self.diagnostics) > 0:
            diag_df = pd.DataFrame(self.diagnostics)
            diag_filename = f"{pattern_clean}_{self.direction}_diagnostics.csv"
            diag_filepath = output_path / diag_filename
            diag_df.to_csv(diag_filepath, index=False)
            logger.info(f"Saved diagnostics to {diag_filepath}")

def optimize_all_patterns(
    commodity: str,
    timeframe: str,
    direction: str = 'long',
    patterns: Optional[List[str]] = None
) -> Dict[str, pd.DataFrame]:
    """
    Optimize all patterns for a commodity-timeframe combination
    
    Parameters:
    -----------
    commodity : str
        Commodity name
    timeframe : str
        Timeframe
    direction : str
        'long' or 'short'
    patterns : List[str], optional
        List of patterns to test. If None, uses default patterns
        
    Returns:
    --------
    Dict mapping pattern names to results DataFrames
    """
    config = get_config()
    
    if patterns is None:
        if direction == 'long':
            patterns = config.get_bullish_patterns()
        else:
            patterns = config.get_bearish_patterns()
    
    logger.info(f"\n{'#'*70}")
    logger.info(f"# OPTIMIZING ALL PATTERNS: {commodity.upper()} {timeframe.upper()} ({direction.upper()})")
    logger.info(f"# Testing {len(patterns)} patterns")
    logger.info(f"{'#'*70}\n")
    
    all_results = {}
    
    for pattern in patterns:
        try:
            optimizer = PatternOptimizer(commodity, timeframe, pattern, direction)
            results_df = optimizer.optimize(use_multiprocessing=True)
            
            if len(results_df) > 0:
                optimizer.save_results()
                all_results[pattern] = results_df
            else:
                logger.warning(f"No valid results for pattern: {pattern}")
                
        except Exception as e:
            logger.error(f"Error optimizing pattern {pattern}: {str(e)}")
            continue
    
    logger.info(f"\n{'#'*70}")
    logger.info(f"# OPTIMIZATION COMPLETE")
    logger.info(f"# Successfully optimized {len(all_results)}/{len(patterns)} patterns")
    logger.info(f"{'#'*70}\n")
    
    return all_results

if __name__ == "__main__":
    # Example usage
    print("Strategy Optimizer Module")
    print("Use optimize_all_patterns() to run comprehensive optimization")

