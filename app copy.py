import streamlit as st
import pandas as pd
from pathlib import Path

# --- ページの設定 ---
st.set_page_config(layout="wide") # 画面を広く使う設定
st.title('イベントカレンダー管理画面')

# --- CSVファイルを探す ---
# 現在のフォルダにある "calendar-export-" で始まるCSVファイルを探す
try:
    # Pathオブジェクトを使って、現在のディレクトリを取得
    current_dir = Path('.')
    # globを使ってパターンに一致する最初のファイルを見つける
    csv_file = next(current_dir.glob("calendar-export-*.csv"))
    st.success(f"読み込み成功: {csv_file.name}")
except StopIteration:
    st.error("エラー: 'calendar-export-....csv' という名前のファイルが見つかりませんでした。")
    st.stop() # ファイルがなければここで処理を停止

# --- メイン処理 ---
# CSVファイルをpandasで読み込む
df = pd.read_csv(csv_file)

st.header('イベントデータ一覧（Google Sheetsのように直接編集できます）')
st.info('↓のテーブルのセルをダブルクリックすると、内容をその場で編集できます。')

# 編集可能なデータテーブルを表示
# これだけで、Google SheetsのようなUIが完成します！
edited_df = st.data_editor(
    df,
    height=800,  # テーブルの高さ
    use_container_width=True # 画面幅に合わせて広げる
)

st.header('（次のステップ）')
st.write('まず、データが正しく表示され、編集できることを確認してみてください。')
st.write('これができたら、次に「選択した行の投稿ドラフトを生成する」ボタンを追加していきましょう！')