import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# Page config
st.set_page_config(
    page_title="MCX Trading Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for professional styling
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #1f4e79 0%, #2e5a8a 100%);
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        text-align: center;
    }
    
    .main-header h1 {
        color: white;
        font-size: 2.5rem;
        font-weight: bold;
        margin: 0;
    }
    
    .main-header p {
        color: #e8f4f8;
        font-size: 1.2rem;
        margin: 0.5rem 0 0 0;
    }
    
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 15px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    
    .currency-card {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        padding: 1.5rem;
        border-radius: 15px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    
    .signal-card-buy {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        padding: 1.5rem;
        border-radius: 15px;
        color: white;
        margin: 1rem 0;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    
    .signal-card-sell {
        background: linear-gradient(135deg, #ff416c 0%, #ff4b2b 100%);
        padding: 1.5rem;
        border-radius: 15px;
        color: white;
        margin: 1rem 0;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    
    .info-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 15px;
        color: white;
        margin: 1rem 0;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    
    .sidebar .sidebar-content {
        background: linear-gradient(180deg, #2c3e50 0%, #3498db 100%);
    }
    
    .stButton > button {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 25px;
        padding: 0.5rem 2rem;
        font-weight: bold;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    }
    
    .refresh-button {
        background: linear-gradient(90deg, #f093fb 0%, #f5576c 100%) !important;
    }
</style>
""", unsafe_allow_html=True)

# Professional Header
st.markdown("""
<div class="main-header">
    <h1>📈 MCX Trading Dashboard</h1>
    <p>Professional Commodity Trading Platform | Live Market Data & Paper Trading</p>
</div>
""", unsafe_allow_html=True)

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
        
        # Pure market conversion using live USD/INR rate
        if commodity == "GOLD":
            # Pure market conversion: USD per troy ounce -> ₹ per 10 grams
            # 1 troy ounce = 31.1035 grams
            # So 10 grams = 10/31.1035 = 0.3215 troy ounces
            troy_ounce_to_grams = 31.1035
            grams_in_10g = 10
            conversion_factor = grams_in_10g / troy_ounce_to_grams  # 0.3215
            
            # Pure market-driven conversion (no artificial adjustments)
            price_inr_per_10g = price_usd * usd_inr_rate * conversion_factor
            lot_size = 1000  # 1 kg
            contract_value = price_inr_per_10g * 100 * lot_size
        else:  # SILVER
            # Pure market conversion: USD per troy ounce -> ₹ per kg
            # 1 troy ounce = 31.1035 grams, so 1 kg = 32.15 troy ounces
            troy_ounce_to_grams = 31.1035
            grams_in_1kg = 1000
            conversion_factor = grams_in_1kg / troy_ounce_to_grams  # 32.15
            
            # Pure market-driven conversion
            price_inr_per_kg = price_usd * usd_inr_rate * conversion_factor
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
        
        # Pure market conversion for historical data using live USD/INR rate
        if commodity == "GOLD":
            # Pure market conversion: USD per ounce -> INR per 10g
            troy_ounce_to_grams = 31.1035
            conversion_factor = 10 / troy_ounce_to_grams  # 0.3215
            data['Close_INR'] = data['Close'] * usd_inr_rate * conversion_factor
        else:
            # Pure market conversion: USD per ounce -> INR per kg
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
    # Professional Currency Display
    st.markdown("### 💱 Live Market Conversion")
    
    col_curr1, col_curr2, col_curr3 = st.columns(3)
    
    with col_curr1:
        st.markdown(f"""
        <div class="currency-card">
            <h3>💱 USD/INR</h3>
            <h2>₹{price_data['usd_inr_rate']:.2f}</h2>
            <p>Live Exchange Rate</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col_curr2:
        st.markdown(f"""
        <div class="currency-card">
            <h3>🇺🇸 {commodity} USD</h3>
            <h2>${price_data['price_usd']:,.2f}</h2>
            <p>Per Troy Ounce</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col_curr3:
        st.markdown(f"""
        <div class="currency-card">
            <h3>🇮🇳 {commodity} INR</h3>
            <h2>₹{price_data['price_inr_per_10g']:,.0f}</h2>
            <p>Per {price_data['currency']}</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Professional conversion formula display
    st.markdown(f"""
    <div class="info-card">
        <h3>🔄 Market Conversion Formula</h3>
        <p><strong>${price_data['price_usd']:,.2f}</strong> (USD/oz) × <strong>₹{price_data['usd_inr_rate']:.2f}</strong> (USD/INR) × <strong>0.3215</strong> (10g/oz) = <strong>₹{price_data['price_inr_per_10g']:,.0f}</strong>/10g</p>
        <p><em>Pure market-driven conversion with live exchange rates</em></p>
    </div>
    """, unsafe_allow_html=True)
    
    # Professional Contract Details
    st.markdown("### 📊 Contract Details")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <h3>📦 Lot Size</h3>
            <h2>{price_data['lot_size']:,}</h2>
            <p>Contract Units</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <h3>💰 Contract Value</h3>
            <h2>₹{price_data['contract_value']:,.0f}</h2>
            <p>Total Value</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <h3>📊 Volume</h3>
            <h2>{price_data['volume']:,.0f}</h2>
            <p>Trading Volume</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        # Show conversion breakdown
        if commodity == "GOLD":
            troy_ounce_to_grams = 31.1035
            conversion_factor = 10 / troy_ounce_to_grams
            st.markdown(f"""
            <div class="metric-card">
                <h3>⚖️ Weight Factor</h3>
                <h2>{conversion_factor:.4f}</h2>
                <p>10g to troy ounce</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            troy_ounce_to_grams = 31.1035
            conversion_factor = 1000 / troy_ounce_to_grams
            st.markdown(f"""
            <div class="metric-card">
                <h3>⚖️ Weight Factor</h3>
                <h2>{conversion_factor:.2f}</h2>
                <p>1kg to troy ounce</p>
            </div>
            """, unsafe_allow_html=True)

# Professional Chart Section
st.markdown("### 📊 Live Price Chart")

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
        title=f"{commodity} Live Price Chart (₹) - {timeframe.upper()} Timeframe",
        xaxis_title="Date & Time",
        yaxis_title="Price (₹)",
        height=600,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#2c3e50'),
        title_font_size=20,
        title_x=0.5
    )
    
    # Add professional styling to the chart
    fig.update_traces(
        increasing_line_color='#2ecc71',
        decreasing_line_color='#e74c3c',
        line=dict(width=2)
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Professional Trading Signals
    if len(hist_data) > 20:
        current_price = hist_data['Close_INR'].iloc[-1]
        avg_price = hist_data['Close_INR'].tail(20).mean()
        
        st.markdown("### 🚨 Trading Signals")
        
        if current_price > avg_price:
            st.markdown(f"""
            <div class="signal-card-buy">
                <h3>🟢 BULLISH SIGNAL</h3>
                <p><strong>Price above 20-period moving average</strong></p>
                <p>Current: ₹{current_price:.0f} | Average: ₹{avg_price:.0f}</p>
            </div>
            """, unsafe_allow_html=True)
            
            if paper_mode:
                col1, col2 = st.columns([1, 3])
                with col1:
                    if st.button("🟢 Execute BUY Trade", type="primary"):
                        st.success("✅ BUY trade executed in paper trading mode!")
        else:
            st.markdown(f"""
            <div class="signal-card-sell">
                <h3>🔴 BEARISH SIGNAL</h3>
                <p><strong>Price below 20-period moving average</strong></p>
                <p>Current: ₹{current_price:.0f} | Average: ₹{avg_price:.0f}</p>
            </div>
            """, unsafe_allow_html=True)
            
            if paper_mode:
                col1, col2 = st.columns([1, 3])
                with col1:
                    if st.button("🔴 Execute SELL Trade", type="primary"):
                        st.success("✅ SELL trade executed in paper trading mode!")
else:
    st.error("Unable to load chart data")

# Professional Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; padding: 2rem; background: linear-gradient(90deg, #1f4e79 0%, #2e5a8a 100%); border-radius: 10px; color: white; margin-top: 2rem;">
    <h4>📈 MCX Trading Dashboard</h4>
    <p><strong>Professional Commodity Trading Platform</strong></p>
    <p>Live data provided by Yahoo Finance | Pure market-driven conversion | Paper Trading Mode</p>
    <p><em>Built for professional traders and investors</em></p>
</div>
""", unsafe_allow_html=True)
