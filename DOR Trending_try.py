import streamlit as st
import pandas as pd
import os

# --- Folder setup ---
os.makedirs("uploads", exist_ok=True)
os.makedirs("data", exist_ok=True)

# --- File paths ---
summary_file = "data/summary_data.csv"
well_file = "data/well_data.csv"

# --- Load historical data ---
if os.path.exists(summary_file):
    summary_df = pd.read_csv(summary_file)
else:
    summary_df = pd.DataFrame(columns=[
        "Date",
        "Total Gas Closing",
        "Total Condensate Closing",
        "CO2 Content",
        "Total Flare"
    ])

if os.path.exists(well_file):
    well_df = pd.read_csv(well_file)
else:
    well_df = pd.DataFrame()

# --- UI ---
st.title("Tangga Barat Gas Field – Daily Surveillance")
uploaded_file = st.file_uploader("Upload Daily Operation Report (TBC DOR)", type=["xlsx"])

if uploaded_file:
    # Save raw upload
    upload_path = f"uploads/{uploaded_file.name}"
    with open(upload_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    # Read Excel
    sheet = pd.read_excel(uploaded_file, sheet_name="TBC DOR", header=None)

    # =========================
    # Extract & validate DOR date
    # =========================
    raw_date = sheet.at[2, 5]  # F3

    dor_date = pd.to_datetime(
        raw_date,
        format="%d %B %Y",   # e.g. 31 January 2026
        errors="coerce"
    )

    if pd.isna(dor_date):
        st.error(f"Invalid DOR Date format in cell F3: {raw_date}")
        st.stop()

    dor_date = dor_date.date()

    # =========================
    # Extract summary metrics
    # =========================
    total_gas = sheet.at[72, 7]        # H73
    total_cond = sheet.at[73, 14]      # O74
    co2_content = sheet.at[78, 14]     # O79
    total_flare = sheet.at[97, 6]      # G98

    # Display summary
    st.subheader(f"Summary Metrics ({dor_date})")
    st.metric("Total Gas Closing", total_gas)
    st.metric("Total Condensate Closing", total_cond)
    st.metric("CO₂ Content (Metering)", co2_content)
    st.metric("Total HP / LP Flare", total_flare)

    # =========================
    # Save summary (date-safe)
    # =========================
    summary_df["Date"] = pd.to_datetime(summary_df["Date"], errors="coerce")

    # Remove existing record for same DOR date
    summary_df = summary_df[summary_df["Date"].dt.date != dor_date]

    new_summary = pd.DataFrame([{
        "Date": dor_date,
        "Total Gas Closing": total_gas,
        "Total Condensate Closing": total_cond,
        "CO2 Content": co2_content,
        "Total Flare": total_flare
    }])

    summary_df = pd.concat([summary_df, new_summary], ignore_index=True)
    summary_df.to_csv(summary_file, index=False)

    # =========================
    # Extract TBDR Well Status
    # =========================
    well_data = sheet.loc[30:, [1,3,4,5,6,7,8,9,10,11,12,13]]
    well_data.columns = [
        "Well No.", "SITHP (kPa)", "Status@0600Hrs", "WELL MSFR %",
        "FTHP (kPa)", "FTHT (°C)", "Bean Size (/64”)",
        "(%) Choke Opening", "Gas Rate (mmscfd)",
        "Condy (Sm3/d)", "Water (Sm3/d)", "REMARKS"
    ]

    # Drop empty wells
    well_data = well_data.dropna(subset=["Well No."])

    # Add date
    well_data["Date"] = dor_date

    # =========================
    # Save well data (deduplicated)
    # =========================
    if not well_df.empty:
        well_df["Date"] = pd.to_datetime(well_df["Date"], errors="coerce").dt.date

        well_df = well_df[
            ~(
                (well_df["Date"] == dor_date) &
                (well_df["Well No."].isin(well_data["Well No."]))
            )
        ]

    well_df = pd.concat([well_df, well_data], ignore_index=True)
    well_df.to_csv(well_file, index=False)

    st.subheader("TBDR Well Status")
    st.dataframe(well_data)

# =========================
# Trending
# =========================
st.subheader("Field Production Trend")

if not summary_df.empty:
    trend_df = summary_df.copy()
    trend_df["Date"] = pd.to_datetime(trend_df["Date"], errors="coerce")
    trend_df = trend_df.dropna(subset=["Date"])
    trend_df = trend_df.sort_values("Date")

    # --- Multi-select metrics to display ---
    metrics = ["Total Gas Closing", "Total Condensate Closing", "CO2 Content", "Total Flare"]
    selected_metrics = st.multiselect(
        "Select metrics to display",
        options=metrics,
        default=["Total Gas Closing"]
    )

    if selected_metrics:
        # Convert date to string for X-axis to remove time
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
    if os.path.exists(well_file):
        os.remove(well_file)
    st.success("All historical data deleted. Please re-upload DOR files.")
    st.stop()

