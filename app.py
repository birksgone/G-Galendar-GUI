import streamlit as st
import pandas as pd
from pathlib import Path
import json
from datetime import datetime, time

# --- Constants ---
DATA_DIR = Path("data")
EVENT_BASE_DIR = Path("D:/PyScript/EMP Extract/")
LANG_BASE_DIR = Path("D:/Nox Screeshot/Nox SS Directory/Download/v32/Download/Download/")
CONFIG_FILE = DATA_DIR / "config.json"
EVENT_HISTORY_FILE = DATA_DIR / ".history_event.log"
LANG_HISTORY_FILE = DATA_DIR / ".history_lang.log"

# --- Helper Functions ---
def initialize_data_dir():
    DATA_DIR.mkdir(exist_ok=True)

def load_json_file(filepath, default_data={}):
    if not filepath.exists(): return default_data
    try:
        with open(filepath, "r", encoding="utf-8") as f: return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError): return default_data

def save_json_file(filepath, data):
    initialize_data_dir()
    with open(filepath, "w", encoding="utf-8") as f: json.dump(data, f, indent=2, ensure_ascii=False)

def load_history(filepath):
    if not filepath.exists(): return []
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()
        return list(dict.fromkeys(filter(None, lines)))

def save_to_history(filepath, new_entry):
    initialize_data_dir()
    history = load_history(filepath)
    if new_entry in history: history.remove(new_entry)
    if new_entry: history.insert(0, new_entry)
    with open(filepath, "w", encoding="utf-8") as f: f.write("\n".join(history))

# --- Data Processing Functions ---
def convert_posix_to_datetime(series, target_tz='UTC'):
    """Converts a POSIX timestamp series to a timezone-aware datetime series."""
    # Convert game's POSIX timestamp to standard UTC datetime
    utc_time = pd.to_datetime(series + 946684800, unit='s', errors='coerce').dt.tz_localize('UTC')
    if target_tz == 'JST':
        return utc_time.dt.tz_convert('Asia/Tokyo')
    return utc_time

def calculate_duration(start_series, end_series):
    """Calculates the duration between two datetime series and formats it as a string."""
    delta = end_series - start_series
    
    def format_delta(td):
        if pd.isna(td):
            return ""
        days = td.days
        hours = td.seconds // 3600
        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        return " ".join(parts) if parts else ""
        
    return delta.apply(format_delta)

# --- Page Setup & Initialization ---
st.set_page_config(layout="wide")
st.title("Event Calendar Management Dashboard")
initialize_data_dir()

# Load last used config and history
config = load_json_file(CONFIG_FILE)
event_history = load_history(EVENT_HISTORY_FILE)
lang_history = load_history(LANG_HISTORY_FILE)

# --- Sidebar UI ---
st.sidebar.header("Select Data Sources")

st.sidebar.subheader("① Latest Data (Required)")
latest_folder = st.sidebar.text_input("Enter daily folder name", value=config.get("event_folder", ""), key="latest_folder_input")

st.sidebar.subheader("② Previous Data for Diff")
diff_options = [h for h in event_history if h != latest_folder]
if not diff_options:
    st.sidebar.selectbox("Select a past folder to compare", options=["No options to select"], index=0, disabled=True, key="diff_folder_select")
    diff_folder = None
else:
    diff_folder = st.sidebar.selectbox("Select a past folder to compare", options=diff_options, index=0, key="diff_folder_select")

st.sidebar.subheader("③ Language Data (Required)")
lang_folder = st.sidebar.text_input("Enter Version/TextAsset folder name", value=config.get("lang_folder", ""), key="lang_folder_input")

st.sidebar.subheader("④ Load Data")
if st.sidebar.button("Load & Display"):
    try:
        # Load all data into session state to persist it across reruns
        latest_dir = EVENT_BASE_DIR / latest_folder
        st.session_state['main_df'] = pd.read_csv(next(latest_dir.glob("calendar-export-*.csv")))
        
        if diff_folder:
            diff_dir = EVENT_BASE_DIR / diff_folder
            st.session_state['diff_df'] = pd.read_csv(next(diff_dir.glob("calendar-export-*.csv")))
        else:
            st.session_state['diff_df'] = None

        lang_dir = LANG_BASE_DIR / lang_folder
        st.session_state['ja_df'] = pd.read_csv(lang_dir / "Japanese.csv")
        st.session_state['en_df'] = pd.read_csv(lang_dir / "English.csv")

        # Save history and config
        save_to_history(EVENT_HISTORY_FILE, latest_folder)
        save_to_history(LANG_HISTORY_FILE, lang_folder)
        new_config = {"event_folder": latest_folder, "lang_folder": lang_folder}
        save_json_file(CONFIG_FILE, new_config)
        
        st.success("All data loaded successfully!")
        st.session_state['data_loaded'] = True

    except Exception as e:
        st.error(f"An error occurred during data loading: {e}")
        st.session_state['data_loaded'] = False

# --- Main Screen Display (only if data is loaded) ---
if st.session_state.get('data_loaded', False):
    st.header(f"Event Display: `{config.get('event_folder')}`")
    
    # --- UI Controls for Filtering ---
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        start_date_filter = st.date_input("Start date")
    with col2:
        end_date_filter = st.date_input("End date")
    with col3:
        timezone = st.radio("Timezone", ["UTC", "JST"], horizontal=True)

    # --- Data Processing ---
    df = st.session_state['main_df'].copy()

    # Convert POSIX to datetime based on selected timezone
    df['Start Time'] = convert_posix_to_datetime(df['startDate'], timezone)
    df['End Time'] = convert_posix_to_datetime(df['endDate'], timezone)

    # Calculate duration
    df['Duration'] = calculate_duration(df['Start Time'], df['End Time'])

    # Apply date filter
    start_datetime = pd.to_datetime(start_date_filter)
    end_datetime = pd.to_datetime(end_date_filter)
    # Combine date and time for accurate filtering, tz-aware
    start_dt_aware = start_datetime.tz_localize(df['Start Time'].dt.tz)
    end_dt_aware = (end_datetime + pd.Timedelta(days=1, seconds=-1)).tz_localize(df['Start Time'].dt.tz)
    
    filtered_df = df[(df['Start Time'] >= start_dt_aware) & (df['Start Time'] <= end_dt_aware)].copy()
    
    # Format datetime for display
    dt_format = "%Y-%m-%d %H:%M"
    filtered_df['Start Time'] = filtered_df['Start Time'].dt.strftime(dt_format)
    filtered_df['End Time'] = filtered_df['End Time'].dt.strftime(dt_format)

    # --- Display the processed data ---
    st.subheader("Filtered Event List")
    
    # Define columns to display in order
    display_columns = [
        'Start Time', 'End Time', 'Duration', 'event', 'type', 
        'advertisedHero', 'H1', 'H2', 'H3', 'H4', 'H5', 'H6',
        'C1', 'C2', 'C3', 'C4', 'C5', 'C6'
    ]
    # Filter out columns that don't exist in the dataframe to prevent errors
    display_columns = [col for col in display_columns if col in filtered_df.columns]
    
    st.dataframe(filtered_df[display_columns])
else:
    st.info("Enter or select folder names in the sidebar and click 'Load & Display'.")