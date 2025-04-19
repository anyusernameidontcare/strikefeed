import streamlit as st
import pandas as pd
import numpy as np
import datetime
import pytz
import requests
import yfinance as yf

# ─────────────────────────────────────────────
# API Tokens
# ─────────────────────────────────────────────
TRADIER_TOKEN = "YOUR_LIVE_TRADIER_TOKEN"  # ← REPLACE THIS
TRADIER_HEADERS = {
    "Authorization": f"Bearer {TRADIER_TOKEN}",
    "Accept": "application/json"
}

# ─────────────────────────────────────────────
# HV Calculation from Yahoo
# ─────────────────────────────────────────────
def get_hv(ticker, days=20):
    data = yf.download(ticker, period='60d', interval='1d', progress=False)
    if data.empty or 'Adj Close' not in data:
        return None
    data['returns'] = np.log(data['Adj Close'] / data['Adj Close'].shift(1))
    std_dev = data['returns'].rolling(window=days).std().iloc[-1]
    hv = std_dev * np.sqrt(252) * 100
    return round(hv, 2)

# ─────────────────────────────────────────────
# Tradier Expiration Dates
# ─────────────────────────────────────────────
def get_expirations(ticker):
    url = f"https://api.tradier.com/v1/markets/options/expirations"
    params = {"symbol": ticker}
    try:
        response = requests.get(url, headers=TRADIER_HEADERS, params=params)
        data = response.json()
        return data['expirations']['date'][:4]  # Limit to next 4 Fridays
    except:
        return []

# ─────────────────────────────────────────────
# Tradier Option Chain
# ─────────────────────────────────────────────
def get_option_chain(ticker, expiration):
    url = "https://api.tradier.com/v1/markets/options/chains"
    params = {"symbol": ticker, "expiration": expiration, "greeks": "true"}
    try:
        response = requests.get(url, headers=TRADIER_HEADERS, params=params)
        data = response.json()
        return pd.DataFrame(data["options"]["option"])
    except:
        return pd.DataFrame()

# ─────────────────────────────────────────────
# Market Status
# ─────────────────────────────────────────────
def get_market_status():
    now = datetime.datetime.now(pytz.timezone("US/Eastern"))
    open_time = now.replace(hour=9, minute=30, second=0)
    close_time = now.replace(hour=16, minute=0, second=0)
    if now.weekday() >= 5: return "closed"
    elif now < open_time: return "pre-market"
    elif now > close_time: return "after-hours"
    else: return "open"

# ─────────────────────────────────────────────
# Scoring Function
# ─────────────────────────────────────────────
def score_option(row, hv):
    try:
        iv = row["implied_volatility"] * 100
        bid = row["bid"]
        ask = row["ask"]
        delta = abs(row["delta"])
        mid = (bid + ask) / 2
        spread_pct = (ask - bid) / mid if mid else 1
        efficiency = bid / mid if mid else 0
        iv_hv_ratio = iv / hv if hv else 10

        if iv_hv_ratio < 0.8: iv_score = 95
        elif iv_hv_ratio < 1.0: iv_score = 85
        elif iv_hv_ratio < 1.2: iv_score = 65
        else: iv_score = 45

        if spread_pct < 0.02: spread_score = 90
        elif spread_pct < 0.05: spread_score = 75
        elif spread_pct < 0.10: spread_score = 60
        else: spread_score = 40

        if 0.30 <= delta <= 0.50: delta_score = 85
        elif 0.20 <= delta <= 0.60: delta_score = 70
        else: delta_score = 50

        if efficiency >= 0.95: eff_score = 90
        elif efficiency >= 0.85: eff_score = 75
        else: eff_score = 60

        final = (
            iv_score * 0.40 +
            spread_score * 0.30 +
            delta_score * 0.15 +
            eff_score * 0.15
        )
        return round(final, 1)
    except:
        return None

def color_score(val):
    if val is None or pd.isna(val): return ""
    if val >= 80: return "color: #34d399;"
    elif val >= 60: return "color: #facc15;"
    else: return "color: #f87171;"

# ─────────────────────────────────────────────
# Streamlit UI
# ─────────────────────────────────────────────
status = get_market_status()
st.set_page_config(layout="wide")
st.markdown("<h1 style='text-align: center;'>📈 StrikeFeed</h1>", unsafe_allow_html=True)
st.markdown(f"<p style='text-align: center; color: gray;'>Last updated: {datetime.datetime.now().strftime('%I:%M:%S %p')}</p>", unsafe_allow_html=True)
if status == "open":
    st.markdown("<p style='text-align: right; color: #00e676;'>✅ Market Open</p>", unsafe_allow_html=True)
elif status == "after-hours":
    st.markdown("<p style='text-align: right; color: #facc15;'>🌙 After Hours</p>", unsafe_allow_html=True)
else:
    st.markdown("<p style='text-align: right; color: #ef4444;'>❌ Market Closed</p>", unsafe_allow_html=True)

st.markdown("### ")
ticker = st.selectbox("🔍 Search Ticker", options=["", "AAPL", "TSLA", "NVDA", "SPY", "QQQ", "MSFT", "META", "AMD"])

if ticker:
    hv = get_hv(ticker)
    expirations = get_expirations(ticker)
    expiration = st.selectbox("Select Expiration", expirations)

    if expiration:
        df = get_option_chain(ticker, expiration)
        if not df.empty:
            df["Score"] = df.apply(lambda row: score_option(row, hv), axis=1)

            calls = df[df["option_type"] == "call"][["strike", "bid", "ask", "Score"]].rename(columns={
                "bid": "Call Bid", "ask": "Call Ask"
            })
            puts = df[df["option_type"] == "put"]["strike", "bid", "ask"].rename(columns={
                "bid": "Put Bid", "ask": "Put Ask"
            })

            merged = pd.merge(calls, puts, on="strike", how="outer").sort_values("strike")
            merged = merged[["Call Bid", "Call Ask", "strike", "Put Bid", "Put Ask", "Score"]]
            merged.rename(columns={"strike": "Strike"}, inplace=True)
            merged.fillna("—", inplace=True)

            st.dataframe(merged.style.applymap(color_score, subset=["Score"]).set_properties(**{
                "text-align": "center",
                "font-size": "14px"
            }), use_container_width=True)
        else:
            st.warning("⚠️ No option data available for this expiration.")
else:
    blank = pd.DataFrame({col: ["—"]*10 for col in ["Call Bid", "Call Ask", "Strike", "Put Bid", "Put Ask", "Score"]})
    st.dataframe(blank, use_container_width=True)

st.markdown("### ")
st.markdown("<div style='text-align:center; color:gray;'>StrikeFeed – Powered by Tradier + Yahoo</div>", unsafe_allow_html=True)
