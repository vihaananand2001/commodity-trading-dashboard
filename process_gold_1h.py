#!/usr/bin/env python3
"""
Process Gold 1H Data
Simple script to process raw Gold 1H data into features
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
from pathlib import Path

from src.utils import get_logger, load_ohlc_data, save_features
from src.feature_engineering import build_features

logger = get_logger(__name__)

def process_gold_1h():
    """Process Gold 1H raw data into features"""
    
    logger.info(f"\n{'='*70}")
    logger.info("PROCESSING GOLD 1H DATA")
    logger.info(f"{'='*70}\n")
    
    raw_file = Path("data/raw/1h/gold_1H.csv")
    processed_file = Path("data/processed/gold_1h_features.csv")
    
    if not raw_file.exists():
        logger.error(f"Raw file not found: {raw_file}")
        return False
    
    if processed_file.exists():
        logger.info(f"Features already exist: {processed_file}")
        logger.info("Skipping processing...")
        return True
    
    logger.info("Loading raw Gold 1H data...")
    try:
        df = load_ohlc_data('gold', '1h')
        logger.info(f"Loaded {len(df)} raw bars")
        logger.info(f"Date range: {df['time'].iloc[0]} to {df['time'].iloc[-1]}")
        
        # Process features
        logger.info("Building features...")
        df_features = build_features(df, '1h')
        
        # Save processed data
        save_features(df_features, 'gold', '1h')
        logger.info(f"✅ Saved features to: {processed_file}")
        
        # Show pattern summary
        pattern_cols = [col for col in df_features.columns if col.startswith('pattern_')]
        logger.info(f"\nPatterns detected: {len(pattern_cols)}")
        
        for pattern in pattern_cols[:10]:  # Show first 10 patterns
            count = df_features[pattern].sum()
            pct = (count / len(df_features)) * 100
            logger.info(f"  {pattern}: {count} occurrences ({pct:.2f}%)")
        
        if len(pattern_cols) > 10:
            logger.info(f"  ... and {len(pattern_cols) - 10} more patterns")
        
        return True
        
    except Exception as e:
        logger.error(f"Error processing data: {str(e)}")
        return False

if __name__ == "__main__":
    success = process_gold_1h()
    if success:
        logger.info("\n✅ GOLD 1H PROCESSING COMPLETE!")
    else:
        logger.error("\n❌ GOLD 1H PROCESSING FAILED!")
