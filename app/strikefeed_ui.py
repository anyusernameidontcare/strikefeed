import streamlit as st
import pandas as pd
import numpy as np
import datetime
import pytz
import requests
import yfinance as yf

# ----------------------------------------------------
# API Tokens
# ----------------------------------------------------
TRADIER_TOKEN = "eA5AZaGxFGOfVxMqtIS7GAA4ZS7W"  # Replace with your actual Tradier API token
TRADIER_HEADERS = {
    "Authorization": f"Bearer {TRADIER_TOKEN}",
    "Accept": "application/json"
}

# ----------------------------------------------------
# Helper Functions
# ----------------------------------------------------

def get_option_expirations(symbol):
    url = f"https://api.tradier.com/v1/markets/options/expirations"
    params = {"symbol": symbol, "includeAllRoots": "true", "strikes": "false"}
    response = requests.get(url, headers=TRADIER_HEADERS, params=params)
    if response.status_code != 200:
        return []
    return response.json().get("expirations", {}).get("date", [])

def get_option_chain(symbol, expiration):
    url = f"https://api.tradier.com/v1/markets/options/chains"
    params = {"symbol": symbol, "expiration": expiration, "greeks": "true"}
    response = requests.get(url, headers=TRADIER_HEADERS, params=params)
    if response.status_code != 200:
        return [], []
    options = response.json().get("options", {}).get("option", [])
    calls = [o for o in options if o["option_type"] == "call"]
    puts = [o for o in options if o["option_type"] == "put"]
    return calls, puts

def get_historical_volatility(symbol):
    try:
        data = yf.Ticker(symbol).history(period="1mo")
        returns = data["Close"].pct_change().dropna()
        hv = np.std(returns) * np.sqrt(252)
        return hv
    except:
        return None

def score_option(iv, hv, bid, ask, delta):
    if iv is None or hv is None or bid is None or ask is None:
        return None

    # Score is weighted based on IV/HV ratio, tight spread, and delta
    iv_hv_ratio = iv / hv if hv else 0
    spread = ask - bid if ask and bid else 0
    spread_score = 1 - min(spread / max(ask, 0.01), 1)
    delta_score = 1 - abs(delta)

    score = (iv_hv_ratio * 0.5 + spread_score * 0.3 + delta_score * 0.2) * 100
    return round(score, 2)

# ----------------------------------------------------
# Streamlit UI
# ----------------------------------------------------
st.set_page_config(page_title="StrikeFeed", layout="wide")
st.markdown("""
    <h1 style='text-align: center;'>📈 StrikeFeed</h1>
    <p style='text-align: center; font-size: 0.9em;'>Last updated: {} UTC</p>
""".format(datetime.datetime.utcnow().strftime("%I:%M:%S %p")), unsafe_allow_html=True)

symbol = st.selectbox("🔍 Search Ticker", options=["AAPL", "NVDA", "TSLA", "AMD"], index=0)
expirations = get_option_expirations(symbol)
expiration = st.selectbox("Expiration", options=expirations)

if symbol and expiration:
    calls, puts = get_option_chain(symbol, expiration)
    hv = get_historical_volatility(symbol)

    calls_df = pd.DataFrame(calls)
    puts_df = pd.DataFrame(puts)

    if "strike" in calls_df.columns:
        calls_df = calls_df.set_index("strike")
    else:
        calls_df = pd.DataFrame(columns=["bid", "ask", "delta", "iv", "score"])

    if "strike" in puts_df.columns:
        puts_df = puts_df.set_index("strike")
    else:
        puts_df = pd.DataFrame(columns=["bid", "ask", "delta", "iv", "score"])

    for df in [calls_df, puts_df]:
        for idx in df.index:
            row = df.loc[idx]
            iv = row.get("greeks", {}).get("iv")
            delta = row.get("greeks", {}).get("delta")
            bid = row.get("bid")
            ask = row.get("ask")
            score = score_option(iv, hv, bid, ask, delta)
            df.at[idx, "iv"] = iv
            df.at[idx, "delta"] = delta
            df.at[idx, "score"] = score

    combined = pd.concat([
        calls_df[["bid", "ask", "delta", "iv", "score"]].rename(columns={"bid": "Call Bid", "ask": "Call Ask"}),
        pd.DataFrame(index=calls_df.index).index.to_frame(name="Strike"),
        puts_df[["bid", "ask", "delta", "iv", "score"]].rename(columns={"bid": "Put Bid", "ask": "Put Ask", "score": "Score"})
    ], axis=1)

    def highlight_score(val):
        if val is None:
            return "color: #ccc"
        val = float(val)
        if val >= 80:
            return "color: lightgreen"
        elif val >= 60:
            return "color: gold"
        else:
            return "color: lightcoral"

    st.dataframe(combined.reset_index(drop=True).style.applymap(highlight_score, subset=["Score"]))

    st.markdown("""
    <p style='text-align: center; font-size: 0.8em;'>StrikeFeed — Powered by Tradier + Yahoo</p>
    """, unsafe_allow_html=True)
