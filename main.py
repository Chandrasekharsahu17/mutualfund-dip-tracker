import streamlit as st
import pandas as pd
import requests
from datetime import datetime

st.set_page_config(page_title="MF Tracker", layout="centered")

st.markdown("<h1 style='text-align:center; color:#0099FF;'>📊 Mutual Fund Portfolio Tracker</h1>", unsafe_allow_html=True)
st.markdown("Track your mutual fund investments, get latest NAVs and visualize your portfolio in one place.")

# --- Fetch AMFI Mutual Fund List (Cached) ---
@st.cache_data(ttl=86400)
def get_all_funds():
    url = "https://www.amfiindia.com/spages/NAVAll.txt"
    response = requests.get(url)
    fund_list = []
    for line in response.text.splitlines():
        if ";" in line and line[0].isdigit():
            parts = line.split(";")
            code, name = parts[0], parts[3]
            if name and code:
                fund_list.append((f"{name} ({code})", code))
    return sorted(fund_list)

fund_choices = get_all_funds()
import yfinance as yf

st.markdown("---")
st.markdown("### 📉 Nifty 50 Dip Strategy")

# Fetch last 60 days Nifty close data
try:
    nifty = yf.Ticker("^NSEI").history(period="60d")['Close']
    latest = nifty.iloc[-1]
    peak = nifty[-30:].max()
    dip = round((peak - latest)/peak * 100, 2)

    st.write(f"📍 Latest Nifty: ₹{latest:.2f}")
    st.write(f"📈 30-day Peak: ₹{peak:.2f}")
    st.write(f"🔻 Dip from Peak: {dip}%")

    signal = "✅ BUY" if dip >= 5 else "⏳ WAIT"
    st.metric("📊 Signal", signal, delta=f"{dip}%", delta_color="inverse")
except Exception as e:
    st.error("❌ Could not fetch Nifty data.")

# --- Investment Form ---
st.markdown("### 🧾 Add New Investment")
with st.form("mf_form"):
    selected_fund = st.selectbox("Select Mutual Fund", fund_choices, index=0)
    inv_date = st.date_input("Investment Date", datetime.today())
    nav = st.number_input("NAV (at the time of purchase)", min_value=1.0, step=0.1)
    units = st.number_input("Units Purchased", min_value=0.0001, step=0.01, format="%.4f")
    submit = st.form_submit_button("➕ Add Investment")

# --- Initialize session state ---
if "investments" not in st.session_state:
    st.session_state.investments = []

# --- Process Form ---
if submit:
    fund_name, amfi_code = selected_fund.split(" (")
    amfi_code = amfi_code.rstrip(")")
    amount = round(nav * units, 2)
    st.session_state.investments.append({
        "Date": inv_date.strftime("%Y-%m-%d"),
        "Fund": fund_name.strip(),
        "AMFI Code": amfi_code,
        "NAV": nav,
        "Units": round(units, 4),
        "Amount": amount
    })
    st.success(f"✅ Added {units:.4f} units of {fund_name} @ ₹{nav} (₹{amount})")

# --- Display Portfolio ---
if st.session_state.investments:
    st.markdown("---")
    st.markdown("### 💼 Your Portfolio")
    df = pd.DataFrame(st.session_state.investments)

    # Fetch latest NAVs and calculate current value
    def fetch_latest_nav(code):
        try:
            url = f"https://api.mfapi.in/mf/{code}"
            r = requests.get(url).json()
            return float(r['data'][0]['nav'].replace(",", ""))
        except:
            return None

    df["Latest NAV"] = df["AMFI Code"].apply(fetch_latest_nav)
    df["Current Value"] = (df["Latest NAV"] * df["Units"]).round(2)
    df["Gain/Loss"] = (df["Current Value"] - df["Amount"]).round(2)

    st.dataframe(df)

    total_invested = df["Amount"].sum()
    total_current = df["Current Value"].sum()
    total_gain = df["Gain/Loss"].sum()

    st.markdown("### 📈 Summary")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Invested", f"₹{total_invested:,.2f}")
    col2.metric("Current Value", f"₹{total_current:,.2f}", delta=f"₹{total_gain:,.2f}")
    col3.metric("Net Gain/Loss", f"₹{total_gain:,.2f}", delta=f"{(total_gain/total_invested)*100:.2f}%")
else:
    st.info("No investments yet. Add some using the form above.")
