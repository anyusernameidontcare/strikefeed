import streamlit as st
import pandas as pd
import numpy as np
import requests
import datetime
import yfinance as yf

# ======================
# ✅ Tradier API Setup
# ======================
TRADIER_TOKEN = "OiteBPyAfIXoXsE1F0yoUV5pKddR"
TRADIER_HEADERS = {
    "Authorization": f"Bearer {TRADIER_TOKEN}",
    "Accept": "application/json"
}
BASE_URL = "https://api.tradier.com/v1/markets/options"

# ======================
# 🔁 Utility Functions
# ======================

def fetch_expirations(symbol):
    url = f"{BASE_URL}/expirations"
    params = {"symbol": symbol, "includeAllRoots": "true", "strikes": "false"}
    r = requests.get(url, headers=TRADIER_HEADERS, params=params)
    data = r.json()
    return data.get("expirations", {}).get("date", [])

def fetch_options_chain(symbol, expiration):
    url = f"{BASE_URL}/chains"
    params = {"symbol": symbol, "expiration": expiration}
    r = requests.get(url, headers=TRADIER_HEADERS, params=params)
    data = r.json()
    return data.get("options", {}).get("option", [])

def fetch_hv(symbol):
    try:
        hist = yf.Ticker(symbol).history(period="90d")
        returns = hist["Close"].pct_change().dropna()
        return returns.std() * np.sqrt(252)  # Annualized HV
    except:
        return None

def calculate_score(row, hv):
    try:
        if pd.isna(row.get("iv")) or pd.isna(hv):
            return None
        iv_hv_ratio = row["iv"] / hv if hv else 0.001
        spread = row["ask"] - row["bid"]
        efficiency = 1 - (spread / row["ask"]) if row["ask"] else 0
        delta_score = 1 - abs(row["delta"] - 0.5)
        score = (1 / iv_hv_ratio) * efficiency * delta_score * 100
        return round(score, 2)
    except:
        return None

def highlight_score(val):
    if pd.isna(val):
        return ""
    if val >= 75:
        return "color: #3ee27e;"  # green
    elif val >= 50:
        return "color: #ffe36e;"  # yellow
    else:
        return "color: #ff6b6b;"  # red

# ======================
# 🌐 Streamlit UI
# ======================

st.markdown("<h1 style='text-align:center;'>📈 StrikeFeed</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center;'>Last updated: " + datetime.datetime.utcnow().strftime("%I:%M:%S %p UTC") + "</p>", unsafe_allow_html=True)

symbol = st.selectbox("🔍 Search Ticker", ["AAPL", "TSLA", "NVDA", "AMD", "MSFT", "SPY"])

if symbol:
    expirations = fetch_expirations(symbol)
    if expirations:
        expiration = st.selectbox("📅 Expiration", expirations[:4])
        if expiration:
            options = fetch_options_chain(symbol, expiration)
            df = pd.DataFrame(options)

            if not df.empty:
                df = df[df["option_type"].isin(["call", "put"])]
                df = df[["option_type", "strike", "bid", "ask", "delta", "iv"]]
                df.columns = ["Type", "Strike", "Bid", "Ask", "Delta", "IV"]
                df = df.dropna(subset=["Strike", "Bid", "Ask", "Delta"])
                hv = fetch_hv(symbol)

                df["Score"] = df.apply(lambda row: calculate_score(row, hv), axis=1)
                df = df.sort_values(by="Strike")

                styled = df.style.applymap(highlight_score, subset=["Score"])
                st.dataframe(styled, use_container_width=True)
            else:
                st.warning("No option chain data returned.")
        else:
            st.warning("Please select an expiration.")
    else:
        st.warning("No expirations found for this ticker.")
else:
    st.warning("Please select a ticker.")
