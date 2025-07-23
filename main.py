import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import datetime
from datetime import datetime as dt

# Configurations
liquid_fund = 600000

mf_codes = {
    "ICICI Balanced Advantage": "INF109K01VX3",
    "UTI Nifty 50 Index": "INF789F1AUV7",
    "Parag Parikh Flexi Cap": "INF879O01018"
}

# Title
st.title("📊 Mutual Fund Portfolio & Dip Strategy Tracker")

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
    inv_date = st.date_input("Investment Date", datetime.date.today())
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

# --- Nifty Dip Strategy ---
nifty = yf.Ticker("^NSEI").history(period="60d")['Close']
latest = nifty.iloc[-1]
peak = nifty[-30:].max()
dip = round((peak - latest) / peak * 100, 2)

st.subheader("🔍 Nifty Watch")
st.write(f"Latest: ₹{latest:.2f}")
st.write(f"30-day Peak: ₹{peak:.2f}")
st.write(f"Dip: {dip}%")
st.metric("Dip Alert", "BUY" if dip >= 5 else "WAIT", delta=f"{dip}%")

# Liquid Fund Logic
dip_trigger = dip >= 5
invest_amt = 100000 if dip_trigger else 0
remaining_liquid = liquid_fund - invest_amt
st.write(f"Liquid Fund Available: ₹{remaining_liquid:,}")

# --- Mutual Fund NAV Section ---
st.subheader("💡 Mutual Fund NAVs & Portfolio")
total_value = 0
data = []
for fund, code in mf_codes.items():
    try:
        resp = requests.get(f"https://api.mfapi.in/mf/{code}")
        nav = float(resp.json()["data"][0]["nav"].replace(",", ""))
        units = 0
        value = units * nav
        gain = value
        data.append([fund, nav, units, value, gain])
        total_value += value
    except:
        data.append([fund, None, None, None, None])

df = pd.DataFrame(data, columns=["Fund", "NAV", "Units", "Value", "Gain"])
st.table(df)

st.subheader("📈 Summary")
st.write(f"Total Portfolio Value: ₹{total_value:,.2f}")
