import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import os
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Mutual Fund Tracker", layout="centered")
CSV_FILE = "portfolio.csv"

st.title("📊 Mutual Fund Portfolio Tracker")

# --- Fetch All Funds (AMFI master) ---
@st.cache_data(ttl=86400)
def get_all_funds():
    url = "https://www.amfiindia.com/spages/NAVAll.txt"
    response = requests.get(url)
    funds = []
    for line in response.text.splitlines():
        if ";" in line and line[0].isdigit():
            parts = line.split(";")
            code, name = parts[0], parts[3]
            if name and code:
                funds.append((name.strip(), code.strip()))
    return sorted(funds)

fund_choices = get_all_funds()

# --- Get current NAV ---
def fetch_latest_nav(code):
    try:
        url = f"https://api.mfapi.in/mf/{code}"
        r = requests.get(url).json()
        return float(r['data'][0]['nav'].replace(",", ""))
    except:
        return None

# --- Load CSV ---
def load_portfolio():
    if os.path.exists(CSV_FILE):
        return pd.read_csv(CSV_FILE)
    return pd.DataFrame(columns=["Date", "Fund", "AMFI Code", "Units", "NAV", "Amount"])

# --- Save to CSV ---
def save_to_csv(df):
    df.to_csv(CSV_FILE, index=False)

# --- Add Investment ---
st.markdown("## ➕ Add Investment")
with st.form("add_form"):
    fund_sel = st.selectbox("Select Fund", fund_choices)
    units = st.number_input("Units", min_value=0.0001, step=0.01, format="%.4f")
    avg_nav = st.number_input("NAV (purchase)", min_value=1.0, step=0.1, format="%.2f")
    submitted = st.form_submit_button("Add")

if submitted:
    fund_name, amfi_code = fund_sel
    amount = round(units * avg_nav, 2)
    df = load_portfolio()
    df.loc[len(df)] = [datetime.today().strftime("%Y-%m-%d"), fund_name, amfi_code, units, avg_nav, amount]
    save_to_csv(df)
    st.success(f"✅ Added {units} units of {fund_name} at ₹{avg_nav}")

# --- Load and Display Portfolio ---
df = load_portfolio()

if not df.empty:
    st.markdown("## 💼 Portfolio Overview")

    df["Latest NAV"] = df["AMFI Code"].apply(fetch_latest_nav)
    df["Current Value"] = (df["Units"] * df["Latest NAV"]).round(2)
    df["P/L"] = (df["Current Value"] - df["Amount"]).round(2)

    st.dataframe(df[["Date", "Fund", "Units", "NAV", "Latest NAV", "Amount", "Current Value", "P/L"]])

    # Delete entries
    st.markdown("### 🗑️ Delete an Entry")
    for idx, row in df.iterrows():
        col1, col2 = st.columns([6, 1])
        with col1:
            st.write(f"{row['Date']} | {row['Fund']} | {row['Units']} units @ ₹{row['NAV']}")
        with col2:
            if st.button("Delete", key=f"del_{idx}"):
                df = df.drop(index=idx).reset_index(drop=True)
                save_to_csv(df)
                st.success("✅ Entry deleted.")
                st.experimental_rerun()

    # Summary
    total_inv = df["Amount"].sum()
    total_val = df["Current Value"].sum()
    gain = df["P/L"].sum()

    st.markdown("## 📈 Summary")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Invested", f"₹{total_inv:,.2f}")
    # --- Pie Chart: Fund Allocation by Current Value ---
st.markdown("## 🥧 Allocation by Fund (Current Value)")
fig_pie = px.pie(
    df,
    names="Fund",
    values="Current Value",
    title="Portfolio Allocation",
    hole=0.4
)
st.plotly_chart(fig_pie, use_container_width=True)

# --- Bar Chart: Profit/Loss by Fund ---
st.markdown("## 📊 Profit / Loss by Fund")
fig_bar = px.bar(
    df,
    x="Fund",
    y="P/L",
    color="P/L",
    title="Profit & Loss Overview",
    color_continuous_scale="Tealrose"
)
st.plotly_chart(fig_bar, use_container_width=True)

    col2.metric("Current Value", f"₹{total_val:,.2f}", delta=f"₹{gain:,.2f}")
    col3.metric("Net Gain/Loss", f"₹{gain:,.2f}", delta=f"{(gain/total_inv)*100:.2f}%" if total_inv > 0 else "0.00%")
else:
    st.info("No investments yet. Add one above.")

# --- Nifty Dip Strategy ---
st.markdown("---")
st.markdown("## 📉 Nifty 50 Dip Strategy")
try:
    import yfinance as yf
    nifty = yf.Ticker("^NSEI").history(period="60d")['Close']
    latest = nifty.iloc[-1]
    peak = nifty[-30:].max()
    dip = round((peak - latest) / peak * 100, 2)

    st.write(f"📍 Latest Nifty: ₹{latest:.2f}")
    st.write(f"📈 30-day Peak: ₹{peak:.2f}")
    st.write(f"🔻 Dip: {dip}%")

    st.metric("📊 Signal", "✅ BUY" if dip >= 5 else "⏳ WAIT", delta=f"{dip}%", delta_color="inverse")
except:
    st.warning("⚠️ Could not fetch Nifty data.")
# --- NAV History Trend Chart ---
st.markdown("## 📈 NAV Trend (Past 30 Days)")

# Show dropdown of only funds in portfolio
funds_in_portfolio = df["Fund"].unique().tolist()
selected_nav_fund = st.selectbox("Select a fund to view NAV trend", funds_in_portfolio)

# Get AMFI Code for the selected fund
selected_code = df[df["Fund"] == selected_nav_fund]["AMFI Code"].iloc[0]

# Fetch last 30 NAVs
def fetch_nav_history(amfi_code):
    try:
        url = f"https://api.mfapi.in/mf/{amfi_code}"
        r = requests.get(url).json()
        data = r['data'][:30]  # Last 30 days
        nav_df = pd.DataFrame(data)
        nav_df['nav'] = nav_df['nav'].astype(float)
        nav_df['date'] = pd.to_datetime(nav_df['date'])
        return nav_df.sort_values("date")
    except:
        return pd.DataFrame()

nav_history = fetch_nav_history(selected_code)

# Plot line chart
if not nav_history.empty:
    fig_line = px.line(
        nav_history,
        x="date",
        y="nav",
        title=f"NAV Trend: {selected_nav_fund}",
        markers=True
    )
    st.plotly_chart(fig_line, use_container_width=True)
else:
    st.warning("Could not fetch NAV history.")
