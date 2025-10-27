#!/usr/bin/env python3
"""
Gold Scalping Strategy for Indian MCX Market
Uses actual Indian commodity prices instead of converted USD prices
Optimized for quick profits with tight stop losses
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import time

from src.mcx_data_fetcher import MCXDataFetcher
from src.utils import get_logger

logger = get_logger(__name__)

class GoldScalpingStrategy:
    """
    Scalping strategy specifically designed for Indian MCX Gold prices
    Uses actual Indian commodity prices for accurate trading
    """
    
    def __init__(self):
        """Initialize the scalping strategy."""
        self.mcx_fetcher = MCXDataFetcher()
        self.position = None
        self.entry_price = 0
        self.stop_loss = 0
        self.take_profit = 0
        self.position_size = 1  # 1 lot (100 grams for Gold Mini)
        
        # Scalping parameters (tight for quick profits)
        self.stop_loss_points = 20  # 20 points stop loss (₹20 per gram)
        self.take_profit_points = 30  # 30 points take profit (₹30 per gram)
        self.max_hold_minutes = 15  # Maximum hold time: 15 minutes
        
        # Strategy parameters
        self.min_volume_ratio = 1.2  # Minimum volume spike
        self.rsi_oversold = 30
        self.rsi_overbought = 70
        self.atr_multiplier = 1.5
        
        # Performance tracking
        self.trades = []
        self.total_pnl = 0
        self.win_count = 0
        self.loss_count = 0
        
    def get_market_data(self) -> Dict:
        """Get current market data from MCX."""
        try:
            # Get live Gold price
            gold_data = self.mcx_fetcher.get_live_price('GOLD')
            
            # Get market status
            market_status = self.mcx_fetcher.get_market_status()
            
            return {
                'gold_price': gold_data.get('close', 0),
                'gold_change': gold_data.get('change', 0),
                'gold_change_pct': gold_data.get('change_pct', 0),
                'volume': gold_data.get('volume', 0),
                'market_open': market_status.get('market_open', False),
                'session': market_status.get('session', 'CLOSED'),
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting market data: {e}")
            return {}
    
    def calculate_technical_indicators(self, price_data: List[float]) -> Dict:
        """Calculate technical indicators for scalping."""
        if len(price_data) < 20:
            return {}
        
        prices = np.array(price_data)
        
        # Calculate RSI (14-period)
        rsi = self.calculate_rsi(prices, 14)
        
        # Calculate ATR (14-period)
        atr = self.calculate_atr(prices, 14)
        
        # Calculate EMA (5, 10, 20)
        ema_5 = self.calculate_ema(prices, 5)
        ema_10 = self.calculate_ema(prices, 10)
        ema_20 = self.calculate_ema(prices, 20)
        
        # Calculate volume ratio (simplified)
        volume_ratio = 1.0  # Placeholder - would need volume data
        
        return {
            'rsi': rsi,
            'atr': atr,
            'ema_5': ema_5,
            'ema_10': ema_10,
            'ema_20': ema_20,
            'volume_ratio': volume_ratio,
            'trend_bullish': ema_5 > ema_10 > ema_20,
            'trend_bearish': ema_5 < ema_10 < ema_20
        }
    
    def calculate_rsi(self, prices: np.ndarray, period: int = 14) -> float:
        """Calculate RSI indicator."""
        if len(prices) < period + 1:
            return 50.0
        
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def calculate_atr(self, prices: np.ndarray, period: int = 14) -> float:
        """Calculate ATR indicator (simplified)."""
        if len(prices) < period + 1:
            return np.std(prices) * 2
        
        # Simplified ATR calculation
        price_changes = np.abs(np.diff(prices))
        atr = np.mean(price_changes[-period:])
        
        return atr
    
    def calculate_ema(self, prices: np.ndarray, period: int) -> float:
        """Calculate EMA indicator."""
        if len(prices) < period:
            return prices[-1]
        
        alpha = 2 / (period + 1)
        ema = prices[0]
        
        for price in prices[1:]:
            ema = alpha * price + (1 - alpha) * ema
        
        return ema
    
    def check_entry_signals(self, market_data: Dict, indicators: Dict) -> Dict:
        """Check for scalping entry signals."""
        signals = {
            'long_signal': False,
            'short_signal': False,
            'signal_strength': 0,
            'reason': ''
        }
        
        if not market_data.get('market_open', False):
            return signals
        
        current_price = market_data.get('gold_price', 0)
        if current_price == 0:
            return signals
        
        rsi = indicators.get('rsi', 50)
        atr = indicators.get('atr', 0)
        trend_bullish = indicators.get('trend_bullish', False)
        trend_bearish = indicators.get('trend_bearish', False)
        volume_ratio = indicators.get('volume_ratio', 1.0)
        
        # Long scalping signals
        if (rsi < self.rsi_oversold and 
            trend_bullish and 
            volume_ratio > self.min_volume_ratio):
            signals['long_signal'] = True
            signals['signal_strength'] = 80
            signals['reason'] = f'RSI oversold ({rsi:.1f}), bullish trend, volume spike'
        
        # Short scalping signals
        elif (rsi > self.rsi_overbought and 
              trend_bearish and 
              volume_ratio > self.min_volume_ratio):
            signals['short_signal'] = True
            signals['signal_strength'] = 80
            signals['reason'] = f'RSI overbought ({rsi:.1f}), bearish trend, volume spike'
        
        # Additional scalping opportunities
        elif rsi < 40 and trend_bullish:
            signals['long_signal'] = True
            signals['signal_strength'] = 60
            signals['reason'] = f'RSI low ({rsi:.1f}), bullish trend'
        
        elif rsi > 60 and trend_bearish:
            signals['short_signal'] = True
            signals['signal_strength'] = 60
            signals['reason'] = f'RSI high ({rsi:.1f}), bearish trend'
        
        return signals
    
    def enter_position(self, direction: str, entry_price: float, indicators: Dict) -> bool:
        """Enter a scalping position."""
        try:
            atr = indicators.get('atr', 20)  # Default ATR
            
            self.position = direction
            self.entry_price = entry_price
            self.entry_time = datetime.now()
            
            # Calculate stop loss and take profit
            if direction == 'long':
                self.stop_loss = entry_price - self.stop_loss_points
                self.take_profit = entry_price + self.take_profit_points
            else:  # short
                self.stop_loss = entry_price + self.stop_loss_points
                self.take_profit = entry_price - self.take_profit_points
            
            # Calculate position value
            position_value = self.mcx_fetcher.calculate_position_value(
                'GOLD', self.position_size, entry_price
            )
            
            logger.info(f"Entered {direction} position at ₹{entry_price:,.2f}")
            logger.info(f"Stop Loss: ₹{self.stop_loss:,.2f}")
            logger.info(f"Take Profit: ₹{self.take_profit:,.2f}")
            logger.info(f"Position Value: ₹{position_value.get('position_value', 0):,.2f}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error entering position: {e}")
            return False
    
    def check_exit_signals(self, current_price: float) -> Tuple[bool, str, float]:
        """Check for exit signals."""
        if not self.position:
            return False, '', 0
        
        # Check stop loss
        if self.position == 'long' and current_price <= self.stop_loss:
            return True, 'stop_loss', self.stop_loss
        
        if self.position == 'short' and current_price >= self.stop_loss:
            return True, 'stop_loss', self.stop_loss
        
        # Check take profit
        if self.position == 'long' and current_price >= self.take_profit:
            return True, 'take_profit', self.take_profit
        
        if self.position == 'short' and current_price <= self.take_profit:
            return True, 'take_profit', self.take_profit
        
        # Check time-based exit
        if datetime.now() - self.entry_time > timedelta(minutes=self.max_hold_minutes):
            return True, 'time_exit', current_price
        
        return False, '', 0
    
    def exit_position(self, exit_price: float, exit_reason: str) -> Dict:
        """Exit the current position."""
        if not self.position:
            return {}
        
        # Calculate P&L
        if self.position == 'long':
            pnl_points = exit_price - self.entry_price
        else:  # short
            pnl_points = self.entry_price - exit_price
        
        pnl_amount = pnl_points * self.position_size * 100  # 100 grams per lot
        
        # Update performance tracking
        self.total_pnl += pnl_amount
        if pnl_amount > 0:
            self.win_count += 1
        else:
            self.loss_count += 1
        
        # Record trade
        trade = {
            'entry_time': self.entry_time.isoformat(),
            'exit_time': datetime.now().isoformat(),
            'direction': self.position,
            'entry_price': self.entry_price,
            'exit_price': exit_price,
            'exit_reason': exit_reason,
            'pnl_points': pnl_points,
            'pnl_amount': pnl_amount,
            'hold_time_minutes': (datetime.now() - self.entry_time).total_seconds() / 60
        }
        
        self.trades.append(trade)
        
        logger.info(f"Exited {self.position} position at ₹{exit_price:,.2f}")
        logger.info(f"Exit reason: {exit_reason}")
        logger.info(f"P&L: ₹{pnl_amount:,.2f} ({pnl_points:+.1f} points)")
        
        # Reset position
        self.position = None
        self.entry_price = 0
        self.stop_loss = 0
        self.take_profit = 0
        
        return trade
    
    def get_performance_summary(self) -> Dict:
        """Get performance summary."""
        total_trades = len(self.trades)
        win_rate = (self.win_count / total_trades * 100) if total_trades > 0 else 0
        
        return {
            'total_trades': total_trades,
            'win_count': self.win_count,
            'loss_count': self.loss_count,
            'win_rate': win_rate,
            'total_pnl': self.total_pnl,
            'avg_pnl_per_trade': self.total_pnl / total_trades if total_trades > 0 else 0,
            'current_position': self.position,
            'strategy_status': 'ACTIVE' if self.position else 'WAITING'
        }
    
    def run_scalping_session(self, duration_minutes: int = 60) -> Dict:
        """Run a scalping session."""
        logger.info(f"Starting Gold Scalping Session for {duration_minutes} minutes")
        
        start_time = datetime.now()
        end_time = start_time + timedelta(minutes=duration_minutes)
        
        price_history = []
        
        while datetime.now() < end_time:
            try:
                # Get market data
                market_data = self.get_market_data()
                
                if not market_data.get('market_open', False):
                    logger.info("Market is closed, waiting...")
                    time.sleep(60)
                    continue
                
                current_price = market_data.get('gold_price', 0)
                if current_price == 0:
                    time.sleep(5)
                    continue
                
                # Add to price history
                price_history.append(current_price)
                if len(price_history) > 50:  # Keep last 50 prices
                    price_history.pop(0)
                
                # Calculate indicators
                indicators = self.calculate_technical_indicators(price_history)
                
                if not self.position:
                    # Check for entry signals
                    signals = self.check_entry_signals(market_data, indicators)
                    
                    if signals['long_signal']:
                        self.enter_position('long', current_price, indicators)
                    elif signals['short_signal']:
                        self.enter_position('short', current_price, indicators)
                
                else:
                    # Check for exit signals
                    should_exit, exit_reason, exit_price = self.check_exit_signals(current_price)
                    
                    if should_exit:
                        self.exit_position(exit_price, exit_reason)
                
                # Log current status
                logger.info(f"Price: ₹{current_price:,.2f}, Position: {self.position or 'None'}")
                
                # Wait before next iteration
                time.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"Error in scalping session: {e}")
                time.sleep(5)
        
        # Close any remaining position
        if self.position:
            market_data = self.get_market_data()
            current_price = market_data.get('gold_price', self.entry_price)
            self.exit_position(current_price, 'session_end')
        
        # Return performance summary
        performance = self.get_performance_summary()
        logger.info(f"Scalping session completed. Performance: {performance}")
        
        return performance

def main():
    """Test the Gold Scalping Strategy."""
    logger.info("Testing Gold Scalping Strategy")
    
    strategy = GoldScalpingStrategy()
    
    # Test market data
    market_data = strategy.get_market_data()
    logger.info(f"Market Data: {market_data}")
    
    # Test indicators
    test_prices = [75000, 75100, 75050, 75200, 75150, 75300, 75250, 75400]
    indicators = strategy.calculate_technical_indicators(test_prices)
    logger.info(f"Indicators: {indicators}")
    
    # Test entry signals
    signals = strategy.check_entry_signals(market_data, indicators)
    logger.info(f"Entry Signals: {signals}")
    
    # Run a short scalping session (5 minutes for testing)
    performance = strategy.run_scalping_session(5)
    logger.info(f"Session Performance: {performance}")

if __name__ == "__main__":
    main()
