import streamlit as st
import pandas as pd
import numpy as np
import requests
import datetime
import yfinance as yf

# ============================
# 🔐 Tradier API Config
# ============================
TRADIER_TOKEN = "OiteBPyAfIXoXsE1F0yoUV5pKddR"  # replace with your real token
TRADIER_HEADERS = {
    "Authorization": f"Bearer {TRADIER_TOKEN}",
    "Accept": "application/json"
}
BASE_URL = "https://api.tradier.com/v1/markets/options"

# ============================
# 📈 Ticker Selection
# ============================
TICKERS = [
    "AAPL", "TSLA", "MSFT", "NVDA", "AMD", "META", "GOOGL", "NFLX", "BABA", "BA",
    "SPY", "QQQ", "IWM", "XLF", "XLE", "XLK", "T", "DIS", "PYPL", "COIN",
    "CRM", "CVX", "WMT", "PFE", "UBER", "SOFI", "INTC", "ABNB", "MU", "SQ",
    "SHOP", "SNAP", "JPM", "TSM", "AMZN", "RIVN", "F", "GM", "PLTR", "DKNG",
    "LULU", "NIO", "ENPH", "ROKU", "LYFT", "MARA", "LCID", "RIOT", "WBD", "ETSY",
    "SPOT", "C", "KO", "PEP", "TGT", "QCOM", "MRNA", "ZM", "AAL", "DAL",
    "UAL", "COST", "SBUX", "XOM", "WBA", "GME", "BBBY", "ARKK", "AFRM", "BIDU",
    "TWLO", "DOCU", "NET", "CRWD", "DDOG", "NVAX", "BMY", "MRK", "VZ", "GE",
    "JNJ", "PG", "IBM", "BLNK", "CHPT", "NKE", "GS", "MS", "VRTX", "VRTX",
    "AIG", "LMT", "TMO", "MDT", "BAX", "HCA", "REGN", "BIIB", "VRTX", "VRTX"
]

# ============================
# ⚙️ Utility Functions
# ============================

def get_expirations(symbol):
    url = f"{BASE_URL}/expirations"
    params = {"symbol": symbol, "includeAllRoots": "true", "strikes": "false"}
    res = requests.get(url, headers=TRADIER_HEADERS, params=params)
    return res.json()["expirations"]["date"]

def get_option_chain(symbol, expiration):
    url = f"{BASE_URL}/chains"
    params = {"symbol": symbol, "expiration": expiration, "greeks": "true"}
    res = requests.get(url, headers=TRADIER_HEADERS, params=params)
    return res.json()["options"]["option"]

def get_current_price(symbol):
    ticker = yf.Ticker(symbol)
    return ticker.info.get("regularMarketPrice", None)

def calculate_score(option, hv):
    greeks = option.get("greeks", {})
    iv = greeks.get("iv")
    delta = greeks.get("delta")
    bid = option.get("bid", 0)
    ask = option.get("ask", 0)
    spread = abs(bid - ask)

    if not iv or not hv or iv == 0 or spread == 0:
        return None

    iv_hv_ratio = iv / hv
    efficiency = (bid / ask) if ask != 0 else 0
    base = (1 / iv_hv_ratio) * efficiency * abs(delta or 0)
    return round(min(max(base * 100, 0), 100), 2)

# ============================
# 🚀 Streamlit UI
# ============================

st.set_page_config(page_title="StrikeFeed", layout="wide")
st.markdown("<h1 style='text-align: center;'>⚡ StrikeFeed</h1>", unsafe_allow_html=True)

symbol = st.selectbox("Select Ticker", TICKERS)
expirations = get_expirations(symbol)
expiration = st.selectbox("Expiration", expirations)

current_price = get_current_price(symbol)
st.markdown(f"<div style='text-align: center; font-weight: bold;'>Current Price: ${current_price:.2f}</div>", unsafe_allow_html=True)

options = get_option_chain(symbol, expiration)
hv = np.std([o["greeks"]["iv"] for o in options if o.get("greeks") and o["greeks"].get("iv")])

calls = [o for o in options if o["option_type"] == "call"]
puts = [o for o in options if o["option_type"] == "put"]

calls = [c for c in calls if c["bid"] > 0]
puts = [p for p in puts if p["bid"] > 0]

data = []
for c, p in zip(calls, puts):
    row = {
        "Call Bid": f"{c['bid']:.2f}",
        "Call Ask": f"{c['ask']:.2f}",
        "Call Score": calculate_score(c, hv),
        "Strike": f"{c['strike']:.2f}",
        "Put Bid": f"{p['bid']:.2f}",
        "Put Ask": f"{p['ask']:.2f}",
        "Put Score": calculate_score(p, hv),
    }
    data.append(row)

df = pd.DataFrame(data)

def colorize(val):
    try:
        val = float(val)
        if val > 0:
            return "color: green; text-align: center;"
        elif val < 0:
            return "color: red; text-align: center;"
    except:
        return "text-align: center;"
    return "text-align: center;"

st.dataframe(
    df.style.set_properties(**{
        "text-align": "center",
        "font-size": "16px"
    }).applymap(colorize),
    height=700,
    use_container_width=True
)