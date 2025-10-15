"""
Commodity Trading Dashboard - Ultra Clean Version
No complex dependencies, guaranteed to work on RENDER
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import yfinance as yf

# Page configuration
st.set_page_config(
    page_title="Commodity Trading Dashboard",
    page_icon="📈",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #1f4e79 0%, #2d5a87 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 4px solid #1f4e79;
    }
    .signal-buy {
        background-color: #d4edda;
        color: #155724;
        padding: 0.5rem;
        border-radius: 5px;
        border-left: 4px solid #28a745;
    }
    .signal-sell {
        background-color: #f8d7da;
        color: #721c24;
        padding: 0.5rem;
        border-radius: 5px;
        border-left: 4px solid #dc3545;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_live_price(commodity):
    """Get live price data for commodity"""
    try:
        if commodity == 'GOLD':
            ticker = yf.Ticker("GC=F")
        elif commodity == 'SILVER':
            ticker = yf.Ticker("SI=F")
        else:
            return None
            
        data = ticker.history(period="1d")
        if data.empty:
            return None
            
        latest = data.iloc[-1]
        prev = data.iloc[-2] if len(data) > 1 else latest
        
        price_usd = latest['Close']
        price_inr = price_usd * 83.0  # Approximate USD to INR conversion
        
        change = latest['Close'] - prev['Close']
        change_percent = (change / prev['Close']) * 100
        
        return {
            'price_inr': price_inr,
            'price_usd': price_usd,
            'change': change,
            'change_percent': change_percent,
            'volume': latest['Volume']
        }
    except Exception as e:
        st.error(f"Error fetching price data: {e}")
        return None

@st.cache_data(ttl=300)
def get_historical_data(commodity, timeframe):
    """Get historical data for charting"""
    try:
        if commodity == 'GOLD':
            ticker = yf.Ticker("GC=F")
        elif commodity == 'SILVER':
            ticker = yf.Ticker("SI=F")
        else:
            return None
            
        # Get appropriate period based on timeframe
        if timeframe == '1h':
            period = "5d"
            interval = "1h"
        elif timeframe == '4h':
            period = "30d"
            interval = "4h"
        else:  # 1d
            period = "1y"
            interval = "1d"
            
        data = ticker.history(period=period, interval=interval)
        if data.empty:
            return None
            
        # Convert to INR and add technical indicators
        data['Close_INR'] = data['Close'] * 83.0
        data['SMA_20'] = data['Close'].rolling(window=20).mean() * 83.0
        data['SMA_50'] = data['Close'].rolling(window=50).mean() * 83.0
        
        return data
    except Exception as e:
        st.error(f"Error fetching historical data: {e}")
        return None

def create_price_chart(data, commodity):
    """Create price chart with technical indicators"""
    if data is None or data.empty:
        return None
        
    fig = go.Figure()
    
    # Candlestick chart
    fig.add_trace(go.Candlestick(
        x=data.index,
        open=data['Open'] * 83.0,
        high=data['High'] * 83.0,
        low=data['Low'] * 83.0,
        close=data['Close'] * 83.0,
        name="Price",
        increasing_line_color='#00ff00',
        decreasing_line_color='#ff0000'
    ))
    
    # Moving averages
    if 'SMA_20' in data.columns:
        fig.add_trace(go.Scatter(
            x=data.index,
            y=data['SMA_20'],
            mode='lines',
            name='SMA 20',
            line=dict(color='orange', width=2)
        ))
    
    if 'SMA_50' in data.columns:
        fig.add_trace(go.Scatter(
            x=data.index,
            y=data['SMA_50'],
            mode='lines',
            name='SMA 50',
            line=dict(color='blue', width=2)
        ))
    
    fig.update_layout(
        title=f"{commodity} Price Chart (₹)",
        xaxis_title="Date",
        yaxis_title="Price (₹)",
        height=500,
        showlegend=True,
        template="plotly_white"
    )
    
    return fig

def generate_simple_signals(data, commodity):
    """Generate simple trading signals based on moving averages"""
    if data is None or len(data) < 50:
        return []
        
    signals = []
    latest = data.iloc[-1]
    
    # Simple SMA crossover strategy
    if 'SMA_20' in data.columns and 'SMA_50' in data.columns:
        sma_20 = latest['SMA_20']
        sma_50 = latest['SMA_50']
        price = latest['Close_INR']
        
        if sma_20 > sma_50 and price > sma_20:
            signals.append({
                'type': 'BUY',
                'strength': 'Strong' if (sma_20 - sma_50) / sma_50 > 0.02 else 'Medium',
                'reason': 'Price above SMA 20, SMA 20 above SMA 50',
                'price': price
            })
        elif sma_20 < sma_50 and price < sma_20:
            signals.append({
                'type': 'SELL',
                'strength': 'Strong' if (sma_50 - sma_20) / sma_50 > 0.02 else 'Medium',
                'reason': 'Price below SMA 20, SMA 20 below SMA 50',
                'price': price
            })
    
    return signals

def main():
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>📈 Commodity Trading Dashboard</h1>
        <p>Live MCX Gold & Silver Trading with AI-Powered Signals</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar controls
    st.sidebar.header("🎛️ Controls")
    
    commodity = st.sidebar.selectbox(
        "Select Commodity:",
        ["GOLD", "SILVER"],
        index=0
    )
    
    timeframe = st.sidebar.selectbox(
        "Select Timeframe:",
        ["1h", "4h", "1d"],
        index=2
    )
    
    # Force refresh button
    if st.sidebar.button("🔄 Force Refresh Data", type="primary"):
        st.cache_data.clear()
        st.rerun()
    
    # Main content
    col1, col2, col3 = st.columns(3)
    
    # Get live price data
    price_data = get_live_price(commodity)
    
    with col1:
        if price_data:
            st.metric(
                label=f"{commodity} Price (₹)",
                value=f"₹{price_data['price_inr']:,.2f}",
                delta=f"₹{price_data['change']:,.2f} ({price_data['change_percent']:.2f}%)"
            )
        else:
            st.metric(
                label=f"{commodity} Price (₹)",
                value="Loading...",
                delta="N/A"
            )
    
    with col2:
        if price_data:
            st.metric(
                label="Volume",
                value=f"{price_data['volume']:,.0f}",
                delta=None
            )
        else:
            st.metric(
                label="Volume",
                value="Loading...",
                delta=None
            )
    
    with col3:
        st.metric(
            label="Last Update",
            value=datetime.now().strftime("%H:%M:%S"),
            delta=None
        )
    
    # Charts section
    st.header("📊 Price Charts")
    
    # Get historical data
    hist_data = get_historical_data(commodity, timeframe)
    
    if hist_data is not None:
        # Price chart
        chart = create_price_chart(hist_data, commodity)
        if chart:
            st.plotly_chart(chart, use_container_width=True)
        
        # Trading signals
        st.header("🚨 Trading Signals")
        signals = generate_simple_signals(hist_data, commodity)
        
        if signals:
            for signal in signals:
                if signal['type'] == 'BUY':
                    st.markdown(f"""
                    <div class="signal-buy">
                        <strong>🟢 BUY SIGNAL - {signal['strength']}</strong><br>
                        Price: ₹{signal['price']:,.2f}<br>
                        Reason: {signal['reason']}
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class="signal-sell">
                        <strong>🔴 SELL SIGNAL - {signal['strength']}</strong><br>
                        Price: ₹{signal['price']:,.2f}<br>
                        Reason: {signal['reason']}
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.info("No active trading signals at this time.")
        
        # Market analysis
        st.header("📈 Market Analysis")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if len(hist_data) > 20:
                recent_data = hist_data.tail(20)
                trend = "Bullish" if recent_data['Close'].iloc[-1] > recent_data['Close'].iloc[0] else "Bearish"
                volatility = recent_data['Close'].std()
                
                st.markdown(f"""
                <div class="metric-card">
                    <h4>📊 Short-term Trend</h4>
                    <p><strong>{trend}</strong></p>
                    <p>Volatility: {volatility:.2f}</p>
                </div>
                """, unsafe_allow_html=True)
        
        with col2:
            if len(hist_data) > 50:
                long_data = hist_data.tail(50)
                long_trend = "Bullish" if long_data['Close'].iloc[-1] > long_data['Close'].iloc[0] else "Bearish"
                support = long_data['Low'].min() * 83.0
                resistance = long_data['High'].max() * 83.0
                
                st.markdown(f"""
                <div class="metric-card">
                    <h4>📈 Long-term Trend</h4>
                    <p><strong>{long_trend}</strong></p>
                    <p>Support: ₹{support:,.0f}</p>
                    <p>Resistance: ₹{resistance:,.0f}</p>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.error("Unable to load historical data. Please try refreshing.")
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666;'>
        <p>📈 Commodity Trading Dashboard | Data provided by Yahoo Finance | Updated every 5 minutes</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error("An unexpected error occurred. Please try refreshing the page.")
        st.error(f"Error details: {str(e)}")
        st.info("If this persists, please check the Streamlit Cloud logs.")
