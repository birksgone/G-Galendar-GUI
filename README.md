# G-Calendar GUI

Google Sheetsで管理されていた複雑なイベントカレンダーのデータ処理と表示を、ローカルで動作するインタラクティブなWebアプリケーションに移植し、日々の運用を効率化・自動化するためのツールです。

## 主な機能

- **動的なイベントカレンダー表示**:
  - 指定した期間のイベントデータを、整形された見やすいテーブル形式で表示します。
  - タイムゾーン（UTC/JST）の切り替えにリアルタイムで対応します。

- **強力な差分ハイライト機能**:
  - 2つの異なる時点のデータ（例: `V7900R-2025-08-29` vs `V7803R-2025-08-25`）を比較します。
  - **新規追加**、**削除**、**変更**されたイベントを、直感的な色分けでハイライト表示します。
    -   <span style="color:#2a4c3a;">■</span> **新規**: 緑色の背景
    -   <span style="color:#2a3a4c;">■</span> **日付変更**: 青色の背景
    -   <span style="color:#333333; text-decoration: line-through;">削除</span>: グレーアウトと取り消し線
    -   <span style="color:#5a522a;">■</span> **Featured Hero変更**: セルが黄色背景
    -   <span style="color:#5a2a2a;">■</span> **Non-Featured Hero変更**: セルが赤色背景

- **柔軟な表示カスタマイズ**:
  - **プリセット**: 「Standard」（主要列のみ）と「All Columns」（全データ列）をワンクリックで切り替え可能。
  - **列選択**: 表示したい列を個別にON/OFFできるカスタマイズ機能を搭載。
  - **ヒーロー名の自動翻訳**: `H1`, `C1`のようなIDを、日英のヒーロー名に自動で変換・連結して表示します。
  - **新登場ヒーローの表示**: 新しくゲームに登場したヒーローには `🆕` 絵文字が自動で付与されます。

## セットアップと実行

### 1. 必要なライブラリのインストール
本プロジェクトには以下のライブラリが必要です。`requirements.txt` を作成し、インストールすることを推奨します。

```txt
streamlit
pandas
gspread
oauth2client
google-auth-httplib2
```

以下のコマンドで一括インストールできます。
```bash
pip install -r requirements.txt
```

### 2. 認証情報の設定
Google Sheets APIにアクセスするため、`gspread` の認証設定が必要です。
`/.config/gspread/` ディレクトリ内に、Google Cloudからダウンロードした認証用のJSONファイル（`service_account.json`など）を配置してください。

### 3. アプリの起動
プロジェクトのルートディレクトリで、以下のコマンドを実行します。
```bash
streamlit run app.py
```

## 使い方

1.  **データソースの選択**:
    -   画面左のサイドバーにある **① Latest Data (Required)** に、比較したい最新のデータが格納されているディレクトリ名（例: `V7900R-2025-08-29`）を入力します。
    -   **② Previous Data for Diff** のドロップダウンから、比較対象としたい過去のデータディレクトリを選択します。
    -   `Load Data` ボタンをクリックすると、データが読み込まれ、テーブルが表示されます。

2.  **表示設定**:
    -   **日付フィルター**: テーブル上部の日付ピッカーで、表示したいイベントの期間を絞り込めます。
    -   **プリセット**: `Presets` ラジオボタンで「Standard」と「All Columns」を切り替えることで、表示する列の組み合わせを簡単に変更できます。
    -   **列のカスタマイズ**: `Customize Columns` を開くと、`multiselect` を使って表示する列を個別に選択・解除できます。

## ディレクトリ構成と主要ファイル

```
G-GALENDAR-GUI/
│
├── .venv/
├── data/
│   ├── config.json            # アプリの状態（選択されたフォルダ名や列）を記憶
│   ├── type_mapping_rules.json # 表示名とアイコンのルールを定義
│   └── .history_event.log     # 使用したフォルダ名の履歴
│
├── modules/
│   ├── data_loader.py         # 全データ（CSV, Google Sheets）の読み込み
│   ├── diff_engine.py         # 2つのデータセットを比較し、差分情報を生成
│   ├── display_formatter.py   # データを表示用に整形（翻訳、HTMLテーブル生成など）
│   └── translation_engine.py  # ヒーロー名の翻訳辞書を作成
│
├── styles.css                 # テーブルの見た目を定義するCSSファイル
└── app.py                     # UIの配置と各モジュールの呼び出しを行うメインスクリプト
```

### 参照する主要なデータファイル
- **ローカルCSV**:
  - `calendar-export-....csv`: メインのイベントデータ。`g-calendar-export.py` によって生成される。
  - `...private_heroes_..._en.csv`: ヒーロー名のマスターデータ。
- **Google Sheets**:
  - `ALLH` シート: ライブ環境のヒーローIDと日英名の対応表。