import streamlit as st
import pandas as pd

# Load with datetime parsing
df = pd.read_csv("market_data_clean.csv", parse_dates=["Date"])

# Streamlit app title and description
st.title("S&P 500 Market Data Deep Dive")
st.write(
    "Explore S&P 500 market data by selecting a custom date range below. "
    "Use the sidebar to pick your start and end months/years."
)

# Sidebar inputs for date range
st.sidebar.header("Select Date Range")
min_date = df["Date"].min()
max_date = df["Date"].max()

default_begin = min_date.strftime("%Y-%m")
default_end = max_date.strftime("%Y-%m")

begin = st.sidebar.text_input("Start (YYYY-MM)", value=default_begin)
end = st.sidebar.text_input("End (YYYY-MM)", value=default_end)

# Convert to full YYYY-MM-DD by forcing the first of the month
try:
    begin_date = pd.to_datetime(begin + "-01")
    end_date = pd.to_datetime(end + "-01")
except Exception:
    st.error("Invalid date format. Please use YYYY-MM.")
    st.stop()

# Filter the dataframe
mask = (df["Date"] >= begin_date) & (df["Date"] <= end_date)
df_filtered = df.loc[mask]

st.dataframe(df_filtered)