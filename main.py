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

import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# --- AMFI NAV Fetch ---
@st.cache_data(ttl=86400)  # cache NAV for 1 day
def get_latest_nav(amfi_code):
    url = f'https://www.amfiindia.com/spages/NAVAll.txt'
    r = requests.get(url)
    for line in r.text.splitlines():
        if line.startswith(str(amfi_code)):
            parts = line.split(";")
            try:
                nav = float(parts[-1])
                return nav
            except:
                return None
    return None

# --- Investment Form ---
st.markdown("## 📥 Add New Investment")

with st.form("investment_form"):
    inv_date = st.date_input("Investment Date", datetime.today())
    amount = st.number_input("Amount Invested (₹)", min_value=1.0, step=1000.0)
    amfi_code = st.text_input("AMFI Code (e.g. 120503 for UTI Nifty 50)")
    submit = st.form_submit_button("Add Investment")

# --- Session storage (temporary) ---
if "investments" not in st.session_state:
    st.session_state.investments = []

# --- Process form ---
if submit and amfi_code:
    nav = get_latest_nav(amfi_code)
    if nav:
        units = round(amount / nav, 4)
        st.session_state.investments.append({
            "Date": inv_date.strftime("%Y-%m-%d"),
            "AMFI Code": amfi_code,
            "Amount": amount,
            "NAV": nav,
            "Units": units
        })
        st.success(f"✅ Added investment: ₹{amount} at NAV {nav}")
    else:
        st.error("❌ Could not fetch NAV. Please check AMFI code.")

# --- Display Investments ---
if st.session_state.investments:
    st.markdown("### 💼 Your Investments")
    df = pd.DataFrame(st.session_state.investments)
    
    # Fetch latest NAVs and compute current value
    df["Latest NAV"] = df["AMFI Code"].apply(get_latest_nav)
    df["Current Value"] = (df["Units"] * df["Latest NAV"]).round(2)
    df["Gain/Loss"] = (df["Current Value"] - df["Amount"]).round(2)

    st.dataframe(df)

    total_invested = df["Amount"].sum()
    total_current = df["Current Value"].sum()
    st.markdown(f"**📊 Total Invested**: ₹{total_invested:,.2f}")
    st.markdown(f"**💹 Current Value**: ₹{total_current:,.2f}")
    st.markdown(f"**📈 Net Gain/Loss**: ₹{(total_current - total_invested):,.2f}")


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

