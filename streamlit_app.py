"""
Commodity Trading Dashboard - Streamlit Cloud Optimized
Simplified version for guaranteed deployment success
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import sys
import os

# Add src directory to path
sys.path.append('src')

try:
    from dashboard_data_service import DashboardDataService
    from yahoo_finance_fetcher import YahooFinanceFetcher
except ImportError as e:
    st.error(f"Import error: {e}")
    st.stop()

# Page configuration
st.set_page_config(
    page_title="Commodity Trading Dashboard",
    page_icon="📈",
    layout="wide"
)

# Initialize services
@st.cache_resource
def get_services():
    """Initialize services with caching"""
    try:
        data_service = DashboardDataService()
        yahoo_fetcher = YahooFinanceFetcher()
        return data_service, yahoo_fetcher
    except Exception as e:
        st.error(f"Failed to initialize services: {e}")
        return None, None

# Cached functions
@st.cache_data(ttl=60)
def get_live_prices():
    """Get live commodity prices"""
    try:
        _, yahoo_fetcher = get_services()
        if yahoo_fetcher is None:
            return {}
            
        prices = {}
        for commodity in ['GOLD', 'SILVER']:
            try:
                data = yahoo_fetcher.get_live_price(commodity)
                if data:
                    prices[commodity] = data
            except Exception as e:
                st.warning(f"Could not fetch {commodity} price: {e}")
        return prices
    except Exception as e:
        st.error(f"Error fetching live prices: {e}")
        return {}

@st.cache_data(ttl=300)
def get_signals(commodity, timeframe):
    """Get trading signals"""
    try:
        data_service, _ = get_services()
        if data_service is None:
            return []
            
        signals = data_service.generate_trading_signals(commodity.lower(), timeframe)
        return signals
    except Exception as e:
        st.error(f"Error getting signals: {e}")
        return []

def main():
    # Header
    st.title("📈 Commodity Trading Dashboard")
    st.markdown("**Live MCX Gold & Silver Trading with AI-Powered Signals**")
    
    # Initialize services
    data_service, yahoo_fetcher = get_services()
    
    if data_service is None or yahoo_fetcher is None:
        st.error("Failed to initialize services. Please refresh the page.")
        return
    
    # Sidebar controls
    with st.sidebar:
        st.header("🎛️ Trading Controls")
        
        commodity = st.selectbox(
            "Select Commodity",
            ["GOLD", "SILVER"],
            index=0
        )
        
        if commodity == "GOLD":
            timeframe_options = ["1h", "4h", "1d"]
            timeframe_labels = ["1 Hour", "4 Hours", "1 Day"]
        else:
            timeframe_options = ["4h", "1d"]
            timeframe_labels = ["4 Hours", "1 Day"]
        
        timeframe = st.selectbox(
            "Select Timeframe",
            timeframe_options,
            index=0,
            format_func=lambda x: timeframe_labels[timeframe_options.index(x)]
        )
        
        if st.button("🔄 Refresh Data"):
            st.cache_data.clear()
            st.rerun()
    
    # Live prices section
    st.header("💰 Live Prices")
    
    live_prices = get_live_prices()
    
    if live_prices and commodity in live_prices:
        price_data = live_prices[commodity]
        mcx_contract = price_data.get('mcx_contract', {})
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            try:
                price_value = price_data.get('close', 0)
                change_value = price_data.get('change', 0)
                change_percent = price_data.get('change_percent', 0)
                
                st.metric(
                    label=f"{mcx_contract.get('name', commodity)} Price",
                    value=f"₹{price_value:,.2f}",
                    delta=f"₹{change_value:,.2f} ({change_percent:.2f}%)"
                )
            except Exception as e:
                st.error(f"Error displaying price: {e}")
        
        with col2:
            st.metric(
                label="Contract Size",
                value=mcx_contract.get('contract_size', 'N/A')
            )
        
        with col3:
            st.metric(
                label="Lot Size",
                value=f"{mcx_contract.get('lot_size', 0):,}"
            )
        
        with col4:
            st.metric(
                label="Volume",
                value=f"{price_data.get('volume', 0):,}"
            )
    else:
        st.warning("Live price data not available")
    
    # Trading signals section
    st.header("🎯 Trading Signals")
    
    signals = get_signals(commodity, timeframe)
    
    if signals:
        st.success(f"Found {len(signals)} trading signals!")
        
        # Show signals in columns
        for i in range(0, len(signals), 2):
            cols = st.columns(2)
            
            for j, col in enumerate(cols):
                if i + j < len(signals):
                    signal = signals[i + j]
                    
                    with col:
                        confidence = signal.get('confidence', 0)
                        confidence_pct = confidence * 100 if confidence <= 1 else confidence
                        
                        if confidence_pct >= 70:
                            color = "🟢"
                        elif confidence_pct >= 50:
                            color = "🟡"
                        else:
                            color = "🔴"
                        
                        st.markdown(f"""
                        <div style="border: 1px solid #ddd; padding: 10px; border-radius: 5px; margin: 5px 0;">
                            <h4>{color} {signal.get('strategy_name', 'Unknown')}</h4>
                            <p><strong>Pattern:</strong> {signal.get('pattern', 'N/A')}</p>
                            <p><strong>Entry Price:</strong> ₹{signal.get('entry_price', 0):,.2f}</p>
                            <p><strong>Confidence:</strong> {confidence_pct:.1f}%</p>
                            <p><strong>Direction:</strong> {signal.get('direction', 'N/A')}</p>
                            <p><strong>Time:</strong> {signal.get('timestamp', 'N/A')}</p>
                        </div>
                        """, unsafe_allow_html=True)
    else:
        st.info("No trading signals found for this commodity and timeframe")
    
    # Market summary
    st.header("📊 Market Summary")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Supported Commodities")
        st.markdown("""
        - **Gold**: 1H, 4H, 1D timeframes
        - **Silver**: 4H, 1D timeframes
        """)
    
    with col2:
        st.subheader("Trading Strategies")
        try:
            rules = data_service.load_trading_rules(commodity.lower(), timeframe)
            if rules:
                strategies = []
                for key, value in rules.items():
                    if key.startswith('strategy_') and key != 'strategy_metadata':
                        strategies.append(value)
                
                st.write(f"**{len(strategies)} strategies active for {commodity} {timeframe}**")
                for strategy in strategies[:3]:
                    st.write(f"• {strategy.get('name', 'Unknown')}")
            else:
                st.write("No strategies loaded")
        except Exception as e:
            st.write(f"Error loading strategies: {e}")
    
    # Footer
    st.markdown("---")
    st.markdown(f"**Last updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    st.markdown("**Data source:** Yahoo Finance + MCX Historical Data")

if __name__ == "__main__":
    main()
