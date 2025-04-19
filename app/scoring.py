# ===============================
# 🧠 scoring.py
# ===============================
def calculate_score(option, hv):
    try:
        greeks = option.get("greeks", {})
        iv = greeks.get("iv")
        delta = abs(greeks.get("delta", 0))
        bid = option.get("bid", 0)
        ask = option.get("ask", 0)

        if not iv or not hv or iv == 0 or ask == 0:
            return None

        iv_hv_ratio = iv / hv
        spread_pct = (ask - bid) / ask if ask else 1
        efficiency = bid / ask if ask else 0
        delta_score = 1 - abs(delta - 0.4)

        score = (
            (1 / iv_hv_ratio) * 40 +
            (1 - spread_pct) * 30 +
            delta_score * 20 +
            efficiency * 10
        )

        return round(min(max(score, 0), 100), 1)
    except:
        return None
