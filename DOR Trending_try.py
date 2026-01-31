import streamlit as st
import pandas as pd
import os

# --- Folder setup ---
if not os.path.exists("uploads"):
    os.makedirs("uploads")
if not os.path.exists("data"):
    os.makedirs("data")

# --- Load historical data ---
summary_file = "data/summary_data.csv"
well_file = "data/well_data.csv"

if os.path.exists(summary_file):
    summary_df = pd.read_csv(summary_file)
else:
    summary_df = pd.DataFrame(columns=["Date", "Total Gas Closing", "Total Condensate Closing", "CO2 Content", "Total Flare"])

if os.path.exists(well_file):
    well_df = pd.read_csv(well_file)
else:
    well_df = pd.DataFrame()

# --- File upload ---
st.title("Tangga Barat Gas Field - Daily Surveillance")
uploaded_file = st.file_uploader("Upload Daily Operation Report", type=["xlsx"])

if uploaded_file:
    # Save raw upload
    upload_path = f"uploads/{uploaded_file.name}"
    with open(upload_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    # Read the specified sheet
    sheet = pd.read_excel(uploaded_file, sheet_name="TBC DOR", header=None)  # header=None to use exact row numbers

    # --- Extract summary data ---
    total_gas = sheet.at[72, 7]        # H73 → row 72, column 7 (0-indexed)
    total_cond = sheet.at[73, 14]      # O74 → row 73, column 14
    co2_content = sheet.at[78, 14]     # O79 → row 78, column 14
    total_flare = sheet.at[97, 6]      # G98 → row 97, column 6

    # Display summary
    st.subheader("Summary Metrics")
    st.write(f"**Total Gas Closing:** {total_gas}")
    st.write(f"**Total Condensate Closing:** {total_cond}")
    st.write(f"**CO2 Content (Metering):** {co2_content}")
    st.write(f"**Total HP/LP Flare:** {total_flare}")

    # Append summary to CSV
    new_summary = pd.DataFrame([{
        "Date": pd.Timestamp.today().strftime("%Y-%m-%d"),
        "Total Gas Closing": total_gas,
        "Total Condensate Closing": total_cond,
        "CO2 Content": co2_content,
        "Total Flare": total_flare
    }])
    summary_df = pd.concat([summary_df, new_summary], ignore_index=True)
    summary_df.to_csv(summary_file, index=False)

    # --- Extract TBDR Well Status ---
    well_data = sheet.loc[30:, [1,3,4,5,6,7,8,9,10,11,12,13]]  # Columns B-N → 1-13 (0-indexed)
    well_data.columns = ["Well No.","SITHP (kPa)","Status@0600Hrs","WELL MSFR %","FTHP (kPa)","FTHT (°C)",
                         "Bean Size (/64”)","(%) Choke Opening","Gas Rate (mmscfd)","Condy (Sm3/d)","Water (Sm3/d)","REMARKS"]
    
    # Display Well Status
    st.subheader("TBDR Well Status")
    st.dataframe(well_data)

    # Append/update well data with date
    well_data["Date"] = pd.Timestamp.today().strftime("%Y-%m-%d")
    well_df = pd.concat([well_df, well_data], ignore_index=True)
    well_df.to_csv(well_file, index=False)

# --- Trending ---
st.subheader("Trending of Total Gas Closing")
if not summary_df.empty:
    st.line_chart(summary_df.set_index("Date")["Total Gas Closing"])
