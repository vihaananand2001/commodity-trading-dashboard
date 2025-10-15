#!/usr/bin/env python3
"""
Train ML Confidence Models for All Silver 4H Strategies
Trains machine learning models to provide confidence scores for trading signals
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
import yaml
from pathlib import Path
from datetime import datetime
import time
from typing import Dict, List, Any

from src.utils import get_logger, load_features
from src.ml_confidence_scorer import MLConfidenceScorer

logger = get_logger(__name__)

# Load Silver 4H strategy configurations
def load_strategy_configs() -> Dict[str, Dict]:
    """Load strategy configurations from the locked rules YAML file."""
    rules_file = Path("models/silver_4h_long_rules.yaml")
    
    if not rules_file.exists():
        logger.error(f"Strategy rules file not found: {rules_file}")
        return {}
    
    with open(rules_file, 'r') as f:
        rules_data = yaml.safe_load(f)
    
    strategies = {}
    
    # Extract strategy configurations
    for i in range(1, 7):  # We have 6 strategies
        strategy_key = f"strategy_{i}"
        if strategy_key in rules_data:
            strategy_data = rules_data[strategy_key]
            
            # Convert YAML structure to our expected format
            strategy_config = {
                'name': strategy_data['name'],
                'pattern': strategy_data['pattern'],
                'rank': strategy_data['rank'],
                'category': strategy_data['category'],
                'performance': strategy_data['performance'],
                
                # Entry conditions
                'trend_condition': strategy_data['entry_conditions']['trend_filter'],
                'rsi_min': strategy_data['entry_conditions']['filters']['rsi_min'],
                'adx_min': strategy_data['entry_conditions']['filters']['adx_min'],
                'atr_min': strategy_data['entry_conditions']['filters']['atr_pct_min'],
                'atr_max': strategy_data['entry_conditions']['filters']['atr_pct_max'],
                'ema_proximity': strategy_data['entry_conditions']['filters']['ema_proximity'],
                'volume_min': strategy_data['entry_conditions']['filters']['volume_min'],
                
                # Exit rules
                'stop_loss_atr': strategy_data['exit_rules']['stop_loss']['atr_multiplier'],
                'take_profit_atr': strategy_data['exit_rules']['take_profit']['atr_multiplier'],
                'max_hold_bars': strategy_data['exit_rules']['max_hold_bars']
            }
            
            strategies[strategy_data['name']] = strategy_config
    
    logger.info(f"Loaded {len(strategies)} strategy configurations")
    return strategies

def train_confidence_models():
    """Train ML confidence models for all Silver 4H strategies."""
    logger.info(f"\n{'='*80}")
    logger.info("TRAINING ML CONFIDENCE MODELS FOR SILVER 4H STRATEGIES")
    logger.info(f"{'='*80}\n")
    
    # Load strategy configurations
    strategies = load_strategy_configs()
    
    if not strategies:
        logger.error("No strategy configurations found. Cannot proceed.")
        return
    
    # Load features data
    df = load_features('silver', '4h')
    logger.info(f"Loaded Silver 4H features: {len(df)} bars, {len(df.columns)} columns")
    
    # Initialize ML confidence scorer
    scorer = MLConfidenceScorer('silver', '4h', 'long')
    
    # Training results
    training_results = {}
    
    # Train models for each strategy
    for strategy_name, strategy_config in strategies.items():
        logger.info(f"\n{'='*60}")
        logger.info(f"TRAINING ML MODELS FOR: {strategy_name}")
        logger.info(f"{'='*60}")
        
        start_time = time.time()
        
        try:
            # Prepare training data
            logger.info("Preparing training data...")
            X, y = scorer.prepare_training_data(df, strategy_config)
            
            if len(X) == 0:
                logger.warning(f"No training data available for {strategy_name}. Skipping.")
                training_results[strategy_name] = {
                    'status': 'FAILED',
                    'reason': 'No training data',
                    'training_time': 0,
                    'samples': 0
                }
                continue
            
            # Train ML models
            logger.info("Training ML models...")
            ml_results = scorer.train_models(X, y)
            
            # Save models
            logger.info("Saving trained models...")
            scorer.save_models(strategy_name.replace(' ', '_').replace('-', '_').lower())
            
            # Generate confidence report
            report = scorer.generate_confidence_report(strategy_name)
            
            training_time = time.time() - start_time
            
            training_results[strategy_name] = {
                'status': 'SUCCESS',
                'training_time': training_time,
                'samples': len(X),
                'win_rate': (y == 1).mean(),
                'model_performance': scorer.model_performance,
                'top_features': dict(sorted(scorer.feature_importance.items(), key=lambda x: x[1], reverse=True)[:5]),
                'report': report
            }
            
            logger.info(f"✅ Successfully trained models for {strategy_name}")
            logger.info(f"   Training time: {training_time:.2f} seconds")
            logger.info(f"   Training samples: {len(X)}")
            logger.info(f"   Win rate in training data: {(y == 1).mean():.1%}")
            logger.info(f"   Best model accuracy: {max([perf['accuracy'] for perf in scorer.model_performance.values()]):.3f}")
            
        except Exception as e:
            logger.error(f"❌ Error training models for {strategy_name}: {e}")
            training_results[strategy_name] = {
                'status': 'FAILED',
                'reason': str(e),
                'training_time': time.time() - start_time,
                'samples': 0
            }
    
    # Generate summary report
    logger.info(f"\n{'='*80}")
    logger.info("ML CONFIDENCE TRAINING SUMMARY")
    logger.info(f"{'='*80}")
    
    successful_strategies = [name for name, result in training_results.items() if result['status'] == 'SUCCESS']
    failed_strategies = [name for name, result in training_results.items() if result['status'] == 'FAILED']
    
    logger.info(f"✅ Successful: {len(successful_strategies)}/{len(strategies)} strategies")
    logger.info(f"❌ Failed: {len(failed_strategies)}/{len(strategies)} strategies")
    
    if successful_strategies:
        logger.info("\n📊 SUCCESSFUL STRATEGIES:")
        for strategy_name in successful_strategies:
            result = training_results[strategy_name]
            logger.info(f"  • {strategy_name}")
            logger.info(f"    - Training samples: {result['samples']}")
            logger.info(f"    - Win rate: {result['win_rate']:.1%}")
            logger.info(f"    - Training time: {result['training_time']:.2f}s")
            
            # Show top features
            if result['top_features']:
                logger.info(f"    - Top features: {', '.join(list(result['top_features'].keys())[:3])}")
    
    if failed_strategies:
        logger.info("\n❌ FAILED STRATEGIES:")
        for strategy_name in failed_strategies:
            result = training_results[strategy_name]
            logger.info(f"  • {strategy_name}: {result['reason']}")
    
    # Save training results
    results_file = Path("reports/ml_confidence_training_results.yaml")
    results_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Convert numpy types for YAML serialization
    serializable_results = {}
    for strategy_name, result in training_results.items():
        serializable_result = {}
        for key, value in result.items():
            if isinstance(value, dict):
                serializable_result[key] = {k: float(v) if isinstance(v, (np.float64, np.float32)) else v 
                                          for k, v in value.items()}
            elif isinstance(value, (np.float64, np.float32)):
                serializable_result[key] = float(value)
            else:
                serializable_result[key] = value
        serializable_results[strategy_name] = serializable_result
    
    with open(results_file, 'w') as f:
        yaml.dump({
            'training_summary': {
                'total_strategies': len(strategies),
                'successful': len(successful_strategies),
                'failed': len(failed_strategies),
                'training_date': datetime.now().isoformat(),
                'commodity': 'silver',
                'timeframe': '4h'
            },
            'strategy_results': serializable_results
        }, f, default_flow_style=False)
    
    logger.info(f"\n📁 Training results saved to: {results_file}")
    
    return training_results

def test_confidence_scoring():
    """Test the trained confidence models with sample data."""
    logger.info(f"\n{'='*60}")
    logger.info("TESTING CONFIDENCE SCORING")
    logger.info(f"{'='*60}")
    
    # Load strategy configurations
    strategies = load_strategy_configs()
    
    if not strategies:
        logger.error("No strategy configurations found. Cannot test.")
        return
    
    # Initialize scorer
    scorer = MLConfidenceScorer('silver', '4h', 'long')
    
    # Test with sample features
    sample_features = {
        'rsi_14': 65.0,
        'adx_14': 25.0,
        'atr_14': 0.8,
        'ema_20': 28000.0,
        'ema_50': 27900.0,
        'volume': 1.5,
        'price_above_ema20': 1.0,
        'price_above_ema50': 1.0,
        'atr_pct': 1.2,
        'volume_ratio': 1.3,
        'price_change_1': 0.5,
        'price_change_3': 1.2,
        'price_change_5': 2.1,
        'volatility_5': 1.8,
        'volatility_10': 1.5
    }
    
    logger.info("Testing confidence scoring with sample features:")
    for feature, value in sample_features.items():
        logger.info(f"  {feature}: {value}")
    
    # Test each strategy
    for strategy_name, strategy_config in strategies.items():
        logger.info(f"\n🔍 Testing: {strategy_name}")
        
        # Add pattern feature
        test_features = sample_features.copy()
        test_features[strategy_config['pattern']] = 1.0
        
        # Try to load models
        strategy_key = strategy_name.replace(' ', '_').replace('-', '_').lower()
        if scorer.load_models(strategy_key):
            # Get confidence scores
            confidence_scores = scorer.predict_confidence(test_features)
            
            if confidence_scores:
                ensemble_confidence = confidence_scores.get('ensemble', 0.0)
                level, recommendation = scorer.get_confidence_interpretation(ensemble_confidence)
                
                logger.info(f"  Confidence Scores:")
                for model_name, score in confidence_scores.items():
                    logger.info(f"    {model_name}: {score:.3f}")
                
                logger.info(f"  Ensemble Confidence: {ensemble_confidence:.3f}")
                logger.info(f"  Confidence Level: {level}")
                logger.info(f"  Recommendation: {recommendation}")
            else:
                logger.warning(f"  No confidence scores generated")
        else:
            logger.warning(f"  Models not found for {strategy_name}")

def main():
    """Main function to train and test ML confidence models."""
    logger.info("Starting ML Confidence Model Training for Silver 4H Strategies")
    
    # Train models
    training_results = train_confidence_models()
    
    # Test confidence scoring
    test_confidence_scoring()
    
    logger.info(f"\n{'='*80}")
    logger.info("ML CONFIDENCE TRAINING COMPLETE")
    logger.info(f"{'='*80}")
    
    # Summary
    successful = sum(1 for result in training_results.values() if result['status'] == 'SUCCESS')
    total = len(training_results)
    
    logger.info(f"✅ Successfully trained ML models for {successful}/{total} strategies")
    logger.info("🎯 Confidence scoring system is ready for live trading!")
    logger.info("📊 Use the MLConfidenceScorer class to get confidence scores for trade signals")

if __name__ == "__main__":
    main()
