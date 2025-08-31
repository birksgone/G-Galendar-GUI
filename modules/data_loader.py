import streamlit as st
import pandas as pd
from pathlib import Path
import gspread
from google.oauth2.service_account import Credentials

# --- Constants related to data loading ---
EVENT_BASE_DIR = Path("D:/PyScript/EMP Extract/")
GCP_CREDS_PATH = "client_secret.json"
GOOGLE_SHEET_ID = "18Qv901QZ8irS1wYh-jbFIPFdsrUFZ01AB6EcN7SX5qM"
GOOGLE_SHEET_NAME = "ALLH"

def load_calendar_csv(directory_path: Path):
    """
    Attempts to load a 'streamlit' version of the calendar CSV first,
    and falls back to the original version if not found.
    Returns the loaded DataFrame and the path of the file.
    """
    try:
        # まずstreamlit版を探す
        csv_path = next(directory_path.glob("calendar-export-streamlit-*.csv"))
        return pd.read_csv(csv_path), csv_path
    except StopIteration:
        # なければオリジナル版を探す
        try:
            csv_path = next(directory_path.glob("calendar-export-*.csv"))
            return pd.read_csv(csv_path), csv_path
        except StopIteration:
            raise FileNotFoundError(f"No calendar CSV file found in '{directory_path}'.")

@st.cache_data
def load_all_data(latest_folder, diff_folder):
    """
    Handles all data loading from local files and Google Sheets.
    Returns a dictionary of dataframes.
    """
    data = {}
    
    # --- 1. Load from Google Sheets ---
    st.write("Connecting to Google Sheets...")
    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds = Credentials.from_service_account_file(GCP_CREDS_PATH, scopes=scopes)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)
    worksheet = spreadsheet.worksheet(GOOGLE_SHEET_NAME)
    
    g_sheet_records = worksheet.get_all_values()
    header = g_sheet_records[0]
    sheet_data = g_sheet_records[1:]
    
    g_sheet_df_full = pd.DataFrame(sheet_data, columns=header)
    data['g_sheet_df'] = g_sheet_df_full.iloc[:, :3]
    data['g_sheet_df'].columns = ['hero_ja', 'id', 'hero_en']

    # --- 2. Load from local files ---
    st.write(f"Searching in folder: {latest_folder}...")
    latest_dir = EVENT_BASE_DIR / latest_folder
    
    try:
        hero_master_path = next(latest_dir.glob("*_private_heroes_*_en.csv"))
        data['hero_master_df'] = pd.read_csv(hero_master_path)
    except StopIteration: 
        raise FileNotFoundError(f"Hero master CSV not found in '{latest_dir}'.")
    
    # ヘルパー関数を使ってCSVを読み込み、ファイルパスも受け取る
    main_df, main_path = load_calendar_csv(latest_dir)
    data['main_df'] = main_df
    st.write(f"-> Loaded main data: `{main_path.name}`")
    
    if diff_folder:
        st.write(f"Searching in diff folder: {diff_folder}...")
        diff_dir = EVENT_BASE_DIR / diff_folder
        # ヘルパー関数を使って比較用CSVを読み込み、ファイルパスも受け取る
        diff_df, diff_path = load_calendar_csv(diff_dir)
        data['diff_df'] = diff_df
        st.write(f"-> Loaded diff data: `{diff_path.name}`")
    else: 
        data['diff_df'] = None
    
    st.write("Data loading complete!")
    return data