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
# Page Layout
# ─────────────────────────────────────────────

st.set_page_config(layout="wide")
st.markdown("<h1 style='text-align: center; font-size: 2.5em;'>📈 StrikeFeed</h1>", unsafe_allow_html=True)
st.markdown(f"<p style='text-align: center; color: gray;'>Last updated: {datetime.datetime.now().strftime('%I:%M:%S %p')}</p>", unsafe_allow_html=True)

if status == "open":
    st.markdown("<p style='text-align: right; color: #00e676;'>✅ Market Open</p>", unsafe_allow_html=True)
elif status == "after-hours":
    st.markdown("<p style='text-align: right; color: #facc15;'>🌙 After Hours</p>", unsafe_allow_html=True)
else:
    st.markdown("<p style='text-align: right; color: #ef4444;'>❌ Market Closed</p>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Load Data
# ─────────────────────────────────────────────

if status == "open":
    df = pd.read_csv("app/strikefeed_mock_data.csv")
    df['Score'] = df['Score'].replace('%', '', regex=False).astype(float)
else:
    df = pd.DataFrame(columns=["Strike", "Type", "Bid", "Ask", "Delta", "IV", "Score"])

# ─────────────────────────────────────────────
# Ticker Search + Filter
# ─────────────────────────────────────────────

st.markdown("### ")
tickers = sorted(df["Ticker"].dropna().unique()) if not df.empty else []
selected_ticker = st.selectbox("🔍 Search Ticker", options=[""] + tickers)

if status == "open" and selected_ticker:
    df = df[df["Ticker"] == selected_ticker]

    # Split into calls/puts
    calls = df[df["Type"] == "call"][["Strike", "Bid", "Ask"]].rename(columns={
        "Bid": "Call Bid", "Ask": "Call Ask"
    })

    puts = df[df["Type"] == "put"][["Strike", "Bid", "Ask"]].rename(columns={
        "Bid": "Put Bid", "Ask": "Put Ask"
    })

    # Merge by Strike
    merged = pd.merge(calls, puts, on="Strike", how="outer").sort_values("Strike")
    merged = merged[["Call Bid", "Call Ask", "Strike", "Put Bid", "Put Ask"]]
    merged.fillna("—", inplace=True)

    # Format table
    styled = merged.style.set_properties(**{
        "text-align": "center",
        "font-size": "14px",
        "background-color": "#111111",
        "color": "white"
    })

    st.dataframe(styled, use_container_width=True)

else:
    # Placeholder table if closed or no ticker
    columns = ["Call Bid", "Call Ask", "Strike", "Put Bid", "Put Ask"]
    blank = pd.DataFrame({col: ["—"]*10 for col in columns})
    st.dataframe(blank, use_container_width=True)

# ─────────────────────────────────────────────
# Footer
# ─────────────────────────────────────────────

st.markdown("### ")
st.markdown("<div style='text-align:center; color:gray;'>StrikeFeed – Real-time options scanner</div>", unsafe_allow_html=True)
