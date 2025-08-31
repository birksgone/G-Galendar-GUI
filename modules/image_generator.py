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

# 定数はdata_loaderからインポートした方が良いが、一旦ここで定義
GCP_CREDS_PATH = "client_secret.json"
GOOGLE_SHEET_ID = "18Qv901QZ8irS1wYh-jbFIPFdsrUFZ01AB6EcN7SX5qM"
EVENT_BASE_DIR = Path("D:/PyScript/EMP Extract/")

@st.cache_data
def load_image_gen_data(data_dir):
    """
    画像生成に必要なすべてのデータを読み込み、マージ済みのヒーローマスターDFを返す
    """
    # Google Sheetsから'ALLH'と'NAME'シートを読み込む
    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds = Credentials.from_service_account_file(GCP_CREDS_PATH, scopes=scopes)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)
    
    # 'ALLH'シート読み込み
    allh_ws = spreadsheet.worksheet("ALLH")
    allh_records = allh_ws.get_all_values()
    df_allh = pd.DataFrame(allh_records[1:], columns=allh_records[0]).iloc[:, :3]
    df_allh.columns = ['hero_ja', 'id', 'hero_en']

    # 'NAME'シート読み込み
    name_ws = spreadsheet.worksheet("NAME")
    name_records = name_ws.get_all_values()
    df_name = pd.DataFrame(name_records[1:], columns=name_records[0])
    df_name = df_name[['日本語表記', 'URL']] # F列とI列を想定
    df_name.columns = ['hero_ja', 'image_url']
    
    # ヒーロー名(日本語)をキーにして、2つのDataFrameをマージ
    hero_master_df = pd.merge(df_allh, df_name, on='hero_ja', how='left')
    
    # hero_master_df['id']を小文字に変換して、IDでの検索を容易にする
    hero_master_df['id'] = hero_master_df['id'].str.lower()
    
    return hero_master_df


def prepare_hero_data_for_image(hero_ids, master_df):
    """
    ヒーローIDのリストから、画像生成に必要な情報（名前、URL）のリストを作成する
    """
    hero_data_list = []
    for hero_id in hero_ids:
        if not hero_id:
            continue
            
        # IDでヒーロー情報を検索
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
            # マスターに見つからなかった場合のフォールバック
            hero_data_list.append({
                'id': hero_id,
                'name_en': hero_id,
                'name_ja': hero_id,
                'image_url': None # 画像URLなし
            })
            
    return hero_data_list

# --- 以降にPillowを使った画像描画関数を追加していく ---