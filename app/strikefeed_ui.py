import streamlit as st
import pandas as pd
import numpy as np
import datetime
import pytz
import requests
import yfinance as yf

# API Token
TRADIER_TOKEN = "eA5ZaGxFG0fVxMqtIS7GAAA2S7W"  # REPLACE THIS
TRADIER_HEADERS = {
    "Authorization": f"Bearer {TRADIER_TOKEN}",
    "Accept": "application/json"
}

st.set_page_config(page_title="StrikeFeed", layout="wide")
st.markdown("""
    <h1 style='text-align: center;'>📈 StrikeFeed</h1>
    <div style='text-align: center; font-size: 14px;'>Last updated: {} UTC</div>
""".format(datetime.datetime.now(pytz.utc).strftime("%I:%M:%S %p")), unsafe_allow_html=True)

# --- Ticker Search ---
st.markdown("#### 🔍 Search Ticker")
ticker = st.selectbox("", options=["AAPL", "TSLA", "NVDA", "AMD", "MSFT", "AMZN"], label_visibility="collapsed")

# --- Fetch Expirations ---
def get_expirations(symbol):
    url = f"https://api.tradier.com/v1/markets/options/expirations?symbol={symbol}&includeAllRoots=true&strikes=false"
    r = requests.get(url, headers=TRADIER_HEADERS)
    if r.status_code != 200:
        return []
    return r.json()['expirations']['date']

# --- Get All Expirations ---
expirations = get_expirations(ticker)
expirations_df = []
today = datetime.date.today()
for exp in expirations:
    exp_date = datetime.datetime.strptime(exp, "%Y-%m-%d").date()
    dte = (exp_date - today).days
    if 0 <= dte <= 28:
        expirations_df.append({
            "label": f"{dte}D - {exp_date.strftime('%a %b %d')}",
            "value": exp
        })

# --- Expiration Select ---
st.markdown("#### Expiration")
expiration_select = st.selectbox("", options=[e["label"] for e in expirations_df], label_visibility="collapsed")
selected_exp_date = next((e['value'] for e in expirations_df if e['label'] == expiration_select), None)

# --- Fetch Chain ---
def get_option_chain(symbol, expiration):
    url = f"https://api.tradier.com/v1/markets/options/chains?symbol={symbol}&expiration={expiration}&greeks=true"
    r = requests.get(url, headers=TRADIER_HEADERS)
    if r.status_code != 200:
        return []
    return r.json()['options']['option']

chain_data = get_option_chain(ticker, selected_exp_date)

def get_hv(symbol):
    hist = yf.Ticker(symbol).history(period="1mo")
    log_returns = np.log(hist['Close'] / hist['Close'].shift(1)).dropna()
    return log_returns.std() * np.sqrt(252)

hv = get_hv(ticker)

# --- Calculate Score ---
def score_option(row):
    if row['iv'] is None or row['delta'] is None or hv == 0:
        return None
    iv_score = 1 - abs(row['iv'] / hv - 1)
    delta_score = 1 - abs(abs(row['delta']) - 0.5) * 2
    spread = abs(row['ask'] - row['bid']) if row['ask'] and row['bid'] else 1
    spread_score = 1 - min(spread / (row['bid'] + 0.01), 1)
    final_score = (0.5 * iv_score + 0.3 * delta_score + 0.2 * spread_score) * 100
    return round(final_score, 2)

# --- Format Layout ---
calls = []
puts = []
for opt in chain_data:
    entry = {
        'type': opt['option_type'],
        'strike': opt['strike'],
        'bid': opt['bid'],
        'ask': opt['ask'],
        'delta': opt['greeks'].get('delta') if opt['greeks'] else None,
        'iv': opt['greeks'].get('iv') if opt['greeks'] else None,
    }
    entry['score'] = score_option(entry)
    if opt['option_type'] == 'call':
        calls.append(entry)
    else:
        puts.append(entry)

calls_df = pd.DataFrame(calls).set_index("strike")
puts_df = pd.DataFrame(puts).set_index("strike")

# --- Display Table ---
merged_df = pd.concat([
    calls_df[['bid', 'ask']],
    calls_df[['bid', 'ask']].columns.map(lambda x: f"Call {x.title()}"),
    puts_df[['bid', 'ask']],
    puts_df[['bid', 'ask']].columns.map(lambda x: f"Put {x.title()}"),
], axis=1, keys=['Call Bid', 'Call Ask', 'Put Bid', 'Put Ask'])

merged_df['Score'] = calls_df['score']  # just as placeholder, adjust logic if needed

# --- Score Styling ---
def color_score(val):
    if pd.isna(val): return 'color: #999999'
    if val > 75: return 'color: #2ecc71'
    elif val > 60: return 'color: #f1c40f'
    else: return 'color: #e74c3c'

styled = merged_df.style.format("{:.2f}").applymap(color_score, subset=['Score'])

st.dataframe(styled, use_container_width=True)

st.markdown("""
---
<div style='text-align: center; font-size: 13px;'>
    StrikeFeed — Powered by Tradier + Yahoo
</div>
""", unsafe_allow_html=True)
