import streamlit as st
import pandas as pd
import io

st.title("Data Viewer and Downloader")

def load_data(uploaded_file):
    if uploaded_file is None:
        st.warning("Please upload an Excel file.")
        st.stop()
    df = pd.read_excel(uploaded_file)
    return df

uploaded_file = st.file_uploader("Upload Excel file", type=["xlsx"])
df = load_data(uploaded_file)

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

# Sidebar for filtering
st.sidebar.header("Filter Data")

years = df['Year'].unique()
months = df['Month'].unique()

begin_year = st.sidebar.selectbox("Begin Year", sorted(years))
end_year = st.sidebar.selectbox("End Year", sorted(years, reverse=True))

begin_month = st.sidebar.selectbox("Begin Month", sorted(months))
end_month = st.sidebar.selectbox("End Month", sorted(months, reverse=True))

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
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='FilteredData')
        writer.save()
    processed_data = output.getvalue()
    return processed_data

excel_data = to_excel(filtered_df)

st.download_button(
    label="Download filtered data as Excel",
    data=excel_data,
    file_name='filtered_data.xlsx',
    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
)
