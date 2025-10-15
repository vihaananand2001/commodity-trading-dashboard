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
    
    # Simple signal
    if len(hist_data) > 20:
        current_price = hist_data['Close_INR'].iloc[-1]
        avg_price = hist_data['Close_INR'].tail(20).mean()
        
        if current_price > avg_price:
            st.success("🟢 Bullish Signal: Price above 20-period average")
        else:
            st.warning("🔴 Bearish Signal: Price below 20-period average")
else:
    st.error("Unable to load chart data")

# Footer
st.markdown("---")
st.markdown("*Data provided by Yahoo Finance*")
