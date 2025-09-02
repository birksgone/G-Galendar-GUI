# modules/image_generator.py

import streamlit as st
import pandas as pd
from pathlib import Path
import gspread
from google.oauth2.service_account import Credentials
from PIL import Image
import requests
from io import BytesIO


# 親ディレクトリへのパスを追加
import sys
sys.path.append(str(Path(__file__).resolve().parent.parent))

from modules.data_loader import load_all_data

# 定数はdata_loaderからインポートした方が良いが、一旦ここで定義
GCP_CREDS_PATH = "client_secret.json"
GOOGLE_SHEET_ID = "18Qv901QZ8irS1wYh-jbFIPFdsrUFZ01AB6EcN7SX5qM"

@st.cache_data
def _load_hero_master_data():
    """
    画像生成に必要なヒーローマスターデータを読み込み、マージして返す内部関数
    """
    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds = Credentials.from_service_account_file(GCP_CREDS_PATH, scopes=scopes)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)
    
    allh_ws = spreadsheet.worksheet("ALLH")
    allh_records = allh_ws.get_all_values()
    df_allh = pd.DataFrame(allh_records[1:], columns=allh_records[0]).iloc[:, :3]
    df_allh.columns = ['hero_ja', 'id', 'hero_en']

    name_ws = spreadsheet.worksheet("NAME")
    name_records = name_ws.get_all_values()
    df_name = pd.DataFrame(name_records[1:], columns=name_records[0])
    df_name = df_name[['日本語表記', 'URL']]
    df_name.columns = ['hero_ja', 'image_url']
    
    hero_master_df = pd.merge(df_allh, df_name, on='hero_ja', how='left')
    hero_master_df['id'] = hero_master_df['id'].str.lower()
    
    return hero_master_df

def _prepare_hero_details(hero_ids, master_df):
    """
    ヒーローIDリストから詳細情報（名前、URL）のリストを作成する内部関数
    """
    hero_data_list = []
    for hero_id in hero_ids:
        if not hero_id: continue
        hero_info = master_df[master_df['id'] == hero_id.lower()]
        if not hero_info.empty:
            info = hero_info.iloc[0]
            hero_data_list.append({
                'id': hero_id,
                'name_en': info['hero_en'],
                'name_ja': info['hero_ja'],
                'image_url': info['image_url']
            })
        else:
            hero_data_list.append({'id': hero_id, 'name_en': hero_id, 'name_ja': hero_id, 'image_url': None})
    return hero_data_list

def generate_image(params):
    """
    app.pyから呼び出されるメイン関数。
    パラメータを解釈し、適切な画像生成処理を呼び出す。
    現時点では、画像オブジェクトの代わりに準備されたヒーローデータのリストを返す。
    """
    event_type = params.get("img_gen")
    data_dir = params.get("data_dir")
    event_id = params.get("id")

    if not all([event_type, data_dir, event_id]):
        raise ValueError("必要なパラメータが不足しています。")

    # 共通のデータ読み込み
    hero_master_df = _load_hero_master_data()
    data = load_all_data(data_dir, "")
    main_df = data['main_df']
    
    target_row = main_df[main_df['event'] == event_id].iloc[0]
    m_cols = [f'M{i}' for i in range(1, 21)]
    hero_ids = [target_row[col] for col in m_cols if col in target_row and pd.notna(target_row[col])]
    
    # ヒーロー詳細リストを作成
    hero_details = _prepare_hero_details(hero_ids, hero_master_df)

    if event_type == "se":
        # --- Soul Exchange 画像生成ロジック (将来実装) ---
        # costs = params.get("costs") # costsパラメータも利用可能
        st.session_state.image_result = hero_details # 現時点では準備したデータを返す
    
    elif event_type == "fs":
        # --- Fated Summon 画像生成ロジック (将来実装) ---
        st.session_state.image_result = hero_details # 現時点では準備したデータを返す
        
    else:
        raise ValueError(f"未知の画像タイプです: {event_type}")