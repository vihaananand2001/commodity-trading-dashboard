import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import json

# Page config
st.set_page_config(
    page_title="Commodity Dashboard",
    page_icon="📈",
    layout="wide"
)

# Simple header
st.title("📈 Commodity Trading Dashboard")
st.markdown("**Live Gold & Silver Prices**")

# Initialize session state for paper trading
if 'paper_trades' not in st.session_state:
    st.session_state.paper_trades = []
if 'paper_balance' not in st.session_state:
    st.session_state.paper_balance = 1000000  # Start with ₹10 lakh
if 'paper_mode' not in st.session_state:
    st.session_state.paper_mode = False

# Sidebar
with st.sidebar:
    st.header("🎛️ Controls")
    commodity = st.selectbox("Commodity", ["GOLD", "SILVER"])
    
    if commodity == "GOLD":
        timeframe = st.selectbox("Timeframe", ["1h", "4h", "1d"])
    else:
        timeframe = st.selectbox("Timeframe", ["4h", "1d"])
    
    # Paper Trading Section
    st.header("📝 Paper Trading")
    paper_mode = st.checkbox("Enable Paper Trading", value=st.session_state.paper_mode)
    st.session_state.paper_mode = paper_mode
    
    if paper_mode:
        st.subheader("💰 Account Balance")
        st.metric("Balance", f"₹{st.session_state.paper_balance:,.0f}")
        
        st.subheader("💼 Position Sizing")
        risk_percent = st.slider("Risk per Trade (%)", 1, 5, 2)
        account_size = st.number_input("Account Size (₹)", value=st.session_state.paper_balance, step=10000)
        
        if st.button("🔄 Reset Account"):
            st.session_state.paper_balance = account_size
            st.session_state.paper_trades = []
            st.rerun()

# Get price data with correct Indian pricing
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
        
        # Correct conversion for Indian markets
        if commodity == "GOLD":
            # Convert from USD/troy ounce to ₹/10 grams
            # 1 troy ounce = 31.1 grams
            # 10 grams = 0.321 troy ounces
            usd_to_inr = 83.0  # Approximate exchange rate
            price_inr_per_10g = (price_usd * usd_to_inr * 0.321)
            
            # MCX Gold futures (1 kg = 1000 grams = 100 units of 10 grams)
            price_inr_per_kg = price_inr_per_10g * 100
            lot_size = 1000  # 1 kg
            contract_value = price_inr_per_kg * lot_size
        else:  # SILVER
            # Convert from USD/troy ounce to ₹/kg
            # 1 troy ounce = 31.1 grams
            # 1 kg = 32.15 troy ounces
            usd_to_inr = 83.0
            price_inr_per_kg = price_usd * usd_to_inr * 32.15
            
            lot_size = 30000  # 30 kg
            contract_value = price_inr_per_kg * lot_size
        
        return {
            'price_inr_per_10g': price_inr_per_10g if commodity == "GOLD" else price_inr_per_kg,
            'price_inr_per_kg': price_inr_per_kg if commodity == "SILVER" else price_inr_per_10g * 100,
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
            
        # Convert to INR with correct pricing
        if commodity == "GOLD":
            # Convert to ₹/10 grams
            data['Close_INR'] = data['Close'] * 83.0 * 0.321
        else:  # SILVER
            # Convert to ₹/kg
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
        st.metric(
            "Lot Size",
            f"{price_data['lot_size']:,}",
            help="Contract size"
        )
    
    with col3:
        st.metric(
            "Contract Value",
            f"₹{price_data['contract_value']:,.0f}",
            help="Total contract value"
        )
    
    with col4:
        st.metric(
            "Volume",
            f"{price_data['volume']:,.0f}",
            help="Trading volume"
        )
    
    # Position Sizing Calculator
    if st.session_state.paper_mode:
        st.header("💼 Position Sizing Calculator")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            risk_amount = st.session_state.paper_balance * (risk_percent / 100)
            st.metric("Risk Amount", f"₹{risk_amount:,.0f}")
        
        with col2:
            # Calculate position size based on 1.2 ATR stop loss (from backtested strategies)
            if commodity == "GOLD":
                # For Gold: 1 kg = 100 units of 10 grams
                # Risk per 10 grams = price * 0.012 (1.2% ATR)
                risk_per_unit = price_data['price_inr_per_10g'] * 0.012
                max_units = int(risk_amount / risk_per_unit) if risk_per_unit > 0 else 0
                position_value = max_units * price_data['price_inr_per_10g'] * 100  # Convert to kg
            else:  # SILVER
                # For Silver: 30 kg lot
                risk_per_kg = price_data['price_inr_per_kg'] * 0.012
                max_kg = int(risk_amount / risk_per_kg) if risk_per_kg > 0 else 0
                position_value = max_kg * price_data['price_inr_per_kg']
            
            st.metric("Max Position Value", f"₹{position_value:,.0f}")
        
        with col3:
            margin_required = position_value * 0.05  # 5% margin
            st.metric("Margin Required", f"₹{margin_required:,.0f}")
            
            if margin_required > st.session_state.paper_balance:
                st.warning("⚠️ Insufficient balance for position!")

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
        signal_active = False
        signal_type = None
        
        if sma_20 > sma_50 and current_price > sma_20:
            signal_active = True
            signal_type = "BUY"
            st.markdown("""
            <div style="background-color: #d4edda; color: #155724; padding: 1rem; border-radius: 5px; border-left: 4px solid #28a745; margin: 0.5rem 0;">
                <strong>🟢 BUY SIGNAL - Moving Average Crossover</strong><br>
                Price: ₹{:.2f} | SMA 20: ₹{:.2f} | SMA 50: ₹{:.2f}<br>
                Reason: Price above SMA 20, SMA 20 above SMA 50
            </div>
            """.format(current_price, sma_20, sma_50), unsafe_allow_html=True)
        elif sma_20 < sma_50 and current_price < sma_20:
            signal_active = True
            signal_type = "SELL"
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
        
        # Paper Trading Execution
        if st.session_state.paper_mode and signal_active:
            st.subheader("📝 Paper Trading")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if signal_type == "BUY":
                    if st.button(f"🟢 Execute {signal_type} Trade", type="primary"):
                        # Calculate trade details
                        entry_price = current_price
                        stop_loss = entry_price * 0.988  # 1.2% stop loss
                        take_profit = entry_price * 1.018  # 1.8% take profit
                        
                        # Calculate position size
                        risk_per_trade = st.session_state.paper_balance * (risk_percent / 100)
                        risk_per_unit = entry_price * 0.012
                        position_size = int(risk_per_trade / risk_per_unit) if risk_per_unit > 0 else 0
                        
                        if position_size > 0:
                            trade = {
                                'id': len(st.session_state.paper_trades) + 1,
                                'commodity': commodity,
                                'type': signal_type,
                                'entry_price': entry_price,
                                'stop_loss': stop_loss,
                                'take_profit': take_profit,
                                'position_size': position_size,
                                'entry_time': datetime.now(),
                                'status': 'OPEN'
                            }
                            st.session_state.paper_trades.append(trade)
                            st.success(f"✅ {signal_type} trade executed! Position size: {position_size}")
                        else:
                            st.error("❌ Position size too small or insufficient balance")
                
                elif signal_type == "SELL":
                    if st.button(f"🔴 Execute {signal_type} Trade", type="primary"):
                        # Similar logic for sell trades
                        entry_price = current_price
                        stop_loss = entry_price * 1.012  # 1.2% stop loss for short
                        take_profit = entry_price * 0.982  # 1.8% take profit for short
                        
                        risk_per_trade = st.session_state.paper_balance * (risk_percent / 100)
                        risk_per_unit = entry_price * 0.012
                        position_size = int(risk_per_trade / risk_per_unit) if risk_per_unit > 0 else 0
                        
                        if position_size > 0:
                            trade = {
                                'id': len(st.session_state.paper_trades) + 1,
                                'commodity': commodity,
                                'type': signal_type,
                                'entry_price': entry_price,
                                'stop_loss': stop_loss,
                                'take_profit': take_profit,
                                'position_size': position_size,
                                'entry_time': datetime.now(),
                                'status': 'OPEN'
                            }
                            st.session_state.paper_trades.append(trade)
                            st.success(f"✅ {signal_type} trade executed! Position size: {position_size}")
                        else:
                            st.error("❌ Position size too small or insufficient balance")
            
            with col2:
                st.info(f"""
                **Trade Details:**
                - Entry: ₹{current_price:,.0f}
                - Stop Loss: ₹{current_price * (0.988 if signal_type == "BUY" else 1.012):,.0f}
                - Take Profit: ₹{current_price * (1.018 if signal_type == "BUY" else 0.982):,.0f}
                - Risk: {risk_percent}% of account
                """)
    
    # Show open trades
    if st.session_state.paper_mode and st.session_state.paper_trades:
        st.header("📋 Open Trades")
        
        open_trades = [t for t in st.session_state.paper_trades if t['status'] == 'OPEN']
        
        if open_trades:
            for trade in open_trades:
                with st.expander(f"Trade #{trade['id']} - {trade['type']} {trade['commodity']}"):
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.write(f"**Entry:** ₹{trade['entry_price']:,.0f}")
                        st.write(f"**Position:** {trade['position_size']} units")
                    
                    with col2:
                        st.write(f"**Stop Loss:** ₹{trade['stop_loss']:,.0f}")
                        st.write(f"**Take Profit:** ₹{trade['take_profit']:,.0f}")
                    
                    with col3:
                        current_price_for_pnl = current_price if 'current_price' in locals() else trade['entry_price']
                        
                        if trade['type'] == 'BUY':
                            pnl = (current_price_for_pnl - trade['entry_price']) * trade['position_size']
                        else:
                            pnl = (trade['entry_price'] - current_price_for_pnl) * trade['position_size']
                        
                        pnl_color = "green" if pnl > 0 else "red"
                        st.write(f"**Current P&L:** <span style='color:{pnl_color}'>₹{pnl:,.0f}</span>", unsafe_allow_html=True)
                        
                        if st.button(f"Close Trade #{trade['id']}", key=f"close_{trade['id']}"):
                            trade['status'] = 'CLOSED'
                            trade['exit_price'] = current_price_for_pnl
                            trade['exit_time'] = datetime.now()
                            trade['final_pnl'] = pnl
                            st.session_state.paper_balance += pnl
                            st.rerun()
        else:
            st.info("No open trades")
else:
    st.error("Unable to load chart data")

# Footer
st.markdown("---")
st.markdown("*Data provided by Yahoo Finance*")
