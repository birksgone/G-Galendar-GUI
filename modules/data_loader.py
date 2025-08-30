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

@st.cache_data
def load_all_data(latest_folder, diff_folder):
    """
    Handles all data loading from local files and Google Sheets.
    Returns a dictionary of dataframes.
    """
    data = {}
    
    # --- 1. Load from Google Sheets ---
    st.write("Connecting to Google Sheets...") # Debug message
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
    # Explicitly rename columns to ensure consistency
    data['g_sheet_df'].columns = ['hero_ja', 'id', 'hero_en']

    # --- 2. Load from local files ---
    st.write(f"Loading data from folder: {latest_folder}...") # Debug message
    latest_dir = EVENT_BASE_DIR / latest_folder
    
    try:
        hero_master_path = next(latest_dir.glob("*_private_heroes_*_en.csv"))
        data['hero_master_df'] = pd.read_csv(hero_master_path)
    except StopIteration: 
        raise FileNotFoundError(f"Hero master CSV not found in '{latest_dir}'.")
    
    data['main_df'] = pd.read_csv(next(latest_dir.glob("calendar-export-*.csv")))
    
    if diff_folder: 
        diff_path = next((EVENT_BASE_DIR / diff_folder).glob("calendar-export-*.csv"), None)
        if diff_path:
            data['diff_df'] = pd.read_csv(diff_path)
        else:
            data['diff_df'] = None
    else: 
        data['diff_df'] = None
    
    st.write("Data loading complete!") # Debug message
    return data