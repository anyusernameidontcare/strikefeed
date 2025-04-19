import streamlit as st
import requests
import pandas as pd
import datetime
import pytz

st.set_page_config(layout="wide")

# ----------------- SETTINGS -----------------
API_KEY = "OiteBPyAfIXoXsE1F0yoUV5pKddR"  # Replace with your actual Tradier API key
TICKERS = [
    "AAPL", "MSFT", "GOOGL", "NVDA", "AMZN", "META", "TSLA", "AMD", "NFLX", "BABA",
    "INTC", "CRM", "PYPL", "UBER", "SHOP", "SQ", "PLTR", "DIS", "NIO", "BIDU",
    "MRNA", "COIN", "ROKU", "FSLR", "ZM", "DKNG", "RBLX", "SNOW", "SOFI", "ABNB",
    "CVNA", "DKS", "FUBO", "TGT", "COST", "HD", "WMT", "LOW", "M", "JWN",
    "CVX", "XOM", "BP", "OXY", "MPC", "PSX", "VLO", "PXD", "EOG", "COP",
    "JPM", "BAC", "WFC", "GS", "MS", "C", "SCHW", "RY", "TD", "USB",
    "PFE", "MRK", "JNJ", "LLY", "BMY", "ABBV", "GILD", "AZN", "AMGN", "BIIB",
    "LUV", "DAL", "UAL", "AAL", "SAVE", "ALK", "RCL", "CCL", "NCLH", "EXPE",
    "BA", "GE", "F", "GM", "TSM", "QCOM", "AVGO", "TXN", "ADI", "MU",
    "SPY", "QQQ", "DIA", "IWM", "XLF", "XLE", "XLK", "ARKK", "TQQQ", "SQQQ"
]

# ----------------- FUNCTIONS -----------------
def fetch_option_chain(ticker):
    headers = {"Authorization": f"Bearer {API_KEY}", "Accept": "application/json"}
    exp_url = f"https://api.tradier.com/v1/markets/options/expirations?symbol={ticker}&includeAllRoots=true&strikes=true"
    exp_res = requests.get(exp_url, headers=headers).json()
    expirations = exp_res.get("expirations", {}).get("date", [])
    if not expirations:
        return None, []
    expiration = expirations[0]
    chain_url = f"https://api.tradier.com/v1/markets/options/chains?symbol={ticker}&expiration={expiration}&greeks=true"
    chain_res = requests.get(chain_url, headers=headers).json()
    options = chain_res.get("options", {}).get("option", [])
    return expiration, options

def fetch_current_price(ticker):
    try:
        url = f"https://api.tradier.com/v1/markets/quotes?symbols={ticker}"
        headers = {"Authorization": f"Bearer {API_KEY}", "Accept": "application/json"}
        data = requests.get(url, headers=headers).json()
        return float(data.get("quotes", {}).get("quote", {}).get("last", 0))
    except:
        return 0

def calculate_score(row):
    try:
        iv_call = row.get("greeks_iv_call", 0)
        iv_put = row.get("greeks_iv_put", 0)
        hv = (iv_call + iv_put) / 2 * 0.8
        ratio = ((iv_call + iv_put) / 2) / hv
        if ratio > 1.2:
            return "High"
        elif ratio > 0.9:
            return "Medium"
        else:
            return "Low"
    except:
        return "—"

def color_score(val):
    color = "green" if val == "High" else "orange" if val == "Medium" else "red" if val == "Low" else "white"
    return f"color: {color}; font-weight: bold"

def build_chain_table(options, current_price):
    df = pd.DataFrame(options)
    df = df.sort_values(by="strike")
    filtered = df[(df.strike >= current_price - 15) & (df.strike <= current_price + 15)]
    calls = filtered[filtered.option_type == "call"].copy()
    puts = filtered[filtered.option_type == "put"].copy()
    merged = pd.merge(calls, puts, on="strike", how="outer", suffixes=("_call", "_put"))
    merged["score"] = merged.apply(lambda row: calculate_score(row), axis=1)
    return pd.DataFrame({
        "Call Bid": merged["bid_call"].fillna("—"),
        "Call Ask": merged["ask_call"].fillna("—"),
        "Strike": merged["strike"].fillna("—"),
        "Put Bid": merged["bid_put"].fillna("—"),
        "Put Ask": merged["ask_put"].fillna("—"),
        "Score": merged["score"].fillna("—")
    })

# ----------------- APP -----------------
st.title("📊 StrikeFeed Options Scanner")
ticker = st.selectbox("Choose Ticker:", TICKERS)
current_price = fetch_current_price(ticker)
st.markdown(f"**Live Price: ${current_price:.2f}**")

expiration, chain = fetch_option_chain(ticker)

if not chain:
    st.warning("No data. Showing placeholder.")
    st.write(pd.DataFrame({"Call Bid": ["—"] * 5, "Call Ask": ["—"] * 5, "Strike": ["—"] * 5, "Put Bid": ["—"] * 5, "Put Ask": ["—"] * 5, "Score": ["—"] * 5}))
else:
    table = build_chain_table(chain, current_price)
    st.dataframe(table.style.applymap(color_score, subset=["Score"]))
