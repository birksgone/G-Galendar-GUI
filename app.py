import streamlit as st
import pandas as pd
from pathlib import Path
import json
from datetime import datetime, date
import subprocess
import sys

from modules.data_loader import load_all_data
from modules.translation_engine import create_translation_dicts
from modules.display_formatter import format_dataframe_for_display

DATA_DIR = Path("data")
CONFIG_FILE = DATA_DIR / "config.json"
RULES_FILE = DATA_DIR / "type_mapping_rules.json"
EVENT_HISTORY_FILE = DATA_DIR / ".history_event.log"
HERO_GEN_SCRIPT_PATH = "D:/PyScript/EMP Extract/FLAT-EXTRACT/All Hero/generate_hero_dataset_gemini_v1.9.py"

def inject_custom_css():
    css_file = "styles.css"
    if Path(css_file).is_file():
        with open(css_file) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

def initialize_files():
    DATA_DIR.mkdir(exist_ok=True)
    if not CONFIG_FILE.exists():
        default_config = {
            "event_folder": "", "diff_folder": "",
            "filter_start_date": date.today().isoformat(),
            "filter_end_date": (date.today() + pd.Timedelta(days=30)).isoformat(),
            "timezone": "UTC", "display_mode": "Japanese"
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

def convert_posix_to_datetime(series, target_tz='UTC'):
    utc_time = pd.to_datetime(series + 946684800, unit='s', errors='coerce').dt.tz_localize('UTC')
    return utc_time.dt.tz_convert('Asia/Tokyo') if target_tz == 'JST' else utc_time

def calculate_duration(start_s, end_s):
    delta = end_s - start_s
    def format_delta(td):
        if pd.isna(td): return ""
        d, s = td.days, td.seconds
        h = s // 3600
        parts = [f"{d}d"] if d > 0 else []
        if h > 0: parts.append(f"{h}h")
        return " ".join(parts) if parts else ""
    return delta.apply(format_delta)

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
    save_to_history(EVENT_HISTORY_FILE, latest_folder)
    st.rerun()

if config.get("event_folder"):
    try:
        data = load_all_data(config["event_folder"], config.get("diff_folder"))
        en_map, ja_map = create_translation_dicts(data['hero_master_df'], data['g_sheet_df'])
        
        display_df = format_dataframe_for_display(data['main_df'].copy(), rules, en_map, ja_map)

        st.header(f"Event Display: `{config['event_folder']}`")
        c1, c2, c3, c4 = st.columns([1, 1, 1, 3])
        start_date_val = date.fromisoformat(config.get('filter_start_date', date.today().isoformat()))
        end_date_val = date.fromisoformat(config.get('filter_end_date', date.today().isoformat()))
        start_date_filter = c1.date_input("Start date", value=start_date_val)
        end_date_filter = c2.date_input("End date", value=end_date_val)
        display_mode = c3.radio("Language", ["Japanese", "English", "Both"], index=["Japanese", "English", "Both"].index(config.get("display_mode", "Japanese")))
        timezone = c4.radio("Timezone", ["UTC", "JST"], index=["UTC", "JST"].index(config.get("timezone", "UTC")), horizontal=True)

        config_changed = False
        if start_date_filter.isoformat() != config.get('filter_start_date'): config['filter_start_date'] = start_date_filter.isoformat(); config_changed = True
        if end_date_filter.isoformat() != config.get('filter_end_date'): config['filter_end_date'] = end_date_filter.isoformat(); config_changed = True
        if timezone != config.get('timezone'): config['timezone'] = timezone; config_changed = True
        if display_mode != config.get('display_mode'): config['display_mode'] = display_mode; config_changed = True
        if config_changed: save_json_file(CONFIG_FILE, config)

        display_df['Start Time'] = convert_posix_to_datetime(display_df['startDate'], timezone)
        display_df['End Time'] = convert_posix_to_datetime(display_df['endDate'], timezone)
        display_df['Duration'] = calculate_duration(display_df['Start Time'], display_df['End Time'])
        start_dt_aware = pd.to_datetime(start_date_filter).tz_localize(display_df['Start Time'].dt.tz)
        end_dt_aware = (pd.to_datetime(end_date_filter) + pd.Timedelta(days=1, seconds=-1)).tz_localize(display_df['Start Time'].dt.tz)
        filtered_df = display_df[display_df['Start Time'].between(start_dt_aware, end_dt_aware)].copy()
        
        dt_format = "%Y-%m-%d %H:%M"
        filtered_df['Start Time'] = filtered_df['Start Time'].dt.strftime(dt_format)
        filtered_df['End Time'] = filtered_df['End Time'].dt.strftime(dt_format)

        st.subheader("Filtered Event List")
        
        base_cols = ['Icon', 'Display Type', 'Start Time', 'End Time', 'Duration']
        consolidated_cols = ['Featured Heroes (JP)', 'Featured Heroes (EN)', 'Other Heroes (JP)', 'Other Heroes (EN)']
        raw_data_cols = [c for c in data['main_df'].columns]
        
        final_display_cols = base_cols + consolidated_cols + raw_data_cols
        
        st.dataframe(
            filtered_df,
            height=800,
            column_order=[c for c in final_display_cols if c in filtered_df.columns],
            column_config={
                "Icon": st.column_config.ImageColumn("Icon", width="small", help="Event Icon")
            }
        )

    except FileNotFoundError as e:
         st.warning(f"Master CSV not found for '{config['event_folder']}'. Please generate it.")
         if st.button("Generate Hero Master Now"):
                command = [sys.executable, HERO_GEN_SCRIPT_PATH, "--version_folder", config["event_folder"], "--cutoff_date", "2300-01-01"]
                with st.spinner(f"Running hero generator script..."):
                    result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='replace')
                    if result.returncode != 0: st.error(result.stderr or result.stdout); st.stop()
                    else: st.success("Hero master generated!"); st.rerun()
    except Exception as e:
        st.error(f"Failed to load or process data: {e}")
else:
    st.info("Please specify data folders in the sidebar and click 'Load Data'.")