import streamlit as st
import pandas as pd
import numpy as np
import datetime
import requests
import yfinance as yf
import pytz

# ================================
# Tradier API Configuration
# ================================
TRADIER_TOKEN = "OiteBPyAfIXoXsE1F0yoUV5pKddR"
TRADIER_HEADERS = {
    "Authorization": f"Bearer {TRADIER_TOKEN}",
    "Accept": "application/json"
}
TRADIER_BASE = "https://api.tradier.com/v1"

# ================================
# Utility Functions
# ================================
def fetch_option_expirations(ticker):
    url = f"{TRADIER_BASE}/markets/options/expirations"
    params = {"symbol": ticker, "includeAllRoots": "true", "strikes": "false"}
    r = requests.get(url, headers=TRADIER_HEADERS, params=params)
    data = r.json()
    return data.get("expirations", {}).get("date", [])

def fetch_option_chain(ticker, expiration):
    url = f"{TRADIER_BASE}/markets/options/chains"
    params = {"symbol": ticker, "expiration": expiration, "greeks": "true"}
    r = requests.get(url, headers=TRADIER_HEADERS, params=params)
    data = r.json()
    return data.get("options", {}).get("option", [])

def get_historical_volatility(ticker):
    try:
        data = yf.download(ticker, period="1mo")['Close']
        log_returns = np.log(data / data.shift(1)).dropna()
        hv = np.std(log_returns) * np.sqrt(252)
        return hv
    except:
        return None

def calculate_score(row, hv):
    if row['iv'] is None or hv is None:
        return None
    iv_hv_ratio = row['iv'] / hv if hv > 0 else 0
    spread = row['ask'] - row['bid'] if row['ask'] and row['bid'] else None
    if spread is None:
        return None
    spread_penalty = min(spread / (row['ask'] + 0.01), 1)
    delta_score = 1 - abs(0.5 - abs(row['delta']))
    score = (1 / iv_hv_ratio) * 50 + delta_score * 30 + (1 - spread_penalty) * 20
    return round(score, 2)

def highlight_score(val):
    if val is None:
        return ""
    if val >= 80:
        return "color: #55ff55"
    elif val >= 60:
        return "color: #ffff66"
    else:
        return "color: #ff6666"

# ================================
# Streamlit App
# ================================
st.set_page_config(page_title="StrikeFeed", layout="wide")
st.markdown("""
    <h1 style='text-align: center;'>📈 StrikeFeed</h1>
    <p style='text-align: center;'>Last updated: {}</p>
    """.format(datetime.datetime.now(pytz.UTC).strftime("%H:%M:%S %Z")), unsafe_allow_html=True)

ticker = st.selectbox("🔍 Search Ticker", options=["AAPL", "NVDA", "TSLA", "AMD"], index=0)
if ticker:
    expirations = fetch_option_expirations(ticker)
    expiration = st.selectbox("Expiration", options=expirations)

    if expiration:
        options = fetch_option_chain(ticker, expiration)
        if options:
            df = pd.DataFrame(options)
            hv = get_historical_volatility(ticker)
            df['score'] = df.apply(lambda row: calculate_score(row, hv), axis=1)

            calls = df[df['option_type'] == 'call'][['strike', 'bid', 'ask', 'delta', 'iv', 'score']]
            puts = df[df['option_type'] == 'put'][['strike', 'bid', 'ask', 'delta', 'iv', 'score']]

            calls.columns = ["Strike", "Call Bid", "Call Ask", "Delta", "IV", "Score"]
            puts.columns = ["Strike", "Put Bid", "Put Ask", "Delta", "IV", "Score"]

            combined = pd.merge(calls, puts, on="Strike", how="outer", suffixes=("", ""))
            combined = combined.sort_values("Strike")

            st.dataframe(
                combined.reset_index(drop=True)
                .style.applymap(highlight_score, subset=["Score_x", "Score_y"])
            )
        else:
            st.warning("No option data available.")
    else:
        st.warning("Select an expiration date.")
