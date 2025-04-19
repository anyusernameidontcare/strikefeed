import streamlit as st
import pandas as pd
import numpy as np
import requests
import datetime
import pytz
import yfinance as yf

# Tradier API setup
TRADIER_TOKEN = "YOUR_TRADIER_TOKEN"  # Replace with your real token
TRADIER_HEADERS = {
    "Authorization": f"Bearer {TRADIER_TOKEN}",
    "Accept": "application/json"
}

# Cache to store last market data fallback
cached_data = {}

# --- Utility Functions ---

def is_market_open():
    now = datetime.datetime.now(pytz.timezone("US/Eastern"))
    if now.weekday() >= 5:
        return False
    market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)
    return market_open <= now <= market_close

def get_next_fridays(n=4):
    today = datetime.date.today()
    fridays = []
    while len(fridays) < n:
        today += datetime.timedelta(days=1)
        if today.weekday() == 4:
            fridays.append(today.strftime("%Y-%m-%d"))
    return fridays

def fetch_option_chain(symbol, expiration):
    url = f"https://api.tradier.com/v1/markets/options/chains?symbol={symbol}&expiration={expiration}&greeks=true"
    response = requests.get(url, headers=TRADIER_HEADERS)
    if response.status_code != 200:
        return None
    data = response.json()
    return data.get("options", {}).get("option", [])

def fetch_hv(symbol):
    try:
        df = yf.download(symbol, period="1mo")
        returns = df['Close'].pct_change().dropna()
        hv = np.std(returns) * np.sqrt(252)
        return round(hv, 4)
    except:
        return None

def calculate_score(option, hv):
    try:
        iv = float(option.get("greeks", {}).get("iv", 0))
        delta = abs(float(option.get("greeks", {}).get("delta", 0)))
        bid = float(option.get("bid", 0))
        ask = float(option.get("ask", 0))

        if not all([iv, hv, bid, ask]):
            return None

        midpoint = (bid + ask) / 2
        spread = ask - bid
        spread_pct = spread / midpoint if midpoint else 1

        iv_hv_ratio = iv / hv if hv else 0
        delta_score = 1 - abs(delta - 0.4)  # sweet spot near 0.4
        efficiency = bid / midpoint if midpoint else 0

        score = (
            (1 / iv_hv_ratio) * 35 +     # lower IV/HV is better
            (1 - spread_pct) * 25 +      # tighter spread is better
            delta_score * 20 +           # ideal delta near 0.4
            efficiency * 20              # good bid vs midpoint
        )

        return round(min(max(score, 0), 100), 2)
    except:
        return None

def get_data(symbol, expiration):
    hv = fetch_hv(symbol)
    options = fetch_option_chain(symbol, expiration)
    rows = []

    if not options:
        return []

    for opt in options:
        score = calculate_score(opt, hv)
        row = {
            "Type": opt.get("option_type"),
            "Strike": opt.get("strike"),
            "Bid": opt.get("bid"),
            "Ask": opt.get("ask"),
            "Delta": opt.get("greeks", {}).get("delta"),
            "IV": opt.get("greeks", {}).get("iv"),
            "Score": score
        }
        rows.append(row)
    return rows

# --- Streamlit UI ---

st.set_page_config(layout="wide")
st.markdown("<h1 style='text-align:center;'>📈 StrikeFeed</h1>", unsafe_allow_html=True)
st.markdown(f"<p style='text-align:center;'>Last updated: {datetime.datetime.now().strftime('%I:%M:%S %p')}</p>", unsafe_allow_html=True)

# Market status
if is_market_open():
    st.markdown("<p style='color:green; float:right;'>✔ Market Open</p>", unsafe_allow_html=True)
else:
    st.markdown("<p style='color:gold; float:right;'>🌙 After Hours</p>", unsafe_allow_html=True)

# User inputs
symbols = ["AAPL", "TSLA", "NVDA", "AMD", "MSFT", "SPY"]
symbol = st.selectbox("🔍 Search Ticker", symbols)

expirations = get_next_fridays()
expiration = st.selectbox("Expiration Date", expirations)

# Load data
rows = []
if is_market_open():
    rows = get_data(symbol, expiration)
    if rows:
        cached_data[(symbol, expiration)] = rows
else:
    rows = cached_data.get((symbol, expiration), [])

# Display table
df = pd.DataFrame(rows)
if not df.empty:
    df["Score"] = df["Score"].apply(lambda x: f"{x}%" if pd.notnull(x) else "—")

    def color_score(val):
        if val == "—" or pd.isnull(val):
            return ""
        val = float(val.strip('%'))
        if val >= 80:
            return "color: rgb(100,255,100); font-weight: bold;"
        elif val >= 60:
            return "color: rgb(255,225,100); font-weight: bold;"
        else:
            return "color: rgb(255,120,120); font-weight: bold;"

    st.dataframe(
        df.style.applymap(color_score, subset=["Score"]),
        use_container_width=True
    )
else:
    st.info("No data available yet. Try again during market hours.")

st.markdown("<p style='text-align:center;'>StrikeFeed — Powered by Tradier + Yahoo</p>", unsafe_allow_html=True)
