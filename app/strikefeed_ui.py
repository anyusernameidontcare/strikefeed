import streamlit as st
import pandas as pd
import numpy as np
import requests
import yfinance as yf
import datetime

# =========================
# 🔐 Tradier API Setup
# =========================

TRADIER_TOKEN = "OiteBPyAfIXoXsE1F0yoUV5pKddR" 
TRADIER_HEADERS = {
    "Authorization": f"Bearer {TRADIER_TOKEN}",
    "Accept": "application/json"
}
BASE_URL = "https://api.tradier.com/v1/markets/options"

# =========================
# ⚙️ Utility Functions
# =========================

def fetch_expirations(symbol):
    url = f"{BASE_URL}/expirations"
    params = {"symbol": symbol, "includeAllRoots": "true", "strikes": "false"}
    r = requests.get(url, headers=TRADIER_HEADERS, params=params)
    if r.status_code != 200:
        return []
    return r.json().get("expirations", {}).get("date", [])

def fetch_option_chain(symbol, expiration):
    url = f"{BASE_URL}/chains"
    params = {"symbol": symbol, "expiration": expiration}
    r = requests.get(url, headers=TRADIER_HEADERS, params=params)
    if r.status_code != 200:
        return [], []
    options = r.json().get("options", {}).get("option", [])
    calls = [o for o in options if o.get("option_type") == "call"]
    puts = [o for o in options if o.get("option_type") == "put"]
    return calls, puts

def get_historical_volatility(symbol):
    try:
        end = datetime.datetime.today()
        start = end - datetime.timedelta(days=20)
        df = yf.download(symbol, start=start, end=end)
        df['returns'] = np.log(df['Close'] / df['Close'].shift(1))
        hv = np.std(df['returns'].dropna()) * np.sqrt(252)
        return hv
    except:
        return None

def calculate_score(row, hv):
    try:
        if row['iv'] is None or hv is None:
            return None
        iv = float(row['iv'])
        delta = abs(float(row['delta']))
        spread = float(row['ask']) - float(row['bid'])
        efficiency = 1 / (spread + 0.01)
        score = ((iv / hv) * (1 - delta)) * efficiency
        return round(score * 100, 2)
    except:
        return None

def highlight_score(val):
    if val is None:
        return ''
    color = 'red' if val < 60 else 'yellow' if val < 80 else 'green'
    return f'color: {color}; font-weight: bold'

# =========================
# 🧠 App UI
# =========================

st.markdown("<h1 style='text-align: center;'>📉 StrikeFeed</h1>", unsafe_allow_html=True)
st.caption(f"Last updated: {datetime.datetime.utcnow().strftime('%H:%M:%S')} UTC")

ticker = st.selectbox("🔍 Search Ticker", ["AAPL", "TSLA", "NVDA", "AMD", "MSFT", "META"], index=0)

expirations = fetch_expirations(ticker)
expiration = st.selectbox("📅 Expiration", expirations) if expirations else None

if expiration:
    calls, puts = fetch_option_chain(ticker, expiration)
    hv = get_historical_volatility(ticker)

    if calls and puts:
        df = pd.DataFrame(calls + puts)
        required_cols = ["option_type", "strike", "bid", "ask", "delta", "iv"]

        if all(col in df.columns for col in required_cols):
            df = df[required_cols].copy()
            df['score'] = df.apply(lambda row: calculate_score(row, hv), axis=1)

            styled_df = df.style.applymap(highlight_score, subset=["score"])
            st.dataframe(styled_df, use_container_width=True)
        else:
            st.warning("⚠️ Some data fields are missing from Tradier's response.")
    else:
        st.warning("⚠️ No option chain data available for this expiration.")
else:
    st.warning("⚠️ No expirations available for this ticker.")
