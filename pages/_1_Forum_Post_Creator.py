# pages/1_Forum_Post_Creator.py

import streamlit as st
import pandas as pd
from datetime import date

st.set_page_config(layout="wide")
st.title("✍️ Forum Post Creator")



if 'diff_data' not in st.session_state or st.session_state['diff_data'].empty:
    st.warning("No difference data found. Please generate it from the main page.")
    st.page_link("app.py", label="Back to Main Page", icon="🏠")
else:
    diff_df = st.session_state['diff_data']
    en_map = st.session_state['en_map']
    ja_map = st.session_state['ja_map']

    st.subheader("Filter by Date Range")
    
    # 日付フィルターのデフォルト値を差分データから取得
    min_date = pd.to_datetime(diff_df['startDate'], unit='s').min().date()
    max_date = pd.to_datetime(diff_df['startDate'], unit='s').max().date()

    col1, col2 = st.columns(2)
    with col1:
        start_date_filter = st.date_input("Start date", value=min_date, min_value=min_date, max_value=max_date)
    with col2:
        end_date_filter = st.date_input("End date", value=max_date, min_value=min_date, max_value=max_date)

    # DataFrameの日付をdatetimeオブジェクトに変換してフィルタリング
    diff_df['start_datetime'] = pd.to_datetime(diff_df['startDate'], unit='s')
    
    mask = (diff_df['start_datetime'].dt.date >= start_date_filter) & \
           (diff_df['start_datetime'].dt.date <= end_date_filter)
    
    filtered_diffs = diff_df[mask]

    st.subheader("Generated Post Text")
    
    if filtered_diffs.empty:
        st.info("No events match the selected date range.")
    else:
        # --- ここにテキスト生成ロジックを実装していく ---
        st.write("Filtered Data:")
        st.dataframe(filtered_diffs)
        
        st.info("Text generation logic will be implemented here.")

    st.page_link("app.py", label="Back to Main Page", icon="🏠")