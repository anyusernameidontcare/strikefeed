import streamlit as st
import pandas as pd
import datetime
import pytz

# ─────────────────────────────────────────────
# Determine Market Status
# ─────────────────────────────────────────────

def get_market_status():
    now = datetime.datetime.now(pytz.timezone("US/Eastern"))
    open_time = now.replace(hour=9, minute=30, second=0, microsecond=0)
    close_time = now.replace(hour=16, minute=0, second=0, microsecond=0)
    weekday = now.weekday()

    if weekday >= 5:
        return "closed"
    elif now < open_time:
        return "pre-market"
    elif now > close_time:
        return "after-hours"
    else:
        return "open"

status = get_market_status()

# ─────────────────────────────────────────────
# Page Settings
# ─────────────────────────────────────────────

st.set_page_config(layout="wide")
st.markdown("<h1 style='text-align: center; font-size: 3em;'>📈 StrikeFeed</h1>", unsafe_allow_html=True)

if status == "open":
    st.markdown("<p style='text-align: right; color: #00e676;'>✅ Market Open</p>", unsafe_allow_html=True)
elif status == "after-hours":
    st.markdown("<p style='text-align: right; color: #facc15;'>🌙 After Hours</p>", unsafe_allow_html=True)
else:
    st.markdown("<p style='text-align: right; color: #ef4444;'>❌ Market Closed</p>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Load or mock data
# ─────────────────────────────────────────────

if status == "open":
    df = pd.read_csv("app/strikefeed_mock_data.csv")  # Live later
    df['Score'] = df['Score'].replace('%', '', regex=False).astype(float)
else:
    # Empty frame with dashes
    cols = ["Strike", "Type", "Bid", "Ask", "Delta", "IV", "Score"]
    df = pd.DataFrame({col: ["—"]*10 for col in cols})

# ─────────────────────────────────────────────
# Ticker Search
# ─────────────────────────────────────────────

tickers = sorted(df["Ticker"].dropna().unique()) if status == "open" else []
selected_ticker = st.selectbox("🔍 Search Ticker", options=[""] + tickers)

if status == "open" and selected_ticker:
    df = df[df["Ticker"] == selected_ticker]

# ─────────────────────────────────────────────
# Display Table
# ─────────────────────────────────────────────

st.markdown("### ")
st.dataframe(df.style.set_properties(**{
    "text-align": "center"
}), use_container_width=True)

# ─────────────────────────────────────────────
# Footer
# ─────────────────────────────────────────────

st.markdown("### ")
st.markdown("<div style='text-align:center; color:gray;'>StrikeFeed – Real-time options scanner</div>", unsafe_allow_html=True)
