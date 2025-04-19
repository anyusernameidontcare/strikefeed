import streamlit as st
import pandas as pd
import numpy as np
import requests
import datetime
import yfinance as yf

# ======================
# 🔐 Tradier API Setup
# ======================
TRADIER_TOKEN = "OiteBPyAfIXoXsE1F0yoUV5pKddR"
TRADIER_HEADERS = {
    "Authorization": f"Bearer {TRADIER_TOKEN}",
    "Accept": "application/json"
}
BASE_URL = "https://api.tradier.com/v1/markets/options"

# ======================
# 🔧 Utility Functions
# ======================

def fetch_expirations(symbol):
    url = f"{BASE_URL}/expirations"
    params = {"symbol": symbol, "includeAllRoots": "true", "strikes": "false"}
    r = requests.get(url, headers=TRADIER_HEADERS, params=params)
    if r.status_code != 200:
        return []
    data = r.json()
    return data.get("expirations", {}).get("date", [])

def fetch_option_chain(symbol, expiration):
    url = f"{BASE_URL}/chains"
    params = {"symbol": symbol, "expiration": expiration, "greeks": "true"}
    r = requests.get(url, headers=TRADIER_HEADERS, params=params)
    if r.status_code != 200:
        return []
    data = r.json()
    return data.get("options", {}).get("option", [])

def fetch_hv(symbol):
    try:
        hist = yf.Ticker(symbol).history(period="30d")['Close']
        returns = hist.pct_change().dropna()
        std_dev = np.std(returns)
        return std_dev * np.sqrt(252)
    except:
        return None

def calculate_score(row, hv):
    if not isinstance(row, dict):
        return None
    iv = row.get("iv")
    if iv is None or hv is None or iv == 0:
        return None
    iv_hv_ratio = iv / hv
    if iv_hv_ratio == 0:
        return None
    score = (1 / iv_hv_ratio) * 100
    score -= abs(row.get("delta", 0)) * 10
    spread = (row.get("ask", 0) - row.get("bid", 0))
    if spread > 0:
        score -= (spread / (row.get("bid", 1) + 0.01)) * 5
    return round(score, 2)

def style_score(val):
    if val is None or val == "—":
        return "color: lightgray;"
    if val >= 80:
        return "color: #74d17a;"  # green
    elif val >= 60:
        return "color: #f4e36d;"  # yellow
    else:
        return "color: #e06666;"  # red

# ======================
# 🚀 Streamlit UI
# ======================

st.markdown("<h1 style='text-align: center;'>📉 StrikeFeed</h1>", unsafe_allow_html=True)
st.caption(f"Last updated: {datetime.datetime.utcnow().strftime('%H:%M:%S')} UTC")

symbol = st.selectbox("🔍 Search Ticker", options=["AAPL", "TSLA", "NVDA", "AMD", "SPY"])
expirations = fetch_expirations(symbol)

if not expirations:
    st.warning("⚠️ No expirations found.")
    st.stop()

expiration = st.selectbox("📅 Expiration", options=expirations)

options = fetch_option_chain(symbol, expiration)
hv = fetch_hv(symbol)

# Construct UI table with dashes as fallback
columns = ["Call Bid", "Call Ask", "Strike", "Put Bid", "Put Ask", "Score"]
rows = []

call_chain = [o for o in options if o.get("option_type") == "call"]
put_chain = [o for o in options if o.get("option_type") == "put"]

for call, put in zip(call_chain, put_chain):
    strike = call.get("strike", put.get("strike", "-"))
    cb = call.get("bid", "-")
    ca = call.get("ask", "-")
    pb = put.get("bid", "-")
    pa = put.get("ask", "-")
    score = calculate_score(call, hv)
    rows.append([
        f"{cb:.2f}" if isinstance(cb, float) else "—",
        f"{ca:.2f}" if isinstance(ca, float) else "—",
        f"{strike:.2f}" if isinstance(strike, float) else "—",
        f"{pb:.2f}" if isinstance(pb, float) else "—",
        f"{pa:.2f}" if isinstance(pa, float) else "—",
        score if score is not None else "—"
    ])

df = pd.DataFrame(rows, columns=columns)
styled_df = df.style.applymap(style_score, subset=["Score"])
st.dataframe(styled_df)
