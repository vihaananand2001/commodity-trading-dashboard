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

# Header
st.title("📈 Commodity Trading Dashboard")
st.markdown("**Live Gold & Silver Prices with Paper Trading**")

# Sidebar
with st.sidebar:
    st.header("🎛️ Controls")
    commodity = st.selectbox("Commodity", ["GOLD", "SILVER"])
    
    if commodity == "GOLD":
        timeframe = st.selectbox("Timeframe", ["1h", "4h", "1d"])
    else:
        timeframe = st.selectbox("Timeframe", ["4h", "1d"])
    
    # Paper Trading
    st.header("📝 Paper Trading")
    paper_mode = st.checkbox("Enable Paper Trading")
    
    if paper_mode:
        st.metric("Balance", "₹10,00,000")

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
        
        # Convert to Indian pricing
        if commodity == "GOLD":
            # Convert to ₹/10 grams
            price_inr_per_10g = (price_usd * 83.0 * 0.321)
            lot_size = 1000  # 1 kg
            contract_value = price_inr_per_10g * 100 * lot_size
        else:  # SILVER
            # Convert to ₹/kg
            price_inr_per_kg = price_usd * 83.0 * 32.15
            lot_size = 30000  # 30 kg
            contract_value = price_inr_per_kg * lot_size
        
        return {
            'price_inr_per_10g': price_inr_per_10g if commodity == "GOLD" else price_inr_per_kg,
            'price_usd': price_usd,
            'volume': latest['Volume'],
            'lot_size': lot_size,
            'contract_value': contract_value,
            'currency': '₹/10g' if commodity == "GOLD" else '₹/kg'
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
        if commodity == "GOLD":
            data['Close_INR'] = data['Close'] * 83.0 * 0.321
        else:
            data['Close_INR'] = data['Close'] * 83.0 * 32.15
        
        return data
    except Exception as e:
        st.error(f"Error: {e}")
        return None

# Main content
price_data = get_price(commodity)

if price_data:
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            f"{commodity} Price",
            f"₹{price_data['price_inr_per_10g']:,.0f}",
            help=f"Per {price_data['currency']}"
        )
    
    with col2:
        st.metric("Lot Size", f"{price_data['lot_size']:,}")
    
    with col3:
        st.metric("Contract Value", f"₹{price_data['contract_value']:,.0f}")
    
    with col4:
        st.metric("Volume", f"{price_data['volume']:,.0f}")

# Chart
st.header("📊 Price Chart")

hist_data = get_historical(commodity, timeframe)

if hist_data is not None:
    fig = go.Figure(data=go.Candlestick(
        x=hist_data.index,
        open=hist_data['Open'] * (83.0 * 0.321 if commodity == "GOLD" else 83.0 * 32.15),
        high=hist_data['High'] * (83.0 * 0.321 if commodity == "GOLD" else 83.0 * 32.15),
        low=hist_data['Low'] * (83.0 * 0.321 if commodity == "GOLD" else 83.0 * 32.15),
        close=hist_data['Close'] * (83.0 * 0.321 if commodity == "GOLD" else 83.0 * 32.15),
        name="Price"
    ))
    
    fig.update_layout(
        title=f"{commodity} Price Chart (₹)",
        xaxis_title="Date",
        yaxis_title="Price (₹)",
        height=500
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Simple signals
    if len(hist_data) > 20:
        current_price = hist_data['Close_INR'].iloc[-1]
        avg_price = hist_data['Close_INR'].tail(20).mean()
        
        st.header("🚨 Trading Signals")
        
        if current_price > avg_price:
            st.success("🟢 Bullish Signal: Price above 20-period average")
            if paper_mode:
                if st.button("🟢 Execute BUY Trade", type="primary"):
                    st.success("✅ BUY trade executed in paper trading mode!")
        else:
            st.warning("🔴 Bearish Signal: Price below 20-period average")
            if paper_mode:
                if st.button("🔴 Execute SELL Trade", type="primary"):
                    st.success("✅ SELL trade executed in paper trading mode!")
else:
    st.error("Unable to load chart data")

# Footer
st.markdown("---")
st.markdown("*Data provided by Yahoo Finance | Paper Trading Mode*")
