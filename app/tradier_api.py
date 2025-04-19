# ===============================
# 🛰 tradier_api.py
# ===============================
import requests
import yfinance as yf
import numpy as np
import pandas as pd
from config import TRADIER_HEADERS, BASE_URL


def get_expirations(symbol):
    url = f"{BASE_URL}/expirations"
    params = {"symbol": symbol, "includeAllRoots": "true", "strikes": "false"}
    res = requests.get(url, headers=TRADIER_HEADERS, params=params)
    return res.json()["expirations"]["date"]


def get_option_chain(symbol, expiration):
    url = f"{BASE_URL}/chains"
    params = {"symbol": symbol, "expiration": expiration, "greeks": "true"}
    res = requests.get(url, headers=TRADIER_HEADERS, params=params)
    return res.json().get("options", {}).get("option", [])


def get_current_price(symbol):
    try:
        return yf.Ticker(symbol).info.get("regularMarketPrice", 0)
    except:
        return 0


def get_historical_volatility(symbol):
    try:
        hist = yf.Ticker(symbol).history(period="30d")["Close"]
        returns = np.log(hist / hist.shift(1)).dropna()
        return np.std(returns) * np.sqrt(252)
    except:
        return None
