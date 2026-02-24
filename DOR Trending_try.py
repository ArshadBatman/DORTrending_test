import streamlit as st
import pandas as pd
import os

# --- Folder setup ---
os.makedirs("uploads", exist_ok=True)
os.makedirs("data", exist_ok=True)

summary_file = "data/summary_data.csv"
well_file = "data/well_data.csv"

# =========================
# Load Historical Data
# =========================
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

if os.path.exists(well_file):
    well_df = pd.read_csv(well_file, dtype={"Date": str})
else:
    well_df = pd.DataFrame()

# =========================
# UI
# =========================
st.title("Tangga Barat Gas Field – Daily Surveillance")
uploaded_file = st.file_uploader("Upload Daily Operation Report (TBC DOR)", type=["xlsx"])

if uploaded_file:

    dor_sheet = pd.read_excel(uploaded_file, sheet_name="TBC DOR", header=None)
    summary_sheet = pd.read_excel(uploaded_file, sheet_name="Summary", header=None)

    # =========================
    # Extract Dates
    # =========================
    start_date = pd.to_datetime(dor_sheet.at[2, 3], format="%d %B %Y", errors="coerce")
    closing_date = pd.to_datetime(dor_sheet.at[2, 5], format="%d %B %Y", errors="coerce")

    if pd.isna(start_date) or pd.isna(closing_date):
        st.error("Invalid Date format in D3 or F3")
        st.stop()

    start_date = start_date.date()
    closing_date = closing_date.date()

    st.info(f"DOR Period: {start_date} 0600Hrs → {closing_date} 0600Hrs")

    # =========================
    # Extract Gas Nom
    # =========================
    gas_nom = summary_sheet.at[1, 3]  # D2

    # =========================
    # Extract Field Summary
    # =========================
    total_gas = dor_sheet.at[72, 7]
    total_cond = dor_sheet.at[73, 14]
    co2_content = dor_sheet.at[78, 14]
    total_flare = dor_sheet.at[97, 6]

    st.subheader(f"Summary Metrics (Closing {closing_date})")
    st.metric("Gas Nomination", gas_nom)
    st.metric("Total Gas Closing", total_gas)

    # =========================
    # Save Daily Summary
    # =========================
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

    # =========================
    # WELL EXTRACTION FUNCTION
    # =========================
    def extract_well_block(start_row, end_row, group_name):
        block = dor_sheet.iloc[start_row:end_row, 1:14].copy()

        block.columns = [
            "Well Name",
            "Flowing Hours",
            "SITHP (kPa)",
            "Status @0600 hrs",
            "Well MSFR%",
            "FTHP (kPa)",
            "FTHT (°C)",
            "Bean Size (/64”)",
            "(%) Choke Opening",
            "Gas Rate (mmscfd)",
            "Condy (Sm3/d)",
            "Water (Sm3/d)",
            "Remarks"
        ]

        block = block.dropna(subset=["Well Name"])
        block["Group"] = group_name
        block["Date"] = str(closing_date)

        return block

    # =========================
    # Extract All Well Groups
    # =========================
    tbdr_wells = extract_well_block(32, 48, "TBDR")
    lhdp_wells = extract_well_block(51, 55, "LHDP")
    mldp_wells = extract_well_block(59, 65, "MLDP")

    new_wells = pd.concat([tbdr_wells, lhdp_wells, mldp_wells], ignore_index=True)

    # =========================
    # Save Well Data (No Duplicates per Date + Well)
    # =========================
    if not well_df.empty:
        well_df = well_df[
            ~(
                (well_df["Date"] == str(closing_date)) &
                (well_df["Well Name"].isin(new_wells["Well Name"]))
            )
        ]

    well_df = pd.concat([well_df, new_wells], ignore_index=True)
    well_df.to_csv(well_file, index=False)

    st.success("Daily summary & well data saved successfully.")

# =========================
# Historical Summary Table
# =========================
st.subheader("Daily Field Summary History")
if not summary_df.empty:
    st.dataframe(summary_df.sort_values("Date"), use_container_width=True)

# =========================
# Well Historical Table
# =========================
st.subheader("Well Historical Data")
if not well_df.empty:
    st.dataframe(well_df.sort_values(["Date", "Group"]), use_container_width=True)

# =========================
# Trend Chart
# =========================
st.subheader("Field Production Trend")

if not summary_df.empty:
    trend_df = summary_df.copy()
    trend_df["Date"] = pd.to_datetime(trend_df["Date"], format="%Y-%m-%d")
    trend_df = trend_df.sort_values("Date")

    metrics = [
        "Gas Nom",
        "Total Gas Closing",
        "Total Condensate Closing",
        "CO2 Content",
        "Total Flare"
    ]

    selected_metrics = st.multiselect(
        "Select metrics",
        metrics,
        default=["Gas Nom", "Total Gas Closing"]
    )

    if selected_metrics:
        trend_df["Date_str"] = trend_df["Date"].dt.strftime("%Y-%m-%d")
        st.line_chart(trend_df.set_index("Date_str")[selected_metrics])
