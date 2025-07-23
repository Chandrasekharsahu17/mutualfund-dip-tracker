import streamlit as st
import pandas as pd
import requests
import yfinance as yf
from datetime import datetime
import os
import plotly.express as px

st.set_page_config(page_title="MF Tracker", layout="centered")

# ---------- Setup ----------
CSV_FILE = "portfolio.csv"

st.markdown("<h1 style='text-align:center; color:#0099FF;'>\ud83d\udcca Mutual Fund Portfolio Tracker</h1>", unsafe_allow_html=True)
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
st.markdown("### \u2795 Add Investment")
with st.form("mf_form"):
    selected_fund = st.selectbox("Select Mutual Fund", fund_choices, index=0)
    units = st.number_input("Units Purchased", min_value=0.0001, step=0.01, format="%.4f")
    submit = st.form_submit_button("Add")

# --- Fetch latest NAV ---
def fetch_latest_nav(code):
    try:
        url = f"https://api.mfapi.in/mf/{code}"
        r = requests.get(url).json()
        return float(r['data'][0]['nav'].replace(",", ""))
    except:
        return None

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

# --- Handle Form Submission ---
if submit:
    fund_name, amfi_code = selected_fund
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
        st.success(f"\u2705 Added {units:.4f} units of {fund_name} @ \u20b9{nav}")
    else:
        st.error("\u274c Couldn't fetch NAV. Try again.")

# --- Load and Display Investments ---
df = load_portfolio()

if not df.empty:
    st.markdown("---")
    st.markdown("### \ud83d\udcbc Your Portfolio")

    df["Latest NAV"] = df["AMFI Code"].apply(fetch_latest_nav)
    df["Current Value"] = (df["Latest NAV"] * df["Units"]).round(2)
    df["P/L"] = (df["Current Value"] - df["Amount"]).round(2)

    st.markdown("### \ud83d\udccb Portfolio Table")
    st.dataframe(df)

    # Delete options
    st.markdown("### \ud83d\uddd1\ufe0f Remove an Entry")
    for idx, row in df.iterrows():
        col1, col2 = st.columns([6, 1])
        with col1:
            st.write(f"{row['Date']} | {row['Fund']} | Units: {row['Units']} | \u20b9{row['Amount']}")
        with col2:
            if st.button("Delete", key=f"del_{idx}"):
                df = df.drop(index=idx).reset_index(drop=True)
                df.to_csv(CSV_FILE, index=False)
                st.success("\u2705 Entry deleted!")
                st.experimental_rerun()

    total_amt = df["Amount"].sum()
    total_val = df["Current Value"].sum()
    gain = df["P/L"].sum()

    st.markdown("---")
    st.markdown("### \ud83d\udcc8 Summary")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Invested", f"\u20b9{total_amt:,.2f}")
    col2.metric("Current Value", f"\u20b9{total_val:,.2f}", delta=f"\u20b9{gain:,.2f}")
    if total_amt > 0:
        col3.metric("Net Gain/Loss", f"\u20b9{gain:,.2f}", delta=f"{(gain / total_amt) * 100:.2f}%")
    else:
        col3.metric("Net Gain/Loss", "\u20b90.00")

    # --- Charts ---
    st.markdown("## \ud83e\udd67 Allocation by Fund")
    fig_pie = px.pie(df, names="Fund", values="Current Value", hole=0.4)
    st.plotly_chart(fig_pie, use_container_width=True)

    st.markdown("## \ud83d\udcca Profit / Loss by Fund")
    fig_bar = px.bar(df, x="Fund", y="P/L", color="P/L", title="Fund-wise P/L")
    st.plotly_chart(fig_bar, use_container_width=True)

    # --- NAV Trend ---
    st.markdown("## \ud83d\udcc8 NAV Trend (Last 30 Days)")
    funds_in_portfolio = df["Fund"].unique().tolist()
    selected_nav_fund = st.selectbox("Select a fund", funds_in_portfolio)
    selected_code = df[df["Fund"] == selected_nav_fund]["AMFI Code"].iloc[0]

    def fetch_nav_history(amfi_code):
        try:
            url = f"https://api.mfapi.in/mf/{amfi_code}"
            r = requests.get(url).json()
            data = r['data'][:30]
            nav_df = pd.DataFrame(data)
            nav_df['nav'] = nav_df['nav'].astype(float)
            nav_df['date'] = pd.to_datetime(nav_df['date'])
            return nav_df.sort_values("date")
        except:
            return pd.DataFrame()

    nav_history = fetch_nav_history(selected_code)
    if not nav_history.empty:
        fig_line = px.line(nav_history, x="date", y="nav", title=f"NAV Trend: {selected_nav_fund}", markers=True)
        st.plotly_chart(fig_line, use_container_width=True)
    else:
        st.warning("Could not fetch NAV history.")

# --- Nifty Dip Strategy ---
st.markdown("---")
st.markdown("### \ud83d\udcc9 Nifty 50 Dip Strategy")
try:
    nifty = yf.Ticker("^NSEI").history(period="60d")["Close"]
    latest = nifty.iloc[-1]
    peak = nifty[-30:].max()
    dip = round((peak - latest) / peak * 100, 2)

    st.write(f"\ud83d\udccd Latest Nifty: \u20b9{latest:.2f}")
    st.write(f"\ud83d\udcc8 30-day Peak: \u20b9{peak:.2f}")
    st.write(f"\ud83d\udd3b Dip from Peak: {dip}%")

    signal = "\u2705 BUY" if dip >= 5 else "\u23f3 WAIT"
    st.metric("\ud83d\udcca Signal", signal, delta=f"{dip}%", delta_color="inverse")
except:
    st.error("\u274c Could not fetch Nifty data.")
else:
    st.info("No investments yet. Add some using the form above.")
