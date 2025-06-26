import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import date
import base64

st.set_page_config(page_title="Project M Trading Dashboard", layout="wide")

# add background logo with 50% opacity
def add_logo_background(png_file):
    """Embed logo as background image for the app with semi-transparent overlay."""
    with open(png_file, "rb") as img:
        encoded = base64.b64encode(img.read()).decode()
    st.markdown(
        f"""
        <style>
        .stApp {{
            position: relative;
            z-index: 1;
        }}
        .stApp::before {{
            content: "";
            position: fixed;
            top: 0;
            left: 0;
            bottom: 0;
            right: 0;
            background-image: url(data:image/png;base64,{encoded});
            background-repeat: no-repeat;
            background-position: center;
            background-size: contain;
            opacity: 0.25;
            z-index: 0;
            pointer-events: none;
        }}
        .main .block-container {{
            background-color: rgba(0, 0, 0, 0.6);
            padding: 2rem;
            border-radius: 12px;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

add_logo_background("Mueller Logo.png")

plt.style.use("dark_background")

# —— CONFIG ——
FILE_PATH = "Updated_Dataset_with_Signals_Ranked.csv"
INITIAL_INVEST = 50_000
CONTRIB_AMOUNT = 3_000
CONTRIB_FREQ = 22
MANUAL_EXIT_DATE = pd.Timestamp("2024-06-27")
HOLD_DAYS = 25
EARLIEST_CHANGE_DATE = pd.Timestamp("2025-06-20")

# —— LOAD DATA ——
@st.cache_data
def load_prices(fp):
    df = pd.read_csv(fp)
    df["Date"] = pd.to_datetime(df["Date"])
    for col in ["Price", "Open"]:
        df[col] = pd.to_numeric(
            df[col].astype(str).str.replace(r"[$,]", "", regex=True), errors="coerce"
        )
    return df.sort_values("Date")

df_sorted = load_prices(FILE_PATH)
date_index = df_sorted["Date"].unique()

# —— BACKTEST ——
@st.cache_data
def run_backtest(df):
    cash, contrib_ctr = INITIAL_INVEST, 0
    portfolio, trades, equity_curve = [], [], []
    trade_history = []

    for i, curr_date in enumerate(date_index):
        contrib_ctr += 1
        if contrib_ctr == CONTRIB_FREQ:
            cash += CONTRIB_AMOUNT
            contrib_ctr = 0

        if curr_date == MANUAL_EXIT_DATE:
            for pos in portfolio[:]:
                px = df.loc[(df["Company"] == pos["company"]) & (df["Date"] == curr_date), "Price"]
                if px.empty:
                    continue
                px = px.iloc[0]
                profit = (px - pos["buy_price"]) * pos["shares_bought"]
                cash += pos["shares_bought"] * px
                trades.append(profit > 0)
                trade_history.append(dict(company=pos["company"], date=curr_date, action="sell", price=px))
            portfolio.clear()

        todays_rows = df[df["Date"] == curr_date]
        for _, row in todays_rows.iterrows():
            if row["30 Day Buy Signal"] == 1 and cash > 0 and i + 1 < len(date_index):
                nxt = df[(df["Company"] == row["Company"]) & (df["Date"] == date_index[i + 1])]
                if nxt.empty:
                    continue
                next_open = nxt.iloc[0]["Open"]
                qty = (cash * 0.30) / next_open
                if qty >= 1:
                    invest = qty * next_open
                    cash -= invest
                    buy_date = date_index[i + 1]
                    sell_date = (date_index[i + HOLD_DAYS] if i + HOLD_DAYS < len(date_index) else None)
                    portfolio.append(dict(company=row["Company"], buy_date=buy_date, sell_date=sell_date,
                                          shares_bought=qty, buy_price=next_open))
                    trade_history.append(dict(company=row["Company"], date=buy_date, action="buy", price=next_open))

        for pos in portfolio[:]:
            if pos["sell_date"] is not None and curr_date == pos["sell_date"]:
                px = df.loc[(df["Company"] == pos["company"]) & (df["Date"] == pos["sell_date"]), "Price"]
                if px.empty:
                    continue
                px = px.iloc[0]
                profit = (px - pos["buy_price"]) * pos["shares_bought"]
                cash += pos["shares_bought"] * px
                trades.append(profit > 0)
                trade_history.append(dict(company=pos["company"], date=curr_date, action="sell", price=px))
                portfolio.remove(pos)

        pv = 0
        for pos in portfolio:
            cur_px = df.loc[(df["Company"] == pos["company"]) & (df["Date"] == curr_date), "Price"]
            if not cur_px.empty:
                pv += pos["shares_bought"] * cur_px.iloc[0]
        equity_curve.append(cash + pv)

    total_contrib = INITIAL_INVEST + CONTRIB_AMOUNT * (len(date_index) // CONTRIB_FREQ)
    final_val = equity_curve[-1]
    roi = (final_val - total_contrib) / total_contrib * 100
    win_rate = (sum(trades) / len(trades) * 100) if trades else 0

    last_date = date_index[-1]
    rows = []
    for pos in portfolio:
        last_px = df.loc[(df["Company"] == pos["company"]) & (df["Date"] == last_date), "Price"]
        if last_px.empty:
            continue
        last_px = last_px.iloc[0]
        pl_val = (last_px - pos["buy_price"]) * pos["shares_bought"]
        pl_pct = (last_px - pos["buy_price"]) / pos["buy_price"] * 100
        if pos["sell_date"] is not None:
            days_remaining = (pos["sell_date"] - last_date).days
        else:
            days_held = (last_date - pos["buy_date"]).days
            days_remaining = HOLD_DAYS - days_held
        rows.append({
            "Company": pos["company"],
            "Shares": round(pos["shares_bought"], 2),
            "Buy Date": pos["buy_date"].date(),
            "Buy Price": round(pos["buy_price"], 2),
            "Current Price": round(last_px, 2),
            "P/L $": round(pl_val, 2),
            "P/L %": round(pl_pct, 2),
            "Days Remaining": days_remaining
        })
    open_df = pd.DataFrame(rows)

    trades_df = pd.DataFrame(trade_history)
    return (
        pd.Series(equity_curve, index=date_index),
        round(final_val, 2),
        round(roi, 2),
        round(win_rate, 2),
        open_df,
        trades_df,
    )

(
    series_vals,
    final_val,
    roi,
    win_rate,
    open_df,
    trade_df,
) = run_backtest(df_sorted)

# —— DASHBOARD ——
st.title("📈 Project M – Virtual Portfolio")
st.subheader(f"Today's Date: {date.today().isoformat()}")

c1, c2, c3 = st.columns(3)
c1.metric("Final Portfolio Value", f"${final_val:,.2f}")
c2.metric("ROI", f"{roi:.2f}%")
c3.metric("Win Rate", f"{win_rate:.2f}%")

# --- PORTFOLIO CHANGE METRIC ---
timeframe_options = {"Weekly": 7, "Monthly": 30, "Yearly": 365}
sel_col, metric_col = st.columns([1, 2])
selected_tf = sel_col.selectbox("Change Period", list(timeframe_options.keys()))
days = timeframe_options[selected_tf]
candidate_idx = len(series_vals) - (days + 1) if len(series_vals) > days else 0
try:
    limit_idx = series_vals.index.get_loc(EARLIEST_CHANGE_DATE)
except KeyError:
    limit_idx = 0
start_idx = max(candidate_idx, limit_idx)
start_val = series_vals.iloc[start_idx]
change = series_vals.iloc[-1] - start_val
change_pct = (change / start_val * 100) if start_val != 0 else 0
metric_col.metric(f"{selected_tf} Change", f"${change:,.2f}", f"{change_pct:.2f}%")

# --- COMPANY DROPDOWN ---
trade_counts = trade_df[trade_df["action"] == "buy"]["company"].value_counts()
options = ["All Companies"] + [f"{c} ({trade_counts[c]})" for c in trade_counts.index]
selected_label = st.selectbox("Select Company", options)
selected_company = None if selected_label == "All Companies" else selected_label.split(" (", 1)[0]

st.subheader("Portfolio Value Over Time")
fig, ax = plt.subplots(figsize=(10, 4))
fig.patch.set_alpha(0)
ax.set_facecolor((0, 0, 0, 0.8))
if selected_company is None:
    ax.plot(series_vals.index, series_vals.values, color="#00BFFF", linewidth=2)
    ax.set_ylabel("Total Portfolio Value ($)", color="white")
else:
    history = df_sorted[df_sorted["Company"] == selected_company]
    ax.plot(history["Date"], history["Price"], color="#00BFFF", linewidth=2, label=selected_company)
    comp_trades = trade_df[trade_df["company"] == selected_company]
    buys = comp_trades[comp_trades["action"] == "buy"]
    sells = comp_trades[comp_trades["action"] == "sell"]
    if not buys.empty:
        ax.scatter(buys["date"], buys["price"], marker="^", color="green", s=80, label="Buy")
    if not sells.empty:
        ax.scatter(sells["date"], sells["price"], marker="v", color="red", s=80, label="Sell")
    ax.legend()
    ax.set_ylabel("Price ($)", color="white")
ax.set_xlabel("Date", color="white")
ax.tick_params(colors="white")
ax.grid(alpha=0.3, color="gray")
for spine in ax.spines.values():
    spine.set_color("white")
st.pyplot(fig, clear_figure=True)

st.subheader("Open Positions")
if open_df.empty:
    st.info("No active trades.")
else:
    table_col, graph_col = st.columns(2)

    with table_col:
        def colour(val):
            if isinstance(val, (int, float)):
                if val > 0:
                    return "color:green;"
                if val < 0:
                    return "color:red;"
            return ""

        styled = open_df.style.applymap(colour, subset=["P/L $", "P/L %"]).format(precision=2)
        st.write(styled.to_html(index=False), unsafe_allow_html=True)

    with graph_col:
        fig2, ax2 = plt.subplots(figsize=(6, 4))
        fig2.patch.set_alpha(0)
        ax2.set_facecolor((0, 0, 0, 0.8))
        for _, row in open_df.iterrows():
            start = pd.to_datetime(row["Buy Date"])
            history = df_sorted[
                (df_sorted["Company"] == row["Company"]) & (df_sorted["Date"] >= start)
            ]
            pct_change = (history["Price"] - row["Buy Price"]) / row["Buy Price"] * 100
            ax2.plot(history["Date"], pct_change, label=row["Company"])

        ax2.set_xlabel("Date", color="white")
        ax2.set_ylabel("Price Change (%)", color="white")
        ax2.tick_params(colors="white", rotation=45)
        ax2.grid(alpha=0.3, color="gray")
        for spine in ax2.spines.values():
            spine.set_color("white")
        ax2.legend()
        st.pyplot(fig2, clear_figure=True)
