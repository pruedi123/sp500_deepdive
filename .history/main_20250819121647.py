import streamlit as st
import pandas as pd
import io
import plotly.express as px

st.title("Perspective is everything")

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
# st.write("Bear markets date range:", bear_df[bear_date_col].min(), "to", bear_df[bear_date_col].max())

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

begin_year = st.sidebar.selectbox("Begin Year", years, index=get_default_index(years, 1959))
end_year = st.sidebar.selectbox("End Year", years[::-1], index=get_default_index(years[::-1], 2025))

begin_month = st.sidebar.selectbox("Begin Month", months, index=get_default_index(months, 11))
end_month = st.sidebar.selectbox("End Month", months[::-1], index=get_default_index(months[::-1], 7))

investment_amount = st.sidebar.number_input("Investment Amount", min_value=10000, max_value=100000, step=10000, value=10000)

# Sidebar radio button for bear market table display
show_bear_table = st.sidebar.radio("Show Bear Market Table?", ["Yes","No"], index=0)

# Ensure begin_date and end_date are proper pd.Timestamp
begin_date = pd.Timestamp(begin_year, begin_month, 1)
end_date = pd.Timestamp(end_year, end_month, 1) + pd.offsets.MonthEnd(0)

# Debug output for filter range
# st.write("Filter range:", begin_date, "to", end_date)
# Filter data based on complete datetime range
date_mask = (df[date_col] >= begin_date) & (df[date_col] <= end_date)
filtered_df = df[date_mask]

st.write(f"Showing data from {begin_year}-{begin_month} to {end_year}-{end_month}")

# Debug statement to show filtered_df columns
# st.write("Filtered columns:", filtered_df.columns.tolist())

# Display columns: include Date_Display for user-friendly output
# st.dataframe(filtered_df)


# Composite column calculations and display
if not filtered_df.empty and "Composite" in filtered_df.columns:
    begin_value = filtered_df["Composite"].iloc[0]
    end_value = filtered_df["Composite"].iloc[-1]
    try:
        factor = end_value / begin_value if begin_value != 0 else float('nan')
    except Exception:
        factor = float('nan')
    # st.write("Begin Composite:", begin_value)
    # st.write("End Composite:", end_value)
    # st.write("Increase Factor:", f"{factor:.2f}x")
else:
    factor = float('nan')


# Total Return column calculations and display
if not filtered_df.empty and "Total Return" in filtered_df.columns:
    begin_tr = filtered_df["Total Return"].iloc[0]
    end_tr = filtered_df["Total Return"].iloc[-1]
    try:
        tr_factor = end_tr / begin_tr if begin_tr != 0 else float('nan')
    except Exception:
        tr_factor = float('nan')
    # st.write("Begin Total Return:", begin_tr)
    # st.write("End Total Return:", end_tr)
    # st.write("Total Return Factor:", f"{tr_factor:.2f}x")
else:
    tr_factor = float('nan')

ending_value = investment_amount * tr_factor
st.markdown(f"**Ending Value (Nominal Total Return): ${ending_value:,.0f}**")

# Calculate CAGR (Nominal Total Return)
if not filtered_df.empty and "Total Return" in filtered_df.columns:
    # Use begin_date and end_date for period calculation
    n_years = (end_date - begin_date).days / 365.25
    if begin_tr > 0 and n_years > 0:
        cagr = (end_tr / begin_tr) ** (1 / n_years) - 1
    else:
        cagr = float('nan')
    st.markdown(f"**CAGR (Nominal Total Return): {cagr:.2%}**")

# C CPI column calculations and display (adjusted to detect any CPI column)
cpi_col = None
for col in filtered_df.columns:
    if "cpi" in col.lower():
        cpi_col = col
        break

if not filtered_df.empty and cpi_col is not None:
    begin_c_cpi = filtered_df[cpi_col].iloc[0]
    end_c_cpi = filtered_df[cpi_col].iloc[-1]
    try:
        c_cpi_factor = end_c_cpi / begin_c_cpi if begin_c_cpi != 0 else float('nan')
    except Exception:
        c_cpi_factor = float('nan')
    # st.write(f"Begin {cpi_col}:", begin_c_cpi)
    # st.write(f"End {cpi_col}:", end_c_cpi)
    # st.write(f"{cpi_col} Factor:", f"{c_cpi_factor:.2f}x")
else:
    c_cpi_factor = float('nan')

# Nominal Dividends column calculations and display
if not filtered_df.empty and "Nominal Dividends" in filtered_df.columns:
    begin_nom_div = filtered_df["Nominal Dividends"].iloc[0]
    end_nom_div = filtered_df["Nominal Dividends"].iloc[-1]
    try:
        nom_div_factor = end_nom_div / begin_nom_div if begin_nom_div != 0 else float('nan')
    except Exception:
        nom_div_factor = float('nan')
    # st.write("Begin Nominal Dividends:", begin_nom_div)
    # st.write("End Nominal Dividends:", end_nom_div)
    # st.write("Nominal Dividends Factor:", f"{nom_div_factor:.2f}x")
else:
    nom_div_factor = float('nan')

# Nominal Earnings column calculations and display
if not filtered_df.empty and "Nominal Earnings" in filtered_df.columns:
    begin_nom_earn = filtered_df["Nominal Earnings"].iloc[0]
    end_nom_earn = filtered_df["Nominal Earnings"].iloc[-1]
    try:
        nom_earn_factor = end_nom_earn / begin_nom_earn if begin_nom_earn != 0 else float('nan')
    except Exception:
        nom_earn_factor = float('nan')
    # st.write("Begin Nominal Earnings:", begin_nom_earn)
    # st.write("End Nominal Earnings:", end_nom_earn)
    # st.write("Nominal Earnings Factor:", f"{nom_earn_factor:.2f}x")
else:
    nom_earn_factor = float('nan')

# Real Total Return column calculations and display
if not filtered_df.empty and "Real Total Return" in filtered_df.columns:
    begin_real_tr = filtered_df["Real Total Return"].iloc[0]
    end_real_tr = filtered_df["Real Total Return"].iloc[-1]
    try:
        real_tr_factor = end_real_tr / begin_real_tr if begin_real_tr != 0 else float('nan')
    except Exception:
        real_tr_factor = float('nan')
else:
    real_tr_factor = float('nan')

# Real Composite column calculations and display
if not filtered_df.empty and "Real Composite" in filtered_df.columns:
    begin_real_comp = filtered_df["Real Composite"].iloc[0]
    end_real_comp = filtered_df["Real Composite"].iloc[-1]
    try:
        real_comp_factor = end_real_comp / begin_real_comp if begin_real_comp != 0 else float('nan')
    except Exception:
        real_comp_factor = float('nan')
else:
    real_comp_factor = float('nan')

# Real Dividends column calculations and display
if not filtered_df.empty and "Real Dividends" in filtered_df.columns:
    begin_real_div = filtered_df["Real Dividends"].iloc[0]
    end_real_div = filtered_df["Real Dividends"].iloc[-1]
    try:
        real_div_factor = end_real_div / begin_real_div if begin_real_div != 0 else float('nan')
    except Exception:
        real_div_factor = float('nan')
else:
    real_div_factor = float('nan')

# Build interactive bar chart for Composite, Total Return, Nominal Dividends, and CPI factors
factors_dict = {
    "Total Return": tr_factor,
    "Composite": factor,
    "Nominal Dividends": nom_div_factor,
    "CPI": c_cpi_factor
}
factors_df = pd.DataFrame(list(factors_dict.items()), columns=["Category", "Factor"])
# Create preformatted label column
def format_label(val):
    if pd.isna(val):
        return ""
    if val >= 10:
        return f"{int(val)}x"
    else:
        return f"{val:.2f}x"
factors_df["Label"] = factors_df["Factor"].apply(format_label)

fig = px.bar(factors_df, x="Category", y="Factor", title="Increase Factors", text="Label")
# Remove texttemplate so Plotly uses provided Label as-is
fig.update_traces(textposition='outside')
fig.update_layout(yaxis_title="Factor", xaxis_title="Category", yaxis=dict(range=[0, max(factors_df["Factor"].max()*1.1,1)]))
st.plotly_chart(fig)

# Build interactive bar chart for Real Total Return, Real Composite, and Real Dividends
real_factors_dict = {
    "Real Total Return": real_tr_factor,
    "Real Composite": real_comp_factor,
    "Real Dividends": real_div_factor
}
real_factors_df = pd.DataFrame(list(real_factors_dict.items()), columns=["Category", "Factor"])
real_factors_df["Label"] = real_factors_df["Factor"].apply(format_label)

fig2 = px.bar(real_factors_df, x="Category", y="Factor", title="Increase Factors (Real)", text="Label")
fig2.update_traces(textposition='outside')
fig2.update_layout(yaxis_title="Factor", xaxis_title="Category", yaxis=dict(range=[0, max(real_factors_df["Factor"].max()*1.1,1)]))
st.plotly_chart(fig2)

# Filter bear_df based on complete datetime range (inclusive)
bear_mask = (bear_df[bear_date_col] >= begin_date) & (bear_df[bear_date_col] <= end_date)
bear_filtered = bear_df[bear_mask]
count = len(bear_filtered)

st.markdown(f"**Number of bear markets in period: {count}**")
if show_bear_table == "Yes":
    st.dataframe(bear_filtered)

# Calculate and display averages for decline and duration columns if present
average_decline = None
average_duration = None

decline_cols = [col for col in bear_filtered.columns if "decline" in col.lower()]
duration_cols = [col for col in bear_filtered.columns if "duration" in col.lower()]

if decline_cols:
    average_decline = bear_filtered[decline_cols[0]].mean()
    formatted_decline = f"{average_decline:.2f}%" if average_decline is not None else ""
    st.write("Average Bear Market Decline:", formatted_decline)

if duration_cols:
    average_duration = bear_filtered[duration_cols[0]].mean()
    formatted_duration = int(round(average_duration)) if average_duration is not None else ""
    st.write("Average Bear Market Duration (days):", formatted_duration)

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
