# modules/data_loader.py

import io
import os
import pandas as pd
from pathlib import Path
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

# --- Configuration ---
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
HERO_MASTER_FILE_ID = "1rpfF9gNclicG0wwtY_EMKKdlqsRBSKjB"
SERVICE_ACCOUNT_FILE = "client_secret.json"
EVENT_BASE_DIR = Path("D:/PyScript/EMP Extract/")

def download_file_from_drive(file_id, local_filepath):
    """
    Downloads a file from Google Drive and saves it locally.
    """
    try:
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        
        service = build("drive", "v3", credentials=creds)

        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        
        done = False
        while not done:
            status, done = downloader.next_chunk()

        fh.seek(0)

        with open(local_filepath, "wb") as f:
            f.write(fh.read())
        
        return True

    except Exception as e:
        print(f"An error occurred while downloading from Google Drive: {e}")
        return False

def load_all_data(latest_folder, diff_folder=None):
    """
    Loads all necessary data for the application.
    """
    # --- Load local event data ---
    data_path = EVENT_BASE_DIR / latest_folder
    event_filename = f"calendar-export-{latest_folder}.csv"
    event_file_path = data_path / event_filename
    
    if not event_file_path.exists():
        raise FileNotFoundError(f"Event CSV file not found: {event_file_path}")
    
    main_df = pd.read_csv(event_file_path)
    
    diff_df = None
    if diff_folder:
        diff_path = EVENT_BASE_DIR / diff_folder
        diff_event_filename = f"calendar-export-{diff_folder}.csv"
        diff_file_path = diff_path / diff_event_filename
        
        if diff_file_path.exists():
            diff_df = pd.read_csv(diff_file_path)
        else:
            print(f"Warning: Diff CSV file not found: {diff_file_path}")

    # --- Download and load hero data ---
    local_hero_master_path = Path("data") / "hero_master.csv"
    local_hero_master_path.parent.mkdir(exist_ok=True)
    
    # Always download fresh data (updated every 6 hours)
    download_file_from_drive(HERO_MASTER_FILE_ID, local_hero_master_path)
    
    hero_df = pd.read_csv(local_hero_master_path)
    
    hero_master_df = hero_df.copy()
    g_sheet_df = hero_df.copy()
    
    if g_sheet_df is not None:
        g_sheet_df.rename(columns={'heroname_en': 'hero_en', 'heroname_ja': 'hero_ja'}, inplace=True)

    return {
        'main_df': main_df,
        'diff_df': diff_df,
        'hero_master_df': hero_master_df,
        'g_sheet_df': g_sheet_df
    }
