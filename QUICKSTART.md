# 🚀 Quick Start Guide

## Step-by-Step: Get Your First Results in 5 Minutes

### 1️⃣ Install Dependencies (30 seconds)

```bash
pip install pandas numpy pyyaml
```

### 2️⃣ Build Features (2-3 minutes)

Start with one commodity to test:

```bash
cd /Users/vihaananand/Desktop/commodity_trading_module
python src/main.py --build-features --commodity gold --timeframe 4h
```

Or build everything at once (5-10 minutes):

```bash
python src/main.py --build-features
```

### 3️⃣ Run Your First Optimization (1-2 minutes)

```bash
python src/main.py --optimize-all --commodity gold --timeframe 4h --direction long
```

### 4️⃣ Check Results

Results are saved to:
```
reports/optimization/gold/4h/
```

Files:
- `{pattern}_long_optimization.csv` - All successful parameter combinations
- `{pattern}_long_diagnostics.csv` - Why combinations failed

### 5️⃣ Run the Demo (Optional)

```bash
python examples/quick_demo.py
```

---

## 📋 Common Commands

### Build Features for All Assets
```bash
python src/main.py --build-features
```

### Optimize Single Pattern
```bash
python src/main.py --optimize \
  --commodity silver \
  --timeframe 1h \
  --pattern pattern_inside_bar \
  --direction long
```

### Optimize All Patterns (Recommended)
```bash
python src/main.py --optimize-all \
  --commodity gold \
  --timeframe 4h \
  --direction long
```

### Run Complete Pipeline
```bash
python src/main.py --full-pipeline \
  --commodity copper \
  --timeframe 1d \
  --direction long
```

### Process Everything (Long Running!)
```bash
# This will take hours - run overnight
python src/main.py --full-pipeline \
  --commodity all \
  --timeframe all \
  --direction both
```

---

## 🎯 Understanding the Output

### Console Output

You'll see progress like:
```
============================================================
OPTIMIZING: GOLD 4H - pattern_inside_bar
Direction: LONG
============================================================
Generated 8640 parameter combinations
Using multiprocessing with 8 processes
Testing 8640 combinations...

Optimization complete in 45.2 seconds
Tested: 8640 combinations
Passed filters: 127

Top 3 Results:
  1. Trades=24, PF=2.15, WR=66.7%, DD=8.3%
  2. Trades=22, PF=2.08, WR=68.2%, DD=9.1%
  3. Trades=21, PF=1.98, WR=63.6%, DD=7.5%
```

### Results Files

Each optimization creates a CSV with columns:
- `trades` - Number of trades
- `win_rate` - Win rate percentage
- `profit_factor` - Gross profit / Gross loss
- `max_dd_pct` - Maximum drawdown percentage
- `total_pnl` - Total profit/loss
- `stop_loss_atr`, `take_profit_atr` - SL/TP parameters
- `rsi_min`, `adx_min`, etc. - Filter parameters
- `trend_condition` - Trend filter used

**Results are sorted by:**
1. Trade count (more is better)
2. Profit factor (higher is better)
3. Win rate (higher is better)
4. Drawdown (lower is better)

---

## 🔧 Customization

### Edit Configuration

```bash
nano config/settings.yaml
```

Key settings to adjust:
- `objectives.max_drawdown_pct` - Max acceptable drawdown
- `objectives.min_profit_factor` - Minimum PF to consider
- `optimization.*_range` - Parameter ranges to test
- `filters.min_trades` - Minimum trades required

### Add Your Own Patterns

Edit `src/patterns.py` and add:
```python
def detect_my_pattern(df: pd.DataFrame) -> pd.Series:
    """Your pattern logic here"""
    # Return a Series of 1s and 0s
    return pattern_signal
```

Then add to `detect_all_patterns()` function.

---

## 🐛 Troubleshooting

### "Features file not found"
**Solution:** Run feature engineering first:
```bash
python src/main.py --build-features --commodity gold --timeframe 4h
```

### "No parameter combinations to test"
**Solution:** Your parameter ranges might be too restrictive. Check `config/settings.yaml`

### "No combinations passed filters"
**Solution:** Your filters might be too strict. Try:
- Lower `min_profit_factor` in config
- Increase `max_drawdown_pct`
- Reduce `filters.min_trades`

### Import Errors
**Solution:** Install dependencies:
```bash
pip install -r requirements.txt
```

### Slow Performance
**Solution:** The optimizer uses multiprocessing by default. If you want to debug:
```bash
python src/main.py --optimize-all --commodity gold --timeframe 4h --no-multiprocessing
```

---

## 📚 Next Steps

1. **Analyze Results**: Open CSV files in Excel or pandas
2. **Test Different Timeframes**: Compare 1h vs 4h vs 1d
3. **Compare Patterns**: Which patterns work best for each commodity?
4. **Refine Parameters**: Narrow ranges based on initial results
5. **Build Custom Strategies**: Use `StrategyBuilder` in Python
6. **Backtest Top Performers**: Deep dive into winning strategies

---

## 💡 Pro Tips

- Start with 4H timeframe (good balance of trades and data)
- Gold typically has more patterns than Copper
- Inside bars and engulfing patterns tend to be most reliable
- Don't over-optimize - look for robust parameters that work across ranges
- Check the diagnostics CSV to understand why combinations fail
- Run optimization for both long and short to see which direction works better

---

**Need Help?** Check the main README.md for detailed architecture and examples.

**Ready to Go Deeper?** Check `examples/quick_demo.py` for Python usage examples.




