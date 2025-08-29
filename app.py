import streamlit as st
import pandas as pd
from pathlib import Path
import json
from datetime import datetime, date

# --- Constants: File Paths ---
DATA_DIR = Path("data")
EVENT_BASE_DIR = Path("D:/PyScript/EMP Extract/")
LANG_BASE_DIR = Path("D:/Nox Screeshot/Nox SS Directory/Download/v32/Download/Download/")
CONFIG_FILE = DATA_DIR / "config.json"
EVENT_HISTORY_FILE = DATA_DIR / ".history_event.log"
LANG_HISTORY_FILE = DATA_DIR / ".history_lang.log"

# --- Helper Functions for File I/O ---
def initialize_files():
    """Ensure data directory and essential files exist."""
    DATA_DIR.mkdir(exist_ok=True)
    if not CONFIG_FILE.exists():
        default_config = {
            "event_folder": "", "diff_folder": "", "lang_folder": "",
            "filter_start_date": date.today().isoformat(),
            "filter_end_date": (date.today() + pd.Timedelta(days=30)).isoformat(),
            "timezone": "UTC"
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

# --- Data Processing Functions ---
@st.cache_data
def load_csv_data(latest_folder, diff_folder, lang_folder):
    data = {}
    latest_dir = EVENT_BASE_DIR / latest_folder
    data['main_df'] = pd.read_csv(next(latest_dir.glob("calendar-export-*.csv")))
    
    if diff_folder:
        diff_dir = EVENT_BASE_DIR / diff_folder
        data['diff_df'] = pd.read_csv(next(diff_dir.glob("calendar-export-*.csv")))
    else: data['diff_df'] = None
    
    lang_dir = LANG_BASE_DIR / lang_folder
    data['ja_df'] = pd.read_csv(lang_dir / "Japanese.csv")
    data['en_df'] = pd.read_csv(lang_dir / "English.csv")
    return data

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
st.set_page_config(layout="wide")
st.title("Event Calendar Management Dashboard")

initialize_files()
config = load_json_file(CONFIG_FILE)

# --- Sidebar UI ---
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

lang_folder = st.sidebar.text_input("③ Language Data (Required)", value=config.get("lang_folder"))

# ★★★ Corrected: Button only updates folder configs and histories ★★★
if st.sidebar.button("Load New Data"):
    config['event_folder'] = latest_folder
    config['diff_folder'] = diff_folder
    config['lang_folder'] = lang_folder
    
    save_json_file(CONFIG_FILE, config)
    save_to_history(EVENT_HISTORY_FILE, latest_folder)
    save_to_history(LANG_HISTORY_FILE, lang_folder)
    st.rerun()

# --- Main Screen ---
if config.get("event_folder") and config.get("lang_folder"):
    try:
        data = load_csv_data(config["event_folder"], config.get("diff_folder"), config["lang_folder"])
        df = data['main_df'].copy()

        st.header(f"Event Display: `{config['event_folder']}`")
        col1, col2, col3 = st.columns([1, 1, 2])
        
        start_date_val = date.fromisoformat(config.get('filter_start_date', date.today().isoformat()))
        end_date_val = date.fromisoformat(config.get('filter_end_date', date.today().isoformat()))

        start_date_filter = col1.date_input("Start date", value=start_date_val)
        end_date_filter = col2.date_input("End date", value=end_date_val)
        timezone = col3.radio("Timezone", ["UTC", "JST"], index=["UTC", "JST"].index(config.get("timezone", "UTC")), horizontal=True)

        # --- Check for changes and save to config ---
        config_changed = False
        if start_date_filter.isoformat() != config.get('filter_start_date'):
            config['filter_start_date'] = start_date_filter.isoformat()
            config_changed = True
        if end_date_filter.isoformat() != config.get('filter_end_date'):
            config['filter_end_date'] = end_date_filter.isoformat()
            config_changed = True
        if timezone != config.get('timezone'):
            config['timezone'] = timezone
            config_changed = True
        
        if config_changed:
            save_json_file(CONFIG_FILE, config)

        # --- Process and display data ---
        df['Start Time'] = convert_posix_to_datetime(df['startDate'], timezone)
        df['End Time'] = convert_posix_to_datetime(df['endDate'], timezone)
        df['Duration'] = calculate_duration(df['Start Time'], df['End Time'])
        
        start_dt = pd.to_datetime(start_date_filter)
        end_dt = pd.to_datetime(end_date_filter)
        start_dt_aware = start_dt.tz_localize(df['Start Time'].dt.tz)
        end_dt_aware = (end_dt + pd.Timedelta(days=1, seconds=-1)).tz_localize(df['Start Time'].dt.tz)
        
        filtered_df = df[df['Start Time'].between(start_dt_aware, end_dt_aware)].copy()
        
        dt_format = "%Y-%m-%d %H:%M"
        filtered_df['Start Time'] = filtered_df['Start Time'].dt.strftime(dt_format)
        filtered_df['End Time'] = filtered_df['End Time'].dt.strftime(dt_format)

        st.subheader("Filtered Event List")
        display_cols = ['Start Time', 'End Time', 'Duration', 'event', 'type', 'advertisedHero']
        st.dataframe(filtered_df[[c for c in display_cols if c in filtered_df.columns]])

    except Exception as e:
        st.error(f"Failed to load or process data. Check folder names and file contents.\nError: {e}")
else:
    st.info("Please specify data folders in the sidebar and click 'Load New Data'.")