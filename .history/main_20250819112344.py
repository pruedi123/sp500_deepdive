import streamlit as st
import pandas as pd
from pathlib import Path
import os

# --- Robust CSV loader that detects/repairs Excel-serial dates or strings ---
def _load_market_csv(source) -> pd.DataFrame:
    # Read without date parsing first so we can inspect the raw values
    raw = pd.read_csv(source)
    st.subheader("Raw CSV Diagnostics")
    if isinstance(source, (str, os.PathLike)):
        st.write("CSV path:", source)
    else:
        st.write("CSV source:", "uploaded file")
    st.write("Raw shape:", raw.shape)
    if "Date" in raw.columns:
        st.write("Raw 'Date' head (as-is):", raw["Date"].head(5).tolist())
        st.write("Raw 'Date' tail (as-is):", raw["Date"].tail(5).tolist())
    else:
        st.write("Columns present:", list(raw.columns))
    if "Date" not in raw.columns:
        st.error("CSV is missing a 'Date' column.")
        st.stop()

    # Peek at the first non-null values to infer type
    sample = raw["Date"].dropna().head(10).tolist()

    # Helper: does it look like all-numeric (Excel serials)?
    def _looks_numeric(vals):
        try:
            # If casting to float works for most items, treat as numeric
            ok = 0
            for v in vals:
                float(v)
                ok += 1
            return ok >= max(1, int(0.7 * len(vals)))
        except Exception:
            return False

    # Decide parsing strategy
    if _looks_numeric(sample):
        # Excel stores days since 1899-12-30 (to emulate the 1900 leap-year bug).
        # Using origin='1899-12-30' matches how Excel serials map to real dates.
        parsed = pd.to_datetime(raw["Date"], origin="1899-12-30", unit="D", errors="coerce")
        parse_mode = "excel_serial"
    else:
        # Try flexible string parsing, then a strict fallback
        parsed = pd.to_datetime(raw["Date"], errors="coerce", infer_datetime_format=True)
        if parsed.isna().all():
            # Try common explicit formats as a fallback
            for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%Y-%m", "%Y/%m"):
                parsed = pd.to_datetime(raw["Date"], format=fmt, errors="coerce")
                if not parsed.isna().all():
                    break
        parse_mode = "string"

    df_local = raw.copy()
    df_local["Date"] = parsed

    # Drop rows with bad/missing dates and sort
    bad_rows = df_local["Date"].isna().sum()
    if bad_rows:
        st.info(f"Dropped {bad_rows} rows with unparseable dates.")
    df_local = df_local.dropna(subset=["Date"]).sort_values("Date").reset_index(drop=True)

    # Surface diagnostics in the UI to debug 1899 issues
    st.subheader("Date Parsing Diagnostics")
    st.code(f"Parse mode: {parse_mode}")
    st.write("Raw 'Date' samples:", sample)
    st.write("Parsed head:", df_local["Date"].head())
    st.write("Parsed tail:", df_local["Date"].tail())
    st.write("Parsed dtype:", df_local["Date"].dtype)

    years = df_local["Date"].dt.year.value_counts().sort_index()
    st.write("Year coverage (counts):")
    st.dataframe(years.to_frame("rows"))

    return df_local

# --- Helpers to standardize CSV/Excel files across the project ---
def _parse_any_date(series: pd.Series) -> pd.Series:
    """
    Robustly parse a pandas Series of dates that may be strings or Excel serials.
    Returns a datetime64[ns] series; unparseable entries become NaT.
    """
    s = series.copy()
    # First try numeric -> Excel serial path (catch non-numeric via try)
    try:
        as_float = pd.to_numeric(s, errors="coerce")
        # If majority are numeric, treat as Excel serials
        if as_float.notna().mean() >= 0.5:
            parsed = pd.to_datetime(as_float, origin="1899-12-30", unit="D", errors="coerce")
        else:
            raise ValueError("Mostly non-numeric, fall back to string parsing.")
    except Exception:
        # Flexible string parsing
        parsed = pd.to_datetime(s, errors="coerce", infer_datetime_format=True)
        if parsed.isna().all():
            for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%Y-%m", "%Y/%m", "%d-%b-%Y", "%b %d, %Y"):
                parsed = pd.to_datetime(s, format=fmt, errors="coerce")
                if not parsed.isna().all():
                    break
    return parsed

def _standardize_df(df_in: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """
    Standardize:
      - Trim column names
      - Normalize any column containing 'date' (case-insensitive) to proper datetime
      - Floor all date columns to first-of-month (if monthly) by converting to Period('M') -> Timestamp
      - Keep original column order; only modify date columns' dtype/values
    Returns (df, meta) where meta includes per-date-column min/max.
    """
    df = df_in.copy()
    df.rename(columns=lambda c: str(c).strip(), inplace=True)
    meta = {"date_columns": {}, "rows": len(df), "cols": list(df.columns)}

    # Identify date-like columns
    date_cols = [c for c in df.columns if "date" in str(c).lower()]
    for c in date_cols:
        parsed = _parse_any_date(df[c])
        # Floor to first day of month when possible
        if parsed.notna().any():
            try:
                parsed = parsed.dt.to_period("M").dt.to_timestamp()
            except Exception:
                # If not period-like (e.g., daily), leave as-is
                pass
        df[c] = parsed
        # Record coverage
        if parsed.notna().any():
            meta["date_columns"][c] = {
                "min": str(parsed.min()),
                "max": str(parsed.max()),
                "nulls": int(parsed.isna().sum()),
            }
        else:
            meta["date_columns"][c] = {"min": None, "max": None, "nulls": len(parsed)}

    return df, meta

def _standardize_files_in_folder(folder: Path) -> pd.DataFrame:
    """
    Scan folder for .csv, .xlsx, .xls files, standardize date columns, and
    write standardized CSVs to a 'standardized' subfolder with suffix '_std.csv'.
    Returns a summary DataFrame of the operations.
    """
    std_dir = folder / "standardized"
    std_dir.mkdir(parents=True, exist_ok=True)

    records = []
    # Gather files
    paths = list(folder.glob("*.csv")) + list(folder.glob("*.xlsx")) + list(folder.glob("*.xls"))
    for p in paths:
        # Load file
        if p.suffix.lower() == ".csv":
            raw = pd.read_csv(p)
        else:
            # For Excel, use first sheet
            raw = pd.read_excel(p)
        df_std, meta = _standardize_df(raw)

        # Choose output path
        out_path = std_dir / f"{p.stem}_std.csv"
        # Ensure deterministic date formatting in file output
        # Convert any datetime columns to ISO strings for CSV
        for c in df_std.columns:
            if pd.api.types.is_datetime64_any_dtype(df_std[c]):
                df_std[c] = df_std[c].dt.strftime("%Y-%m-%d")

        df_std.to_csv(out_path, index=False)

        # Compose record
        rec = {
            "input": str(p),
            "output": str(out_path),
            "rows": meta["rows"],
            "columns": "|".join(meta["cols"]),
            "date_cols": "|".join(meta["date_columns"].keys()) if meta["date_columns"] else "",
        }
        # Add min/max for known date columns if present
        for dc, info in meta["date_columns"].items():
            rec[f"{dc}_min"] = info["min"]
            rec[f"{dc}_max"] = info["max"]
            rec[f"{dc}_nulls"] = info["nulls"]
        records.append(rec)

    return pd.DataFrame.from_records(records) if records else pd.DataFrame(columns=["input","output","rows","columns","date_cols"])

st.sidebar.header("Data Source")
uploaded = st.sidebar.file_uploader("Upload market_data_clean.csv", type=["csv"])

st.sidebar.header("Normalize Data")
if st.sidebar.button("Standardize all CSV/Excel files in project folder"):
    try:
        summary_df = _standardize_files_in_folder(Path(__file__).resolve().parent)
        st.success("Standardization complete. Outputs written to the 'standardized' subfolder with *_std.csv suffix.")
        if not summary_df.empty:
            st.write("**Standardization Summary**")
            st.dataframe(summary_df)
    except Exception as e:
        st.error(f"Standardization failed: {e}")

_SCRIPT_DIR = Path(__file__).resolve().parent
_CSV_PATH = _SCRIPT_DIR / "market_data_clean.csv"
_STD_DIR = _SCRIPT_DIR / "standardized"
_STD_CANDIDATE = _STD_DIR / "market_data_clean_std.csv"
if uploaded is not None:
    st.caption("Using uploaded CSV file.")
    df = _load_market_csv(uploaded)
else:
    if _STD_CANDIDATE.exists():
        st.caption(f"Loading CSV from: {_STD_CANDIDATE} (standardized)")
        df = _load_market_csv(str(_STD_CANDIDATE))
    else:
        st.caption(f"Loading CSV from: {_CSV_PATH}")
        df = _load_market_csv(str(_CSV_PATH))

_data_min = df["Date"].min()
_data_max = df["Date"].max()
if _data_max.year < 1900 or _data_min.year < 1900:
    st.warning(f"Detected dates prior to 1900 (min={_data_min}, max={_data_max}). This often indicates Excel-serial parsing. Review the diagnostics above.")
if _data_max.year < 1950:
    st.error(f"The latest date in the loaded CSV is {_data_max.strftime('%Y-%m')}. This likely means you're loading an early-era dataset (e.g., 1871–1899) or the wrong file. Please confirm the CSV at {_CSV_PATH} actually contains modern rows (e.g., 2000–2025).")
st.caption(f"Data coverage: {_data_min.strftime('%Y-%m')} → {_data_max.strftime('%Y-%m')}")

st.sidebar.header("Select Date Range")

# Streamlit app title and description
st.title("S&P 500 Market Data Deep Dive")
st.write(
    "Explore S&P 500 market data by selecting a custom date range below. "
    "Use the sidebar to pick your start and end months/years."
)


# Build list of available YYYY-MM values in the data, sorted and unique
available_months = sorted(df["Date"].dt.strftime("%Y-%m").unique())

# Ensure months are sorted chronologically (string sort is fine for YYYY-MM)
if available_months and available_months[-1] < "1900-01":
    st.error("All detected months are before 1900, which is unexpected for this dataset. Please verify the CSV's 'Date' column format.")

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
_BEARS_PATH = _SCRIPT_DIR / "bear_markets_clean.csv"
_RECESSIONS_PATH = _SCRIPT_DIR / "recessions_clean.csv"
bears = pd.read_csv(_BEARS_PATH, parse_dates=["Start Date", "End Date"])
recessions = pd.read_csv(_RECESSIONS_PATH, parse_dates=["Begin Date", "End Date"])

# Count overlapping bear markets: event overlaps window if it starts before window end AND ends after window start
bear_count = bears[(bears["End Date"] >= begin_date) & (bears["Start Date"] <= end_date)].shape[0]

# Count overlapping recessions using the same overlap rule
recession_count = recessions[(recessions["End Date"] >= begin_date) & (recessions["Begin Date"] <= end_date)].shape[0]

st.write(f"**Number of Bear Markets in Range:** {bear_count}")
st.write(f"**Number of Recessions in Range:** {recession_count}")