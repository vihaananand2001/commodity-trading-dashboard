# Commodity Trading Pattern Optimization Framework

A comprehensive, pattern-first trading framework for Gold, Silver, and Copper across multiple timeframes (1H, 4H, 1D).

## 🎯 Objectives

- **Primary Goal**: Maximize number of profitable trades
- **Drawdown**: 10-15% maximum (flexible based on profitability)
- **Profit Factor**: > 1.25
- **Win Rate**: 60%+
- **Philosophy**: Use guardrails intelligently - can push boundaries if profitability justifies

## 🏗️ Architecture

```
commodity_trading_module/
├── data/
│   ├── raw/              # OHLC data (1h, 4h, 1d)
│   └── processed/        # Feature-engineered datasets
├── src/
│   ├── utils.py          # Utility functions
│   ├── indicators.py     # Technical indicators (RSI, ADX, ATR, EMA, etc.)
│   ├── patterns.py       # Candlestick pattern detection (25+ patterns)
│   ├── feature_engineering.py  # Complete feature pipeline
│   ├── backtest_engine.py      # Backtesting with SL/TP
│   ├── strategy_builder.py     # Pattern + indicator strategies
│   ├── optimizer.py            # Multiprocessing grid search
│   ├── config.py               # Configuration management
│   └── main.py                 # Main entry point
├── config/
│   └── settings.yaml     # Configuration parameters
├── models/               # Saved models and rules
├── reports/              # Optimization results
└── requirements.txt      # Python dependencies
```

## 🔍 Pattern-First Approach

The framework detects **25+ candlestick patterns** including:

### Bullish Patterns:
- Inside Bar (consolidation → breakout)
- Bullish Engulfing
- Hammer / Bullish Pin Bar
- Morning Star
- Three White Soldiers
- Breakout Bars (10, 20-period)
- Range Expansion
- Harami Bullish
- Marubozu Bullish
- Tweezer Bottom

### Bearish Patterns:
- Bearish Engulfing
- Shooting Star / Bearish Pin Bar
- Evening Star
- Three Black Crows
- Breakdown Bars
- Harami Bearish
- Marubozu Bearish
- Tweezer Top

### Pattern Confirmation with Indicators:
- **Trend**: EMA (5, 10, 20, 50, 100, 200), SMA
- **Momentum**: RSI (7, 14, 21), MACD, Stochastic
- **Strength**: ADX (14, 20), Directional Movement
- **Volatility**: ATR (7, 14, 21), Bollinger Bands
- **Volume**: OBV, Volume Ratios
- **Other**: Supertrend, VWAP

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Build Features

```bash
# Build features for all commodities and timeframes
python src/main.py --build-features

# Or for specific commodity/timeframe
python src/main.py --build-features --commodity gold --timeframe 4h
```

### 3. Run Optimization

```bash
# Optimize all patterns for Gold 4H (long)
python src/main.py --optimize-all --commodity gold --timeframe 4h --direction long

# Optimize specific pattern
python src/main.py --optimize --commodity silver --timeframe 1h --pattern pattern_inside_bar --direction long

# Run full pipeline (features + optimization)
python src/main.py --full-pipeline --commodity copper --timeframe 1d --direction long
```

### 4. Optimize Everything

```bash
# Process all commodities, all timeframes, both directions
python src/main.py --full-pipeline --commodity all --timeframe all --direction both
```

## 📊 Results

Results are saved to `reports/optimization/{commodity}/{timeframe}/` with:
- Optimization results CSV (all parameter combinations that passed filters)
- Diagnostics CSV (why combinations failed)
- Sorted by: Trade count → Profit Factor → Win Rate → Drawdown

## ⚙️ Configuration

Edit `config/settings.yaml` to customize:

- **Optimization ranges**: SL/TP multipliers, RSI/ADX thresholds, volatility bands
- **Trading objectives**: Max drawdown, min profit factor, target trade count
- **Multiprocessing**: Number of cores, chunk size
- **Patterns**: Which patterns to focus on
- **Filters**: Minimum trades, max combinations to test

## 🔬 Example Workflow

```python
# In Python or Jupyter
from utils import load_features
from strategy_builder import StrategyBuilder
from backtest_engine import simple_backtest

# Load data
df = load_features('gold', '4h')

# Build strategy
strategy = StrategyBuilder(df)
strategy.add_pattern('pattern_inside_bar')
strategy.add_trend_filter('ema_20 > ema_50')
strategy.add_momentum_filter('rsi_14 >= 55')
strategy.add_strength_filter('adx_14 >= 20')

# Backtest
trades, summary = simple_backtest(
    df=df,
    entry_condition=lambda df: strategy.get_entry_signal(),
    direction='long',
    stop_loss_atr=2.0,
    take_profit_atr=2.5,
    max_hold_bars=10
)

print(f"Trades: {summary['total_trades']}")
print(f"Win Rate: {summary['win_rate']:.1f}%")
print(f"Profit Factor: {summary['profit_factor']:.2f}")
print(f"Max DD: {summary['max_dd_pct']:.2f}%")
```

## 🧪 Features Included

The feature engineering pipeline creates **150+ features** per bar:

- **Price Action**: Body %, wicks, gaps, consecutive bars
- **Patterns**: 25+ candlestick patterns
- **Indicators**: All major technical indicators
- **Trend**: EMA slopes, higher highs/lows, trend states
- **Momentum**: RSI zones, MACD signals, Stochastic
- **Volatility**: ATR zones, ADX strength, Bollinger Bands
- **Market Context**: Time of day, session, day of week

## 📈 Backtesting Engine

Robust backtesting with:
- ✅ ATR-based stop loss and take profit
- ✅ Time-based exits (max hold bars)
- ✅ Breakeven moves (optional)
- ✅ MAE/MFE tracking (maximum adverse/favorable excursion)
- ✅ Multiple exit reasons tracked
- ✅ Full trade log with timestamps

## 🎓 Key Concepts

1. **Pattern-First**: Patterns trigger entries, indicators filter for quality
2. **Broad Discovery**: Test all patterns across all assets/timeframes
3. **Flexible Guardrails**: Objectives are guidelines, not hard limits
4. **Trade Density**: Maximize trades while maintaining quality metrics
5. **Multiprocessing**: Fast grid search with parallel processing

## 📝 Next Steps

1. Run full feature engineering: `python src/main.py --build-features`
2. Optimize patterns for your preferred commodity/timeframe
3. Analyze results in `reports/optimization/`
4. Refine parameter ranges in `config/settings.yaml`
5. Build custom strategies using `StrategyBuilder`
6. Create visualizations of equity curves and parameter sensitivity

## 🤝 Contributing

This framework is designed to be extensible:
- Add new patterns in `patterns.py`
- Add new indicators in `indicators.py`
- Modify optimization ranges in `config/settings.yaml`
- Create custom strategies in `strategy_builder.py`

## 📄 License

Open source - use and modify as needed.

---

**Happy Trading! 📈🚀**




