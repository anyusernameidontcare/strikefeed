# ===============================
# ⚡ strikefeed_ui.py (Main App)
# ===============================
import streamlit as st
import pandas as pd
import datetime

from config import TICKERS
from scoring import calculate_score
from layout import render_score_key, show_greek_toggle, style_cell
from tradier_api import get_expirations, get_option_chain, get_current_price, get_historical_volatility

# Streamlit Setup
st.set_page_config(layout="wide")
st.markdown("<h2 style='text-align:center;'>⚡ StrikeFeed</h2>", unsafe_allow_html=True)

# User Controls
symbol = st.selectbox("Ticker", TICKERS)
expirations = get_expirations(symbol)
expiration = st.selectbox("Expiration", expirations)
current_price = get_current_price(symbol)

st.markdown(f"<p style='text-align:center;'>Current Price: ${current_price:.2f}</p>", unsafe_allow_html=True)
show_raw = show_greek_toggle()
render_score_key()

# Data Fetching
options = get_option_chain(symbol, expiration)
hv = get_historical_volatility(symbol)
calls = [o for o in options if o["option_type"] == "call" and o.get("bid", 0) > 0]
puts = [o for o in options if o["option_type"] == "put" and o.get("bid", 0) > 0]

# Match by strike
rows = []
for c, p in zip(calls, puts):
    strike = c.get("strike")
    row = {
        "Call Bid": f"{c.get('bid', 0):.2f}",
        "Call Ask": f"{c.get('ask', 0):.2f}",
        "Call Score": calculate_score(c, hv),
        "Strike": f"{strike:.2f}",
        "Put Bid": f"{p.get('bid', 0):.2f}",
        "Put Ask": f"{p.get('ask', 0):.2f}",
        "Put Score": calculate_score(p, hv),
        "Call Delta": c.get("greeks", {}).get("delta"),
        "Put Delta": p.get("greeks", {}).get("delta"),
        "IV": c.get("greeks", {}).get("iv"),
        "HV": hv
    }
    rows.append(row)

# Display
visible_cols = ["Call Bid", "Call Ask", "Call Score", "Strike", "Put Bid", "Put Ask", "Put Score"]
extra_cols = ["Call Delta", "Put Delta", "IV", "HV"]
final_cols = visible_cols + extra_cols if show_raw else visible_cols

df = pd.DataFrame(rows)
st.dataframe(df[final_cols].style.applymap(style_cell), use_container_width=True)
