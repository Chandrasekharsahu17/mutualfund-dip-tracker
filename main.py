import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import datetime

# Configurations
liquid_fund = 600000
sip_amt = 50000
sip_start = datetime.date(2024, 7, 1)
sip_months = 18

mf_codes = {
    "ICICI Balanced Advantage": "INF109K01VX3",
    "UTI Nifty 50 Index": "INF789F1AUV7",
    "Parag Parikh Flexi Cap": "INF879O01018"
}

# Title
st.title("📊 Mutual Fund Portfolio & Dip Strategy Tracker")

# Fetch Nifty
nifty = yf.Ticker("^NSEI").history(period="60d")['Close']
latest = nifty.iloc[-1]
peak = nifty[-30:].max()
dip = round((peak - latest)/peak * 100, 2)

st.subheader("🔍 Nifty Watch")
st.write(f"Latest: ₹{latest:.2f}")
st.write(f"30-day Peak: ₹{peak:.2f}")
st.write(f"Dip: {dip}%")
st.metric("Dip Alert", "BUY" if dip >= 5 else "WAIT", delta=f"{dip}%")

# SIP Progress
st.subheader("📆 SIP Tracker")
months_done = min((datetime.date.today().year - sip_start.year)*12 + datetime.date.today().month - sip_start.month, sip_months)
sip_invested = months_done * sip_amt
st.write(f"{months_done} of {sip_months} months completed")
st.write(f"SIP Invested: ₹{sip_invested:,}")

# Liquid Fund Logic
dip_trigger = dip >= 5
if dip_trigger:
    invest_amt = 100000
else:
    invest_amt = 0
remaining_liquid = liquid_fund - invest_amt
st.write(f"Liquid Fund Available: ₹{remaining_liquid:,}")

# Fetch NAVs
st.subheader("💡 Mutual Fund NAVs & Portfolio")
total_value = 0
data = []
for fund, code in mf_codes.items():
    try:
        resp = requests.get(f"https://api.mfapi.in/mf/{code}")
        nav = float(resp.json()["data"][0]["nav"].replace(",", ""))
        units = sip_invested / nav
        value = units * nav
        gain = value - sip_invested
        data.append([fund, nav, units, value, gain])
        total_value += value
    except:
        data.append([fund, None, None, None, None])

df = pd.DataFrame(data, columns=["Fund", "NAV", "Units", "Value", "Gain"])
st.table(df)

st.subheader("📈 Summary")
st.write(f"Total Invested (SIP): ₹{sip_invested:,}")
st.write(f"Total Portfolio Value: ₹{total_value:,.2f}")
st.write(f"Unrealized Gain/Loss: ₹{total_value - sip_invested:,.2f}")

