#!/usr/bin/env python3
"""
Main Entry Point for Commodity Trading Framework

Usage:
------
# Build features for all commodities and timeframes
python main.py --build-features

# Optimize a specific commodity/timeframe
python main.py --optimize --commodity gold --timeframe 4h --direction long

# Optimize all patterns for a commodity/timeframe
python main.py --optimize-all --commodity gold --timeframe 4h --direction long

# Run complete pipeline
python main.py --full-pipeline --commodity silver --timeframe 1h
"""

import argparse
import sys
from pathlib import Path

from utils import get_logger, get_all_commodities, get_all_timeframes
from feature_engineering import build_features, build_all_features
from optimizer import PatternOptimizer, optimize_all_patterns
from strategy_builder import get_default_patterns
from config import get_config

logger = get_logger(__name__)

def main():
    parser = argparse.ArgumentParser(
        description="Commodity Trading Pattern Optimization Framework",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Actions
    parser.add_argument(
        '--build-features',
        action='store_true',
        help='Build features for all commodities and timeframes'
    )
    
    parser.add_argument(
        '--optimize',
        action='store_true',
        help='Run optimization for a specific pattern'
    )
    
    parser.add_argument(
        '--optimize-all',
        action='store_true',
        help='Optimize all patterns for a commodity/timeframe'
    )
    
    parser.add_argument(
        '--full-pipeline',
        action='store_true',
        help='Run complete pipeline: features + optimization'
    )
    
    # Parameters
    parser.add_argument(
        '--commodity',
        type=str,
        choices=['gold', 'silver', 'copper', 'all'],
        help='Commodity to process'
    )
    
    parser.add_argument(
        '--timeframe',
        type=str,
        choices=['1h', '4h', '1d', 'all'],
        help='Timeframe to process'
    )
    
    parser.add_argument(
        '--direction',
        type=str,
        choices=['long', 'short', 'both'],
        default='long',
        help='Trading direction (default: long)'
    )
    
    parser.add_argument(
        '--pattern',
        type=str,
        help='Specific pattern to optimize'
    )
    
    parser.add_argument(
        '--no-multiprocessing',
        action='store_true',
        help='Disable multiprocessing (use for debugging)'
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if not any([args.build_features, args.optimize, args.optimize_all, args.full_pipeline]):
        parser.print_help()
        sys.exit(1)
    
    # Build features
    if args.build_features or args.full_pipeline:
        logger.info("\n" + "="*70)
        logger.info("BUILDING FEATURES")
        logger.info("="*70 + "\n")
        
        if args.commodity and args.commodity != 'all' and args.timeframe and args.timeframe != 'all':
            # Build for specific commodity/timeframe
            build_features(args.commodity, args.timeframe)
        else:
            # Build for all
            build_all_features()
    
    # Optimization
    if args.optimize or args.optimize_all or args.full_pipeline:
        if not args.commodity or not args.timeframe:
            logger.error("--commodity and --timeframe required for optimization")
            sys.exit(1)
        
        # Handle 'all' cases
        commodities = get_all_commodities() if args.commodity == 'all' else [args.commodity]
        timeframes = get_all_timeframes() if args.timeframe == 'all' else [args.timeframe]
        directions = ['long', 'short'] if args.direction == 'both' else [args.direction]
        
        for commodity in commodities:
            for timeframe in timeframes:
                for direction in directions:
                    logger.info(f"\n{'='*70}")
                    logger.info(f"Processing: {commodity.upper()} {timeframe.upper()} ({direction.upper()})")
                    logger.info(f"{'='*70}\n")
                    
                    try:
                        if args.optimize and args.pattern:
                            # Optimize specific pattern
                            optimizer = PatternOptimizer(
                                commodity=commodity,
                                timeframe=timeframe,
                                pattern=args.pattern,
                                direction=direction
                            )
                            
                            results = optimizer.optimize(
                                use_multiprocessing=not args.no_multiprocessing
                            )
                            
                            if len(results) > 0:
                                optimizer.save_results()
                        
                        elif args.optimize_all or args.full_pipeline:
                            # Optimize all patterns
                            results = optimize_all_patterns(
                                commodity=commodity,
                                timeframe=timeframe,
                                direction=direction
                            )
                            
                            logger.info(f"\nSuccessfully optimized {len(results)} patterns")
                        
                    except Exception as e:
                        logger.error(f"Error processing {commodity} {timeframe} {direction}: {str(e)}")
                        continue
    
    logger.info("\n" + "="*70)
    logger.info("PIPELINE COMPLETE")
    logger.info("="*70 + "\n")

if __name__ == "__main__":
    main()




