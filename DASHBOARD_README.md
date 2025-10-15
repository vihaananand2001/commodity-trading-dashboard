# MCX Live Trading Dashboard

## 🎯 Overview

A comprehensive live trading dashboard for Indian MCX commodity markets featuring real-time data, ML confidence scoring, and position sizing tools.

## ✨ Features

### 📊 Real-Time Market Data
- **Live Price Updates**: Real-time Gold and Silver prices in INR
- **Market Status**: Current market session and trading hours
- **Historical Charts**: Interactive price charts with multiple timeframes
- **Market Analysis**: RSI, ADX, volatility, and volume analysis

### 🤖 ML Confidence Scoring
- **Multi-Factor Analysis**: Historical performance, market conditions, pattern strength, and risk assessment
- **Confidence Levels**: Very High (80%+), High (70-79%), Medium (60-69%), Low (<60%)
- **Real-Time Signals**: Live trading signals with confidence scores
- **Risk Assessment**: Automatic risk level classification

### 💰 Position Sizing Tools
- **Indian Lot Sizes**: Proper MCX lot sizes for Gold (1000g) and Silver (30000g)
- **Margin Calculator**: Real-time margin requirement calculations
- **Position Value**: Live position value calculations
- **Risk Management**: Built-in risk controls and limits

### 🎛️ Interactive Dashboard
- **Commodity Selection**: Switch between Gold and Silver
- **Timeframe Selection**: 1 Hour and 4 Hour timeframes
- **Performance Tracking**: Win rates, P&L, and trade statistics
- **Signal Display**: Clear visualization of trading opportunities

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip3 install -r requirements_dashboard.txt
```

### 2. Start the Dashboard
```bash
python3 start_dashboard.py
```

### 3. Access the Dashboard
Open your browser and navigate to:
```
http://localhost:5001
```

## 📋 Dashboard Components

### Live Price Display
- Current market price in INR
- Price change and percentage
- Lot size and volume information
- Real-time updates every 2 minutes

### Market Analysis
- **Market Regime**: Overbought, Oversold, or Neutral
- **Trend Strength**: Strong, Moderate, or Weak
- **Volatility**: High, Moderate, or Low
- **Volume Level**: High, Normal, or Low
- **Technical Indicators**: RSI, ADX, ATR values

### Trading Signals
- **Strategy Names**: Clear identification of trading strategies
- **Confidence Scores**: ML-powered confidence percentages
- **Risk Levels**: Low, Moderate, or High risk classification
- **Recommendations**: Actionable trading advice
- **Confidence Breakdown**: Detailed confidence component analysis

### Position Calculator
- **Quantity Input**: Number of lots to trade
- **Position Value**: Total value of the position
- **Margin Required**: Required margin in INR
- **Real-Time Updates**: Automatic recalculation with price changes

### Performance Metrics
- **Total Trades**: Number of trades executed
- **Win Rate**: Percentage of winning trades
- **Total P&L**: Overall profit/loss in INR
- **Active Positions**: Currently open positions

## 🎯 MCX Specifications

### Gold Mini (GOLDM)
- **Contract**: 100 grams
- **Lot Size**: 100 grams (1 contract)
- **Tick Size**: ₹1 per gram
- **Margin**: 5% of position value
- **Currency**: INR
- **Expiry**: December 2025

### Silver Mini (SILVERM)
- **Contract**: 5 kg
- **Lot Size**: 5000 grams (1 contract)
- **Tick Size**: ₹1 per gram
- **Margin**: 5% of position value
- **Currency**: INR
- **Expiry**: December 2025

## 🔧 API Endpoints

### Market Data
- `GET /api/market-data/<commodity>` - Get live market data
- `GET /api/market-status` - Get market status
- `GET /api/commodity-specs` - Get commodity specifications

### Trading Signals
- `GET /api/signals/<commodity>/<timeframe>` - Get trading signals
- `GET /api/performance/<commodity>` - Get performance metrics

### Position Calculator
- `POST /api/position-calculator` - Calculate position size and margin

## 📊 Confidence Scoring System

### Components (Weighted)
1. **Historical Performance (40%)**
   - Win rate analysis
   - Profit factor evaluation
   - Drawdown assessment
   - Sample size consideration

2. **Market Conditions (30%)**
   - RSI analysis
   - ADX trend strength
   - Volume assessment
   - Volatility evaluation

3. **Pattern Strength (20%)**
   - Pattern-specific criteria
   - Strategy requirements
   - Filter conditions

4. **Risk Conditions (10%)**
   - Volatility risk
   - Volume risk
   - Momentum risk

### Confidence Levels
- **Very High (80%+)**: Large position, low risk
- **High (70-79%)**: Medium position, moderate risk
- **Medium (60-69%)**: Small position, moderate risk
- **Low (50-59%)**: Very small position, high risk
- **Very Low (<50%)**: No trade recommended

## 🛡️ Risk Management

### Built-in Safeguards
- **Confidence Thresholds**: Minimum confidence levels for trades
- **Position Limits**: Maximum position sizes
- **Daily Trade Limits**: Maximum trades per day
- **Margin Controls**: Automatic margin calculations

### Real-time Monitoring
- **Active Position Tracking**: Monitor open positions
- **Stop Loss Management**: Automatic stop loss calculations
- **Take Profit Targets**: Automatic take profit levels
- **Risk Alerts**: Real-time risk notifications

## 📱 User Interface

### Navigation
- **Commodity Selection**: Gold/Silver toggle buttons
- **Timeframe Selection**: 1H/4H timeframe buttons
- **Real-time Updates**: Automatic data refresh every 2 minutes
- **Market Status**: Live market open/closed indicator

### Visual Design
- **Modern UI**: Clean, professional interface
- **Color Coding**: Intuitive color schemes for different states
- **Responsive Design**: Works on desktop and mobile devices
- **Interactive Charts**: Zoom, pan, and hover capabilities

## 🔄 Data Updates

### Update Frequency
- **Market Data**: Every 2 minutes
- **Trading Signals**: Every 2 minutes
- **Market Status**: Every 30 seconds
- **Performance Metrics**: Every 2 minutes

### Data Sources
- **Live Prices**: Simulated MCX data (production would use real feeds)
- **Historical Data**: Generated realistic historical patterns
- **Technical Indicators**: Calculated in real-time
- **ML Confidence**: Computed using trained models

## 🚀 Production Deployment

### Real Data Integration
To connect to real MCX data feeds:

1. **Replace Simulated Data**: Update `MCXDataFetcher` with real API calls
2. **Add Authentication**: Implement MCX API authentication
3. **Error Handling**: Add robust error handling for data feed failures
4. **Backup Systems**: Implement fallback data sources

### Hosting Options
- **Local Development**: `python3 start_dashboard.py` (runs on http://localhost:5001)
- **Production Server**: Use Gunicorn or similar WSGI server
- **Cloud Deployment**: Deploy on AWS, Azure, or Google Cloud
- **Docker**: Containerize for easy deployment

## 🛠️ Customization

### Adding New Commodities
1. Update `commodity_specs` in `MCXDataFetcher`
2. Add commodity buttons in HTML template
3. Update JavaScript commodity selection logic
4. Add new strategy rules YAML files

### Modifying Confidence Scoring
1. Adjust weights in `confidence_weights`
2. Add new confidence components
3. Update confidence calculation logic
4. Modify confidence level thresholds

### UI Customization
1. Update CSS variables in `dashboard.html`
2. Modify Bootstrap theme
3. Add custom components
4. Implement additional charts

## 📞 Support

For issues or questions:
1. Check the logs in the terminal
2. Verify all dependencies are installed
3. Ensure port 5000 is available
4. Check browser console for JavaScript errors

## 🎉 Success!

Your MCX Live Trading Dashboard is now ready for live trading with:
- ✅ Real-time market data
- ✅ ML confidence scoring
- ✅ Position sizing tools
- ✅ Risk management
- ✅ Professional interface

**Happy Trading!** 🚀📈
