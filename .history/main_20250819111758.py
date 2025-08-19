import streamlit as st
import pandas as pd
from pathlib import Path

# --- Robust CSV loader that detects/repairs Excel-serial dates or strings ---
def _load_market_csv(path: str) -> pd.DataFrame:
    # Read without date parsing first so we can inspect the raw values
    raw = pd.read_csv(path)
    st.subheader("Raw CSV Diagnostics")
    st.write("CSV path:", path)
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

# Resolve CSV path relative to this script so we don't accidentally read a similarly named file elsewhere
_SCRIPT_DIR = Path(__file__).resolve().parent
_CSV_PATH = _SCRIPT_DIR / "market_data_clean.csv"
st.caption(f"Loading CSV from: {_CSV_PATH}")
df = _load_market_csv(str(_CSV_PATH))

_data_min = df["Date"].min()
_data_max = df["Date"].max()
if _data_max.year < 1900 or _data_min.year < 1900:
    st.warning(f"Detected dates prior to 1900 (min={_data_min}, max={_data_max}). This often indicates Excel-serial parsing. Review the diagnostics above.")
if _data_max.year < 1950:
    st.error(f"The latest date in the loaded CSV is {_data_max.strftime('%Y-%m')}. This likely means you're loading an early-era dataset (e.g., 1871–1899) or the wrong file. Please confirm the CSV at {_CSV_PATH} actually contains modern rows (e.g., 2000–2025).")
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