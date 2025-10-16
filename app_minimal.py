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
    
    # Paper Trading
    st.header("📝 Paper Trading")
    paper_mode = st.checkbox("Enable Paper Trading")
    
    if paper_mode:
        st.metric("Balance", "₹10,00,000")

# Get live USD/INR exchange rate
@st.cache_data(ttl=60)
def get_usd_inr_rate():
    """Get live USD/INR exchange rate from Yahoo Finance"""
    try:
        usd_inr_ticker = yf.Ticker('USDINR=X')
        usd_inr_data = usd_inr_ticker.history(period='1d')
        if not usd_inr_data.empty:
            return usd_inr_data['Close'].iloc[-1]
        else:
            return 83.0  # Fallback rate
    except Exception as e:
        st.warning(f"Could not fetch USD/INR rate: {e}")
        return 83.0  # Fallback rate

# Get price data
@st.cache_data(ttl=60)  # 1 minute cache for more live data
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
        
        # Get live USD/INR exchange rate
        usd_inr_rate = get_usd_inr_rate()
        
        # Convert to Indian pricing with correct ounce-to-gram conversion
        if commodity == "GOLD":
            # Convert from USD per troy ounce to ₹ per 10 grams
            # 1 troy ounce = 31.1035 grams
            # So 10 grams = 10/31.1035 = 0.3215 troy ounces
            troy_ounce_to_grams = 31.1035
            grams_in_10g = 10
            conversion_factor = grams_in_10g / troy_ounce_to_grams  # 0.3215
            
            # USD per ounce -> USD per 10g -> INR per 10g (with live exchange rate)
            price_inr_per_10g = (price_usd * usd_inr_rate * conversion_factor)
            lot_size = 1000  # 1 kg
            contract_value = price_inr_per_10g * 100 * lot_size
        else:  # SILVER
            # Convert from USD per troy ounce to ₹ per kg
            # 1 troy ounce = 31.1035 grams, so 1 kg = 32.15 troy ounces
            troy_ounce_to_grams = 31.1035
            grams_in_1kg = 1000
            conversion_factor = grams_in_1kg / troy_ounce_to_grams  # 32.15
            
            price_inr_per_kg = price_usd * usd_inr_rate * conversion_factor  # Live exchange rate
            lot_size = 30000  # 30 kg
            contract_value = price_inr_per_kg * lot_size
        
        return {
            'price_inr_per_10g': price_inr_per_10g if commodity == "GOLD" else price_inr_per_kg,
            'price_usd': price_usd,
            'volume': latest['Volume'],
            'lot_size': lot_size,
            'contract_value': contract_value,
            'currency': '₹/10g' if commodity == "GOLD" else '₹/kg',
            'usd_inr_rate': usd_inr_rate
        }
    except Exception as e:
        st.error(f"Error: {e}")
        return None

# Get historical data
@st.cache_data(ttl=120)  # 2 minute cache for historical data
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
            
        # Get live USD/INR rate for historical conversion
        usd_inr_rate = get_usd_inr_rate()
        
        # Convert to INR with correct ounce-to-gram conversion using live rate
        if commodity == "GOLD":
            # Correct conversion: USD per ounce -> USD per 10g -> INR per 10g
            troy_ounce_to_grams = 31.1035
            conversion_factor = 10 / troy_ounce_to_grams  # 0.3215
            data['Close_INR'] = data['Close'] * usd_inr_rate * conversion_factor
        else:
            # Correct conversion: USD per ounce -> USD per kg -> INR per kg
            troy_ounce_to_grams = 31.1035
            conversion_factor = 1000 / troy_ounce_to_grams  # 32.15
            data['Close_INR'] = data['Close'] * usd_inr_rate * conversion_factor
        
        return data
    except Exception as e:
        st.error(f"Error: {e}")
        return None

# Main content
price_data = get_price(commodity)

if price_data:
    # Currency and Exchange Rate Display
    st.subheader("💱 Live Currency Rates")
    col_curr1, col_curr2, col_curr3 = st.columns(3)
    
    with col_curr1:
        st.metric("USD/INR Rate", f"₹{price_data['usd_inr_rate']:.2f}")
    
    with col_curr2:
        if commodity == "GOLD":
            st.metric(f"{commodity} USD", f"${price_data['price_usd']:,.2f}/oz")
        else:
            st.metric(f"{commodity} USD", f"${price_data['price_usd']:,.2f}/oz")
    
    with col_curr3:
        st.metric(f"{commodity} INR", f"₹{price_data['price_inr_per_10g']:,.0f}", 
                 help=f"Per {price_data['currency']}")
    
    # Main metrics
    st.subheader("📊 Contract Details")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Lot Size", f"{price_data['lot_size']:,}")
    
    with col2:
        st.metric("Contract Value", f"₹{price_data['contract_value']:,.0f}")
    
    with col3:
        st.metric("Volume", f"{price_data['volume']:,.0f}")
    
    with col4:
        # Show conversion breakdown
        if commodity == "GOLD":
            troy_ounce_to_grams = 31.1035
            conversion_factor = 10 / troy_ounce_to_grams
            st.metric("Conversion", f"{conversion_factor:.4f}", 
                     help="10g to troy ounce factor")
        else:
            troy_ounce_to_grams = 31.1035
            conversion_factor = 1000 / troy_ounce_to_grams
            st.metric("Conversion", f"{conversion_factor:.2f}", 
                     help="1kg to troy ounce factor")

# Chart
st.header("📊 Price Chart")

hist_data = get_historical(commodity, timeframe)

if hist_data is not None:
    # Chart conversion with live USD/INR rate
    usd_inr_rate = get_usd_inr_rate()
    if commodity == "GOLD":
        troy_ounce_to_grams = 31.1035
        conversion_factor = 10 / troy_ounce_to_grams  # 0.3215
        chart_factor = usd_inr_rate * conversion_factor
    else:
        troy_ounce_to_grams = 31.1035
        conversion_factor = 1000 / troy_ounce_to_grams  # 32.15
        chart_factor = usd_inr_rate * conversion_factor
    
    fig = go.Figure(data=go.Candlestick(
        x=hist_data.index,
        open=hist_data['Open'] * chart_factor,
        high=hist_data['High'] * chart_factor,
        low=hist_data['Low'] * chart_factor,
        close=hist_data['Close'] * chart_factor,
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
