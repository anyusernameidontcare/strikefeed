import streamlit as st
import pandas as pd
import numpy as np
import requests
import datetime
import pytz
import yfinance as yf

# ───── Tradier Settings ─────
TRADIER_TOKEN = "eA5AZaGxFGOfVxMqtIS7GAA4ZS7W"
TRADIER_HEADERS = {
    "Authorization": f"Bearer {TRADIER_TOKEN}",
    "Accept": "application/json"
}
cache_store = {}

# ───── Utility ─────
def is_market_open():
    now = datetime.datetime.now(pytz.timezone("US/Eastern"))
    if now.weekday() >= 5:
        return False
    return now.time() >= datetime.time(9,30) and now.time() <= datetime.time(16,0)

def get_next_fridays(n=4):
    today = datetime.date.today()
    fridays = []
    while len(fridays) < n:
        today += datetime.timedelta(days=1)
        if today.weekday() == 4:
            fridays.append(today.strftime("%Y-%m-%d"))
    return fridays

def fetch_hv(ticker):
    try:
        df = yf.download(ticker, period="1mo")
        returns = df['Close'].pct_change().dropna()
        return round(np.std(returns) * np.sqrt(252), 4)
    except:
        return None

def fetch_chain(ticker, exp):
    url = f"https://api.tradier.com/v1/markets/options/chains"
    params = {"symbol": ticker, "expiration": exp, "greeks": "true"}
    r = requests.get(url, headers=TRADIER_HEADERS, params=params)
    if r.status_code == 200:
        return r.json().get("options", {}).get("option", [])
    return []

def score_option(opt, hv):
    try:
        iv = float(opt["greeks"]["iv"])
        delta = abs(float(opt["greeks"]["delta"]))
        bid = float(opt["bid"])
        ask = float(opt["ask"])
        mid = (bid + ask) / 2
        spread = (ask - bid) / mid if mid else 1
        iv_hv = iv / hv if hv else 10
        efficiency = bid / mid if mid else 0
        delta_score = 1 - abs(delta - 0.4)

        score = (
            (1 / iv_hv) * 35 +
            (1 - spread) * 25 +
            delta_score * 20 +
            efficiency * 20
        )
        return round(min(max(score, 0), 100), 2)
    except:
        return None

# ───── UI Layout ─────
st.set_page_config(layout="wide")
st.markdown("<h1 style='text-align:center;'>📈 StrikeFeed</h1>", unsafe_allow_html=True)
st.markdown(f"<p style='text-align:center;'>Last updated: {datetime.datetime.now().strftime('%I:%M:%S %p')}</p>", unsafe_allow_html=True)

market_status = "✅ Market Open" if is_market_open() else "🌙 After Hours"
color = "#00e676" if "Open" in market_status else "#facc15"
st.markdown(f"<p style='color:{color}; float:right;'>{market_status}</p>", unsafe_allow_html=True)

tickers = ["AAPL", "TSLA", "NVDA", "MSFT", "SPY"]
ticker = st.selectbox("🔍 Search Ticker", tickers)
expirations = get_next_fridays()
expiration = st.selectbox("Expiration", expirations)

# ───── Pull + Cache Data ─────
key = (ticker, expiration)
hv = fetch_hv(ticker)

options = fetch_chain(ticker, expiration)
if options:
    cache_store[key] = options
else:
    options = cache_store.get(key, [])

# ───── Table Display ─────
rows = []
for opt in options:
    score = score_option(opt, hv)
    rows.append({
        "Type": opt.get("option_type"),
        "Strike": opt.get("strike"),
        "Bid": opt.get("bid"),
        "Ask": opt.get("ask"),
        "Delta": opt.get("greeks", {}).get("delta"),
        "IV": opt.get("greeks", {}).get("iv"),
        "Score": f"{score}%" if score is not None else "—"
    })

df = pd.DataFrame(rows)
if not df.empty:
    def color_score(val):
        if val == "—" or pd.isnull(val): return ""
        val = float(val.strip('%'))
        if val >= 80: return "color: #34d399;"
        elif val >= 60: return "color: #facc15;"
        else: return "color: #f87171;"

    st.dataframe(df.style.applymap(color_score, subset=["Score"]), use_container_width=True)
else:
    st.warning("No data available yet — please try again later.")

st.markdown("<p style='text-align:center;'>StrikeFeed — Powered by Tradier + Yahoo</p>", unsafe_allow_html=True)
