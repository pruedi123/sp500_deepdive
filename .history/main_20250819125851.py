import streamlit as st
import pandas as pd
import io
import plotly.express as px

st.title("Perspective is EVERYTHING!")

# Placeholder for narrative summary (to be updated after metrics are computed)
summary_placeholder = st.empty()

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

# Load recession data from either CSV or Excel
recession_df = None
try:
    recession_df = pd.read_csv("recessions_clean.csv")
except Exception:
    try:
        recession_df = pd.read_excel("recessions.xlsx")
    except Exception:
        recession_df = None

if recession_df is not None:
    # Detect date column in recession_df using coercion and 50% non-null threshold
    recession_date_col = None
    for col in recession_df.columns:
        if pd.api.types.is_numeric_dtype(recession_df[col]):
            if recession_df[col].dropna().gt(1000).all():
                try:
                    parsed_dates = pd.to_datetime(recession_df[col], origin="1899-12-30", unit="D", errors="coerce")
                    if parsed_dates.notna().mean() >= 0.5:
                        recession_date_col = col
                        break
                except Exception:
                    continue
        else:
            parsed_dates = pd.to_datetime(recession_df[col], errors="coerce")
            if parsed_dates.notna().mean() >= 0.5:
                recession_date_col = col
                break
    if recession_date_col is None and 'Date' in recession_df.columns:
        recession_date_col = 'Date'
    if recession_date_col is None:
        st.error("No date-like column found in recession data.")
        st.stop()

    if pd.api.types.is_numeric_dtype(recession_df[recession_date_col]):
        recession_df[recession_date_col] = pd.to_datetime(recession_df[recession_date_col], origin="1899-12-30", unit="D", errors="coerce")
    else:
        recession_df[recession_date_col] = pd.to_datetime(recession_df[recession_date_col], errors="coerce")
    recession_df = recession_df.dropna(subset=[recession_date_col])
else:
    recession_df = pd.DataFrame()
    recession_date_col = None

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

 # Let the user choose how to enter years (dropdown or typed number)
year_input_mode = st.sidebar.radio("Year input mode", ["Dropdown", "Type a number"], index=0, horizontal=True)
if year_input_mode == "Dropdown":
    begin_year = st.sidebar.selectbox("Begin Year", years, index=get_default_index(years, 1959))
    end_year = st.sidebar.selectbox("End Year", years[::-1], index=get_default_index(years[::-1], 2025))
else:
    begin_year = st.sidebar.number_input("Begin Year", min_value=int(min(years)), max_value=int(max(years)), value=2000, step=1)
    end_year = st.sidebar.number_input("End Year", min_value=int(min(years)), max_value=int(max(years)), value=2025, step=1)

begin_month = st.sidebar.selectbox("Begin Month", months, index=get_default_index(months, 11))
end_month = st.sidebar.selectbox("End Month", months[::-1], index=get_default_index(months[::-1], 7))

investment_amount = st.sidebar.number_input("Investment Amount", min_value=10000, max_value=100000, step=10000, value=10000)

# Slider to apply a custom percent of Ending Value (0% to 10% in 0.5% steps)
custom_pct = st.sidebar.slider("Custom % of Ending Value", min_value=0.0, max_value=10.0, value=0.0, step=0.5, format="%.1f%%")

# Sidebar radio button for bear market table display
show_bear_table = st.sidebar.radio("Show Bear Market Table?", ["Yes","No"], index=0)

# Sidebar radio button for recession table display
show_recession_table = st.sidebar.radio("Show Recession Table?", ["Yes","No"], index=0)

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

    # --- Ending-period dividend yield and dividends at ending nominal value ---
    if not filtered_df.empty and all(col in filtered_df.columns for col in ["Nominal Dividends", "Composite"]):
        end_row = filtered_df.iloc[-1]
        # Yield = Nominal Dividends / Composite for the ending month
        try:
            end_div_yield = (end_row["Nominal Dividends"] / end_row["Composite"]) if end_row["Composite"] != 0 else float('nan')
        except Exception:
            end_div_yield = float('nan')

        # Label date for display
        if "Date_Display" in filtered_df.columns:
            end_label = str(end_row["Date_Display"])  # e.g., Mar-03
        else:
            try:
                end_label = pd.to_datetime(end_row[date_col]).strftime("%b-%y")
            except Exception:
                end_label = "(ending month)"

        # Show the ending dividend yield
        # if pd.notnull(end_div_yield):
        #     st.markdown(f"**Ending Dividend Yield ({end_label}): {end_div_yield:.2%}**")
        # else:
        #     st.warning("Could not compute ending dividend yield (missing or zero Composite/Dividends).")

        # Dividends at ending nominal value = yield × Ending Value (Nominal Total Return)
        try:
            end_div_dollars = end_div_yield * ending_value if pd.notnull(end_div_yield) and pd.notnull(ending_value) else float('nan')
        except Exception:
            end_div_dollars = float('nan')

        if pd.notnull(end_div_dollars):
            st.markdown(f"**Current Dividends at Ending Portfolio Value (Nominal): ${end_div_dollars:,.0f}**")
            # Also show a custom percentage of the Ending Value directly under dividends
            if pd.notnull(ending_value):
                custom_value = (custom_pct / 100.0) * ending_value
                st.markdown(f"**Custom % of Ending Value ({custom_pct:.1f}%): ${custom_value:,.0f}**")
    else:
        st.warning("'Nominal Dividends' or 'Composite' column not found — cannot compute ending dividend yield.")
    # ---

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
fig.update_traces(textposition='outside', texttemplate='<b>%{text}</b>', textfont=dict(size=18))
fig.update_layout(
    title={'text': '<b>Increase Factors</b>', 'font': {'size': 20}},
    xaxis_title={'text': '<b>Category</b>'},
    yaxis_title={'text': '<b>Factor</b>'},
    xaxis=dict(tickfont=dict(size=14)),
    yaxis=dict(tickfont=dict(size=14), range=[0, max(factors_df["Factor"].max()*1.1, 1)])
)
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
fig2.update_traces(textposition='outside', texttemplate='<b>%{text}</b>', textfont=dict(size=18))
fig2.update_layout(
    title={'text': '<b>Increase Factors (Real)</b>', 'font': {'size': 20}},
    xaxis_title={'text': '<b>Category</b>'},
    yaxis_title={'text': '<b>Factor</b>'},
    xaxis=dict(tickfont=dict(size=14)),
    yaxis=dict(tickfont=dict(size=14), range=[0, max(real_factors_df["Factor"].max()*1.1, 1)])
)
st.plotly_chart(fig2)

import numpy as np
# Filter bear_df based on complete datetime range (inclusive)
bear_mask = (bear_df[bear_date_col] >= begin_date) & (bear_df[bear_date_col] <= end_date)
bear_filtered = bear_df[bear_mask].copy()
count = len(bear_filtered)

# --- Compute and format bear‑market metrics (decline / unemployment / duration) ---
# Identify columns by normalized names so we handle spelling/spacing variants
def _norm(s: str) -> str:
    return "".join(ch for ch in str(s).lower() if ch.isalnum())

norm_map = {col: _norm(col) for col in bear_filtered.columns}

# Find likely columns
decline_col = None
for col, n in norm_map.items():
    if any(tok in n for tok in ["decline", "drawdown", "drop", "loss"]):
        decline_col = col
        break

unemp_col = None
for col, n in norm_map.items():
    if any(tok in n for tok in ["unemployment", "unemp", "unempolyment", "peakunemployment", "peakunemp"]):
        unemp_col = col
        break

duration_col = None
for col, n in norm_map.items():
    if "duration" in n:
        duration_col = col
        break

# Compute averages BEFORE formatting
average_decline = None
average_duration = None

if decline_col is not None:
    decline_num = pd.to_numeric(bear_filtered[decline_col], errors="coerce")
    average_decline = decline_num.mean()
    # Multiply by 100 unconditionally for display and format with one decimal place
    bear_filtered[decline_col] = (decline_num * 100).map(lambda x: f"{x:.1f}%" if pd.notnull(x) else "")

if unemp_col is not None:
    unemp_num = pd.to_numeric(bear_filtered[unemp_col], errors="coerce")
    bear_filtered[unemp_col] = (unemp_num * 100).map(lambda x: f"{x:.1f}%" if pd.notnull(x) else "")

if duration_col is not None:
    duration_num = pd.to_numeric(bear_filtered[duration_col], errors="coerce")
    average_duration = duration_num.mean()

st.markdown(f"**Number of bear markets in period: {count}**")
if show_bear_table == "Yes":
    st.dataframe(bear_filtered)

# Display averages using the numeric (pre-format) values
if average_decline is not None:
    st.write("Average Bear Market Decline:", f"{average_decline*100:.2f}%")
if average_duration is not None:
    st.markdown(f"Average Bear Market Duration (days): **{int(round(average_duration))}**")
# ---

# Filter recession_df based on complete datetime range (inclusive)
if recession_df is not None and not recession_df.empty and recession_date_col is not None:
    recession_mask = (recession_df[recession_date_col] >= begin_date) & (recession_df[recession_date_col] <= end_date)
    recession_filtered = recession_df[recession_mask]
    recession_count = len(recession_filtered)
else:
    recession_filtered = pd.DataFrame()
    recession_count = 0


st.markdown(f"**Number of recessions in period: {recession_count}**")
if show_recession_table == "Yes":
    st.dataframe(recession_filtered)


# Narrative summary (rendered after metrics are computed)
if average_decline is not None and average_duration is not None:
    bad_news_text = (
        f"First the bad news. During the period you chose, there were {count} bear markets "
        f"(temporary declines of 20% or more). The average of those temporary declines was "
        f"{average_decline*100:.2f}% and the average duration of the bear market(s) was "
        f"{int(round(average_duration))} days. "
        f"We also experienced {recession_count} recessions during this time. "
        f"Now the good news..."
    )
    summary_placeholder.markdown(bad_news_text)
