# modules/data_loader.py

import streamlit as st
import pandas as pd
from pathlib import Path
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io

# --- 定数定義 ---
EVENT_BASE_DIR = Path("D:/PyScript/EMP Extract/")
GCP_CREDS_PATH = "client_secret.json"
HERO_MASTER_CSV_ID = '1rpfF9gNclicG0wwtY_EMKKdlqsRBSKjB' # Google Drive上のhero_master.csvのファイルID
SCOPES = [
    'https://www.googleapis.com/auth/drive.readonly'      # Google Drive読み取り用
]

@st.cache_data
def load_hero_master_from_drive():
    """
    Google Driveからhero_master.csvをダウンロードし、DataFrameとして返す。
    """
    st.write("Loading hero master from Google Drive...")
    creds = Credentials.from_service_account_file(GCP_CREDS_PATH, scopes=SCOPES)
    service = build('drive', 'v3', credentials=creds)

    request = service.files().get_media(fileId=HERO_MASTER_CSV_ID)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()
    
    fh.seek(0)
    df = pd.read_csv(fh)
    st.write("-> Hero master loaded successfully!")
    return df

def load_calendar_csv(directory_path: Path):
    """
    指定されたディレクトリからイベントカレンダーCSVを読み込む（フォールバック機能付き）。
    """
    try:
        csv_path = next(directory_path.glob("calendar-export-streamlit-*.csv"))
        return pd.read_csv(csv_path), csv_path
    except StopIteration:
        try:
            csv_path = next(directory_path.glob("calendar-export-*.csv"))
            return pd.read_csv(csv_path), csv_path
        except StopIteration:
            raise FileNotFoundError(f"No calendar CSV file found in '{directory_path}'.")

@st.cache_data
def load_all_data(latest_folder, diff_folder):
    """
    全てのデータを読み込む。ヒーローマスターはGoogle Driveから、イベントはローカルから。
    """
    data = {}
    
    # --- 1. Google Driveからヒーローマスターを読み込む ---
    hero_master_df = load_hero_master_from_drive()
    data['hero_master_df'] = hero_master_df

    # 従来のg_sheet_dfの形式を模倣して作成する
    # translation_engineがこの形式を期待しているため
    # CSVの実際のヘッダー名 'heroname_ja', 'id', 'heroname_en' に合わせる
    data['g_sheet_df'] = hero_master_df[['heroname_ja', 'id', 'heroname_en']].copy()
    # 互換性のために列名をリネームする
    data['g_sheet_df'].columns = ['hero_ja', 'id', 'hero_en']


    # --- 2. ローカルからイベントCSVを読み込む ---
    st.write(f"Searching in folder: {latest_folder}...")
    latest_dir = EVENT_BASE_DIR / latest_folder
    
    main_df, main_path = load_calendar_csv(latest_dir)
    data['main_df'] = main_df
    st.write(f"-> Loaded main data: `{main_path.name}`")
    
    if diff_folder:
        st.write(f"Searching in diff folder: {diff_folder}...")
        diff_dir = EVENT_BASE_DIR / diff_folder
        diff_df, diff_path = load_calendar_csv(diff_dir)
        data['diff_df'] = diff_df
        st.write(f"-> Loaded diff data: `{diff_path.name}`")
    else: 
        data['diff_df'] = None
    
    st.write("Data loading complete!")
    return data