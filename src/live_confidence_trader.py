#!/usr/bin/env python3
"""
Live Trading with ML Confidence Scoring
Integrates ML confidence models with live trading signals for enhanced decision making
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
import yaml
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

from src.utils import get_logger
from src.ml_confidence_scorer import MLConfidenceScorer
from src.strategy_builder import create_pattern_strategy

logger = get_logger(__name__)

class LiveConfidenceTrader:
    """
    Live trading system with ML confidence scoring.
    
    This class integrates trained ML models to provide confidence scores
    for live trading signals, enabling better position sizing and risk management.
    """
    
    def __init__(self, commodity: str, timeframe: str, direction: str = "long"):
        """
        Initialize the Live Confidence Trader.
        
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
        
        # Initialize ML confidence scorers for each strategy
        self.confidence_scorers = {}
        self._initialize_confidence_scorers()
        
        # Trading state
        self.active_signals = {}
        self.signal_history = []
        
        # Risk management parameters
        self.max_position_size = 100000  # Maximum position size
        self.confidence_threshold = 0.6  # Minimum confidence threshold
        self.max_risk_per_trade = 0.02   # Maximum 2% risk per trade
        
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
    
    def _initialize_confidence_scorers(self):
        """Initialize ML confidence scorers for each strategy."""
        logger.info("Initializing ML confidence scorers...")
        
        for strategy_name, strategy_config in self.strategies.items():
            try:
                # Create scorer
                scorer = MLConfidenceScorer(self.commodity, self.timeframe, self.direction)
                
                # Load trained models
                strategy_key = strategy_name.replace(' ', '_').replace('-', '_').lower()
                if scorer.load_models(strategy_key):
                    self.confidence_scorers[strategy_name] = scorer
                    logger.info(f"✅ Loaded confidence models for: {strategy_name}")
                else:
                    logger.warning(f"⚠️ Could not load models for: {strategy_name}")
                    
            except Exception as e:
                logger.error(f"❌ Error initializing scorer for {strategy_name}: {e}")
        
        logger.info(f"Initialized {len(self.confidence_scorers)} confidence scorers")
    
    def analyze_signal(self, df: pd.DataFrame, current_bar: int, strategy_name: str) -> Optional[Dict[str, Any]]:
        """
        Analyze a trading signal and provide confidence scoring.
        
        Args:
            df: Current market data dataframe
            current_bar: Index of current bar
            strategy_name: Name of the strategy to analyze
            
        Returns:
            Dictionary with signal analysis and confidence scores, or None if no signal
        """
        if strategy_name not in self.strategies:
            logger.error(f"Strategy not found: {strategy_name}")
            return None
        
        if strategy_name not in self.confidence_scorers:
            logger.warning(f"No confidence scorer available for: {strategy_name}")
            return None
        
        strategy_config = self.strategies[strategy_name]
        scorer = self.confidence_scorers[strategy_name]
        
        # Check if current bar has the pattern signal
        pattern_col = strategy_config['pattern']
        if pattern_col not in df.columns or current_bar >= len(df):
            return None
        
        if df.iloc[current_bar][pattern_col] != 1:
            return None
        
        # Get current market features
        current_features = self._extract_features(df, current_bar, strategy_config)
        
        if not current_features:
            return None
        
        # Check if signal meets basic strategy criteria
        if not self._check_strategy_criteria(df, current_bar, strategy_config):
            return None
        
        # Get ML confidence scores
        confidence_scores = scorer.predict_confidence(current_features)
        
        if not confidence_scores:
            return None
        
        # Analyze signal
        ensemble_confidence = confidence_scores.get('ensemble', 0.0)
        confidence_level, recommendation = scorer.get_confidence_interpretation(ensemble_confidence)
        
        # Calculate position size based on confidence
        position_size = self._calculate_position_size(ensemble_confidence, df.iloc[current_bar])
        
        signal_analysis = {
            'timestamp': df.iloc[current_bar].name if hasattr(df.iloc[current_bar], 'name') else current_bar,
            'strategy_name': strategy_name,
            'pattern': pattern_col,
            'current_price': df.iloc[current_bar]['close'],
            'confidence_scores': confidence_scores,
            'ensemble_confidence': ensemble_confidence,
            'confidence_level': confidence_level,
            'recommendation': recommendation,
            'position_size': position_size,
            'risk_amount': position_size * self.max_risk_per_trade,
            'features': current_features,
            'strategy_config': strategy_config
        }
        
        return signal_analysis
    
    def _extract_features(self, df: pd.DataFrame, bar_index: int, strategy_config: Dict) -> Dict[str, float]:
        """Extract features for ML confidence scoring."""
        try:
            current_bar = df.iloc[bar_index]
            
            features = {
                'rsi_14': current_bar.get('rsi_14', 50.0),
                'adx_14': current_bar.get('adx_14', 20.0),
                'atr_14': current_bar.get('atr_14', 1.0),
                'ema_20': current_bar.get('ema_20', current_bar['close']),
                'ema_50': current_bar.get('ema_50', current_bar['close']),
                'volume': current_bar.get('volume', 1.0),
                'price_above_ema20': 1.0 if current_bar['close'] > current_bar.get('ema_20', current_bar['close']) else 0.0,
                'price_above_ema50': 1.0 if current_bar['close'] > current_bar.get('ema_50', current_bar['close']) else 0.0,
                'atr_pct': (current_bar.get('atr_14', 1.0) / current_bar['close']) * 100,
                'volume_ratio': current_bar.get('volume_ratio', 1.0),
                'price_change_1': current_bar.get('price_change_1', 0.0),
                'price_change_3': current_bar.get('price_change_3', 0.0),
                'price_change_5': current_bar.get('price_change_5', 0.0),
                'volatility_5': current_bar.get('volatility_5', 1.0),
                'volatility_10': current_bar.get('volatility_10', 1.0),
                strategy_config['pattern']: 1.0
            }
            
            # Add time-based features
            if hasattr(current_bar, 'name'):
                timestamp = current_bar.name
                if hasattr(timestamp, 'hour'):
                    features['time_of_day'] = timestamp.hour
                if hasattr(timestamp, 'weekday'):
                    features['day_of_week'] = timestamp.weekday()
                if hasattr(timestamp, 'month'):
                    features['month'] = timestamp.month
            
            return features
            
        except Exception as e:
            logger.error(f"Error extracting features: {e}")
            return {}
    
    def _check_strategy_criteria(self, df: pd.DataFrame, bar_index: int, strategy_config: Dict) -> bool:
        """Check if current bar meets strategy entry criteria."""
        try:
            current_bar = df.iloc[bar_index]
            
            # Check RSI
            rsi = current_bar.get('rsi_14', 50)
            if rsi < strategy_config['rsi_min']:
                return False
            
            # Check ADX
            adx = current_bar.get('adx_14', 20)
            if adx < strategy_config['adx_min']:
                return False
            
            # Check ATR percentage
            atr_pct = (current_bar.get('atr_14', 1) / current_bar['close']) * 100
            if not (strategy_config['atr_min'] <= atr_pct <= strategy_config['atr_max']):
                return False
            
            # Check volume
            volume = current_bar.get('volume', 1)
            if volume < strategy_config['volume_min']:
                return False
            
            # Check trend condition
            if strategy_config['trend_condition']:
                if 'ema_20 > ema_50' in strategy_config['trend_condition']:
                    if current_bar.get('ema_20', 0) <= current_bar.get('ema_50', 0):
                        return False
                elif 'price_above_ema20' in strategy_config['trend_condition']:
                    if current_bar['close'] <= current_bar.get('ema_20', 0):
                        return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking strategy criteria: {e}")
            return False
    
    def _calculate_position_size(self, confidence: float, current_bar: pd.Series) -> float:
        """Calculate position size based on confidence score."""
        # Base position size
        base_size = self.max_position_size * 0.1  # 10% of max position
        
        # Adjust based on confidence
        confidence_multiplier = max(0.1, min(1.0, confidence))  # Between 0.1 and 1.0
        
        # Adjust based on volatility (lower size for higher volatility)
        atr = current_bar.get('atr_14', 1.0)
        price = current_bar['close']
        volatility_adjustment = max(0.5, min(1.0, 1.0 - (atr / price) * 10))
        
        position_size = base_size * confidence_multiplier * volatility_adjustment
        
        return min(position_size, self.max_position_size)
    
    def scan_for_signals(self, df: pd.DataFrame, current_bar: int = -1) -> List[Dict[str, Any]]:
        """
        Scan for trading signals across all strategies.
        
        Args:
            df: Current market data dataframe
            current_bar: Index of current bar (-1 for latest)
            
        Returns:
            List of signal analyses
        """
        if current_bar == -1:
            current_bar = len(df) - 1
        
        signals = []
        
        for strategy_name in self.strategies.keys():
            signal = self.analyze_signal(df, current_bar, strategy_name)
            if signal and signal['ensemble_confidence'] >= self.confidence_threshold:
                signals.append(signal)
        
        # Sort by confidence score
        signals.sort(key=lambda x: x['ensemble_confidence'], reverse=True)
        
        return signals
    
    def get_signal_summary(self, signals: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get summary of trading signals."""
        if not signals:
            return {'total_signals': 0}
        
        return {
            'total_signals': len(signals),
            'high_confidence_signals': len([s for s in signals if s['ensemble_confidence'] >= 0.8]),
            'medium_confidence_signals': len([s for s in signals if 0.6 <= s['ensemble_confidence'] < 0.8]),
            'avg_confidence': np.mean([s['ensemble_confidence'] for s in signals]),
            'total_position_size': sum([s['position_size'] for s in signals]),
            'total_risk': sum([s['risk_amount'] for s in signals]),
            'top_strategy': signals[0]['strategy_name'] if signals else None,
            'top_confidence': signals[0]['ensemble_confidence'] if signals else 0.0
        }
    
    def log_signal(self, signal: Dict[str, Any]):
        """Log a trading signal for record keeping."""
        signal_record = {
            'timestamp': datetime.now().isoformat(),
            'strategy': signal['strategy_name'],
            'pattern': signal['pattern'],
            'price': signal['current_price'],
            'confidence': signal['ensemble_confidence'],
            'confidence_level': signal['confidence_level'],
            'position_size': signal['position_size'],
            'risk_amount': signal['risk_amount'],
            'recommendation': signal['recommendation']
        }
        
        self.signal_history.append(signal_record)
        
        # Log to file
        log_file = Path(f"logs/signals_{self.commodity}_{self.timeframe}.csv")
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        signal_df = pd.DataFrame([signal_record])
        
        if log_file.exists():
            signal_df.to_csv(log_file, mode='a', header=False, index=False)
        else:
            signal_df.to_csv(log_file, index=False)
    
    def generate_trading_report(self, signals: List[Dict[str, Any]]) -> str:
        """Generate a human-readable trading report."""
        if not signals:
            return "No trading signals found."
        
        summary = self.get_signal_summary(signals)
        
        report = f"""
🎯 TRADING SIGNALS REPORT - {self.commodity.upper()} {self.timeframe.upper()}
{'='*60}

📊 SUMMARY:
• Total Signals: {summary['total_signals']}
• High Confidence (≥80%): {summary['high_confidence_signals']}
• Medium Confidence (60-79%): {summary['medium_confidence_signals']}
• Average Confidence: {summary['avg_confidence']:.1%}
• Total Position Size: ${summary['total_position_size']:,.0f}
• Total Risk: ${summary['total_risk']:,.0f}

🏆 TOP SIGNAL:
• Strategy: {summary['top_strategy']}
• Confidence: {summary['top_confidence']:.1%}

📈 DETAILED SIGNALS:
"""
        
        for i, signal in enumerate(signals, 1):
            report += f"""
{i}. {signal['strategy_name']}
   • Pattern: {signal['pattern']}
   • Price: ${signal['current_price']:,.2f}
   • Confidence: {signal['ensemble_confidence']:.1%} ({signal['confidence_level']})
   • Position Size: ${signal['position_size']:,.0f}
   • Risk: ${signal['risk_amount']:,.0f}
   • Recommendation: {signal['recommendation']}
"""
        
        return report

def main():
    """Example usage of Live Confidence Trader."""
    logger.info("Live Confidence Trader - Example Usage")
    
    # Initialize trader
    trader = LiveConfidenceTrader('silver', '4h', 'long')
    
    # Example: Load recent data (in real implementation, this would be live data)
    from src.utils import load_features
    df = load_features('silver', '4h')
    
    # Scan for signals in the latest bar
    signals = trader.scan_for_signals(df)
    
    if signals:
        # Generate and display report
        report = trader.generate_trading_report(signals)
        logger.info(report)
        
        # Log signals
        for signal in signals:
            trader.log_signal(signal)
    else:
        logger.info("No trading signals found in current market conditions.")

if __name__ == "__main__":
    main()
