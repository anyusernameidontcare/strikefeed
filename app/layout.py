# ===============================
# 🎨 layout.py
# ===============================
import streamlit as st

def render_score_key():
    st.markdown("""
    <div style='position: fixed; bottom: 16px; left: 16px; background: #111; padding: 10px 15px; border-radius: 8px; color: white; font-size: 12px;'>
    <b>🧠 Score Key</b><br>
    • IV / HV Ratio × 40<br>
    • Spread Efficiency × 30<br>
    • Delta Strength × 20<br>
    • Bid / Ask Efficiency × 10
    </div>
    """, unsafe_allow_html=True)

def show_greek_toggle():
    return st.checkbox("Show Raw Greeks + Score Inputs", value=False)

def style_cell(val):
    try:
        val = float(val)
        if val >= 80:
            return "color: #44ff44; text-align: center;"
        elif val >= 60:
            return "color: #facc15; text-align: center;"
        else:
            return "color: #ff4d4d; text-align: center;"
    except:
        return "text-align: center;"
