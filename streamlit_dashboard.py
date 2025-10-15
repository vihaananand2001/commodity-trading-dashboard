"""
Streamlit Trading Dashboard
Advanced commodity trading dashboard with live data, signals, and analytics
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import yaml
import sys
import os

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from dashboard_data_service import DashboardDataService
from yahoo_finance_fetcher import YahooFinanceFetcher

# Page configuration
st.set_page_config(
    page_title="Commodity Trading Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 1rem 0;
        background: linear-gradient(90deg, #1f4e79, #2e7d32);
        color: white;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 4px solid #2e7d32;
    }
    
    .signal-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #28a745;
        margin: 0.5rem 0;
    }
    
    .signal-card.bearish {
        border-left-color: #dc3545;
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #f0f2f6;
        border-radius: 4px 4px 0px 0px;
        gap: 1px;
        padding-left: 20px;
        padding-right: 20px;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #2e7d32;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'data_service' not in st.session_state:
    st.session_state.data_service = DashboardDataService()

if 'yahoo_fetcher' not in st.session_state:
    st.session_state.yahoo_fetcher = YahooFinanceFetcher()

# Helper functions
@st.cache_data(ttl=60)  # Cache for 1 minute
def get_live_prices():
    """Get live commodity prices"""
    try:
        fetcher = st.session_state.yahoo_fetcher
        prices = {}
        
        for commodity in ['GOLD', 'SILVER']:
            data = fetcher.get_live_price(commodity)
            if data:
                prices[commodity] = data
        return prices
    except Exception as e:
        st.error(f"Error fetching live prices: {e}")
        return {}

@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_trading_signals(commodity, timeframe):
    """Get trading signals for commodity and timeframe"""
    try:
        data_service = st.session_state.data_service
        signals = data_service.generate_trading_signals(commodity.lower(), timeframe)
        market_analysis = data_service.get_market_analysis(commodity.lower(), timeframe)
        return signals, market_analysis
    except Exception as e:
        st.error(f"Error getting trading signals: {e}")
        return [], {}

@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_chart_data(commodity, timeframe, days=30):
    """Get chart data for plotting"""
    try:
        data_service = st.session_state.data_service
        chart_data = data_service.get_chart_data(commodity.lower(), timeframe, days)
        return chart_data
    except Exception as e:
        st.error(f"Error getting chart data: {e}")
        return {}

@st.cache_data(ttl=600)  # Cache for 10 minutes
def get_past_signals(commodity, timeframe, lookback_days=30):
    """Get past trading signals"""
    try:
        data_service = st.session_state.data_service
        past_signals = data_service.get_past_signals(commodity.lower(), timeframe, lookback_days)
        return past_signals
    except Exception as e:
        st.error(f"Error getting past signals: {e}")
        return []

def create_candlestick_chart(df):
    """Create candlestick chart"""
    if df.empty:
        return None
    
    fig = go.Figure(data=go.Candlestick(
        x=df.index,
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        name="Price"
    ))
    
    # Add moving averages if available
    if 'ema_20' in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index,
            y=df['ema_20'],
            mode='lines',
            name='EMA 20',
            line=dict(color='orange', width=1)
        ))
    
    if 'ema_50' in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index,
            y=df['ema_50'],
            mode='lines',
            name='EMA 50',
            line=dict(color='blue', width=1)
        ))
    
    fig.update_layout(
        title="Price Chart with Moving Averages",
        xaxis_title="Date",
        yaxis_title="Price (₹)",
        height=500,
        showlegend=True
    )
    
    return fig

def create_signal_chart(df, signals):
    """Create chart with trading signals"""
    if df.empty:
        return None
    
    fig = go.Figure(data=go.Candlestick(
        x=df.index,
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        name="Price"
    ))
    
    # Add signal markers
    for signal in signals:
        timestamp = pd.to_datetime(signal['timestamp'])
        if timestamp in df.index:
            fig.add_annotation(
                x=timestamp,
                y=signal['entry_price'],
                text=f"🚀 {signal['strategy_name']}",
                showarrow=True,
                arrowhead=2,
                arrowcolor="green",
                bgcolor="lightgreen",
                bordercolor="green"
            )
    
    fig.update_layout(
        title="Price Chart with Trading Signals",
        xaxis_title="Date",
        yaxis_title="Price (₹)",
        height=500
    )
    
    return fig

# Main app
def main():
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>📈 Commodity Trading Dashboard</h1>
        <p>Live MCX Gold & Silver Trading with AI-Powered Signals</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar for controls
    with st.sidebar:
        st.header("🎛️ Trading Controls")
        
        # Commodity selection
        commodity = st.selectbox(
            "Select Commodity",
            ["GOLD", "SILVER"],
            index=0
        )
        
        # Timeframe selection based on commodity
        if commodity == "GOLD":
            timeframe_options = ["1h", "4h", "1d"]
            timeframe_labels = ["1 Hour", "4 Hours", "1 Day"]
        else:  # SILVER
            timeframe_options = ["4h", "1d"]
            timeframe_labels = ["4 Hours", "1 Day"]
        
        timeframe = st.selectbox(
            "Select Timeframe",
            timeframe_options,
            index=0,
            format_func=lambda x: timeframe_labels[timeframe_options.index(x)]
        )
        
        # Date range selection
        days = st.slider("Chart History (Days)", 7, 90, 30)
        
        # Refresh button
        if st.button("🔄 Refresh Data", type="primary"):
            st.cache_data.clear()
            st.rerun()
    
    # Get live prices
    live_prices = get_live_prices()
    
    # Main content area
    if live_prices and commodity in live_prices:
        price_data = live_prices[commodity]
        mcx_contract = price_data.get('mcx_contract', {})
        
        # Live price display
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            try:
                price_value = price_data.get('close', price_data.get('price', 0))
                change_value = price_data.get('change', 0)
                change_percent = price_data.get('change_percent', 0)
                
                st.metric(
                    label=f"{mcx_contract.get('name', commodity)} Price",
                    value=f"₹{price_value:,.2f}",
                    delta=f"₹{change_value:,.2f} ({change_percent:.2f}%)"
                )
            except Exception as e:
                st.error(f"Error displaying price: {e}")
                st.metric(
                    label=f"{mcx_contract.get('name', commodity)} Price",
                    value="N/A",
                    delta="N/A"
                )
        
        with col2:
            st.metric(
                label="Contract Size",
                value=mcx_contract.get('contract_size', 'N/A'),
                delta=f"Lot: {mcx_contract.get('lot_size', 0):,}"
            )
        
        with col3:
            st.metric(
                label="Expiry",
                value=mcx_contract.get('expiry', 'N/A'),
                delta=f"Symbol: {mcx_contract.get('symbol', 'N/A')}"
            )
        
        with col4:
            st.metric(
                label="Volume",
                value=f"{price_data.get('volume', 0):,}",
                delta=f"Last Updated: {datetime.now().strftime('%H:%M:%S')}"
            )
    
    # Tabs for different views
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Charts & Signals", "📈 Market Analysis", "📋 Past Performance", "⚙️ Strategy Details"])
    
    with tab1:
        st.header("📊 Live Charts & Trading Signals")
        
        # Get chart data and signals
        chart_data = get_chart_data(commodity, timeframe, days)
        signals, market_analysis = get_trading_signals(commodity, timeframe)
        
        if chart_data and 'ohlc' in chart_data:
            df = pd.DataFrame(chart_data['ohlc'])
            df.index = pd.to_datetime(df.index)
            
            # Create charts
            col1, col2 = st.columns(2)
            
            with col1:
                # Price chart
                price_fig = create_candlestick_chart(df)
                if price_fig:
                    st.plotly_chart(price_fig, use_container_width=True)
            
            with col2:
                # Signal chart
                signal_fig = create_signal_chart(df, signals)
                if signal_fig:
                    st.plotly_chart(signal_fig, use_container_width=True)
            
            # Current signals
            st.subheader("🎯 Current Trading Signals")
            if signals:
                for signal in signals:
                    confidence_color = "green" if signal['confidence'] > 70 else "orange" if signal['confidence'] > 50 else "red"
                    
                    st.markdown(f"""
                    <div class="signal-card">
                        <h4>🚀 {signal['strategy_name']}</h4>
                        <p><strong>Pattern:</strong> {signal['pattern']}</p>
                        <p><strong>Entry Price:</strong> ₹{signal['entry_price']:,.2f}</p>
                        <p><strong>Confidence:</strong> <span style="color: {confidence_color}">{signal['confidence']:.1f}%</span></p>
                        <p><strong>Direction:</strong> {signal['direction']}</p>
                        <p><strong>Timestamp:</strong> {signal['timestamp']}</p>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("No active trading signals at this time.")
    
    with tab2:
        st.header("📈 Market Analysis")
        
        if market_analysis:
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Market Conditions")
                if 'trend' in market_analysis:
                    st.metric("Trend", market_analysis['trend'])
                if 'volatility' in market_analysis:
                    st.metric("Volatility", market_analysis['volatility'])
                if 'volume' in market_analysis:
                    st.metric("Volume Status", market_analysis['volume'])
            
            with col2:
                st.subheader("Technical Indicators")
                if 'rsi' in market_analysis:
                    st.metric("RSI (14)", f"{market_analysis['rsi']:.1f}")
                if 'adx' in market_analysis:
                    st.metric("ADX (14)", f"{market_analysis['adx']:.1f}")
                if 'atr_pct' in market_analysis:
                    st.metric("ATR %", f"{market_analysis['atr_pct']:.2f}%")
        else:
            st.info("Market analysis data not available.")
    
    with tab3:
        st.header("📋 Past Performance")
        
        past_signals = get_past_signals(commodity, timeframe)
        
        if past_signals:
            # Summary metrics
            total_signals = len(past_signals)
            winning_signals = len([s for s in past_signals if s['outcome'] == 'WIN'])
            losing_signals = len([s for s in past_signals if s['outcome'] == 'LOSS'])
            total_pnl = sum([s['pnl'] for s in past_signals])
            win_rate = (winning_signals / total_signals * 100) if total_signals > 0 else 0
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Signals", total_signals)
            with col2:
                st.metric("Win Rate", f"{win_rate:.1f}%")
            with col3:
                st.metric("Total P&L", f"₹{total_pnl:,.0f}")
            with col4:
                st.metric("Winning Signals", f"{winning_signals}/{total_signals}")
            
            # Past signals table
            st.subheader("Recent Past Signals")
            df_signals = pd.DataFrame(past_signals[:20])  # Show last 20
            if not df_signals.empty:
                st.dataframe(
                    df_signals[['timestamp', 'strategy_name', 'pattern', 'entry_price', 'outcome', 'pnl', 'confidence']],
                    use_container_width=True
                )
        else:
            st.info("No past signals data available.")
    
    with tab4:
        st.header("⚙️ Strategy Details")
        
        try:
            data_service = st.session_state.data_service
            rules = data_service.load_trading_rules(commodity.lower(), timeframe)
            
            if rules:
                strategies = []
                for key, value in rules.items():
                    if key.startswith('strategy_') and key != 'strategy_metadata':
                        strategies.append(value)
                
                if strategies:
                    for i, strategy in enumerate(strategies, 1):
                        with st.expander(f"Strategy {i}: {strategy.get('name', 'Unknown')}"):
                            st.write(f"**Pattern:** {strategy.get('pattern', 'N/A')}")
                            st.write(f"**Status:** {strategy.get('status', 'N/A')}")
                            st.write(f"**Category:** {strategy.get('category', 'N/A')}")
                            
                            if 'performance' in strategy:
                                perf = strategy['performance']
                                st.write("**Performance:**")
                                col1, col2 = st.columns(2)
                                with col1:
                                    st.write(f"- Trades: {perf.get('trades', 0)}")
                                    st.write(f"- Win Rate: {perf.get('win_rate', 0):.1f}%")
                                with col2:
                                    st.write(f"- Profit Factor: {perf.get('profit_factor', 0):.2f}")
                                    st.write(f"- Max Drawdown: {perf.get('max_drawdown_pct', 0):.1f}%")
            else:
                st.info("No strategy rules found for this commodity and timeframe.")
        except Exception as e:
            st.error(f"Error loading strategy details: {e}")

if __name__ == "__main__":
    main()
