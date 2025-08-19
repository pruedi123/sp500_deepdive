


import streamlit as st
import pandas as pd

# Load the CSV
df = pd.read_csv("market_data_clean.csv")

# Ensure the Date column is parsed
df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
df = df.dropna(subset=["Date"]).sort_values("Date").reset_index(drop=True)

# Build list of available YYYY-MM strings
available_months = sorted(df["Date"].dt.strftime("%Y-%m").unique())

# Sidebar selectors for begin and end
st.sidebar.header("Select Date Range")
begin = st.sidebar.selectbox("Begin Date", available_months, index=0)
end = st.sidebar.selectbox("End Date", available_months, index=len(available_months)-1)

# Output selected and all dates
st.write("**Begin Date Selected:**", begin)
st.write("**End Date Selected:**", end)
st.write("**All Available Dates:**")
st.write(available_months)