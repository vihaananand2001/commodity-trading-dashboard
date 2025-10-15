import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# Page config
st.set_page_config(
    page_title="Commodity Dashboard",
    page_icon="📈",
    layout="wide"
)

# Simple header
st.title("📈 Commodity Trading Dashboard")
st.markdown("**Live Gold & Silver Prices**")

# Sidebar
with st.sidebar:
    st.header("Controls")
    commodity = st.selectbox("Commodity", ["GOLD", "SILVER"])
    
    if commodity == "GOLD":
        timeframe = st.selectbox("Timeframe", ["1h", "4h", "1d"])
    else:
        timeframe = st.selectbox("Timeframe", ["4h", "1d"])

# Get price data
@st.cache_data(ttl=300)
def get_price(commodity):
    try:
        if commodity == "GOLD":
            ticker = yf.Ticker("GC=F")
        else:
            ticker = yf.Ticker("SI=F")
        
        data = ticker.history(period="1d")
        if data.empty:
            return None
            
        latest = data.iloc[-1]
        price_usd = latest['Close']
        price_inr = price_usd * 83.0
        
        return {
            'price_inr': price_inr,
            'price_usd': price_usd,
            'volume': latest['Volume']
        }
    except Exception as e:
        st.error(f"Error: {e}")
        return None

# Get historical data
@st.cache_data(ttl=300)
def get_historical(commodity, timeframe):
    try:
        if commodity == "GOLD":
            ticker = yf.Ticker("GC=F")
        else:
            ticker = yf.Ticker("SI=F")
        
        if timeframe == "1h":
            data = ticker.history(period="5d", interval="1h")
        elif timeframe == "4h":
            data = ticker.history(period="30d", interval="4h")
        else:
            data = ticker.history(period="1y", interval="1d")
        
        if data.empty:
            return None
            
        # Convert to INR
        data['Close_INR'] = data['Close'] * 83.0
        return data
    except Exception as e:
        st.error(f"Error: {e}")
        return None

# Main content
price_data = get_price(commodity)

if price_data:
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            f"{commodity} Price (₹)",
            f"₹{price_data['price_inr']:,.2f}"
        )
    
    with col2:
        st.metric(
            f"{commodity} Price (USD)",
            f"${price_data['price_usd']:,.2f}"
        )
    
    with col3:
        st.metric(
            "Volume",
            f"{price_data['volume']:,.0f}"
        )

# Chart
st.header("📊 Price Chart")

hist_data = get_historical(commodity, timeframe)

if hist_data is not None:
    fig = go.Figure(data=go.Candlestick(
        x=hist_data.index,
        open=hist_data['Open'] * 83.0,
        high=hist_data['High'] * 83.0,
        low=hist_data['Low'] * 83.0,
        close=hist_data['Close'] * 83.0,
        name="Price"
    ))
    
    fig.update_layout(
        title=f"{commodity} Price Chart (₹)",
        xaxis_title="Date",
        yaxis_title="Price (₹)",
        height=500
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Enhanced trading signals
    if len(hist_data) > 50:
        current_price = hist_data['Close_INR'].iloc[-1]
        
        # Calculate moving averages
        sma_20 = hist_data['Close_INR'].tail(20).mean()
        sma_50 = hist_data['Close_INR'].tail(50).mean()
        
        # Calculate RSI
        delta = hist_data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        current_rsi = rsi.iloc[-1]
        
        st.header("🚨 Trading Signals")
        
        # Signal 1: Moving Average Crossover
        if sma_20 > sma_50 and current_price > sma_20:
            st.markdown("""
            <div style="background-color: #d4edda; color: #155724; padding: 1rem; border-radius: 5px; border-left: 4px solid #28a745; margin: 0.5rem 0;">
                <strong>🟢 BUY SIGNAL - Moving Average Crossover</strong><br>
                Price: ₹{:.2f} | SMA 20: ₹{:.2f} | SMA 50: ₹{:.2f}<br>
                Reason: Price above SMA 20, SMA 20 above SMA 50
            </div>
            """.format(current_price, sma_20, sma_50), unsafe_allow_html=True)
        elif sma_20 < sma_50 and current_price < sma_20:
            st.markdown("""
            <div style="background-color: #f8d7da; color: #721c24; padding: 1rem; border-radius: 5px; border-left: 4px solid #dc3545; margin: 0.5rem 0;">
                <strong>🔴 SELL SIGNAL - Moving Average Crossover</strong><br>
                Price: ₹{:.2f} | SMA 20: ₹{:.2f} | SMA 50: ₹{:.2f}<br>
                Reason: Price below SMA 20, SMA 20 below SMA 50
            </div>
            """.format(current_price, sma_20, sma_50), unsafe_allow_html=True)
        else:
            st.info("📊 No clear trend signal - Wait for crossover")
        
        # Signal 2: RSI Signals
        if current_rsi < 30:
            st.markdown("""
            <div style="background-color: #d4edda; color: #155724; padding: 1rem; border-radius: 5px; border-left: 4px solid #28a745; margin: 0.5rem 0;">
                <strong>🟢 BUY SIGNAL - Oversold RSI</strong><br>
                RSI: {:.1f}<br>
                Reason: RSI below 30 (oversold condition)
            </div>
            """.format(current_rsi), unsafe_allow_html=True)
        elif current_rsi > 70:
            st.markdown("""
            <div style="background-color: #f8d7da; color: #721c24; padding: 1rem; border-radius: 5px; border-left: 4px solid #dc3545; margin: 0.5rem 0;">
                <strong>🔴 SELL SIGNAL - Overbought RSI</strong><br>
                RSI: {:.1f}<br>
                Reason: RSI above 70 (overbought condition)
            </div>
            """.format(current_rsi), unsafe_allow_html=True)
        else:
            st.info("📊 RSI: {:.1f} - Neutral zone (30-70)".format(current_rsi))
        
        # Signal 3: Volume Analysis
        current_volume = hist_data['Volume'].iloc[-1]
        avg_volume = hist_data['Volume'].tail(20).mean()
        
        if current_volume > avg_volume * 1.5:
            st.markdown("""
            <div style="background-color: #fff3cd; color: #856404; padding: 1rem; border-radius: 5px; border-left: 4px solid #ffc107; margin: 0.5rem 0;">
                <strong>⚠️ HIGH VOLUME ALERT</strong><br>
                Current Volume: {:,} | Average: {:,}<br>
                Reason: Volume 50% above average - Watch for breakout
            </div>
            """.format(int(current_volume), int(avg_volume)), unsafe_allow_html=True)
        
        # Support and Resistance
        support = hist_data['Close_INR'].tail(50).min()
        resistance = hist_data['Close_INR'].tail(50).max()
        
        st.subheader("📈 Support & Resistance")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Support", f"₹{support:,.0f}")
        with col2:
            st.metric("Current Price", f"₹{current_price:,.0f}")
        with col3:
            st.metric("Resistance", f"₹{resistance:,.0f}")
        
        # Price position analysis
        price_position = (current_price - support) / (resistance - support) * 100
        if price_position > 80:
            st.warning("🔴 Near Resistance - Consider taking profits")
        elif price_position < 20:
            st.success("🟢 Near Support - Consider buying opportunity")
        else:
            st.info("📊 Price in middle range - Wait for breakout")
else:
    st.error("Unable to load chart data")

# Footer
st.markdown("---")
st.markdown("*Data provided by Yahoo Finance*")
