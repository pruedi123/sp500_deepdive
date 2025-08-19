import pandas as pd

# Load with datetime parsing
df = pd.read_csv("market_data_clean.csv", parse_dates=["Date"])

# --- Pick your test range ---
begin = "1900-01"   # January 1900
end   = "2000-06"   # June 1900

# Convert to full YYYY-MM-DD by forcing the first of the month
begin_date = pd.to_datetime(begin + "-01")
end_date   = pd.to_datetime(end + "-01")

# Filter the dataframe
mask = (df["Date"] >= begin_date) & (df["Date"] <= end_date)
df_filtered = df.loc[mask]

print(df_filtered)