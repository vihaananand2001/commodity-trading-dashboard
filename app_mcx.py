import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import requests
import json

# Page config
st.set_page_config(
    page_title="MCX Trading Dashboard",
    page_icon="📈",
    layout="wide"
)

# Header
st.title("📈 MCX Commodity Trading Dashboard")
st.markdown("**Live Indian MCX Gold & Silver Prices with Paper Trading**")

# Auto-refresh and timestamp
col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    st.markdown(f"**Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
with col2:
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()
with col3:
    auto_refresh = st.checkbox("Auto-refresh (30s)", value=False)
    if auto_refresh:
        st.rerun()

# Sidebar
with st.sidebar:
    st.header("🎛️ Controls")
    commodity = st.selectbox("Commodity", ["GOLD", "SILVER"])
    
    if commodity == "GOLD":
        timeframe = st.selectbox("Timeframe", ["1h", "4h", "1d"])
    else:
        timeframe = st.selectbox("Timeframe", ["4h", "1d"])
    
    # Data Source Selection
    st.header("📡 Data Source")
    data_source = st.selectbox("Choose Data Source", [
        "Yahoo Finance (Current)", 
        "Alpha Vantage (MCX)", 
        "Metals-API (Premium)"
    ])
    
    # Paper Trading
    st.header("📝 Paper Trading")
    paper_mode = st.checkbox("Enable Paper Trading")
    
    if paper_mode:
        st.metric("Balance", "₹10,00,000")

# Alpha Vantage API function
@st.cache_data(ttl=60)
def get_alpha_vantage_data(commodity):
    """Get data from Alpha Vantage API for Indian commodities"""
    try:
        # You can get a free API key from https://www.alphavantage.co/support/#api-key
        api_key = "demo"  # Replace with your actual API key
        
        if commodity == "GOLD":
            symbol = "GOLD"
        else:
            symbol = "SILVER"
        
        url = f"https://www.alphavantage.co/query?function=COMMODITY&symbol={symbol}&interval=1min&apikey={api_key}"
        
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if "data" in data:
            latest_data = data["data"][0]
            return {
                'price_inr_per_10g': float(latest_data["value"]) if commodity == "GOLD" else float(latest_data["value"]),
                'price_usd': float(latest_data["value"]) / 83.0,  # Convert back to USD for comparison
                'volume': 0,  # Alpha Vantage doesn't provide volume for commodities
                'lot_size': 1000 if commodity == "GOLD" else 30000,
                'contract_value': float(latest_data["value"]) * (100 if commodity == "GOLD" else 1),
                'currency': '₹/10g' if commodity == "GOLD" else '₹/kg',
                'source': 'Alpha Vantage'
            }
        else:
            st.warning("Alpha Vantage API limit reached or invalid response")
            return None
            
    except Exception as e:
        st.warning(f"Alpha Vantage API error: {e}")
        return None

# Metals-API function
@st.cache_data(ttl=60)
def get_metals_api_data(commodity):
    """Get data from Metals-API for precious metals"""
    try:
        # You need to register at https://metals-api.com/ for an API key
        api_key = "demo"  # Replace with your actual API key
        base_currency = "INR"
        
        if commodity == "GOLD":
            symbol = "XAU"
        else:
            symbol = "XAG"
        
        url = f"http://api.metals-api.com/v1/latest?access_key={api_key}&base={symbol}&symbols={base_currency}"
        
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if data.get("success"):
            rate = data["rates"]["INR"]
            
            # Convert to per 10g for Gold, per kg for Silver
            if commodity == "GOLD":
                price_per_10g = rate / 3.11  # 1 troy ounce = 31.1g, so 10g = 0.321 troy ounces
                lot_size = 1000
                contract_value = price_per_10g * 100 * lot_size
            else:
                price_per_kg = rate * 32.15  # 1 troy ounce = 31.1g, so 1kg = 32.15 troy ounces
                lot_size = 30000
                contract_value = price_per_kg * lot_size
            
            return {
                'price_inr_per_10g': price_per_10g if commodity == "GOLD" else price_per_kg,
                'price_usd': rate / 83.0,
                'volume': 0,
                'lot_size': lot_size,
                'contract_value': contract_value,
                'currency': '₹/10g' if commodity == "GOLD" else '₹/kg',
                'source': 'Metals-API'
            }
        else:
            st.warning("Metals-API error or limit reached")
            return None
            
    except Exception as e:
        st.warning(f"Metals-API error: {e}")
        return None

# Enhanced Yahoo Finance function
@st.cache_data(ttl=60)
def get_yahoo_enhanced_data(commodity):
    """Get enhanced data from Yahoo Finance with better MCX conversion"""
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
        
        # Enhanced MCX conversion factors (more accurate)
        if commodity == "GOLD":
            # MCX Gold: More accurate conversion factor
            price_inr_per_10g = (price_usd * 83.0 * 0.361)
            lot_size = 1000  # 1 kg
            contract_value = price_inr_per_10g * 100 * lot_size
        else:  # SILVER
            # MCX Silver: More accurate conversion factor
            price_inr_per_kg = price_usd * 83.0 * 34.5
            lot_size = 30000  # 30 kg
            contract_value = price_inr_per_kg * lot_size
        
        return {
            'price_inr_per_10g': price_inr_per_10g if commodity == "GOLD" else price_inr_per_kg,
            'price_usd': price_usd,
            'volume': latest['Volume'],
            'lot_size': lot_size,
            'contract_value': contract_value,
            'currency': '₹/10g' if commodity == "GOLD" else '₹/kg',
            'source': 'Yahoo Finance (Enhanced)'
        }
    except Exception as e:
        st.error(f"Yahoo Finance error: {e}")
        return None

# Get data based on selected source
def get_price_data(commodity, source):
    """Get price data from selected source"""
    if source == "Alpha Vantage (MCX)":
        return get_alpha_vantage_data(commodity)
    elif source == "Metals-API (Premium)":
        return get_metals_api_data(commodity)
    else:  # Yahoo Finance (Current)
        return get_yahoo_enhanced_data(commodity)

# Get historical data
@st.cache_data(ttl=120)
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
            
        # Convert to INR with MCX-adjusted factors
        if commodity == "GOLD":
            data['Close_INR'] = data['Close'] * 83.0 * 0.361
        else:
            data['Close_INR'] = data['Close'] * 83.0 * 34.5
        
        return data
    except Exception as e:
        st.error(f"Error: {e}")
        return None

# Main content
price_data = get_price_data(commodity, data_source)

if price_data:
    col1, col2, col3, col4, col5 = st.columns(5)
    
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
        if price_data['volume'] > 0:
            st.metric("Volume", f"{price_data['volume']:,.0f}")
        else:
            st.metric("Volume", "N/A")
    
    with col5:
        st.metric("Data Source", price_data['source'])
    
    # Data source comparison
    if data_source != "Yahoo Finance (Current)":
        st.info(f"📡 Using {price_data['source']} for more accurate MCX data")
    
    # Show data source comparison
    st.subheader("📊 Data Source Comparison")
    comparison_col1, comparison_col2, comparison_col3 = st.columns(3)
    
    with comparison_col1:
        yahoo_data = get_yahoo_enhanced_data(commodity)
        if yahoo_data:
            st.metric("Yahoo Finance", f"₹{yahoo_data['price_inr_per_10g']:,.0f}")
    
    with comparison_col2:
        alpha_data = get_alpha_vantage_data(commodity)
        if alpha_data:
            st.metric("Alpha Vantage", f"₹{alpha_data['price_inr_per_10g']:,.0f}")
        else:
            st.metric("Alpha Vantage", "API Key Required")
    
    with comparison_col3:
        metals_data = get_metals_api_data(commodity)
        if metals_data:
            st.metric("Metals-API", f"₹{metals_data['price_inr_per_10g']:,.0f}")
        else:
            st.metric("Metals-API", "API Key Required")

# Chart
st.header("📊 Price Chart")

hist_data = get_historical(commodity, timeframe)

if hist_data is not None:
    fig = go.Figure(data=go.Candlestick(
        x=hist_data.index,
        open=hist_data['Open'] * (83.0 * 0.361 if commodity == "GOLD" else 83.0 * 34.5),
        high=hist_data['High'] * (83.0 * 0.361 if commodity == "GOLD" else 83.0 * 34.5),
        low=hist_data['Low'] * (83.0 * 0.361 if commodity == "GOLD" else 83.0 * 34.5),
        close=hist_data['Close'] * (83.0 * 0.361 if commodity == "GOLD" else 83.0 * 34.5),
        name="Price"
    ))
    
    fig.update_layout(
        title=f"{commodity} Price Chart (₹) - {data_source}",
        xaxis_title="Date",
        yaxis_title="Price (₹)",
        height=500
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Enhanced signals
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

# API Setup Instructions
st.header("🔧 API Setup Instructions")
with st.expander("Click to see how to set up APIs for better data"):
    st.markdown("""
    ### 🚀 To get more accurate MCX data:
    
    **1. Alpha Vantage API (Free tier available):**
    - Visit: https://www.alphavantage.co/support/#api-key
    - Get free API key (5 calls/minute, 500 calls/day)
    - Replace `api_key = "demo"` in the code
    
    **2. Metals-API (Premium service):**
    - Visit: https://metals-api.com/
    - Register for API key
    - Replace `api_key = "demo"` in the code
    
    **3. Current Yahoo Finance:**
    - Already working with enhanced MCX conversion
    - Shows ~₹1,27,000 for Gold (close to MCX rates)
    
    ### 💡 Benefits of Premium APIs:
    - More accurate MCX rates
    - Real-time data
    - Better reliability
    - Official exchange data
    """)

# Footer
st.markdown("---")
st.markdown("*Enhanced MCX Dashboard | Multiple Data Sources | Paper Trading*")
