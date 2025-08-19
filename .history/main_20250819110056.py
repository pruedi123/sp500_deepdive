import streamlit as st
import pandas as pd

# Load with datetime parsing
df = pd.read_csv("market_data_clean.csv", parse_dates=["Date"])
# Force datetimes, drop bad rows, and sort
df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
df = df.dropna(subset=["Date"]).sort_values("Date").reset_index(drop=True)

# Show the detected data coverage so user knows what months are available
_data_min = df["Date"].min()
_data_max = df["Date"].max()
st.caption(f"Data coverage: {_data_min.strftime('%Y-%m')} → {_data_max.strftime('%Y-%m')}")

# Streamlit app title and description
st.title("S&P 500 Market Data Deep Dive")
st.write(
    "Explore S&P 500 market data by selecting a custom date range below. "
    "Use the sidebar to pick your start and end months/years."
)

st.sidebar.header("Select Date Range")
# Build list of available YYYY-MM values in the data, sorted and unique
available_months = sorted(df["Date"].dt.strftime("%Y-%m").unique())

# Desired defaults
default_begin = "2000-01"
default_end = "2025-07"

# Warn if requested defaults are not present in the dataset
if default_begin not in available_months:
    st.warning(f"Default begin {default_begin} not in dataset. Using earliest available: {available_months[0]}")
if default_end not in available_months:
    st.warning(f"Default end {default_end} not in dataset. Using latest available: {available_months[-1]}")

# Initialize session state with defaults (only on first run)
if "begin_month" not in st.session_state:
    st.session_state.begin_month = default_begin if default_begin in available_months else available_months[0]
if "end_month" not in st.session_state:
    st.session_state.end_month = default_end if default_end in available_months else available_months[-1]

# Optional: a quick reset button to put defaults back
if st.sidebar.button("Reset to defaults"):
    st.session_state.begin_month = default_begin if default_begin in available_months else available_months[0]
    st.session_state.end_month = default_end if default_end in available_months else available_months[-1]

# Sidebar selectors use session_state-backed keys so defaults apply
begin = st.sidebar.selectbox("Start (YYYY-MM)", options=available_months, key="begin_month")
end = st.sidebar.selectbox("End (YYYY-MM)", options=available_months, key="end_month")

# Convert to full YYYY-MM-DD by forcing the first of the month
try:
    begin_date = pd.to_datetime(begin + "-01")
    end_date = pd.to_datetime(end + "-01")
except Exception:
    st.error("Invalid date format. Please use YYYY-MM.")
    st.stop()
# Ensure begin_date <= end_date
if begin_date > end_date:
    begin_date, end_date = end_date, begin_date

# Filter the dataframe
mask = (df["Date"] >= begin_date) & (df["Date"] <= end_date)
df_filtered = df.loc[mask].sort_values("Date").reset_index(drop=True)

st.dataframe(df_filtered)

# Display Composite at start and end of period
if not df_filtered.empty:
    composite_start = df_filtered["Composite"].iloc[0]
    composite_end = df_filtered["Composite"].iloc[-1]
    st.write(f"**Composite at Start:** {composite_start}")
    st.write(f"**Composite at End:** {composite_end}")

# --- Bear markets & recessions in selected range ---
# Load event datasets (dates parsed)
bears = pd.read_csv("bear_markets_clean.csv", parse_dates=["Start Date", "End Date"]) 
recessions = pd.read_csv("recessions_clean.csv", parse_dates=["Begin Date", "End Date"]) 

# Count overlapping bear markets: event overlaps window if it starts before window end AND ends after window start
bear_count = bears[(bears["End Date"] >= begin_date) & (bears["Start Date"] <= end_date)].shape[0]

# Count overlapping recessions using the same overlap rule
recession_count = recessions[(recessions["End Date"] >= begin_date) & (recessions["Begin Date"] <= end_date)].shape[0]

st.write(f"**Number of Bear Markets in Range:** {bear_count}")
st.write(f"**Number of Recessions in Range:** {recession_count}")