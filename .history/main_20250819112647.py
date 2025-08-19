


import streamlit as st
import pandas as pd

st.title("Date Debug — market_data_clean.csv")

# Load raw CSV without parsing so we can inspect the Date column as-is
df_raw = pd.read_csv("market_data_clean.csv")

# Find a date-like column (prefer exact 'Date', else any column containing 'date')
date_col_name = None
for c in df_raw.columns:
  if str(c).strip() == "Date":
    date_col_name = c
    break
if date_col_name is None:
  for c in df_raw.columns:
    if "date" in str(c).lower():
      date_col_name = c
      break

if date_col_name is None:
  st.error("No 'Date' column found (case-insensitive). Columns present: " + ", ".join(map(str, df_raw.columns)))
  st.stop()

st.write("Using date column:", f"`{date_col_name}`")
st.write("Raw 'Date' head (as-is):", df_raw[date_col_name].head(10).tolist())
st.write("Raw 'Date' tail (as-is):", df_raw[date_col_name].tail(10).tolist())

# Detect whether dates are numeric (Excel serial) or strings
as_num = pd.to_numeric(df_raw[date_col_name], errors="coerce")
frac_numeric = as_num.notna().mean()
st.write(f"Fraction of date column that is numeric: {frac_numeric:.2%}")

# Parse strategy
if frac_numeric >= 0.5:
    # Treat as Excel serial dates (Excel-compatible origin including the 1900 leap year bug)
    dates = pd.to_datetime(as_num, origin="1899-12-30", unit="D", errors="coerce")
    parse_mode = "excel_serial (origin=1899-12-30)"
else:
    dates = pd.to_datetime(df_raw[date_col_name], errors="coerce", infer_datetime_format=True)
    if dates.isna().all():
        # Try a few common formats explicitly
        tried = []
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%Y-%m", "%Y/%m", "%d-%b-%Y", "%b %d, %Y"):
            tried.append(fmt)
            dates = pd.to_datetime(df_raw[date_col_name], format=fmt, errors="coerce")
            if not dates.isna().all():
                parse_mode = f"string (format='{fmt}')"
                break
        else:
            parse_mode = f"string (all tried failed: {', '.join(tried)})"
    else:
        parse_mode = "string (infer)"

st.write("Parse mode:", parse_mode)

df = df_raw.copy()
df["Date"] = dates
bad = df["Date"].isna().sum()
if bad:
    st.warning(f"Dropped {bad} rows with unparseable dates.")
df = df.dropna(subset=["Date"]).sort_values("Date").reset_index(drop=True)

# Coverage + sanity checks
if df.empty:
    st.error("No valid dates after parsing.")
    st.stop()

data_min = df["Date"].min()
data_max = df["Date"].max()
st.write("Parsed 'Date' head:", df["Date"].head(10).tolist())
st.write("Parsed 'Date' tail:", df["Date"].tail(10).tolist())
st.write(f"Data coverage: {data_min.strftime('%Y-%m')} → {data_max.strftime('%Y-%m')}")
if data_max.year < 1950:
    st.error("Latest date is before 1950 — this almost certainly means the file itself doesn't contain modern rows. Confirm you're loading the correct CSV.")

# Build list of available YYYY-MM strings
available_months = sorted(df["Date"].dt.strftime("%Y-%m").unique())

# Sidebar selectors for begin and end
st.sidebar.header("Select Date Range")
begin = st.sidebar.selectbox("Begin Date", available_months, index=0)
end = st.sidebar.selectbox("End Date", available_months, index=len(available_months) - 1)

# Output selected and all dates
st.write("**Begin Date Selected:**", begin)
st.write("**End Date Selected:**", end)
st.write("**All Available Dates (count = {0}):**".format(len(available_months)))
st.write(available_months)