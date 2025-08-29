import streamlit as st
import pandas as pd
from pathlib import Path
import json
from datetime import datetime, date
import subprocess
import sys
import gspread
from google.oauth2.service_account import Credentials
from modules.translation_engine import create_translation_dicts

# --- Constants ---
DATA_DIR = Path("data")
EVENT_BASE_DIR = Path("D:/PyScript/EMP Extract/")
CONFIG_FILE = DATA_DIR / "config.json"
EVENT_HISTORY_FILE = DATA_DIR / ".history_event.log"
HERO_GEN_SCRIPT_PATH = "D:/PyScript/EMP Extract/FLAT-EXTRACT/All Hero/generate_hero_dataset_gemini_v1.9.py"
GCP_CREDS_PATH = "client_secret.json"
GOOGLE_SHEET_ID = "18Qv901QZ8irS1wYh-jbFIPFdsrUFZ01AB6EcN7SX5qM"
GOOGLE_SHEET_NAME = "ALLH"

# --- Helper Functions ---
def initialize_files():
    DATA_DIR.mkdir(exist_ok=True)
    if not CONFIG_FILE.exists():
        default_config = {"event_folder": "", "diff_folder": "", "filter_start_date": date.today().isoformat(), "filter_end_date": (date.today() + pd.Timedelta(days=30)).isoformat(), "timezone": "UTC", "display_mode": "Japanese"}
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
    with open(filepath, "r", encoding="utf-8") as f: lines = f.read().splitlines(); return list(dict.fromkeys(filter(None, lines)))
def save_to_history(filepath, new_entry):
    history = load_history(filepath);
    if new_entry in history: history.remove(new_entry)
    if new_entry: history.insert(0, new_entry)
    with open(filepath, "w", encoding="utf-8") as f: f.write("\n".join(history))

# --- Data Processing Functions ---
@st.cache_data
def load_all_data(latest_folder, diff_folder):
    data = {}
    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds = Credentials.from_service_account_file(GCP_CREDS_PATH, scopes=scopes)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)
    worksheet = spreadsheet.worksheet(GOOGLE_SHEET_NAME)
    g_sheet_records = worksheet.get_all_values()
    g_sheet_data = [row[:3] for row in g_sheet_records]
    # Use first row as header for the first 3 columns
    header = g_sheet_data[0]
    data['g_sheet_df'] = pd.DataFrame(g_sheet_data[1:], columns=header)

    latest_dir = EVENT_BASE_DIR / latest_folder
    try:
        hero_master_path = next(latest_dir.glob("*_private_heroes_*_en.csv"))
        data['hero_master_df'] = pd.read_csv(hero_master_path)
    except StopIteration: raise FileNotFoundError(f"Hero master CSV not found in '{latest_dir}'.")
    
    data['main_df'] = pd.read_csv(next(latest_dir.glob("calendar-export-*.csv")))
    
    if diff_folder: data['diff_df'] = pd.read_csv(next((EVENT_BASE_DIR / diff_folder).glob("calendar-export-*.csv")))
    else: data['diff_df'] = None
    return data
@st.cache_data
def get_translation_maps(_hero_master_df, _g_sheet_df):
    return create_translation_dicts(_hero_master_df, _g_sheet_df)
def convert_posix_to_datetime(series, target_tz='UTC'):
    utc_time = pd.to_datetime(series + 946684800, unit='s', errors='coerce').dt.tz_localize('UTC')
    return utc_time.dt.tz_convert('Asia/Tokyo') if target_tz == 'JST' else utc_time
def calculate_duration(start_s, end_s):
    delta = end_s - start_s
    def format_delta(td):
        if pd.isna(td): return ""
        d, s = td.days, td.seconds; h = s // 3600
        parts = [f"{d}d"] if d > 0 else [];
        if h > 0: parts.append(f"{h}h")
        return " ".join(parts) if parts else ""
    return delta.apply(format_delta)

# --- Main App Logic ---
st.set_page_config(layout="wide"); st.title("Event Calendar Management Dashboard")
initialize_files(); config = load_json_file(CONFIG_FILE)

# --- Sidebar ---
st.sidebar.header("Select Data Sources")
latest_folder = st.sidebar.text_input("① Latest Data (Required)", value=config.get("event_folder"))
event_history = load_history(EVENT_HISTORY_FILE); diff_options = [h for h in event_history if h != latest_folder]
if not diff_options: diff_folder = st.sidebar.selectbox("② Previous Data for Diff", ["No options"], disabled=True)
else:
    current_diff = config.get("diff_folder"); index = diff_options.index(current_diff) if current_diff in diff_options else 0
    diff_folder = st.sidebar.selectbox("② Previous Data for Diff", diff_options, index=index)

if st.sidebar.button("Load Data", key="load_data_button"):
    config['event_folder'] = latest_folder; config['diff_folder'] = diff_folder
    save_json_file(CONFIG_FILE, config); save_to_history(EVENT_HISTORY_FILE, latest_folder)
    st.rerun()

# --- Main Screen ---
if config.get("event_folder"):
    try:
        latest_dir = EVENT_BASE_DIR / config["event_folder"]
        try: next(latest_dir.glob("*_private_heroes_*_en.csv"))
        except StopIteration:
            st.warning(f"Hero master not found. Please generate it.");
            if st.button("Generate Hero Master Now"):
                command = [sys.executable, HERO_GEN_SCRIPT_PATH, "--version_folder", config["event_folder"], "--cutoff_date", "2300-01-01"]
                with st.spinner(f"Running hero generator script..."):
                    result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='replace')
                    if result.returncode != 0: st.error(result.stderr or result.stdout); st.stop()
                    else: st.success("Hero master generated!"); st.rerun()
            st.stop()

        data = load_all_data(config["event_folder"], config.get("diff_folder"))
        df = data['main_df'].copy()
        en_map, ja_map = get_translation_maps(data['hero_master_df'], data['g_sheet_df'])

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

        df['Start Time'] = convert_posix_to_datetime(df['startDate'], timezone); df['End Time'] = convert_posix_to_datetime(df['endDate'], timezone); df['Duration'] = calculate_duration(df['Start Time'], df['End Time'])
        start_dt_aware = pd.to_datetime(start_date_filter).tz_localize(df['Start Time'].dt.tz); end_dt_aware = (pd.to_datetime(end_date_filter) + pd.Timedelta(days=1, seconds=-1)).tz_localize(df['Start Time'].dt.tz)
        filtered_df = df[df['Start Time'].between(start_dt_aware, end_dt_aware)].copy()
        
        hero_cols_all = [col for col in ['advertisedHero', 'H1', 'H2', 'H3', 'H4', 'H5', 'H6', 'C1', 'C2', 'C3', 'C4', 'C5', 'C6'] if col in filtered_df.columns]
        
        # --- Create the final dataframe for display ---
        display_df = filtered_df.copy()
        for col in hero_cols_all:
            display_df[f'{col} (JP)'] = display_df[col].map(ja_map).fillna('')
            display_df[f'{col} (EN)'] = display_df[col].map(en_map).fillna('')

        dt_format = "%Y-%m-%d %H:%M"; display_df['Start Time'] = display_df['Start Time'].dt.strftime(dt_format); display_df['End Time'] = display_df['End Time'].dt.strftime(dt_format)
        
        st.subheader("Filtered Event List")
        # Define the final column order
        base_cols = ['Start Time', 'End Time', 'Duration', 'event', 'type']
        
        if display_mode == "Japanese":
            display_cols = base_cols + [f'{c} (JP)' for c in hero_cols_all]
        elif display_mode == "English":
            display_cols = base_cols + [f'{c} (EN)' for c in hero_cols_all]
        else: # Both
            display_cols = base_cols
            for col in hero_cols_all:
                display_cols.extend([f'{col} (JP)', f'{col} (EN)'])

        st.dataframe(display_df[[c for c in display_cols if c in display_df.columns]], height=800)

    except Exception as e:
        st.error(f"Failed to load or process data. Check folder names and file contents.\nError: {e}")
else:
    st.info("Please specify data folders in the sidebar and click 'Load Data'.")