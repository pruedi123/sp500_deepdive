import streamlit as st
import pandas as pd
from pathlib import Path

def standardize_csv_dates(input_path: str, output_path: str, date_col="Date"):
    """
    Read a CSV, robustly parse the date column even if mixed formats are present,
    and write a new CSV with dates standardized to YYYY-MM-DD (first of month preserved if present).
    """
    import pandas as pd
    df0 = pd.read_csv(input_path)
    if date_col not in df0.columns:
        raise ValueError(f"'{date_col}' column not found in {input_path}. Columns: {list(df0.columns)}")
    # Work on a copy
    s = df0[date_col].astype(str).str.strip()
    # First pass: general parse
    d = pd.to_datetime(s, errors="coerce")
    # Second pass for remaining NaT: explicit US short format like 10/1/24
    mask_nat = d.isna()
    if mask_nat.any():
        d2 = pd.to_datetime(s[mask_nat], format="%m/%d/%y", errors="coerce")
        d.loc[mask_nat] = d2
    # Third pass for 4-digit year slash format like 10/01/2024
    mask_nat = d.isna()
    if mask_nat.any():
        d3 = pd.to_datetime(s[mask_nat], format="%m/%d/%Y", errors="coerce")
        d.loc[mask_nat] = d3
    # Fourth pass for year-month strings like 2024-10
    mask_nat = d.isna()
    if mask_nat.any():
        d4 = pd.to_datetime(s[mask_nat], format="%Y-%m", errors="coerce")
        d.loc[mask_nat] = d4

    # Adjust two-digit year interpretations: if parsed year is implausibly in the future,
    # assume century rollover and subtract 100 years (e.g., '12/1/68' -> 1968, not 2068).
    from datetime import datetime
    current_year = datetime.now().year
    # Identify original strings that look like mm/dd/yy
    two_digit_mask = s.str.match(r"\d{1,2}/\d{1,2}/\d{2}$", na=False)
    # Where those parsed to a year > current_year + 1, roll back a century
    future_mask = two_digit_mask & d.notna() & (d.dt.year > current_year + 1)
    if future_mask.any():
        d.loc[future_mask] = d.loc[future_mask] - pd.offsets.DateOffset(years=100)

    # If mostly numeric Excel serials remain, try that too
    mask_nat = d.isna()
    if mask_nat.any():
        as_num = pd.to_numeric(s[mask_nat], errors="coerce")
        if as_num.notna().any():
            d5 = pd.to_datetime(as_num, origin="1899-12-30", unit="D", errors="coerce")
            d.loc[mask_nat] = d5
    # Drop rows we still can't parse
    df = df0.copy()
    df[date_col] = d
    before = len(df)
    df = df.dropna(subset=[date_col]).copy()
    dropped = before - len(df)
    # Normalize to the first of the month if original strings looked monthly
    # Strategy: if day is 1 for >=90% rows, coerce all to first-of-month for consistency
    day_is_one_ratio = (df[date_col].dt.day == 1).mean()
    if day_is_one_ratio >= 0.90:
        df[date_col] = df[date_col].dt.to_period("M").dt.to_timestamp()
    # Standardized output as YYYY-MM-DD
    df[date_col] = df[date_col].dt.strftime("%Y-%m-%d")
    df.to_csv(output_path, index=False)
    return {"input": input_path, "output": output_path, "rows_out": len(df), "dropped_rows": dropped}

import io

# Sidebar: one-click "Standardize & Download"
st.sidebar.header("Fix Dates")
proj_dir = Path(__file__).resolve().parent
raw_csv = proj_dir / "market_data_clean.csv"
std_csv = proj_dir / "market_data_clean_std.csv"
if st.sidebar.button("Standardize Now"):
    try:
        result = standardize_csv_dates(str(raw_csv), str(std_csv), date_col="Date")
        st.success(f"Standardized CSV written: {std_csv}")
        st.write(result)
        # Provide download of the standardized CSV
        with open(std_csv, "rb") as f:
            st.download_button("Download standardized CSV", f, file_name="market_data_clean_std.csv")
    except Exception as e:
        st.error(f"Standardization failed: {e}")

# Prefer standardized CSV if present
proj_dir = Path(__file__).resolve().parent
std_csv = proj_dir / "market_data_clean_std.csv"
raw_csv = proj_dir / "market_data_clean.csv"
csv_to_use = std_csv if std_csv.exists() else raw_csv
st.caption(f"Loading: {csv_to_use}")
df_raw = pd.read_csv(csv_to_use)

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