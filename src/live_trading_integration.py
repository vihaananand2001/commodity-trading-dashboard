#!/usr/bin/env python3
"""
Live Trading Integration with Confidence Scoring
Complete system for live trading with ML-enhanced confidence scoring
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

from src.utils import get_logger, load_features
from src.simple_confidence_scorer import SimpleConfidenceScorer
from src.backtest_engine import BacktestEngine
from src.strategy_builder import create_pattern_strategy

logger = get_logger(__name__)

class LiveTradingIntegration:
    """
    Complete live trading integration with confidence scoring.
    
    This class provides:
    1. Real-time signal generation
    2. Confidence scoring for each signal
    3. Position sizing based on confidence
    4. Risk management
    5. Trade logging and monitoring
    """
    
    def __init__(self, commodity: str, timeframe: str, direction: str = "long"):
        """
        Initialize the Live Trading Integration.
        
        Args:
            commodity: Trading commodity (e.g., 'gold', 'silver')
            timeframe: Trading timeframe (e.g., '1h', '4h', '1d')
            direction: Trading direction ('long' or 'short')
        """
        self.commodity = commodity
        self.timeframe = timeframe
        self.direction = direction
        
        # Initialize confidence scorer
        self.confidence_scorer = SimpleConfidenceScorer(commodity, timeframe, direction)
        
        # Trading parameters
        self.max_position_size = 100000  # Maximum position size
        self.confidence_threshold = 0.6  # Minimum confidence threshold
        self.max_risk_per_trade = 0.02   # Maximum 2% risk per trade
        self.max_daily_trades = 5        # Maximum trades per day
        
        # Trading state
        self.active_positions = {}
        self.daily_trade_count = 0
        self.last_trade_date = None
        self.signal_history = []
        
        # Performance tracking
        self.total_pnl = 0.0
        self.total_trades = 0
        self.winning_trades = 0
        
    def analyze_market_data(self, df: pd.DataFrame, current_bar: int = -1) -> Dict[str, Any]:
        """
        Analyze current market data and generate trading signals with confidence scores.
        
        Args:
            df: Current market data dataframe
            current_bar: Index of current bar (-1 for latest)
            
        Returns:
            Dictionary with market analysis and signals
        """
        if current_bar == -1:
            current_bar = len(df) - 1
        
        current_data = df.iloc[current_bar]
        
        # Extract current features
        current_features = self._extract_current_features(current_data)
        
        # Scan for signals
        signals = self.confidence_scorer.scan_for_signals(current_features, self.confidence_threshold)
        
        # Analyze market conditions
        market_analysis = self._analyze_market_conditions(current_features)
        
        # Generate trading recommendations
        recommendations = self._generate_trading_recommendations(signals, current_features)
        
        return {
            'timestamp': current_data.name if hasattr(current_data, 'name') else current_bar,
            'market_analysis': market_analysis,
            'signals': signals,
            'recommendations': recommendations,
            'features': current_features,
            'current_price': current_data['close']
        }
    
    def _extract_current_features(self, current_data: pd.Series) -> Dict[str, float]:
        """Extract features from current market data."""
        features = {
            'rsi_14': current_data.get('rsi_14', 50.0),
            'adx_14': current_data.get('adx_14', 20.0),
            'atr_14': current_data.get('atr_14', 1.0),
            'ema_20': current_data.get('ema_20', current_data['close']),
            'ema_50': current_data.get('ema_50', current_data['close']),
            'volume': current_data.get('volume', 1.0),
            'price_above_ema20': 1.0 if current_data['close'] > current_data.get('ema_20', current_data['close']) else 0.0,
            'price_above_ema50': 1.0 if current_data['close'] > current_data.get('ema_50', current_data['close']) else 0.0,
            'atr_pct': (current_data.get('atr_14', 1.0) / current_data['close']) * 100,
            'volume_ratio': current_data.get('volume_ratio', 1.0),
            'price_change_1': current_data.get('price_change_1', 0.0),
            'price_change_3': current_data.get('price_change_3', 0.0),
            'price_change_5': current_data.get('price_change_5', 0.0),
            'volatility_5': current_data.get('volatility_5', 1.0),
            'volatility_10': current_data.get('volatility_10', 1.0),
            'close': current_data['close']
        }
        
        # Add pattern features
        pattern_columns = [col for col in current_data.index if col.startswith('pattern_')]
        for pattern_col in pattern_columns:
            features[pattern_col] = current_data.get(pattern_col, 0.0)
        
        return features
    
    def _analyze_market_conditions(self, features: Dict[str, float]) -> Dict[str, Any]:
        """Analyze current market conditions."""
        rsi = features['rsi_14']
        adx = features['adx_14']
        volume = features['volume']
        atr_pct = features['atr_pct']
        
        # Determine market regime
        if rsi > 70:
            regime = "OVERBOUGHT"
        elif rsi < 30:
            regime = "OVERSOLD"
        else:
            regime = "NEUTRAL"
        
        # Determine trend strength
        if adx > 25:
            trend_strength = "STRONG"
        elif adx > 15:
            trend_strength = "MODERATE"
        else:
            trend_strength = "WEAK"
        
        # Determine volatility
        if atr_pct > 2.0:
            volatility = "HIGH"
        elif atr_pct > 1.0:
            volatility = "MODERATE"
        else:
            volatility = "LOW"
        
        # Determine volume
        if volume > 1.5:
            volume_level = "HIGH"
        elif volume > 1.0:
            volume_level = "NORMAL"
        else:
            volume_level = "LOW"
        
        return {
            'regime': regime,
            'trend_strength': trend_strength,
            'volatility': volatility,
            'volume_level': volume_level,
            'rsi': rsi,
            'adx': adx,
            'volume': volume,
            'atr_pct': atr_pct
        }
    
    def _generate_trading_recommendations(self, signals: List[Dict], features: Dict[str, float]) -> Dict[str, Any]:
        """Generate trading recommendations based on signals and market conditions."""
        if not signals:
            return {
                'action': 'WAIT',
                'reason': 'No high-confidence signals found',
                'top_signal': None,
                'position_sizing': 'NONE'
            }
        
        top_signal = signals[0]
        confidence = top_signal['overall_confidence']
        
        # Determine position sizing based on confidence
        if confidence >= 0.8:
            position_size = 'LARGE'
            action = 'ENTER'
        elif confidence >= 0.7:
            position_size = 'MEDIUM'
            action = 'ENTER'
        elif confidence >= 0.6:
            position_size = 'SMALL'
            action = 'ENTER'
        else:
            position_size = 'NONE'
            action = 'WAIT'
        
        # Check daily trade limits
        today = datetime.now().date()
        if self.last_trade_date == today and self.daily_trade_count >= self.max_daily_trades:
            action = 'WAIT'
            reason = 'Daily trade limit reached'
        else:
            reason = f"Confidence: {confidence:.1%}"
        
        return {
            'action': action,
            'reason': reason,
            'top_signal': top_signal,
            'position_sizing': position_size,
            'confidence_level': top_signal['confidence_level'],
            'risk_level': top_signal['risk_level']
        }
    
    def calculate_position_size(self, confidence: float, current_price: float, atr: float) -> Dict[str, float]:
        """Calculate position size based on confidence and risk parameters."""
        # Base position size
        base_size = self.max_position_size * 0.1  # 10% of max position
        
        # Adjust based on confidence
        confidence_multiplier = max(0.1, min(1.0, confidence))  # Between 0.1 and 1.0
        
        # Calculate stop loss and take profit levels
        stop_loss_atr_mult = 1.2  # Standard from our strategies
        take_profit_atr_mult = 1.5  # Standard from our strategies
        
        stop_loss_distance = atr * stop_loss_atr_mult
        take_profit_distance = atr * take_profit_atr_mult
        
        # Calculate position size based on risk
        risk_amount = self.max_position_size * self.max_risk_per_trade
        position_size_by_risk = risk_amount / stop_loss_distance
        
        # Use the smaller of confidence-based or risk-based sizing
        position_size = min(base_size * confidence_multiplier, position_size_by_risk)
        position_size = min(position_size, self.max_position_size)
        
        # Calculate number of units
        units = position_size / current_price
        
        return {
            'position_size': position_size,
            'units': units,
            'stop_loss': current_price - stop_loss_distance if self.direction == 'long' else current_price + stop_loss_distance,
            'take_profit': current_price + take_profit_distance if self.direction == 'long' else current_price - take_profit_distance,
            'risk_amount': risk_amount,
            'stop_loss_distance': stop_loss_distance,
            'take_profit_distance': take_profit_distance
        }
    
    def execute_trade(self, signal: Dict, current_price: float, features: Dict[str, float]) -> Dict[str, Any]:
        """Execute a trade based on signal and confidence."""
        strategy_name = signal['strategy_name']
        confidence = signal['overall_confidence']
        atr = features['atr_14']
        
        # Calculate position size
        position_info = self.calculate_position_size(confidence, current_price, atr)
        
        # Create trade record
        trade_record = {
            'timestamp': datetime.now().isoformat(),
            'strategy': strategy_name,
            'pattern': signal['pattern'],
            'direction': self.direction,
            'entry_price': current_price,
            'position_size': position_info['position_size'],
            'units': position_info['units'],
            'stop_loss': position_info['stop_loss'],
            'take_profit': position_info['take_profit'],
            'confidence': confidence,
            'confidence_level': signal['confidence_level'],
            'risk_level': signal['risk_level'],
            'risk_amount': position_info['risk_amount'],
            'status': 'OPEN'
        }
        
        # Add to active positions
        trade_id = f"{strategy_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.active_positions[trade_id] = trade_record
        
        # Update counters
        self.daily_trade_count += 1
        self.last_trade_date = datetime.now().date()
        
        # Log trade
        self._log_trade(trade_record)
        
        logger.info(f"✅ Trade executed: {strategy_name}")
        logger.info(f"   Entry Price: ${current_price:,.2f}")
        logger.info(f"   Position Size: ${position_info['position_size']:,.0f}")
        logger.info(f"   Confidence: {confidence:.1%}")
        logger.info(f"   Stop Loss: ${position_info['stop_loss']:,.2f}")
        logger.info(f"   Take Profit: ${position_info['take_profit']:,.2f}")
        
        return trade_record
    
    def _log_trade(self, trade_record: Dict[str, Any]):
        """Log trade to file."""
        log_file = Path(f"logs/trades_{self.commodity}_{self.timeframe}.csv")
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        trade_df = pd.DataFrame([trade_record])
        
        if log_file.exists():
            trade_df.to_csv(log_file, mode='a', header=False, index=False)
        else:
            trade_df.to_csv(log_file, index=False)
    
    def monitor_positions(self, current_price: float) -> List[Dict[str, Any]]:
        """Monitor active positions and check for exits."""
        closed_trades = []
        
        for trade_id, position in list(self.active_positions.items()):
            # Check for stop loss or take profit
            if self.direction == 'long':
                if current_price <= position['stop_loss']:
                    exit_reason = 'STOP_LOSS'
                elif current_price >= position['take_profit']:
                    exit_reason = 'TAKE_PROFIT'
                else:
                    continue
            else:
                if current_price >= position['stop_loss']:
                    exit_reason = 'STOP_LOSS'
                elif current_price <= position['take_profit']:
                    exit_reason = 'TAKE_PROFIT'
                else:
                    continue
            
            # Calculate P&L
            if self.direction == 'long':
                pnl = (current_price - position['entry_price']) * position['units']
            else:
                pnl = (position['entry_price'] - current_price) * position['units']
            
            # Update trade record
            position['exit_price'] = current_price
            position['exit_reason'] = exit_reason
            position['pnl'] = pnl
            position['status'] = 'CLOSED'
            position['exit_timestamp'] = datetime.now().isoformat()
            
            # Update performance tracking
            self.total_pnl += pnl
            self.total_trades += 1
            if pnl > 0:
                self.winning_trades += 1
            
            # Remove from active positions
            del self.active_positions[trade_id]
            closed_trades.append(position)
            
            logger.info(f"🔒 Position closed: {position['strategy']}")
            logger.info(f"   Exit Price: ${current_price:,.2f}")
            logger.info(f"   P&L: ${pnl:,.2f}")
            logger.info(f"   Exit Reason: {exit_reason}")
        
        return closed_trades
    
    def generate_trading_summary(self) -> str:
        """Generate a comprehensive trading summary."""
        win_rate = (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0
        
        summary = f"""
📊 TRADING SUMMARY - {self.commodity.upper()} {self.timeframe.upper()}
{'='*60}

🎯 PERFORMANCE METRICS:
• Total Trades: {self.total_trades}
• Winning Trades: {self.winning_trades}
• Win Rate: {win_rate:.1f}%
• Total P&L: ${self.total_pnl:,.2f}
• Daily Trades Today: {self.daily_trade_count}

📈 ACTIVE POSITIONS: {len(self.active_positions)}
"""
        
        if self.active_positions:
            for trade_id, position in self.active_positions.items():
                summary += f"""
• {position['strategy']}
  - Entry: ${position['entry_price']:,.2f}
  - Size: ${position['position_size']:,.0f}
  - Confidence: {position['confidence']:.1%}
  - Stop Loss: ${position['stop_loss']:,.2f}
  - Take Profit: ${position['take_profit']:,.2f}
"""
        else:
            summary += "• No active positions"
        
        return summary
    
    def run_live_analysis(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Run complete live analysis and return actionable insights."""
        # Analyze market data
        analysis = self.analyze_market_data(df)
        
        # Monitor existing positions
        closed_trades = self.monitor_positions(analysis['current_price'])
        
        # Generate recommendations
        recommendations = analysis['recommendations']
        
        # Prepare response
        response = {
            'timestamp': analysis['timestamp'],
            'current_price': analysis['current_price'],
            'market_analysis': analysis['market_analysis'],
            'signals_found': len(analysis['signals']),
            'top_signals': analysis['signals'][:3],  # Top 3 signals
            'recommendation': recommendations,
            'closed_trades': closed_trades,
            'active_positions': len(self.active_positions),
            'daily_trades': self.daily_trade_count
        }
        
        return response

def main():
    """Example usage of Live Trading Integration."""
    logger.info("Live Trading Integration - Example Usage")
    
    # Initialize trading system
    trader = LiveTradingIntegration('silver', '4h', 'long')
    
    # Load recent data (in real implementation, this would be live data)
    df = load_features('silver', '4h')
    
    # Run live analysis
    response = trader.run_live_analysis(df)
    
    # Display results
    logger.info(f"\n🎯 LIVE TRADING ANALYSIS")
    logger.info(f"Current Price: ${response['current_price']:,.2f}")
    logger.info(f"Market Regime: {response['market_analysis']['regime']}")
    logger.info(f"Trend Strength: {response['market_analysis']['trend_strength']}")
    logger.info(f"Signals Found: {response['signals_found']}")
    logger.info(f"Recommendation: {response['recommendation']['action']}")
    
    if response['signals_found'] > 0:
        top_signal = response['top_signals'][0]
        logger.info(f"Top Signal: {top_signal['strategy_name']}")
        logger.info(f"Confidence: {top_signal['overall_confidence']:.1%}")
        logger.info(f"Risk Level: {top_signal['risk_level']}")
    
    # Generate trading summary
    summary = trader.generate_trading_summary()
    logger.info(summary)

if __name__ == "__main__":
    main()
