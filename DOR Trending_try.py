import streamlit as st
import pandas as pd
import os

# =========================
# Setup
# =========================
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

uploaded_files = st.file_uploader(
    "Upload Daily Operation Report (TBC DOR)",
    type=["xlsx"],
    accept_multiple_files=True
)

# =========================
# PROCESS MULTIPLE FILES
# =========================
if uploaded_files:

    progress = st.progress(0)
    total_files = len(uploaded_files)

    for idx, uploaded_file in enumerate(uploaded_files):

        try:
            dor_sheet = pd.read_excel(uploaded_file, sheet_name="TBC DOR", header=None)
            summary_sheet = pd.read_excel(uploaded_file, sheet_name="Summary", header=None)

            # ---- Extract Dates ----
            start_date = pd.to_datetime(dor_sheet.at[2, 3], format="%d %B %Y", errors="coerce")
            closing_date = pd.to_datetime(dor_sheet.at[2, 5], format="%d %B %Y", errors="coerce")

            if pd.isna(start_date) or pd.isna(closing_date):
                st.warning(f"{uploaded_file.name} skipped (invalid date format)")
                continue

            closing_date = str(closing_date.date())

            # ---- Extract Gas Nom ----
            gas_nom = summary_sheet.at[1, 3]

            # ---- Extract Field Summary ----
            total_gas = dor_sheet.at[72, 7]
            total_cond = dor_sheet.at[73, 14]
            co2_content = dor_sheet.at[78, 14]
            total_flare = dor_sheet.at[97, 6]

            # ---- Remove duplicate summary date ----
            summary_df = summary_df[summary_df["Date"] != closing_date]

            new_summary = pd.DataFrame([{
                "Date": closing_date,
                "Gas Nom": gas_nom,
                "Total Gas Closing": total_gas,
                "Total Condensate Closing": total_cond,
                "CO2 Content": co2_content,
                "Total Flare": total_flare
            }])

            summary_df = pd.concat([summary_df, new_summary], ignore_index=True)

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
                block["Date"] = closing_date

                return block

            tbdr = extract_well_block(32, 48, "TBDR")
            lhdp = extract_well_block(51, 55, "LHDP")
            mldp = extract_well_block(59, 65, "MLDP")

            new_wells = pd.concat([tbdr, lhdp, mldp], ignore_index=True)

            # ---- Remove duplicate wells for same date ----
            if not well_df.empty:
                well_df = well_df[
                    ~(
                        (well_df["Date"] == closing_date) &
                        (well_df["Well Name"].isin(new_wells["Well Name"]))
                    )
                ]

            well_df = pd.concat([well_df, new_wells], ignore_index=True)

            st.success(f"{uploaded_file.name} processed successfully.")

        except Exception as e:
            st.error(f"Error processing {uploaded_file.name}: {e}")

        progress.progress((idx + 1) / total_files)

    # ---- Save after ALL files processed ----
    summary_df.to_csv(summary_file, index=False)
    well_df.to_csv(well_file, index=False)

# =========================
# DAILY SUMMARY TABLE
# =========================
st.subheader("Daily Field Summary History")
if not summary_df.empty:
    st.dataframe(summary_df.sort_values("Date"), use_container_width=True)

# =========================
# WELL HISTORY BY DATE
# =========================
st.subheader("Well Historical Data")

if not well_df.empty:

    available_dates = sorted(well_df["Date"].unique())
    selected_date = st.selectbox("Select Date", available_dates[::-1])

    filtered_wells = well_df[well_df["Date"] == selected_date]
    st.dataframe(filtered_wells.sort_values("Group"), use_container_width=True)

# =========================
# WELL STATUS SUMMARY
# =========================
st.subheader("Well Status Summary")

if not well_df.empty:

    status_df = well_df.copy()
    status_df["Date"] = pd.to_datetime(status_df["Date"])

    latest_date = status_df["Date"].max()
    latest_status = status_df[status_df["Date"] == latest_date]

    shutin_df = status_df[
        status_df["Status @0600 hrs"].str.lower().str.contains("shut", na=False)
    ]

    last_shutin = (
        shutin_df.sort_values("Date")
        .groupby("Well Name")
        .tail(1)[["Well Name", "Date"]]
    )

    last_shutin = last_shutin.rename(columns={"Date": "Last Shut-In Date"})

    well_status_summary = latest_status.merge(
        last_shutin,
        on="Well Name",
        how="left"
    )

    well_status_summary["Last Shut-In Date"] = well_status_summary[
        "Last Shut-In Date"
    ].dt.strftime("%Y-%m-%d")

    st.dataframe(
        well_status_summary[
            ["Well Name", "Group", "Status @0600 hrs", "Last Shut-In Date"]
        ].sort_values("Group"),
        use_container_width=True
    )

# =========================
# TREND CHART
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

# =========================
# DATA RESET (ADMIN)
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
