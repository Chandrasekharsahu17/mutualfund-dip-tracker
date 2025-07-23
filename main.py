import streamlit as st
import pandas as pd
import requests
import yfinance as yf
from datetime import datetime
import os

st.set_page_config(page_title="MF Tracker", layout="centered")

# ---------- Setup ----------
CSV_FILE = "portfolio.csv"

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

# --- Investment Form (Simplified) ---
st.markdown("### ➕ Add Investment")
with st.form("mf_form"):
    selected_fund = st.selectbox("Select Mutual Fund", fund_choices, index=0)
    units = st.number_input("Units Purchased", min_value=0.0001, step=0.01, format="%.4f")
    submit = st.form_submit_button("Add")

# --- Save to CSV ---
def save_to_csv(new_entry):
    if os.path.exists(CSV_FILE):
        df = pd.read_csv(CSV_FILE)
        df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
    else:
        df = pd.DataFrame([new_entry])
    df.to_csv(CSV_FILE, index=False)

# --- Load from CSV ---
def load_portfolio():
    if os.path.exists(CSV_FILE):
        return pd.read_csv(CSV_FILE)
    return pd.DataFrame(columns=["Date", "Fund", "AMFI Code", "NAV", "Units", "Amount"])

# --- Save to CSV ---
def save_to_csv(new_entry):
    if os.path.exists(CSV_FILE):
        df = pd.read_csv(CSV_FILE)
        df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
    else:
        df = pd.DataFrame([new_entry])
    df.to_csv(CSV_FILE, index=False)

# --- Handle Form Submission ---
if submit:
    fund_name = selected_fund[0]
    amfi_code = selected_fund[1]
    nav = fetch_latest_nav(amfi_code)
    if nav:
        amount = round(nav * units, 2)
        new_entry = {
            "Date": datetime.today().strftime("%Y-%m-%d"),
            "Fund": fund_name,
            "AMFI Code": amfi_code,
            "NAV": nav,
            "Units": round(units, 4),
            "Amount": amount
        }
        save_to_csv(new_entry)
        st.success(f"✅ Added {units:.4f} units of {fund_name} @ ₹{nav}")
    else:
        st.error("❌ Couldn't fetch NAV. Try again.")

# --- Load and Display Investments ---
df = load_portfolio()

if not df.empty:
    st.markdown("---")
    st.markdown("### 💼 Your Portfolio")

    # Fetch Latest NAVs
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

    # Show full data table
    st.markdown("### 📋 Portfolio Details")
    st.dataframe(df)

    # Add delete options below table
    st.markdown("### 🗑️ Remove an Entry")
    for idx, row in df.iterrows():
        col1, col2 = st.columns([6, 1])
        with col1:
            st.write(f"{row['Date']} | {row['Fund']} | Units: {row['Units']} | ₹{row['Amount']}")
        with col2:
            if st.button("Delete", key=f"del_{idx}"):
                df = df.drop(index=idx).reset_index(drop=True)
                df.to_csv(CSV_FILE, index=False)
                st.success("✅ Entry deleted!")
                st.experimental_rerun()

    # Totals & Summary
    total_invested = df["Amount"].sum()
    total_current = df["Current Value"].sum()
    total_gain = df["Gain/Loss"].sum()

    st.markdown("---")
    st.markdown("### 📈 Summary")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Invested", f"₹{total_invested:,.2f}")
    col2.metric("Current Value", f"₹{total_current:,.2f}", delta=f"₹{total_gain:,.2f}")
    col3.metric("Net Gain/Loss", f"₹{total_gain:,.2f}", delta=f"{(total_gain/total_invested)*100:.2f}%")
else:
    st.info("No investments yet. Add some using the form above.")

# --- Nifty Dip Strategy ---
st.markdown("---")
st.markdown("### 📉 Nifty 50 Dip Strategy")
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
except:
    st.error("❌ Could not fetch Nifty data.")
