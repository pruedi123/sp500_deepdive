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

 # Load bear markets data
bear_df = pd.read_csv("bear_markets_clean.csv")


# Detect date column in bear_df using coercion and 50% non-null threshold
bear_date_col = None
for col in bear_df.columns:
    if pd.api.types.is_numeric_dtype(bear_df[col]):
        # Check if values are large enough to be Excel serial dates
        if bear_df[col].dropna().gt(1000).all():
            try:
                parsed_dates = pd.to_datetime(bear_df[col], origin="1899-12-30", unit="D", errors="coerce")
                if parsed_dates.notna().mean() >= 0.5:
                    bear_date_col = col
                    break
            except Exception:
                continue
    else:
        parsed_dates = pd.to_datetime(bear_df[col], errors="coerce")
        if parsed_dates.notna().mean() >= 0.5:
            bear_date_col = col
            break
if bear_date_col is None and 'Date' in bear_df.columns:
    bear_date_col = 'Date'
if bear_date_col is None:
    st.error("No date-like column found in bear_markets_clean.csv.")
    st.stop()

if pd.api.types.is_numeric_dtype(bear_df[bear_date_col]):
    bear_df[bear_date_col] = pd.to_datetime(bear_df[bear_date_col], origin="1899-12-30", unit="D", errors="coerce")
else:
    bear_df[bear_date_col] = pd.to_datetime(bear_df[bear_date_col], errors="coerce")
bear_df = bear_df.dropna(subset=[bear_date_col])

# Show min/max dates in bear_df for debugging
st.write("Bear markets date range:", bear_df[bear_date_col].min(), "to", bear_df[bear_date_col].max())

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

investment_amount = st.sidebar.number_input("Investment Amount", min_value=10000, max_value=100000, step=10000, value=10000)

# Ensure begin_date and end_date are proper pd.Timestamp
begin_date = pd.Timestamp(begin_year, begin_month, 1)
end_date = pd.Timestamp(end_year, end_month, 1) + pd.offsets.MonthEnd(0)

# Debug output for filter range
st.write("Filter range:", begin_date, "to", end_date)
# Filter data based on complete datetime range
date_mask = (df[date_col] >= begin_date) & (df[date_col] <= end_date)
filtered_df = df[date_mask]

st.write(f"Showing data from {begin_year}-{begin_month} to {end_year}-{end_month}")
# Display columns: include Date_Display for user-friendly output
st.dataframe(filtered_df)

# Filter bear_df based on complete datetime range (inclusive)
bear_mask = (bear_df[bear_date_col] >= begin_date) & (bear_df[bear_date_col] <= end_date)
bear_filtered = bear_df[bear_mask]
count = len(bear_filtered)

st.write("Number of bear markets in period:", count)
st.dataframe(bear_filtered)

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
