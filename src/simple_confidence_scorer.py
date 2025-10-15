#!/usr/bin/env python3
"""
Simple Confidence Scorer for Trading Strategies
Provides confidence scores based on historical performance and current market conditions
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
import yaml
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

from src.utils import get_logger

logger = get_logger(__name__)

class SimpleConfidenceScorer:
    """
    Simple confidence scorer based on historical performance and market conditions.
    
    This class provides confidence scores for trading signals based on:
    1. Historical win rates and profit factors
    2. Current market volatility and trend strength
    3. Pattern-specific performance metrics
    """
    
    def __init__(self, commodity: str, timeframe: str, direction: str = "long"):
        """
        Initialize the Simple Confidence Scorer.
        
        Args:
            commodity: Trading commodity (e.g., 'gold', 'silver')
            timeframe: Trading timeframe (e.g., '1h', '4h', '1d')
            direction: Trading direction ('long' or 'short')
        """
        self.commodity = commodity
        self.timeframe = timeframe
        self.direction = direction
        
        # Load strategy configurations
        self.strategies = self._load_strategy_configs()
        
        # Confidence scoring parameters
        self.confidence_weights = {
            'historical_performance': 0.4,  # 40% weight on historical performance
            'market_conditions': 0.3,       # 30% weight on current market conditions
            'pattern_strength': 0.2,        # 20% weight on pattern strength
            'risk_conditions': 0.1          # 10% weight on risk conditions
        }
        
    def _load_strategy_configs(self) -> Dict[str, Dict]:
        """Load strategy configurations from locked rules."""
        rules_file = Path(f"models/{self.commodity}_{self.timeframe}_long_rules.yaml")
        
        if not rules_file.exists():
            logger.error(f"Strategy rules file not found: {rules_file}")
            return {}
        
        with open(rules_file, 'r') as f:
            rules_data = yaml.safe_load(f)
        
        strategies = {}
        
        # Extract strategy configurations
        for i in range(1, 10):  # Check up to 9 strategies
            strategy_key = f"strategy_{i}"
            if strategy_key in rules_data:
                strategy_data = rules_data[strategy_key]
                
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
    
    def calculate_historical_confidence(self, strategy_name: str) -> float:
        """Calculate confidence based on historical performance."""
        if strategy_name not in self.strategies:
            return 0.0
        
        performance = self.strategies[strategy_name]['performance']
        
        # Extract key metrics
        win_rate = performance['win_rate'] / 100.0  # Convert percentage to decimal
        profit_factor = performance['profit_factor']
        max_drawdown = performance['max_drawdown_pct']
        total_trades = performance['trades']
        
        # Normalize metrics to 0-1 scale
        win_rate_score = min(win_rate, 1.0)
        profit_factor_score = min(profit_factor / 5.0, 1.0)  # Normalize to max 5.0
        drawdown_score = max(0, 1.0 - (max_drawdown / 50.0))  # Penalize high drawdown
        sample_size_score = min(total_trades / 50.0, 1.0)  # Reward more trades
        
        # Weighted historical confidence
        historical_confidence = (
            win_rate_score * 0.4 +
            profit_factor_score * 0.3 +
            drawdown_score * 0.2 +
            sample_size_score * 0.1
        )
        
        return min(max(historical_confidence, 0.0), 1.0)
    
    def calculate_market_conditions_confidence(self, features: Dict[str, float]) -> float:
        """Calculate confidence based on current market conditions."""
        try:
            # RSI conditions (prefer moderate RSI values)
            rsi = features.get('rsi_14', 50.0)
            rsi_score = 1.0 - abs(rsi - 50.0) / 50.0  # Best at RSI 50
            
            # ADX conditions (prefer strong trends)
            adx = features.get('adx_14', 20.0)
            adx_score = min(adx / 30.0, 1.0)  # Best above 30
            
            # Volume conditions (prefer above-average volume)
            volume = features.get('volume', 1.0)
            volume_score = min(volume, 2.0) / 2.0  # Normalize to 0-1
            
            # Trend strength
            price_above_ema20 = features.get('price_above_ema20', 0.0)
            price_above_ema50 = features.get('price_above_ema50', 0.0)
            trend_score = (price_above_ema20 + price_above_ema50) / 2.0
            
            # Volatility conditions (prefer moderate volatility)
            atr_pct = features.get('atr_pct', 1.0)
            volatility_score = 1.0 - abs(atr_pct - 1.5) / 3.0  # Best around 1.5%
            
            market_confidence = (
                rsi_score * 0.2 +
                adx_score * 0.3 +
                volume_score * 0.2 +
                trend_score * 0.2 +
                volatility_score * 0.1
            )
            
            return min(max(market_confidence, 0.0), 1.0)
            
        except Exception as e:
            logger.error(f"Error calculating market conditions confidence: {e}")
            return 0.5  # Default moderate confidence
    
    def calculate_pattern_strength_confidence(self, features: Dict[str, float], strategy_name: str) -> float:
        """Calculate confidence based on pattern strength and conditions."""
        if strategy_name not in self.strategies:
            return 0.0
        
        strategy_config = self.strategies[strategy_name]
        
        try:
            # Check if pattern is present
            pattern_col = strategy_config['pattern']
            pattern_present = features.get(pattern_col, 0.0)
            
            if pattern_present != 1.0:
                return 0.0  # No pattern, no confidence
            
            # Check strategy-specific conditions
            confidence_score = 1.0
            
            # RSI conditions
            rsi = features.get('rsi_14', 50.0)
            rsi_min = strategy_config['rsi_min']
            if rsi < rsi_min:
                confidence_score *= 0.5
            
            # ADX conditions
            adx = features.get('adx_14', 20.0)
            adx_min = strategy_config['adx_min']
            if adx < adx_min:
                confidence_score *= 0.5
            
            # ATR conditions
            atr_pct = features.get('atr_pct', 1.0)
            atr_min = strategy_config['atr_min']
            atr_max = strategy_config['atr_max']
            if not (atr_min <= atr_pct <= atr_max):
                confidence_score *= 0.7
            
            # Volume conditions
            volume = features.get('volume', 1.0)
            volume_min = strategy_config['volume_min']
            if volume < volume_min:
                confidence_score *= 0.8
            
            # Trend conditions
            if strategy_config['trend_condition']:
                if 'ema_20 > ema_50' in strategy_config['trend_condition']:
                    ema_20 = features.get('ema_20', 0)
                    ema_50 = features.get('ema_50', 0)
                    if ema_20 <= ema_50:
                        confidence_score *= 0.3
                elif 'price_above_ema20' in strategy_config['trend_condition']:
                    price = features.get('close', 0)
                    ema_20 = features.get('ema_20', 0)
                    if price <= ema_20:
                        confidence_score *= 0.3
            
            return min(max(confidence_score, 0.0), 1.0)
            
        except Exception as e:
            logger.error(f"Error calculating pattern strength confidence: {e}")
            return 0.5
    
    def calculate_risk_conditions_confidence(self, features: Dict[str, float]) -> float:
        """Calculate confidence based on risk conditions."""
        try:
            # Volatility risk (prefer moderate volatility)
            atr_pct = features.get('atr_pct', 1.0)
            volatility_risk = 1.0 - abs(atr_pct - 1.5) / 3.0
            
            # Volume risk (prefer good volume)
            volume = features.get('volume', 1.0)
            volume_risk = min(volume, 2.0) / 2.0
            
            # Price momentum risk
            price_change_1 = features.get('price_change_1', 0.0)
            price_change_3 = features.get('price_change_3', 0.0)
            momentum_risk = 1.0 - abs(price_change_1) / 5.0  # Prefer less extreme moves
            
            risk_confidence = (
                volatility_risk * 0.4 +
                volume_risk * 0.3 +
                momentum_risk * 0.3
            )
            
            return min(max(risk_confidence, 0.0), 1.0)
            
        except Exception as e:
            logger.error(f"Error calculating risk conditions confidence: {e}")
            return 0.5
    
    def predict_confidence(self, features: Dict[str, float], strategy_name: str) -> Dict[str, float]:
        """
        Predict confidence score for a given set of features and strategy.
        
        Args:
            features: Dictionary of feature values
            strategy_name: Name of the strategy
            
        Returns:
            Dictionary with confidence scores and breakdown
        """
        if strategy_name not in self.strategies:
            logger.error(f"Strategy not found: {strategy_name}")
            return {}
        
        # Calculate individual confidence components
        historical_conf = self.calculate_historical_confidence(strategy_name)
        market_conf = self.calculate_market_conditions_confidence(features)
        pattern_conf = self.calculate_pattern_strength_confidence(features, strategy_name)
        risk_conf = self.calculate_risk_conditions_confidence(features)
        
        # Calculate weighted overall confidence
        overall_confidence = (
            historical_conf * self.confidence_weights['historical_performance'] +
            market_conf * self.confidence_weights['market_conditions'] +
            pattern_conf * self.confidence_weights['pattern_strength'] +
            risk_conf * self.confidence_weights['risk_conditions']
        )
        
        # If pattern is not present, set confidence to 0
        pattern_col = self.strategies[strategy_name]['pattern']
        if features.get(pattern_col, 0) != 1.0:
            overall_confidence = 0.0
        
        confidence_scores = {
            'overall': overall_confidence,
            'historical': historical_conf,
            'market_conditions': market_conf,
            'pattern_strength': pattern_conf,
            'risk_conditions': risk_conf,
            'strategy_name': strategy_name,
            'pattern': pattern_col
        }
        
        return confidence_scores
    
    def get_confidence_interpretation(self, confidence_score: float) -> Tuple[str, str, str]:
        """
        Interpret confidence score into human-readable format.
        
        Args:
            confidence_score: Confidence score between 0 and 1
            
        Returns:
            Tuple of (confidence_level, recommendation, risk_level)
        """
        if confidence_score >= 0.8:
            return "VERY HIGH", "Strong signal - High probability of success", "LOW RISK"
        elif confidence_score >= 0.7:
            return "HIGH", "Good signal - Good probability of success", "MODERATE RISK"
        elif confidence_score >= 0.6:
            return "MEDIUM", "Moderate signal - Moderate probability of success", "MODERATE RISK"
        elif confidence_score >= 0.5:
            return "LOW", "Weak signal - Low probability of success", "HIGH RISK"
        else:
            return "VERY LOW", "Poor signal - High probability of failure", "HIGH RISK"
    
    def scan_for_signals(self, features: Dict[str, float], min_confidence: float = 0.6) -> List[Dict[str, Any]]:
        """
        Scan for trading signals across all strategies.
        
        Args:
            features: Current market features
            min_confidence: Minimum confidence threshold
            
        Returns:
            List of signal analyses
        """
        signals = []
        
        for strategy_name in self.strategies.keys():
            confidence_scores = self.predict_confidence(features, strategy_name)
            
            if confidence_scores and confidence_scores['overall'] >= min_confidence:
                confidence_level, recommendation, risk_level = self.get_confidence_interpretation(
                    confidence_scores['overall']
                )
                
                signal_analysis = {
                    'strategy_name': strategy_name,
                    'pattern': confidence_scores['pattern'],
                    'overall_confidence': confidence_scores['overall'],
                    'confidence_level': confidence_level,
                    'recommendation': recommendation,
                    'risk_level': risk_level,
                    'confidence_breakdown': {
                        'historical': confidence_scores['historical'],
                        'market_conditions': confidence_scores['market_conditions'],
                        'pattern_strength': confidence_scores['pattern_strength'],
                        'risk_conditions': confidence_scores['risk_conditions']
                    },
                    'strategy_config': self.strategies[strategy_name]
                }
                
                signals.append(signal_analysis)
        
        # Sort by confidence score
        signals.sort(key=lambda x: x['overall_confidence'], reverse=True)
        
        return signals
    
    def generate_confidence_report(self, features: Dict[str, float]) -> str:
        """Generate a comprehensive confidence report."""
        signals = self.scan_for_signals(features)
        
        if not signals:
            return "No trading signals found above confidence threshold."
        
        report = f"""
🎯 CONFIDENCE SCORING REPORT - {self.commodity.upper()} {self.timeframe.upper()}
{'='*70}

📊 MARKET CONDITIONS:
• RSI: {features.get('rsi_14', 0):.1f}
• ADX: {features.get('adx_14', 0):.1f}
• Volume: {features.get('volume', 0):.2f}
• ATR %: {features.get('atr_pct', 0):.2f}
• Price vs EMA20: {'Above' if features.get('price_above_ema20', 0) else 'Below'}
• Price vs EMA50: {'Above' if features.get('price_above_ema50', 0) else 'Below'}

📈 TRADING SIGNALS FOUND: {len(signals)}
"""
        
        for i, signal in enumerate(signals, 1):
            report += f"""
{i}. {signal['strategy_name']}
   • Pattern: {signal['pattern']}
   • Overall Confidence: {signal['overall_confidence']:.1%} ({signal['confidence_level']})
   • Risk Level: {signal['risk_level']}
   • Recommendation: {signal['recommendation']}
   
   📊 Confidence Breakdown:
   • Historical Performance: {signal['confidence_breakdown']['historical']:.1%}
   • Market Conditions: {signal['confidence_breakdown']['market_conditions']:.1%}
   • Pattern Strength: {signal['confidence_breakdown']['pattern_strength']:.1%}
   • Risk Conditions: {signal['confidence_breakdown']['risk_conditions']:.1%}
"""
        
        return report

def main():
    """Example usage of Simple Confidence Scorer."""
    logger.info("Simple Confidence Scorer - Example Usage")
    
    # Initialize scorer
    scorer = SimpleConfidenceScorer('silver', '4h', 'long')
    
    # Example features
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
        'volatility_10': 1.5,
        'close': 28100.0,
        # Add pattern features
        'pattern_morning_star': 1.0,
        'pattern_breakout_20': 0.0,
        'pattern_outside_bar': 0.0,
        'pattern_doji': 0.0,
        'pattern_three_white_soldiers': 0.0,
        'pattern_evening_star': 0.0
    }
    
    # Generate confidence report
    report = scorer.generate_confidence_report(sample_features)
    logger.info(report)
    
    # Test individual strategy
    strategy_name = "Silver 4H Long - Morning Star"
    confidence_scores = scorer.predict_confidence(sample_features, strategy_name)
    
    if confidence_scores:
        logger.info(f"\n🔍 Individual Strategy Analysis: {strategy_name}")
        logger.info(f"Overall Confidence: {confidence_scores['overall']:.1%}")
        logger.info(f"Historical: {confidence_scores['historical']:.1%}")
        logger.info(f"Market Conditions: {confidence_scores['market_conditions']:.1%}")
        logger.info(f"Pattern Strength: {confidence_scores['pattern_strength']:.1%}")
        logger.info(f"Risk Conditions: {confidence_scores['risk_conditions']:.1%}")
        
        level, recommendation, risk = scorer.get_confidence_interpretation(confidence_scores['overall'])
        logger.info(f"Confidence Level: {level}")
        logger.info(f"Recommendation: {recommendation}")
        logger.info(f"Risk Level: {risk}")

if __name__ == "__main__":
    main()
