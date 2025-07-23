import streamlit as st
import pandas as pd
import requests
import yfinance as yf
from datetime import datetime
import plotly.express as px
import os

st.set_page_config(page_title="📊 MF Portfolio", layout="wide")

CSV_FILE = "portfolio.csv"

st.title("Mutual Fund Portfolio Tracker")
# ---------------- Fetch AMFI Fund List ----------------
@st.cache_data(ttl=86400)
def get_all_funds():
    url = "https://www.amfiindia.com/spages/NAVAll.txt"
    r = requests.get(url)
    fund_list = []
    for line in r.text.splitlines():
        if ";" in line and line[0].isdigit():
            parts = line.split(";")
            code, name = parts[0], parts[3]
            if code and name:
                fund_list.append((f"{name} ({code})", code))
    return sorted(fund_list)

fund_choices = get_all_funds()

# ---------------- Fetch Latest NAV ----------------
@st.cache_data(ttl=3600)
def fetch_nav(code):
    try:
        res = requests.get(f"https://api.mfapi.in/mf/{code}").json()
        return float(res["data"][0]["nav"].replace(",", ""))
    except:
        return None

# ---------------- Load Portfolio ----------------
def load_portfolio():
    if os.path.exists(CSV_FILE):
        return pd.read_csv(CSV_FILE)
    return pd.DataFrame(columns=["Date", "Fund", "AMFI Code", "Units", "NAV", "Amount"])

# ---------------- Save Portfolio ----------------
def save_portfolio(df):
    df.to_csv(CSV_FILE, index=False)

# ---------------- Add Investment ----------------
st.sidebar.header("➕ Add Investment")
with st.sidebar.form("add_form"):
    fund_sel = st.selectbox("Select Mutual Fund", fund_choices)
    units = st.number_input("Units Bought", min_value=0.0001, step=0.01)
    submit = st.form_submit_button("Add")

if submit:
    fund_name = fund_sel.split(" (")[0]
    amfi_code = fund_sel.split(" (")[1].strip(")")
    nav = fetch_nav(amfi_code)
    if nav:
        amt = round(nav * units, 2)
        new_entry = {
            "Date": datetime.today().strftime("%Y-%m-%d"),
            "Fund": fund_name,
            "AMFI Code": amfi_code,
            "Units": round(units, 4),
            "NAV": nav,
            "Amount": amt
        }
        df = load_portfolio()
        df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
        save_portfolio(df)
        st.success(f"✅ Added {units:.4f} units of {fund_name} @ ₹{nav}")
        st.experimental_rerun()
    else:
        st.error("❌ Couldn't fetch NAV for selected fund.")

# ---------------- Show Portfolio ----------------
df = load_portfolio()

if not df.empty:
    df["Latest NAV"] = df["AMFI Code"].apply(fetch_nav)
    df["Current Value"] = (df["Latest NAV"] * df["Units"]).round(2)
    df["Gain/Loss"] = (df["Current Value"] - df["Amount"]).round(2)

    st.subheader("📋 Portfolio Table")
    st.dataframe(df, use_container_width=True)

    # 🗑️ Delete
    st.subheader("🗑️ Remove an Entry")
    for i, row in df.iterrows():
        col1, col2 = st.columns([6, 1])
        with col1:
            st.write(f"{row['Date']} | {row['Fund']} | Units: {row['Units']} | ₹{row['Amount']}")
        with col2:
            if st.button("Delete", key=f"del_{i}"):
                df = df.drop(index=i).reset_index(drop=True)
                save_portfolio(df)
                st.experimental_rerun()

    # 📈 Summary
    st.subheader("📈 Summary")
    total_amt = df["Amount"].sum()
    total_val = df["Current Value"].sum()
    gain = total_val - total_amt
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Invested", f"₹{total_amt:,.2f}")
    col2.metric("Current Value", f"₹{total_val:,.2f}", delta=f"₹{gain:,.2f}")
    if total_amt > 0:
        col3.metric("Net Gain/Loss", f"₹{gain:,.2f}", delta=f"{(gain/total_amt)*100:.2f}%")
    else:
        col3.metric("Net Gain/Loss", "₹0.00")

    # 🥧 Allocation Pie
    st.subheader("🥧 Allocation by Fund")
    pie = px.pie(df, names="Fund", values="Current Value", title="Fund Allocation")
    st.plotly_chart(pie, use_container_width=True)

    # 📊 Bar Chart - P/L
    st.subheader("📊 Profit / Loss by Fund")
    bar = px.bar(df, x="Fund", y="Gain/Loss", color="Gain/Loss", text="Gain/Loss")
    st.plotly_chart(bar, use_container_width=True)

# ---------------- Nifty Dip Strategy ----------------
st.subheader("📉 Nifty 50 Dip Strategy")
try:
    nifty = yf.Ticker("^NSEI").history(period="60d")['Close']
    latest = nifty.iloc[-1]
    peak = nifty[-30:].max()
    dip = round((peak - latest) / peak * 100, 2)

    st.write(f"📍 Latest Nifty: ₹{latest:.2f}")
    st.write(f"📈 30-day Peak: ₹{peak:.2f}")
    st.write(f"🔻 Dip from Peak: {dip}%")
    signal = "✅ BUY" if dip >= 5 else "⏳ WAIT"
    st.metric("📊 Signal", signal, delta=f"{dip}%", delta_color="inverse")
except:
    st.error("❌ Could not fetch Nifty data.")
