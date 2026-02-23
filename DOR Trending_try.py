import streamlit as st
import pandas as pd
import os

# --- Folder setup ---
os.makedirs("uploads", exist_ok=True)
os.makedirs("data", exist_ok=True)

# --- File path ---
summary_file = "data/summary_data.csv"

# --- Load historical data safely ---
if os.path.exists(summary_file):
    summary_df = pd.read_csv(summary_file, dtype={"Date": str})
else:
    summary_df = pd.DataFrame(columns=[
        "Date",
        "Gas Nom",
        "Total Gas Closing",
        "Total Condensate Closing",
        "CO2 Content",
        "Total Flare"
    ])

# --- UI ---
st.title("Tangga Barat Gas Field – Daily Surveillance")
uploaded_file = st.file_uploader("Upload Daily Operation Report (TBC DOR)", type=["xlsx"])

if uploaded_file:

    upload_path = f"uploads/{uploaded_file.name}"
    with open(upload_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    # =========================
    # Read required sheets
    # =========================
    dor_sheet = pd.read_excel(uploaded_file, sheet_name="TBC DOR", header=None)
    summary_sheet = pd.read_excel(uploaded_file, sheet_name="Summary", header=None)

    # =========================
    # Extract Dates
    # =========================
    raw_start_date = dor_sheet.at[2, 3]   # D3
    raw_closing_date = dor_sheet.at[2, 5] # F3

    start_date = pd.to_datetime(raw_start_date, format="%d %B %Y", errors="coerce")
    closing_date = pd.to_datetime(raw_closing_date, format="%d %B %Y", errors="coerce")

    if pd.isna(start_date) or pd.isna(closing_date):
        st.error("Invalid Date format in D3 or F3")
        st.stop()

    start_date = start_date.date()
    closing_date = closing_date.date()

    st.info(f"DOR Period: {start_date} 0600Hrs → {closing_date} 0600Hrs")

    # =========================
    # Extract Gas Nom (Summary sheet D2)
    # =========================
    gas_nom = summary_sheet.at[1, 3]  # D2

    # =========================
    # Extract Summary Metrics
    # =========================
    total_gas = dor_sheet.at[72, 7]
    total_cond = dor_sheet.at[73, 14]
    co2_content = dor_sheet.at[78, 14]
    total_flare = dor_sheet.at[97, 6]

    st.subheader(f"Summary Metrics (Closing {closing_date})")

    col1, col2 = st.columns(2)
    col1.metric("Gas Nomination", gas_nom)
    col1.metric("Total Gas Closing", total_gas)
    col2.metric("Total Condensate Closing", total_cond)
    col2.metric("Total HP / LP Flare", total_flare)

    st.metric("CO₂ Content (Metering)", co2_content)

    # =========================
    # Save Summary (SAFE STRING DATE)
    # =========================
    summary_df["Date"] = summary_df["Date"].astype(str)
    summary_df = summary_df[summary_df["Date"] != str(closing_date)]

    new_summary = pd.DataFrame([{
        "Date": str(closing_date),
        "Gas Nom": gas_nom,
        "Total Gas Closing": total_gas,
        "Total Condensate Closing": total_cond,
        "CO2 Content": co2_content,
        "Total Flare": total_flare
    }])

    summary_df = pd.concat([summary_df, new_summary], ignore_index=True)
    summary_df.to_csv(summary_file, index=False)

    st.success("Daily summary saved successfully.")

# =========================
# Display Historical Daily Summary Table
# =========================
st.subheader("Daily Field Summary History")

if not summary_df.empty:
    display_df = summary_df.copy()
    display_df = display_df.sort_values("Date")
    st.dataframe(display_df, use_container_width=True)

# =========================
# Trending Section
# =========================
st.subheader("Field Production Trend")

if not summary_df.empty:

    trend_df = summary_df.copy()

    trend_df["Date"] = pd.to_datetime(trend_df["Date"], format="%Y-%m-%d", errors="coerce")
    trend_df = trend_df.dropna(subset=["Date"])
    trend_df = trend_df.sort_values("Date")

    metrics = [
        "Gas Nom",
        "Total Gas Closing",
        "Total Condensate Closing",
        "CO2 Content",
        "Total Flare"
    ]

    selected_metrics = st.multiselect(
        "Select metrics to display",
        options=metrics,
        default=["Total Gas Closing", "Gas Nom"]
    )

    if selected_metrics:
        trend_df["Date_str"] = trend_df["Date"].dt.strftime("%Y-%m-%d")

        st.line_chart(
            trend_df.set_index("Date_str")[selected_metrics]
        )

# =========================
# Data Reset (Admin)
# =========================
st.divider()
st.subheader("⚠️ Data Reset (Admin)")

confirm = st.checkbox("I understand this will delete all historical data")

if confirm and st.button("Delete ALL Historical Data"):
    if os.path.exists(summary_file):
        os.remove(summary_file)
    st.success("All historical data deleted. Please re-upload DOR files.")
    st.stop()
