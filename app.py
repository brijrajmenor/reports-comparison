import streamlit as st
import re
import pandas as pd
from datetime import datetime, timedelta

# Custom CSS for professional UI with Poppins font
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600&display=swap');

* {
    font-family: 'Poppins', sans-serif !important;
}

.header {
    color: #2c3e50;
    border-bottom: 1px solid #eaeaea;
    padding-bottom: 10px;
    margin-bottom: 1.5rem;
}

.sidebar .sidebar-content {
    background-color: #f8f9fa;
}

.stButton>button {
    background-color: #4a90e2;
    color: white;
    border-radius: 5px;
    padding: 8px 16px;
    border: none;
    font-weight: 500;
    transition: all 0.3s;
}

.stButton>button:hover {
    background-color: #357abd;
    transform: translateY(-1px);
}

.report-card {
    background: white;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    padding: 20px;
    margin-bottom: 20px;
}

.download-btn {
    margin-top: 15px;
    margin-bottom: 15px;
}
            
/* Prevent content from being hidden behind footer */
.stApp {
    margin-bottom: 50px;
}
.footer {
    position: fixed;
    left: 0;
    bottom: 0;
    width: 100%;
    background-color: #2c3e50;
    color: white;
    text-align: center;
    padding: 10px;
    z-index: 1000;
    font-family: 'Poppins', sans-serif;
}
</style>
            
<div class="footer">
    <div style="display: flex; justify-content: space-evenly; align-items: center;">
        <div style="font-size: 14px;">Developed by Netcreators Automation</div>
        
    
</div>
""", unsafe_allow_html=True)

# App Header
st.header("Netcreators Automation", divider="blue")

# File Upload Section
with st.expander("📁 Upload Data Files", expanded=True):
    col1, col2 = st.columns(2)
    with col1:
        log_file = st.file_uploader("Sensor Log File (.txt)", type=["txt"])
    with col2:
        excel_file = st.file_uploader("Booking Records (.xlsx)", type=["xlsx"])

# Hardcoded year
ANALYSIS_YEAR = 2025

if log_file and excel_file:
    # Process log file
    log_data = log_file.readlines()
    events = []
    for line in log_data:
        line = line.decode("utf-8")
        line = re.sub(r"(Room no\.)(\d+)", r"\1 \2", line)
        
        if "light is ON" in line or "light is OFF" in line:
            parts = line.split("\t")
            timestamp = parts[0].strip()
            room_info = parts[1].strip()
            room_no = room_info.split(" ")[2]
            light_status = "ON" if "ON" in room_info else "OFF"
            events.append((timestamp, room_no, light_status))
    
    log_df = pd.DataFrame(events, columns=["Timestamp", "Room No", "Light Status"])
    log_df["Timestamp"] = pd.to_datetime(log_df["Timestamp"], format="%Y-%m-%d %p %I:%M")

    # Process Excel file with robust date handling
    try:
        excel_df = pd.read_excel(excel_file, sheet_name="Occupancy Statistics", header=3)
        excel_df.columns = excel_df.columns.str.strip()
        
        # Verify required columns exist
        required_cols = ['Room No', 'Arrival Date', 'Time', 'Departure Date', 'Time.1']
        missing_cols = [col for col in required_cols if col not in excel_df.columns]
        if missing_cols:
            st.error(f"Missing required columns: {', '.join(missing_cols)}")
            st.stop()
        
        # Robust date parsing with error handling
        def parse_datetime(date_str, time_str, year):
            try:
                if pd.isna(date_str) or pd.isna(time_str):
                    return pd.NaT
                return pd.to_datetime(
                    f"{date_str} {year} {time_str}",
                    format='%b %d %Y %H:%M',
                    errors='coerce'
                )
            except Exception:
                return pd.NaT
        
        excel_df['Arrival DateTime'] = excel_df.apply(
            lambda x: parse_datetime(x['Arrival Date'], x['Time'], ANALYSIS_YEAR), 
            axis=1
        )
        excel_df['Departure DateTime'] = excel_df.apply(
            lambda x: parse_datetime(x['Departure Date'], x['Time.1'], ANALYSIS_YEAR), 
            axis=1
        )
        
        # Clean data - drop rows with invalid dates
        initial_count = len(excel_df)
        excel_df = excel_df.dropna(subset=['Arrival DateTime', 'Departure DateTime'])
        cleaned_count = len(excel_df)
            
        if excel_df.empty:
            st.error("No valid booking records found after cleaning")
            st.stop()
            
        excel_df = excel_df[['Room No', 'Arrival DateTime', 'Departure DateTime', 'Guest Name']]
        
    except Exception as e:
        st.error(f"Failed to parse Excel file: {str(e)}")
        st.stop()

    # Date filters
    st.sidebar.header("🔍 Filter Options")
    date_col1, date_col2 = st.sidebar.columns(2)
    with date_col1:
        start_date = st.date_input("Start date", value=log_df["Timestamp"].min().date())
    with date_col2:
        end_date = st.date_input("End date", value=log_df["Timestamp"].max().date())
    
    # Room filter
    room_options = log_df["Room No"].unique()
    selected_rooms = st.sidebar.multiselect(
        "Select Rooms", 
        options=room_options, 
        default=room_options
    )
    
    # Filter data
    log_df = log_df[log_df["Room No"].isin(selected_rooms)]
    log_df = log_df[
        (log_df["Timestamp"] >= pd.Timestamp(start_date)) & 
        (log_df["Timestamp"] <= pd.Timestamp(end_date))
    ]

    # Generate light duration report
    light_report = []
    for room in log_df["Room No"].unique():
        room_events = log_df[log_df["Room No"] == room].sort_values("Timestamp")
        on_events = room_events[room_events["Light Status"] == "ON"]
        off_events = room_events[room_events["Light Status"] == "OFF"]
        
        i, j = 0, 0
        while i < len(on_events) and j < len(off_events):
            on_time = on_events.iloc[i]["Timestamp"]
            off_time = off_events.iloc[j]["Timestamp"]
            
            if on_time < off_time:
                duration = (off_time - on_time).total_seconds() / 60
                light_report.append({
                    "Room": room,
                    "Light ON": on_time,
                    "Light OFF": off_time,
                    "Duration (min)": round(duration, 2),
                    "Activity Type": "Housekeeping" if duration < 15 else "Guest"
                })
                i += 1
                j += 1
            else:
                j += 1
    
    if not light_report:
        st.warning("No light activity events found in the selected date range")
        st.stop()
    
    light_report_df = pd.DataFrame(light_report)
    
    # Generate comparison report
    comparison_report = []
    for _, row in light_report_df.iterrows():
        room = row["Room"]
        activity = excel_df[excel_df["Room No"].astype(str) == str(room)]
        
        if activity.empty:
            status = "⚠️ Unregistered"
            discrepancy = "No booking record"
            guest = "N/A"
        else:
            booked_start = activity["Arrival DateTime"].iloc[0]
            booked_end = activity["Departure DateTime"].iloc[0]
            guest = activity["Guest Name"].iloc[0]
            
            if row["Light ON"] < booked_start or row["Light OFF"] > booked_end:
                status = "❌ Mismatch"
                discrepancy = f"Outside booked period ({booked_start.strftime('%Y-%m-%d %H:%M')} to {booked_end.strftime('%Y-%m-%d %H:%M')})"
            else:
                status = "✅ Valid"
                discrepancy = "Within booked period"
        
        comparison_report.append({
            **row.to_dict(),
            "Status": status,
            "Discrepancy": discrepancy,
            "Guest": guest
        })
    
    comparison_df = pd.DataFrame(comparison_report)

    # Display Reports
    st.markdown("### 📊 Light Duration Report")
    st.dataframe(
        light_report_df.style.format({
            "Light ON": lambda x: x.strftime("%Y-%m-%d %H:%M"),
            "Light OFF": lambda x: x.strftime("%Y-%m-%d %H:%M"),
            "Duration (min)": "{:.2f}"
        }),
        height=400
    )

    st.markdown("### 🔍 Occupancy Comparison Report")
    st.dataframe(
        comparison_df.style.format({
            "Light ON": lambda x: x.strftime("%Y-%m-%d %H:%M"),
            "Light OFF": lambda x: x.strftime("%Y-%m-%d %H:%M"),
            "Duration (min)": "{:.2f}"
        }),
        height=400
    )

    # Download Buttons
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            label="📥 Download Light Duration Report",
            data=light_report_df.to_csv(index=False),
            file_name=f"light_duration_report_{start_date}_to_{end_date}.csv",
            mime="text/csv",
            key="light_report"
        )
        
    with col2:
        # Before creating download buttons - clean the symbols
        # Add this before creating the download buttons
        comparison_df['Status'] = comparison_df['Status'].str.replace('❌', '')
        comparison_df['Status'] = comparison_df['Status'].str.replace('✅', '')
        comparison_df['Status'] = comparison_df['Status'].str.replace('⚠️', '')

        # Then create download button with UTF-8 encoding
        st.download_button(
            label="📥 Download Comparison Report",
            data=comparison_df.to_csv(index=False, encoding='utf-8-sig'),
            file_name=f"occupancy_comparison_{start_date}_to_{end_date}.csv",
            mime="text/csv",
            key="comparison_report"
)

else:
    st.info("ℹ️ Please upload both sensor log and booking record files to begin analysis")
