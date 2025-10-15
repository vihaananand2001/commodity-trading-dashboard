"""
Simplified Streamlit Trading Dashboard
A minimal version to ensure Streamlit Cloud compatibility
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import sys
import os

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

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

# Initialize session state
if 'data_service' not in st.session_state:
    st.session_state.data_service = DashboardDataService()

if 'yahoo_fetcher' not in st.session_state:
    st.session_state.yahoo_fetcher = YahooFinanceFetcher()

@st.cache_data(ttl=60)
def get_live_prices_simple():
    """Get live commodity prices with error handling"""
    try:
        fetcher = st.session_state.yahoo_fetcher
        prices = {}
        
        for commodity in ['GOLD', 'SILVER']:
            try:
                data = fetcher.get_live_price(commodity)
                if data:
                    prices[commodity] = data
            except Exception as e:
                st.warning(f"Could not fetch {commodity} price: {e}")
                
        return prices
    except Exception as e:
        st.error(f"Error fetching live prices: {e}")
        return {}

@st.cache_data(ttl=300)
def get_trading_signals_simple(commodity, timeframe):
    """Get trading signals with error handling"""
    try:
        data_service = st.session_state.data_service
        signals = data_service.generate_trading_signals(commodity.lower(), timeframe)
        return signals
    except Exception as e:
        st.error(f"Error getting trading signals: {e}")
        return []

def main():
    # Header
    st.title("📈 Commodity Trading Dashboard")
    st.markdown("Live MCX Gold & Silver Trading with AI-Powered Signals")
    
    # Sidebar
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
    
    # Get live prices
    st.subheader("💰 Live Prices")
    live_prices = get_live_prices_simple()
    
    if live_prices and commodity in live_prices:
        price_data = live_prices[commodity]
        mcx_contract = price_data.get('mcx_contract', {})
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            try:
                price_value = price_data.get('close', price_data.get('price', 0))
                st.metric(
                    label=f"{mcx_contract.get('name', commodity)} Price",
                    value=f"₹{price_value:,.2f}",
                    delta=f"₹{price_data.get('change', 0):,.2f}"
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
                label="Volume",
                value=f"{price_data.get('volume', 0):,}"
            )
    else:
        st.warning("Live price data not available")
    
    # Trading signals
    st.subheader("🎯 Trading Signals")
    signals = get_trading_signals_simple(commodity, timeframe)
    
    if signals:
        st.success(f"Found {len(signals)} trading signals!")
        
        for i, signal in enumerate(signals[:10], 1):  # Show first 10 signals
            with st.expander(f"Signal {i}: {signal.get('strategy_name', 'Unknown')}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Pattern:** {signal.get('pattern', 'N/A')}")
                    st.write(f"**Entry Price:** ₹{signal.get('entry_price', 0):,.2f}")
                
                with col2:
                    confidence = signal.get('confidence', 0)
                    confidence_pct = confidence * 100 if confidence <= 1 else confidence
                    st.write(f"**Confidence:** {confidence_pct:.1f}%")
                    st.write(f"**Direction:** {signal.get('direction', 'N/A')}")
                
                st.write(f"**Timestamp:** {signal.get('timestamp', 'N/A')}")
    else:
        st.info("No trading signals found for this commodity and timeframe")
    
    # Footer
    st.markdown("---")
    st.markdown(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()
