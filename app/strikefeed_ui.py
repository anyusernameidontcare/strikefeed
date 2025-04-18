import streamlit as st
import pandas as pd
import time

# Load data
df = pd.read_csv("app/strikefeed_mock_data.csv")

# Format Score column if it's a string %
if df['Score'].dtype == 'object':
    df['Score'] = df['Score'].str.replace('%', '', regex=False)
    df['Score'] = pd.to_numeric(df['Score'], errors='coerce')

# UI Config
st.set_page_config(layout="wide")
st.markdown("<h1 style='text-align: center;'>📈 StrikeFeed</h1>", unsafe_allow_html=True)

# Timestamp
st.markdown(f"<p style='text-align:center; color:gray;'>Last updated: {time.strftime('%I:%M:%S %p')}</p>", unsafe_allow_html=True)

# Ticker search
tickers = sorted(df['Ticker'].dropna().unique())
selected_ticker = st.selectbox("Search Ticker", options=["All"] + tickers)

# Score filter
min_score = st.slider("Minimum Score", 0, 100, 0)

# Filter data
filtered_df = df.copy()
if selected_ticker != "All":
    filtered_df = filtered_df[filtered_df['Ticker'] == selected_ticker]

filtered_df = filtered_df[filtered_df['Score'].fillna(0) >= min_score]

# Style score column
def color_score(val):
    if pd.isna(val): return ""
    if val >= 80: return "background-color: #1fba55; color: white;"
    elif val >= 60: return "background-color: #facc15; color: black;"
    else: return "background-color: #ef4444; color: white;"

styled_df = filtered_df.style.applymap(color_score, subset=["Score"])

# Display table
st.dataframe(styled_df, use_container_width=True)

# Footer
st.markdown("---")
st.markdown("Scores are mock values for demonstration purposes.")
