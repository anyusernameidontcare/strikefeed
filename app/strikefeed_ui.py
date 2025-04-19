import streamlit as st
import pandas as pd
import numpy as np
import requests
import yfinance as yf
import datetime

# ===============================
# 🔐 Tradier API Configuration
# ===============================
TRADIER_TOKEN = "OiteBPyAfIXoXsE1F0yoUV5pKddR"
TRADIER_HEADERS = {
    "Authorization": f"Bearer {TRADIER_TOKEN}",
    "Accept": "application/json"
}
BASE_URL = "https://api.tradier.com/v1/markets/options"

# ===============================
# 📈 Ticker List
# ===============================
TICKERS = ["AAPL", "TSLA", "MSFT", "NVDA", "SPY"]

# ===============================
# 🧠 Data Functions
# ===============================
def get_expirations(symbol):
    res = requests.get(f"{BASE_URL}/expirations", headers=TRADIER_HEADERS, params={"symbol": symbol})
    return res.json()["expirations"]["date"]

def get_option_chain(symbol, expiration):
    res = requests.get(f"{BASE_URL}/chains", headers=TRADIER_HEADERS, params={"symbol": symbol, "expiration": expiration, "greeks": "true"})
    return res.json()["options"]["option"]

def get_current_price(symbol):
    return yf.Ticker(symbol).info.get("regularMarketPrice", 0)

def get_hv(symbol):
    try:
        hist = yf.Ticker(symbol).history(period="30d")["Close"]
        returns = np.log(hist / hist.shift(1)).dropna()
        return np.std(returns) * np.sqrt(252)
    except:
        return None

def calculate_score(opt, hv):
    try:
        greeks = opt.get("greeks", {})
        iv = greeks.get("iv")
        delta = abs(greeks.get("delta", 0))
        bid = opt.get("bid", 0)
        ask = opt.get("ask", 0)
        if not iv or not hv or iv == 0 or ask == 0:
            return None
        iv_hv_ratio = iv / hv
        spread_pct = (ask - bid) / ask if ask else 1
        efficiency = bid / ask if ask else 0
        delta_score = 1 - abs(delta - 0.4)
        score = (1 / iv_hv_ratio) * 40 + (1 - spread_pct) * 30 + delta_score * 20 + efficiency * 10
        return round(score, 1)
    except:
        return None

# ===============================
# 🚀 Streamlit UI
# ===============================
st.set_page_config(layout="wide")
st.markdown("<h2 style='text-align:center;'>⚡ StrikeFeed</h2>", unsafe_allow_html=True)

symbol = st.selectbox("Ticker", TICKERS)
expirations = get_expirations(symbol)
expiration = st.selectbox("Expiration", expirations)
current_price = get_current_price(symbol)
st.markdown(f"<p style='text-align:center;'>Current Price: ${current_price:.2f}</p>", unsafe_allow_html=True)

options = get_option_chain(symbol, expiration)
hv = get_hv(symbol)

calls = [o for o in options if o["option_type"] == "call" and o.get("bid", 0) > 0]
puts = [o for o in options if o["option_type"] == "put" and o.get("bid", 0) > 0]

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

show_raw = st.checkbox("Show Raw Score Inputs (IV, HV, Delta)", value=False)
df = pd.DataFrame(rows)

if not show_raw:
    df = df[["Call Bid", "Call Ask", "Call Score", "Strike", "Put Bid", "Put Ask", "Put Score"]]

# Display styled table
st.dataframe(
    df.style.set_properties(**{
        'text-align': 'center',
        'font-size': '16px'
    }),
    use_container_width=True
)

# Always-on Score Key
st.markdown("""
    <div style='position: fixed; bottom: 16px; left: 16px; background: #111; padding: 10px 15px; border-radius: 8px; color: white; font-size: 12px;'>
    <b>🧠 Score Key</b><br>
    • IV/HV Ratio × 40<br>
    • Spread Efficiency × 30<br>
    • Delta Strength × 20<br>
    • Bid/Ask Efficiency × 10
    </div>
""", unsafe_allow_html=True)
