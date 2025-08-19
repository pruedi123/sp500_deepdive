import streamlit as st
import pandas as pd
import io

st.title("Data Viewer and Downloader")

def load_data():
    file_path = "data.xlsx"
    df = pd.read_excel(file_path)
    return df

# Load data directly from fixed file path
df = load_data()

# Detect date column
date_col = None
for col in df.columns:
    try:
        pd.to_datetime(df[col])
        date_col = col
        break
    except Exception:
        continue
if date_col is None and 'Date' in df.columns:
    date_col = 'Date'
if date_col is None:
    st.error("No date-like column found in the uploaded file.")
    st.stop()

df[date_col] = pd.to_datetime(df[date_col])
df["Year"] = df[date_col].dt.year
df["Month"] = df[date_col].dt.month
df["Date_Display"] = df[date_col].dt.strftime("%b-%y")
date_display_pos = df.columns.get_loc(date_col) + 1
df.insert(date_display_pos, "Date_Display", df.pop("Date_Display"))

# Sidebar for filtering
st.sidebar.header("Filter Data")

years = sorted(df['Year'].unique())
months = sorted(df['Month'].unique())

def get_default_index(values, default_value):
    try:
        return values.index(default_value)
    except ValueError:
        return 0

begin_year = st.sidebar.selectbox("Begin Year", years, index=get_default_index(years, 2000))
end_year = st.sidebar.selectbox("End Year", years[::-1], index=get_default_index(years[::-1], 2025))

begin_month = st.sidebar.selectbox("Begin Month", months, index=get_default_index(months, 1))
end_month = st.sidebar.selectbox("End Month", months[::-1], index=get_default_index(months[::-1], 7))

# Filter data based on selection
filtered_df = df[
    (df['Year'] >= begin_year) & (df['Year'] <= end_year) &
    (df['Month'] >= begin_month) & (df['Month'] <= end_month)
]

st.write(f"Showing data from {begin_year}-{begin_month} to {end_year}-{end_month}")
st.dataframe(filtered_df)

# Download filtered data
def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='FilteredData')
    processed_data = output.getvalue()
    return processed_data

excel_data = to_excel(filtered_df)

st.download_button(
    label="Download filtered data as Excel",
    data=excel_data,
    file_name='filtered_data.xlsx',
    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
)
