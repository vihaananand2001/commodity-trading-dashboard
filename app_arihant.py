"""
Enhanced MCX Trading Dashboard with Arihant Spot Integration
Multiple data sources including Arihant Spot, Yahoo Finance, and Indian APIs
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import sys
import os

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

try:
    from arihant_price_fetcher import ArihantSpotFetcher
    from indian_gold_api import IndianGoldPriceAPI, IndianGoldPriceScraper
except ImportError:
    st.warning("Arihant Spot integration modules not available. Using Yahoo Finance only.")
    ArihantSpotFetcher = None
    IndianGoldPriceAPI = None

# Page config
st.set_page_config(
    page_title="MCX Trading Dashboard - Arihant Spot",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Enhanced CSS for professional styling
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
        margin: 0.5rem 0;
    }
    
    .currency-card {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        padding: 1.5rem;
        border-radius: 15px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    
    .source-card {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        margin: 0.5rem 0;
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
</style>
""", unsafe_allow_html=True)

# Professional Header
st.markdown("""
<div class="main-header">
    <h1>📈 MCX Trading Dashboard</h1>
    <p>Professional Commodity Trading Platform | Live Data from Multiple Sources</p>
</div>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("### ⚙️ Configuration")
    
    # Data source selection
    st.markdown("#### 📡 Data Sources")
    use_arihant = st.checkbox("Arihant Spot", value=True, help="Live prices from Arihant Spot website")
    use_yahoo = st.checkbox("Yahoo Finance", value=True, help="International futures prices")
    use_indian_api = st.checkbox("Indian APIs", value=False, help="Alternative Indian gold price APIs")
    
    # Commodity selection
    commodity = st.selectbox("Commodity", ["GOLD", "SILVER"])
    
    # Timeframe selection
    if commodity == "GOLD":
        timeframe = st.selectbox("Timeframe", ["1h", "4h", "1d"])
    else:
        timeframe = st.selectbox("Timeframe", ["4h", "1d"])
    
    # Paper trading
    st.markdown("#### 📊 Paper Trading")
    paper_mode = st.checkbox("Enable Paper Trading", value=False)
    
    if paper_mode:
        st.number_input("Initial Balance (₹)", value=100000, step=10000)
    
    # Auto-refresh
    st.markdown("#### 🔄 Refresh Settings")
    auto_refresh = st.checkbox("Auto Refresh", value=True)
    refresh_interval = st.slider("Refresh Interval (seconds)", 30, 300, 60)

# Auto-refresh and timestamp
col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    st.markdown(f"**Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

with col2:
    if st.button("🔄 Force Refresh"):
        st.rerun()

with col3:
    if auto_refresh:
        st.markdown("🔄 Auto-refresh enabled")

# Data fetching functions
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

@st.cache_data(ttl=60)
def get_arihant_prices():
    """Get prices from Arihant Spot"""
    if not ArihantSpotFetcher:
        return None
    
    try:
        fetcher = ArihantSpotFetcher()
        prices = fetcher.fetch_prices()
        return prices
    except Exception as e:
        st.warning(f"Could not fetch Arihant Spot prices: {e}")
        return None

@st.cache_data(ttl=60)
def get_yahoo_prices(commodity):
    """Get prices from Yahoo Finance"""
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
            troy_ounce_to_grams = 31.1035
            grams_in_10g = 10
            conversion_factor = grams_in_10g / troy_ounce_to_grams  # 0.3215
            
            price_inr_per_10g = price_usd * usd_inr_rate * conversion_factor
            lot_size = 1000  # 1 kg
            contract_value = price_inr_per_10g * 100 * lot_size
        else:  # SILVER
            troy_ounce_to_grams = 31.1035
            grams_in_1kg = 1000
            conversion_factor = grams_in_1kg / troy_ounce_to_grams  # 32.15
            
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
            'usd_inr_rate': usd_inr_rate,
            'source': 'Yahoo Finance'
        }
    except Exception as e:
        st.error(f"Error fetching Yahoo Finance data: {e}")
        return None

@st.cache_data(ttl=60)
def get_indian_api_prices():
    """Get prices from Indian APIs"""
    if not IndianGoldPriceAPI:
        return None
    
    try:
        api = IndianGoldPriceAPI()
        prices = api.fetch_indian_spot_prices()
        return prices
    except Exception as e:
        st.warning(f"Could not fetch Indian API prices: {e}")
        return None

# Main content
st.markdown("### 💱 Live Market Data")

# Fetch data from selected sources
data_sources = []

if use_arihant:
    arihant_data = get_arihant_prices()
    if arihant_data:
        data_sources.append(arihant_data)

if use_yahoo:
    yahoo_data = get_yahoo_prices(commodity)
    if yahoo_data:
        data_sources.append(yahoo_data)

if use_indian_api:
    indian_data = get_indian_api_prices()
    if indian_data:
        data_sources.append(indian_data)

# Display data from multiple sources
if data_sources:
    st.markdown("#### 📊 Price Comparison Across Sources")
    
    for i, data in enumerate(data_sources):
        source_name = data.get('source', f'Source {i+1}')
        
        st.markdown(f"""
        <div class="source-card">
            <h4>📡 {source_name}</h4>
        </div>
        """, unsafe_allow_html=True)
        
        if commodity == "GOLD":
            if 'gold_inr_per_10g' in data:
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Gold (₹/10g)", f"₹{data['gold_inr_per_10g']:,.0f}")
                with col2:
                    if 'timestamp' in data:
                        st.metric("Last Updated", data['timestamp'][:19])
                with col3:
                    if 'url' in data:
                        st.markdown(f"[Visit Source]({data['url']})")
        else:
            if 'silver_inr_per_kg' in data:
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Silver (₹/kg)", f"₹{data['silver_inr_per_kg']:,.0f}")
                with col2:
                    if 'timestamp' in data:
                        st.metric("Last Updated", data['timestamp'][:19])
                with col3:
                    if 'url' in data:
                        st.markdown(f"[Visit Source]({data['url']})")
        
        st.markdown("---")

# Use primary data source for main display
primary_data = None
if use_arihant and arihant_data:
    primary_data = arihant_data
elif use_yahoo and yahoo_data:
    primary_data = yahoo_data
elif use_indian_api and indian_data:
    primary_data = indian_data

if primary_data:
    st.markdown("### 📈 Primary Data Source")
    
    if commodity == "GOLD":
        if 'gold_inr_per_10g' in primary_data:
            st.markdown(f"""
            <div class="currency-card">
                <h3>🇮🇳 {commodity} INR</h3>
                <h2>₹{primary_data['gold_inr_per_10g']:,.0f}</h2>
                <p>Per 10g (Source: {primary_data.get('source', 'Unknown')})</p>
            </div>
            """, unsafe_allow_html=True)
    else:
        if 'silver_inr_per_kg' in primary_data:
            st.markdown(f"""
            <div class="currency-card">
                <h3>🇮🇳 {commodity} INR</h3>
                <h2>₹{primary_data['silver_inr_per_kg']:,.0f}</h2>
                <p>Per kg (Source: {primary_data.get('source', 'Unknown')})</p>
            </div>
            """, unsafe_allow_html=True)

# Chart section (using Yahoo Finance for historical data)
st.markdown("### 📊 Price Chart")
if use_yahoo:
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
            else: # 1d
                data = ticker.history(period="1y", interval="1d")
            
            if data.empty:
                return None
                
            # Get live USD/INR rate for historical conversion
            usd_inr_rate = get_usd_inr_rate()
            
            # Pure market conversion for historical data using live USD/INR rate
            if commodity == "GOLD":
                troy_ounce_to_grams = 31.1035
                conversion_factor = 10 / troy_ounce_to_grams  # 0.3215
                data['Close_INR'] = data['Close'] * usd_inr_rate * conversion_factor
            else:
                troy_ounce_to_grams = 31.1035
                conversion_factor = 1000 / troy_ounce_to_grams  # 32.15
                data['Close_INR'] = data['Close'] * usd_inr_rate * conversion_factor
            
            return data
        except Exception as e:
            st.error(f"Error: {e}")
            return None

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
        
        # Trading signals
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
else:
    st.info("Enable Yahoo Finance in sidebar to view price charts")

# Professional Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; padding: 2rem; background: linear-gradient(90deg, #1f4e79 0%, #2e5a8a 100%); border-radius: 10px; color: white; margin-top: 2rem;">
    <h4>📈 MCX Trading Dashboard</h4>
    <p><strong>Professional Commodity Trading Platform</strong></p>
    <p>Live data from multiple sources | Arihant Spot Integration | Paper Trading Mode</p>
    <p><em>Built for professional traders and investors</em></p>
</div>
""", unsafe_allow_html=True)
