
import requests
import csv
import datetime
from math import sqrt

# ======== CONFIG ======== #
ACCESS_TOKEN = "eA5AZaGxFGOfVxMqtIS7GAA4ZS7W"
HEADERS = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Accept": "application/json"}
BASE_URL = "https://api.tradier.com/v1"

TICKERS = [
    'SPY', 'QQQ', 'IWM', 'DIA', 'VIX', 'TLT', 'XLF', 'XLK', 'XLE', 'XLV', 'XLY',
    'AAPL', 'TSLA', 'NVDA', 'AMD', 'INTC', 'MSFT', 'GOOGL', 'META', 'CRM', 'AVGO'
]  # Feel free to expand this list

# ======== FUNCTIONS ======== #

def within_28_days(exp_date_str):
    try:
        exp_date = datetime.datetime.strptime(exp_date_str, "%Y-%m-%d").date()
        today = datetime.date.today()
        return 0 < (exp_date - today).days <= 28
    except:
        return False

def get_option_expirations(symbol):
    url = f"{BASE_URL}/markets/options/expirations?symbol={symbol}&includeAllRoots=true&strikes=false"
    response = requests.get(url, headers=HEADERS)
    dates = response.json().get("expirations", {}).get("date", [])
    return [d for d in dates if within_28_days(d)]

def save_csv(data, filename):
    keys = data[0].keys()
    with open(filename, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(data)

# ======== MAIN ENGINE ======== #
def run_strikefeed():
    output = []
    for ticker in TICKERS:
        try:
            expirations = get_option_expirations(ticker)
            for exp in expirations:
                chain_url = f"{BASE_URL}/markets/options/chains?symbol={ticker}&expiration={exp}&greeks=true"
                chain_res = requests.get(chain_url, headers=HEADERS).json()
                options = chain_res.get("options", {}).get("option", [])
                for opt in options:
                    try:
                        greeks = opt.get("greeks", {})
                        iv = greeks.get("iv")
                        delta = greeks.get("delta")
                        if iv is None or delta is None:
                            continue

                        # TEMP: Always append, use dummy score
                        output.append({
                            "Ticker": ticker,
                            "Type": opt["option_type"],
                            "Strike": opt["strike"],
                            "Exp": opt["expiration_date"],
                            "Bid": opt["bid"],
                            "Ask": opt["ask"],
                            "Delta": delta,
                            "IV": iv,
                            "Score": 50
                        })
                    except Exception as e:
                        print(f"Error scoring contract in {ticker}: {e}")
        except Exception as e:
            print(f"Error with {ticker}: {e}")

    if output:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"strikefeed_output_{timestamp}.csv"
        save_csv(output, filename)
        print(f"Saved {len(output)} entries to {filename}")
    else:
        print("No valid contracts found.")

if __name__ == "__main__":
    run_strikefeed()
