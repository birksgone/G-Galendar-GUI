import streamlit as st
import pandas as pd
import json
from pathlib import Path
from modules.display_formatter import format_dataframe_for_display

st.set_page_config(layout="wide", page_title="Forum Post Creator")
st.title("✍️ Forum Post Creator")

# --- Load Data and Template ---
def load_template():
    template_path = Path("data/forum-template.json")
    if template_path.exists():
        with open(template_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"en": "Template not found.", "ja": "テンプレートが見つかりません。"}

if 'diff_data' not in st.session_state or st.session_state['diff_data'].empty:
    st.warning("No difference data found. Please generate it from the main page.")
    st.page_link("app.py", label="Back to Main Page", icon="🏠")
    st.stop()

diff_df_raw = st.session_state['diff_data']
en_map = st.session_state['en_map']
ja_map = st.session_state['ja_map']
template = load_template()

# --- Format Data ---
rules_path = Path("data/type_mapping_rules.json")
rules = []
if rules_path.exists():
    with open(rules_path, 'r', encoding='utf-8') as f:
        rules = json.load(f)

# This is the full dataframe with all columns, used for populating the template
display_df_all_cols = format_dataframe_for_display(diff_df_raw, rules, en_map, ja_map, timezone="UTC")

# --- Restore Date Filter ---
st.subheader("Filter by Date Range")
if not display_df_all_cols.empty:
    min_date = display_df_all_cols['Start Time'].min().date()
    max_date = display_df_all_cols['Start Time'].max().date()

    col1, col2 = st.columns(2)
    with col1:
        start_date_filter = st.date_input("Start date", value=min_date, min_value=min_date, max_value=max_date)
    with col2:
        end_date_filter = st.date_input("End date", value=max_date, min_value=min_date, max_value=max_date)

    # Apply date filter
    mask = ((display_df_all_cols['Start Time'].dt.date >= start_date_filter) &
           (display_df_all_cols['Start Time'].dt.date <= end_date_filter))
    filtered_display_df = display_df_all_cols[mask]
else:
    filtered_display_df = display_df_all_cols # Handle case with no data

# --- Display Table with Standard Columns ---
st.subheader("Difference Data (Standard View)")

# Define standard columns
standard_cols = [
    'Icon', 'Display Type', 'Event Name', 'Start Time', 'End Time', 'Duration',
    'Featured Heroes (EN)', 'Non-Featured Heroes (EN)',
    'Featured Heroes (JA)', 'Non-Featured Heroes (JA)', '_diff_status'
]

# Create a view for the table with only standard columns
table_view_df = filtered_display_df[[col for col in standard_cols if col in filtered_display_df.columns]].copy()

# Format datetime columns for display in the table
dt_format = "%Y-%m-%d %H:%M"
for col in ['Start Time', 'End Time']:
    if col in table_view_df.columns:
        table_view_df[col] = table_view_df[col].dt.strftime(dt_format)

st.dataframe(table_view_df, use_container_width=True)

# --- Generate Post Text from Template ---
st.subheader("Generated Post Text")

if filtered_display_df.empty:
    st.info("No events match the selected date range.")
else:
    # Iterate through the filtered dataframe which contains ALL columns needed for the template
    for index, row in filtered_display_df.iterrows():
        st.markdown(f"--- Event: **{row.get('Event Name', '')}** (`{row.get('_diff_status', '')}`) ---")
        
        # Prepare data for template
        template_data = row.to_dict()
        # Format datetime objects into strings for the template
        template_data['Start Time'] = row['Start Time'].strftime(dt_format) if pd.notna(row['Start Time']) else ''
        template_data['End Time'] = row['End Time'].strftime(dt_format) if pd.notna(row['End Time']) else ''
        # Ensure list-based hero columns are converted to strings
        template_data['Featured Heroes (EN)'] = ", ".join(template_data.get('Featured Heroes (EN)', []))
        template_data['Non-Featured Heroes (EN)'] = ", ".join(template_data.get('Non-Featured Heroes (EN)', []))
        template_data['Featured Heroes (JA)'] = ", ".join(template_data.get('Featured Heroes (JA)', []))
        template_data['Non-Featured Heroes (JA)'] = ", ".join(template_data.get('Non-Featured Heroes (JA)', []))

        # Generate text
        try:
            en_text = template['en'].format(**template_data)
            ja_text = template['ja'].format(**template_data)
        except KeyError as e:
            st.error(f"Template error: Placeholder {e} not found in data.")
            en_text = ""
            ja_text = ""

        col1, col2 = st.columns(2)
        with col1:
            st.text_area("English Post", value=en_text, height=150, key=f"en_{index}")
        with col2:
            st.text_area("Japanese Post", value=ja_text, height=150, key=f"ja_{index}")

st.page_link("app.py", label="Back to Main Page", icon="🏠")