import streamlit as st
import pandas as pd
import numpy as np
import requests
import datetime
import yfinance as yf

# ===========================
# 🔐 Tradier API Config
# ===========================
TRADIER_TOKEN = "OiteBPyAfIXoXsE1F0yoUV5pKddR"
TRADIER_HEADERS = {
    "Authorization": f"Bearer {TRADIER_TOKEN}",
    "Accept": "application/json"
}
BASE_URL = "https://api.tradier.com/v1/markets/options"

# ===========================
# 📊 Ticker List (trimmed)
# ===========================
TICKERS = [
    "AAPL", "MSFT", "TSLA", "NVDA", "SPY", "QQQ", "AMD", "META", "GOOGL", "AMZN"
]

# ===========================
# 📈 Helper Functions
# ===========================
def fetch_expirations(symbol):
    url = f"{BASE_URL}/expirations"
    params = {"symbol": symbol}
    r = requests.get(url, headers=TRADIER_HEADERS, params=params)
    return r.json().get("expirations", {}).get("date", [])

def fetch_option_chain(symbol, expiration):
    url = f"{BASE_URL}/chains"
    params = {"symbol": symbol, "expiration": expiration, "greeks": "true"}
    r = requests.get(url, headers=TRADIER_HEADERS, params=params)
    return r.json().get("options", {}).get("option", [])

def fetch_hv(symbol):
    try:
        hist = yf.Ticker(symbol).history(period="30d")["Close"]
        returns = hist.pct_change().dropna()
        return np.std(returns) * np.sqrt(252)
    except:
        return None

def fetch_price(symbol):
    try:
        return yf.Ticker(symbol).info.get("regularMarketPrice", 0)
    except:
        return 0

def calculate_score(opt, hv):
    try:
        iv = opt.get("greeks", {}).get("iv", 0)
        delta = abs(opt.get("greeks", {}).get("delta", 0))
        bid = opt.get("bid", 0)
        ask = opt.get("ask", 0)

        if None in [iv, hv] or hv == 0 or iv == 0:
            return None

        iv_hv_ratio = iv / hv
        spread = ask - bid
        spread_pct = spread / ask if ask else 1
        efficiency = bid / ((bid + ask) / 2) if (bid + ask) else 0
        delta_score = 1 - abs(delta - 0.4)

        score = (
            (1 / iv_hv_ratio) * 40 +
            (1 - spread_pct) * 25 +
            delta_score * 20 +
            efficiency * 15
        )
        return round(min(max(score, 1), 100), 1)
    except:
        return None

def color_score(val):
    if val is None:
        return "color: lightgray"
    elif val >= 80:
        return "color: #44ff44"
    elif val >= 60:
        return "color: #facc15"
    else:
        return "color: #ff5f5f"

# ===========================
# 🧠 Streamlit Layout
# ===========================
st.set_page_config(layout="wide")
st.markdown("<h2 style='text-align:center;'>⚡ StrikeFeed</h2>", unsafe_allow_html=True)

symbol = st.selectbox("Select Ticker", TICKERS)
exp_list = fetch_expirations(symbol)
expiration = st.selectbox("Expiration", exp_list[:4]) if exp_list else None

if expiration:
    chain = fetch_option_chain(symbol, expiration)
    price = fetch_price(symbol)
    hv = fetch_hv(symbol)

    calls = [o for o in chain if o.get("option_type") == "call"]
    puts = [o for o in chain if o.get("option_type") == "put"]
    strikes = sorted(set(o.get("strike") for o in chain if o.get("strike")))

    atm_strike = min(strikes, key=lambda x: abs(x - price))
    range_strikes = [s for s in strikes if abs(s - atm_strike) <= 15]

    rows = []
    for strike in range_strikes:
        call = next((c for c in calls if c.get("strike") == strike), {})
        put = next((p for p in puts if p.get("strike") == strike), {})

        row = {
            "Call Bid": call.get("bid", "—"),
            "Call Ask": call.get("ask", "—"),
            "Call Score": calculate_score(call, hv),
            "Strike": strike,
            "Put Bid": put.get("bid", "—"),
            "Put Ask": put.get("ask", "—"),
            "Put Score": calculate_score(put, hv)
        }
        rows.append(row)

    df = pd.DataFrame(rows)

    def style_row(row):
        return [
            "color: green" if i in ["Call Bid", "Put Bid"] else
            "color: red" if i in ["Call Ask", "Put Ask"] else
            color_score(row[i]) if "Score" in i else ""
            for i in row.index
        ]

    st.markdown(f"<p style='text-align:center;'>Current Price: ${price:.2f}</p>", unsafe_allow_html=True)
    st.dataframe(
        df.style.apply(style_row, axis=1),
        use_container_width=True
    )
else:
    st.warning("No expiration data available.")
