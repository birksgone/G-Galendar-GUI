import streamlit as st
import pandas as pd
from pathlib import Path
import json

# --- Constants ---
DATA_DIR = Path("data")
EVENT_BASE_DIR = Path("D:/PyScript/EMP Extract/")
LANG_BASE_DIR = Path("D:/Nox Screeshot/Nox SS Directory/Download/v32/Download/Download/")
CONFIG_FILE = DATA_DIR / "config.json"
EVENT_HISTORY_FILE = DATA_DIR / ".history_event.log"
LANG_HISTORY_FILE = DATA_DIR / ".history_lang.log"

# --- Helper Functions for File I/O ---
def initialize_data_dir():
    """Ensure the data directory exists."""
    DATA_DIR.mkdir(exist_ok=True)

def load_json_file(filepath, default_data={}):
    """Load a JSON file, return default data if it doesn't exist or is invalid."""
    if not filepath.exists():
        return default_data
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return default_data

def save_json_file(filepath, data):
    """Save data to a JSON file."""
    initialize_data_dir()
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def load_history(filepath):
    """Load history from a file."""
    if not filepath.exists():
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()
        # Use dict.fromkeys to remove duplicates while preserving order
        return list(dict.fromkeys(filter(None, lines)))

def save_to_history(filepath, new_entry):
    """Append a new entry to the history file, ensuring it's at the top."""
    initialize_data_dir()
    history = load_history(filepath)
    if new_entry in history:
        history.remove(new_entry)
    if new_entry:
        history.insert(0, new_entry)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(history))

# --- Page Setup & Initialization ---
st.set_page_config(layout="wide")
st.title("Event Calendar Management Dashboard")

# Ensure data directory exists
initialize_data_dir()

# Load last used config and history
config = load_json_file(CONFIG_FILE)
event_history = load_history(EVENT_HISTORY_FILE)
lang_history = load_history(LANG_HISTORY_FILE)

# --- Sidebar UI ---
st.sidebar.header("Select Data Sources")

# --- 1. Latest Data (Required) ---
st.sidebar.subheader("① Latest Data (Required)")
latest_folder = st.sidebar.text_input(
    "Enter daily folder name",
    value=config.get("event_folder", ""),
    key="latest_folder_input"
)

# --- 2. Previous Data for Diff ---
st.sidebar.subheader("② Previous Data for Diff")
# Options for diff dropdown should not include the currently selected latest folder
diff_options = [h for h in event_history if h != latest_folder]

# Handle the case where there are no options left
if not diff_options:
    st.sidebar.selectbox(
        "Select a past folder to compare",
        options=["No options to select"],
        index=0,
        disabled=True,
        key="diff_folder_select"
    )
    diff_folder = None
else:
    diff_folder = st.sidebar.selectbox(
        "Select a past folder to compare",
        options=diff_options,
        index=0, # Default to the most recent in the filtered list
        key="diff_folder_select"
    )

# --- 3. Language Data (Required) ---
st.sidebar.subheader("③ Language Data (Required)")
lang_folder = st.sidebar.text_input(
    "Enter Version/TextAsset folder name",
    value=config.get("lang_folder", ""),
    key="lang_folder_input"
)

# --- 4. Load Button ---
st.sidebar.subheader("④ Load Data")
if st.sidebar.button("Load & Display"):
    try:
        # --- Path construction ---
        latest_dir = EVENT_BASE_DIR / latest_folder
        diff_dir = EVENT_BASE_DIR / diff_folder if diff_folder else None
        lang_dir = LANG_BASE_DIR / lang_folder

        latest_csv_path = next(latest_dir.glob("calendar-export-*.csv"))
        diff_csv_path = next(diff_dir.glob("calendar-export-*.csv")) if diff_dir else None
        ja_csv_path = lang_dir / "Japanese.csv"
        en_csv_path = lang_dir / "English.csv"

        # --- Data loading ---
        main_df = pd.read_csv(latest_csv_path)
        diff_df = pd.read_csv(diff_csv_path) if diff_csv_path else None
        ja_df = pd.read_csv(ja_csv_path)
        en_df = pd.read_csv(en_csv_path)

        st.success("All data loaded successfully!")

        # --- Save history and config ---
        save_to_history(EVENT_HISTORY_FILE, latest_folder)
        save_to_history(LANG_HISTORY_FILE, lang_folder)
        new_config = {"event_folder": latest_folder, "lang_folder": lang_folder}
        save_json_file(CONFIG_FILE, new_config)

        # --- Data Display ---
        st.header(f"Latest Data: `{latest_folder}`")
        st.dataframe(main_df)

        if diff_df is not None:
            st.header(f"Previous Data for Diff: `{diff_folder}`")
            st.dataframe(diff_df)

        st.header(f"Language Data (Japanese) from `{lang_folder}`")
        st.dataframe(ja_df.head())

        st.header(f"Language Data (English) from `{lang_folder}`")
        st.dataframe(en_df.head())

    except FileNotFoundError as e:
        st.error(f"File or directory not found. Please check the paths.\nDetails: {e}")
    except StopIteration:
        st.error(f"Could not find a 'calendar-export-*.csv' file in the specified folder(s).")
    except Exception as e:
        st.error(f"An error occurred during data loading.\nDetails: {e}")

else:
    st.info("Enter or select folder names in the sidebar and click 'Load & Display'.")