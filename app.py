import streamlit as st
import pandas as pd
from pathlib import Path
import json
from datetime import datetime, date
import subprocess
import sys

from modules.data_loader import load_all_data
from modules.translation_engine import create_translation_dicts
from modules.display_formatter import format_dataframe_for_display, to_html_table
from modules.diff_engine import compare_dataframes

DATA_DIR = Path("data")
CONFIG_FILE = DATA_DIR / "config.json"
RULES_FILE = DATA_DIR / "type_mapping_rules.json"
EVENT_HISTORY_FILE = DATA_DIR / ".history_event.log"
HERO_GEN_SCRIPT_PATH = "D:/PyScript/EMP Extract/FLAT-EXTRACT/All Hero/generate_hero_dataset_gemini_v1.9.py"

def inject_custom_css():
    css_file = "styles.css"
    if Path(css_file).is_file():
        with open(css_file, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

def initialize_files():
    DATA_DIR.mkdir(exist_ok=True)
    if not CONFIG_FILE.exists():
        default_config = {
            "event_folder": "", "diff_folder": "",
            "filter_start_date": date.today().isoformat(),
            "filter_end_date": (date.today() + pd.Timedelta(days=30)).isoformat(),
            "timezone": "UTC",
        }
        save_json_file(CONFIG_FILE, default_config)

def load_json_file(filepath, default_data={}):
    if not filepath.exists(): return default_data
    try:
        with open(filepath, "r", encoding="utf-8") as f: return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError): return default_data

def save_json_file(filepath, data):
    with open(filepath, "w", encoding="utf-8") as f: json.dump(data, f, indent=2, ensure_ascii=False)

def load_history(filepath):
    if not filepath.exists(): return []
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()
        return list(dict.fromkeys(filter(None, lines)))

def save_to_history(filepath, new_entry):
    history = load_history(filepath)
    if new_entry in history: history.remove(new_entry)
    if new_entry: history.insert(0, new_entry)
    with open(filepath, "w", encoding="utf-8") as f: f.write("\n".join(history))

st.set_page_config(layout="wide")
inject_custom_css()
st.title("Event Calendar Management Dashboard")

initialize_files()
config = load_json_file(CONFIG_FILE)
rules = load_json_file(RULES_FILE, [])

st.sidebar.header("Select Data Sources")
latest_folder = st.sidebar.text_input("① Latest Data (Required)", value=config.get("event_folder"))
event_history = load_history(EVENT_HISTORY_FILE)
diff_options = [h for h in event_history if h != latest_folder]
if not diff_options:
    diff_folder = st.sidebar.selectbox("② Previous Data for Diff", ["No options"], disabled=True)
else:
    current_diff = config.get("diff_folder")
    index = diff_options.index(current_diff) if current_diff in diff_options else 0
    diff_folder = st.sidebar.selectbox("② Previous Data for Diff", diff_options, index=index)

if st.sidebar.button("Load Data", key="load_data_button"):
    config['event_folder'] = latest_folder
    config['diff_folder'] = diff_folder
    save_json_file(CONFIG_FILE, config)
    st.rerun()

if config.get("event_folder"):
    try:
        data = load_all_data(config["event_folder"], config.get("diff_folder"))
        
        comparison_df = None
        if data['diff_df'] is not None:
            comparison_df = compare_dataframes(data['main_df'], data['diff_df'])
        else:
            comparison_df = data['main_df'].copy()
            comparison_df['_diff_status'] = 'unchanged'
            comparison_df['_changed_columns'] = [[] for _ in range(len(comparison_df))]

        en_map, ja_map = create_translation_dicts(data['hero_master_df'], data['g_sheet_df'])
        
        st.header(f"Event Display: `{config['event_folder']}`")
        col1, col2, col3 = st.columns(3)
        with col1:
            start_date_val = date.fromisoformat(config.get('filter_start_date', date.today().isoformat()))
            start_date_filter = st.date_input("Start date", value=start_date_val)
        with col2:
            end_date_val = date.fromisoformat(config.get('filter_end_date', date.today().isoformat()))
            end_date_filter = st.date_input("End date", value=end_date_val)
        with col3:
            timezone = st.selectbox("Timezone", ["UTC", "JST"], index=["UTC", "JST"].index(config.get("timezone", "UTC")))

        config_changed = False
        if start_date_filter.isoformat() != config.get('filter_start_date'): config['filter_start_date'] = start_date_filter.isoformat(); config_changed = True
        if end_date_filter.isoformat() != config.get('filter_end_date'): config['filter_end_date'] = end_date_filter.isoformat(); config_changed = True
        if timezone != config.get('timezone'): config['timezone'] = timezone; config_changed = True
        if config_changed: save_json_file(CONFIG_FILE, config)

        display_df = format_dataframe_for_display(comparison_df, rules, en_map, ja_map, timezone)

        start_dt_aware = pd.to_datetime(start_date_filter).tz_localize(display_df['Start Time'].dt.tz)
        end_dt_aware = (pd.to_datetime(end_date_filter) + pd.Timedelta(days=1, seconds=-1)).tz_localize(display_df['Start Time'].dt.tz)
        
        filtered_df = display_df[display_df['Start Time'].between(start_dt_aware, end_dt_aware)].copy()
        
        st.subheader("Filtered Event List")
        
        if not filtered_df.empty:
            # 日付を文字列フォーマットに戻す処理
            dt_format = "%Y-%m-%d %H:%M"
            for col in ['Start Time', 'End Time']:
                if col in filtered_df.columns and pd.api.types.is_datetime64_any_dtype(filtered_df[col]):
                     filtered_df[col] = filtered_df[col].dt.strftime(dt_format)

            header_labels = {
                "Icon": "Icon", "Display Type": "Type", "Start Time": "Start", "End Time": "End", "Duration": "Days",
                "Featured Heroes (EN)": "Feat.(EN)", "Non-Featured Heroes (EN)": "Non-Feat.(EN)",
                "Featured Heroes (JA)": "Feat.(JA)", "Non-Featured Heroes (JA)": "Non-Feat.(JA)",
                "Event Name": "Event ID", "_diff_status": "Diff Status", "_changed_columns": "Changed Parts"
            }
            all_df_columns = display_df.columns.tolist()
            for col in all_df_columns:
                if col not in header_labels:
                    header_labels[col] = col
            label_to_col_map = {v: k for k, v in header_labels.items()}

            standard_cols = ['Icon', 'Display Type', 'questline', 'Start Time', 'End Time', 'Duration',
                             'Featured Heroes (EN)', 'Non-Featured Heroes (EN)',
                             'Featured Heroes (JA)', 'Non-Featured Heroes (JA)']
            
            other_cols = sorted([col for col in all_df_columns if col not in standard_cols])
            ordered_all_cols = standard_cols + other_cols

            presets = {
                "Standard": standard_cols,
                "All Columns": ordered_all_cols
            }
            
            # --- UI: プリセット選択 ---
            preset_choice = st.radio("Presets", list(presets.keys()), horizontal=True, key="preset_radio")
            
            # --- UI: 列の個別カスタマイズ ---
            with st.expander("Customize Columns", expanded=False):
                if 'selected_cols' not in st.session_state:
                    st.session_state.selected_cols = presets["Standard"]
                if st.session_state.get('current_preset') != preset_choice:
                    st.session_state.selected_cols = presets[preset_choice]
                    st.session_state.current_preset = preset_choice

                selected_labels = st.multiselect(
                    "Select columns to display:",
                    options=[header_labels.get(col, col) for col in ordered_all_cols],
                    default=[header_labels.get(col, col) for col in st.session_state.selected_cols if col in header_labels],
                )
                st.session_state.selected_cols = [label_to_col_map[label] for label in selected_labels]

            # --- テーブル生成 ---
            selected_user_cols = st.session_state.selected_cols
            final_df = filtered_df.copy()
            
            st.markdown('<div class="table-container">', unsafe_allow_html=True)
            html_table = to_html_table(final_df, header_labels, columns_to_display=selected_user_cols, data_dir=latest_folder)
            st.markdown(html_table, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        else:
            st.warning("No events found in the selected date range.")

    except Exception as e:
        st.error(f"Failed to load or process data: {e}")
        st.exception(e)
else:
    st.info("Please specify data folders in the sidebar and click 'Load Data'.")