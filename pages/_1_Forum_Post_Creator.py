import streamlit as st
import pandas as pd
import json
import re
from pathlib import Path
from datetime import date
from modules.display_formatter import format_dataframe_for_display, to_html_table

# --- Config and CSS Helper Functions ---
DATA_DIR = Path("data")
CONFIG_FILE = DATA_DIR / "config.json"

def load_json_file(filepath, default_data={}):
    if not filepath.exists(): return default_data
    try:
        with open(filepath, "r", encoding="utf-8") as f: return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError): return default_data

def save_json_file(filepath, data):
    with open(filepath, "w", encoding="utf-8") as f: json.dump(data, f, indent=2, ensure_ascii=False)

def inject_custom_css():
    css_file = "styles.css"
    if Path(css_file).is_file():
        with open(css_file, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# --- Custom Template Processor ---
def process_custom_template(template_str, data_dict):
    output = ""
    i = 0
    while i < len(template_str):
        char = template_str[i]
        if char == '\\':  # Escape character
            if i + 1 < len(template_str):
                output += template_str[i+1]
                i += 2
            else:  # Dangling escape char
                output += char
                i += 1
        elif char == '{':
            end_brace = template_str.find('}', i)
            if end_brace != -1:
                key = template_str[i+1:end_brace]
                value = data_dict.get(key)
                if value is not None:
                    output += str(value) if pd.notna(value) else ""
                else:
                    # If key not found, treat it as literal text
                    output += f"{{{key}}}"
                i = end_brace + 1
            else:  # Unmatched opening brace
                output += char
                i += 1
        else:
            output += char
            i += 1
    return output

st.set_page_config(layout="wide", page_title="Forum Post Creator")
inject_custom_css()

# --- Sidebar ---
st.sidebar.page_link("app.py", label="Back to Main Page", icon="🏠")

st.title("✍️ Forum Post Creator")

# --- Load Data and Template ---
def load_template():
    template_path = Path("data/forum-template.txt")
    templates = {}
    if not template_path.exists():
        return templates
    
    with open(template_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Corrected regex to only split on [key] that starts on a new line.
    pattern = re.compile(r'\[(.*?)\]\s*([\s\S]*?)(?=\n\s*\[|\Z)')
    matches = pattern.findall(content)
    
    for key, value in matches:
        templates[key.strip()] = value.strip()
        
    return templates

if 'diff_data' not in st.session_state or st.session_state['diff_data'].empty:
    st.warning("No difference data found. Please generate it from the main page.")
    st.page_link("app.py", label="Back to Main Page", icon="🏠")
    st.stop()

config = load_json_file(CONFIG_FILE)
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

# --- Date Filter Logic ---
st.subheader("Filter by Date Range")
if not display_df_all_cols.empty:
    min_date = display_df_all_cols['Start Time'].min().date()
    max_date = display_df_all_cols['Start Time'].max().date()

    # Get dates from config, default to data range
    start_date_str = config.get('post_start', min_date.isoformat())
    end_date_str = config.get('post_end', max_date.isoformat())

    # Convert to date objects and clamp
    try:
        start_date_value = date.fromisoformat(start_date_str)
    except (ValueError, TypeError):
        start_date_value = min_date
    try:
        end_date_value = date.fromisoformat(end_date_str)
    except (ValueError, TypeError):
        end_date_value = max_date

    start_date_value = max(min_date, min(start_date_value, max_date))
    end_date_value = max(min_date, min(end_date_value, max_date))

    col1, col2 = st.columns(2)
    with col1:
        start_date_filter = st.date_input(
            "Start date",
            value=start_date_value,
            min_value=min_date,
            max_value=max_date
        )
    with col2:
        end_date_filter = st.date_input(
            "End date",
            value=end_date_value,
            min_value=min_date,
            max_value=max_date
        )

    # Check if dates have changed and save to config
    config_changed = False
    if start_date_filter.isoformat() != config.get('post_start'):
        config['post_start'] = start_date_filter.isoformat()
        config_changed = True
    if end_date_filter.isoformat() != config.get('post_end'):
        config['post_end'] = end_date_filter.isoformat()
        config_changed = True
    
    if config_changed:
        save_json_file(CONFIG_FILE, config)

    mask = ((display_df_all_cols['Start Time'].dt.date >= start_date_filter) &
           (display_df_all_cols['Start Time'].dt.date <= end_date_filter))
    filtered_display_df = display_df_all_cols[mask]
else:
    filtered_display_df = display_df_all_cols

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
    if col in table_view_df.columns and pd.api.types.is_datetime64_any_dtype(table_view_df[col]):
        table_view_df[col] = table_view_df[col].dt.strftime(dt_format)

header_labels = {
    "Icon": "Icon", "Display Type": "Type", "Start Time": "Start", "End Time": "End", "Duration": "Days",
    "Featured Heroes (EN)": "Feat.(EN)", "Non-Featured Heroes (EN)": "Non-Feat.(EN)",
    "Featured Heroes (JA)": "Feat.(JA)", "Non-Featured Heroes (JA)": "Non-Feat.(JA)",
    "Event Name": "Event ID", "_diff_status": "Diff Status"
}

html_table = to_html_table(table_view_df, header_labels, columns_to_display=standard_cols)
st.markdown(html_table, unsafe_allow_html=True)

# --- Generate Post Text from Template ---
st.subheader("Generated Post Text")

if filtered_display_df.empty:
    st.info("No events match the selected date range.")
else:
    all_en_texts = []
    all_ja_texts = []
    # Iterate through the filtered dataframe which contains ALL columns needed for the template
    for index, row in filtered_display_df.iterrows():
        st.markdown(f"--- Event: **{row.get('Event Name', '')}** (`{row.get('_diff_status', '')}`) ---")
        
        status = row.get('_diff_status', 'unchanged')
        en_template_key = f"{status}_en"
        ja_template_key = f"{status}_ja"

        en_template_str = template.get(en_template_key, f"**English template for '{status}' not found.**")
        ja_template_str = template.get(ja_template_key, f"**Japanese template for '{status}' not found.**")

        # Prepare data for template
        template_data = row.to_dict()
        
        # Generate text using the new robust parser
        en_text = process_custom_template(en_template_str, template_data)
        ja_text = process_custom_template(ja_template_str, template_data)

        all_en_texts.append(en_text)
        all_ja_texts.append(ja_text)

        col1, col2 = st.columns(2)
        with col1:
            st.text_area("English Post", value=en_text, height=150, key=f"en_{index}")
        with col2:
            st.text_area("Japanese Post", value=ja_text, height=150, key=f"ja_{index}")

    # --- Summary Section ---
    st.subheader("📝 Summary for Copy & Paste")

    summary_en = "\r\n".join(all_en_texts)
    summary_ja = "\r\n".join(all_ja_texts)

    col1, col2 = st.columns(2)
    with col1:
        st.text_area("English Summary", value=summary_en, height=300, key="summary_en")
    with col2:
        st.text_area("Japanese Summary", value=summary_ja, height=300, key="summary_ja")
