# app.py

import streamlit as st
import pandas as pd
from pathlib import Path
import json
from datetime import datetime, date
import subprocess
import sys
import io
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from modules.data_loader import load_all_data
from modules.translation_engine import create_translation_dicts
from modules.display_formatter import format_dataframe_for_display, to_html_table
from modules.diff_engine import compare_dataframes
from modules.forum_post_creator import render_forum_post_creator
from modules.discord_post_creator import render_discord_post_creator

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
    if new_entry in history: 
        history.remove(new_entry)
    if new_entry:
        history.insert(0, new_entry)
    with open(filepath, "w", encoding="utf-8") as f: 
        f.write("\n".join(history))

@st.cache_data
def load_and_process_data(latest_folder, diff_folder):
    """
    データの読み込み、差分比較、翻訳マップ作成までを一括で行う。
    結果はStreamlitによってキャッシュされる。
    """
    try:
        data = load_all_data(latest_folder, diff_folder)
        
        comparison_df = None
        if data['diff_df'] is not None:
            comparison_df = compare_dataframes(data['main_df'], data['diff_df'])
        else:
            comparison_df = data['main_df'].copy()
            comparison_df['_diff_status'] = 'unchanged'
            comparison_df['_changed_columns'] = [[] for _ in range(len(comparison_df))]

        en_map, ja_map = create_translation_dicts(data['hero_master_df'], data['g_sheet_df'])
        
        return comparison_df, en_map, ja_map
    except FileNotFoundError as e:
        st.error(f"ファイルが見つかりません: {e}")
        st.info("以下のことを確認してください:")
        st.info("1. EMP Extractフォルダに最新のCSVファイルがあるか")
        st.info("2. CSVファイル名が 'calendar-export-{フォルダ名}.csv' 形式になっているか")
        st.info("3. フォルダ名が正しいか (例: V7900R-2025-09-15)")
        raise
    except Exception as e:
        st.error(f"データの読み込み中にエラーが発生しました: {e}")
        raise

def debug_google_drive_data():
    st.subheader("Google Drive Integration Status")
    with st.expander("Click to view Google Drive integration details"):
        try:
            # Check if service account file exists
            SERVICE_ACCOUNT_FILE = "client_secret.json"
            if not Path(SERVICE_ACCOUNT_FILE).exists():
                st.warning(f"Service account file '{SERVICE_ACCOUNT_FILE}' not found.")
                st.info("Google Drive access requires a service account JSON file.")
                return
            
            st.success("Service account file found.")
            
            # Check if hero_master.csv exists and show info
            LOCAL_FILEPATH = Path("data") / "hero_master.csv"
            if LOCAL_FILEPATH.exists():
                file_size = LOCAL_FILEPATH.stat().st_size
                mod_time = datetime.fromtimestamp(LOCAL_FILEPATH.stat().st_mtime)
                st.info(f"hero_master.csv file exists ({file_size} bytes)")
                st.info(f"Last modified: {mod_time.strftime('%Y-%m-%d %H:%M:%S')}")
                try:
                    df = pd.read_csv(LOCAL_FILEPATH)
                    st.write(f"File contains {len(df)} rows and {len(df.columns)} columns")
                    st.write("Sample columns:", list(df.columns)[:5])
                except Exception as e:
                    st.warning(f"Could not read CSV file: {e}")
            else:
                st.info("hero_master.csv file will be downloaded when data is loaded")
            
            st.info("Note: The hero_master.csv file is automatically downloaded from Google Drive")
            st.info("every time data is loaded, ensuring fresh data (updated every 6 hours).")

        except Exception as e:
            st.error("An error occurred while checking Google Drive integration.")
            st.exception(e)

st.set_page_config(layout="wide")
inject_custom_css()
st.title("Event Calendar Management Dashboard")
debug_google_drive_data()

initialize_files()
config = load_json_file(CONFIG_FILE)
rules = load_json_file(RULES_FILE, [])

st.sidebar.header("Select Data Sources")
latest_folder = st.sidebar.text_input("① Latest Data (Required)", value=config.get("event_folder"))

# Load history and create dropdown first
event_history = load_history(EVENT_HISTORY_FILE)
diff_options = [h for h in event_history if h != latest_folder]
if not diff_options:
    diff_folder = st.sidebar.selectbox("② Previous Data for Diff", ["No options"], disabled=True)
else:
    current_diff = config.get("diff_folder")
    index = diff_options.index(current_diff) if current_diff in diff_options else 0
    diff_folder = st.sidebar.selectbox("② Previous Data for Diff", diff_options, index=index)

# Load history after potential updates
if st.sidebar.button("Load Data", key="load_data_button"):
    save_to_history(EVENT_HISTORY_FILE, latest_folder)
    config['event_folder'] = latest_folder
    config['diff_folder'] = diff_folder
    save_json_file(CONFIG_FILE, config)
    st.rerun()

# JSON変換ツールへのリンク
st.sidebar.markdown("---")
st.sidebar.page_link("pages/_2_JSON_to_Template_Converter.py", label="🔄 JSON Template Converter", icon="🔄")
        
if latest_folder:
    try:
        comparison_df, en_map, ja_map = load_and_process_data(latest_folder, diff_folder)
        
        st.header(f"Event Display: `{latest_folder}`")
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

        # Get timezone from first valid datetime in Start Time column
        valid_start_times = display_df['Start Time'].dropna()
        if not valid_start_times.empty:
            tz = valid_start_times.iloc[0].tz
        else:
            tz = 'UTC'
        
        start_dt_aware = pd.to_datetime(start_date_filter).tz_localize(tz)
        end_dt_aware = (pd.to_datetime(end_date_filter) + pd.Timedelta(days=1, seconds=-1)).tz_localize(tz)
        
        # Filter only rows with valid datetime values
        valid_mask = display_df['Start Time'].notna()
        filtered_df = display_df[valid_mask & display_df['Start Time'].between(start_dt_aware, end_dt_aware)].copy()
        
        st.subheader("Filtered Event List")
        
        if not filtered_df.empty:
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
                "All Columns": ordered_all_cols,
                "Changes Only": []  # Empty list indicates post creator mode
            }
            
            # Post type selection
            post_types = ["Forum Post", "Discord Post"]
            selected_post_type = st.selectbox(
                "Post Type", 
                post_types,
                key="post_type_select",
                index=0
            )
            
            preset_choice = st.radio("Presets", list(presets.keys()), horizontal=True, key="preset_radio")
            
            if preset_choice == "Changes Only":
                # Show appropriate post creator based on selection
                diff_df = comparison_df[comparison_df['_diff_status'] != 'unchanged'].copy()
                if not diff_df.empty:
                    if selected_post_type == "Forum Post":
                        render_forum_post_creator(diff_df, en_map, ja_map, timezone)
                    elif selected_post_type == "Discord Post":
                        render_discord_post_creator(diff_df, en_map, ja_map, timezone)
                else:
                    st.info("No changes found to create posts.")
            else:
                # Show normal table view
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

                selected_user_cols = st.session_state.selected_cols
                final_df = filtered_df.copy() 
                
                # CSV export functionality
                csv_data = final_df[selected_user_cols].to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label="📥 Export to CSV", 
                    data=csv_data,
                    file_name=f"events_{latest_folder}_{date.today().isoformat()}.csv",
                    mime="text/csv",
                    key="csv_export_button"
                )
                
                st.markdown('<div class="table-container">', unsafe_allow_html=True)
                html_table = to_html_table(final_df, header_labels, columns_to_display=selected_user_cols, data_dir=latest_folder)
                st.markdown(html_table, unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

        else:
            st.warning("No events found in the selected date range.")

    except FileNotFoundError as e:
        st.error(f"ファイルが見つかりません: {e}")
        st.info("以下のことを確認してください:")
        st.info("1. EMP Extractフォルダに最新のCSVファイルがあるか")
        st.info("2. CSVファイル名が 'calendar-export-{フォルダ名}.csv' 形式になっているか")
        st.info("3. フォルダ名が正しいか (例: V7900R-2025-09-15)")
        st.info("4. ファイルパス: D:/PyScript/EMP Extract/{フォルダ名}/calendar-export-{フォルダ名}.csv")
        st.button("再試行", on_click=lambda: st.rerun())
    except Exception as e:
        st.error(f"データの読み込み中にエラーが発生しました: {e}")
        st.exception(e)
        st.button("再試行", on_click=lambda: st.rerun())
else:
    st.info("Please specify data folders in the sidebar and click 'Load Data'.")
