"""
Minimal Streamlit App for Testing Deployment
"""

import streamlit as st

st.title("📈 Commodity Trading Dashboard")
st.subheader("Live MCX Gold & Silver Trading")

st.write("✅ Streamlit app is working!")

# Test basic functionality
st.header("Test Section")
st.write("If you can see this, the deployment is successful!")

# Add some interactive elements
commodity = st.selectbox("Select Commodity", ["GOLD", "SILVER"])
timeframe = st.selectbox("Select Timeframe", ["1H", "4H", "1D"])

st.write(f"Selected: {commodity} {timeframe}")

# Test data display
import pandas as pd
import numpy as np

data = pd.DataFrame({
    'Price': np.random.normal(100000, 1000, 10),
    'Volume': np.random.randint(1000, 10000, 10)
})

st.line_chart(data)

st.success("🎉 Dashboard is live and working!")
