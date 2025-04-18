
import streamlit as st
import pandas as pd

st.set_page_config(page_title="StrikeFeed Option Scanner", layout="wide")

st.title("📈 StrikeFeed Deal Scanner")
st.markdown("Prototype UI — displaying mock option chain data with Deal Scores")

# Load mock data
df = pd.read_csv("strikefeed_mock_data.csv")

# Filters
tickers = df["Ticker"].unique()
selected_ticker = st.selectbox("Select Ticker", options=["All"] + list(tickers))
min_score = st.slider("Minimum Score", 0, 100, 0)

# Apply filters
filtered_df = df.copy()
if selected_ticker != "All":
    filtered_df = filtered_df[filtered_df["Ticker"] == selected_ticker]
filtered_df = filtered_df[filtered_df["Score"].fillna(0) >= min_score]

# Display
st.dataframe(filtered_df.style.format({
    "Bid": "${:.2f}", "Ask": "${:.2f}", "Delta": "{:.2f}", "IV": "{:.0%}", "Score": "{:.0f}"
}), use_container_width=True)

st.markdown("---")
st.caption("Scores are mock values for demonstration purposes.")
