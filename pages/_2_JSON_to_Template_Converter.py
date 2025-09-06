import streamlit as st
import json
import re
from pathlib import Path

# --- Config ---
DATA_DIR = Path("data")
DISCORD_TEMPLATE_FILE = DATA_DIR / "discord-template.json"

def _load_json_file(filepath: Path, default_data=None):
    if default_data is None:
        default_data = {}
    if not filepath.exists():
        return default_data
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return default_data

def _save_json_file(filepath: Path, data):
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def extract_variables_from_json(json_data):
    """JSONデータから変数を抽出する"""
    variables = set()
    
    def extract_from_value(value):
        if isinstance(value, str):
            # {variable} 形式の変数を抽出
            matches = re.findall(r'\{([^}]+)\}', value)
            variables.update(matches)
        elif isinstance(value, dict):
            for v in value.values():
                extract_from_value(v)
        elif isinstance(value, list):
            for item in value:
                extract_from_value(item)
    
    extract_from_value(json_data)
    
    # 日付関連の変数を自動追加（JSONに変数が含まれていない場合）
    date_related_vars = {
        'start_date_full', 'start_date_md', 'start_date_weekday',
        'duration_days', 'end_date_full'
    }
    variables.update(date_related_vars)
    
    return sorted(variables)

def json_to_template(json_str, template_name, template_description):
    """JSON文字列をテンプレート形式に変換"""
    try:
        json_data = json.loads(json_str)
        
        # まず変数を抽出（実際の値ではなく変数名を保持するため）
        variables = extract_variables_from_json(json_data)
        
        # JSONデータ内の実際の値を変数名に戻す処理
        def restore_variables(data):
            if isinstance(data, dict):
                result = {}
                for key, value in data.items():
                    result[key] = restore_variables(value)
                return result
            elif isinstance(data, list):
                return [restore_variables(item) for item in data]
            elif isinstance(data, str):
                # 実際の日付や時刻を変数名に戻す
                # 日付パターン: YYYY/MM/DD (曜日)
                date_pattern = r'\d{4}/\d{1,2}/\d{1,2} \(\S+\)'
                # 時刻パターン: 4PM, 3PMなど
                time_pattern = r'\d{1,2}(?:AM|PM)'
                
                # 日付と時刻の組み合わせパターン
                datetime_pattern = rf'({date_pattern}) ({time_pattern})'
                
                # 日付+時刻の組み合わせを {start_date_full} {start_time_12h} に置換
                if re.search(datetime_pattern, data):
                    data = re.sub(datetime_pattern, '{start_date_full} {start_time_12h}', data)
                
                # 単独の日付を変数に置換
                data = re.sub(date_pattern, '{start_date_full}', data)
                
                # 単独の時刻を変数に置換
                data = re.sub(time_pattern, '{start_time_12h}', data)
                
                # その他の一般的な変数パターンもここで処理
                # 例: イベント名、ヒーロー名など
                return data
            else:
                return data
        
        # 実際の値を変数名に戻す
        template_data = restore_variables(json_data)
        
        # テンプレート構造を作成（variablesセクションを削除）
        template = {
            "name": template_name,
            "description": template_description,
            "template": template_data
        }
        
        return template, None
    except Exception as e:
        return None, str(e)

def main():
    st.set_page_config(page_title="JSON to Template Converter", page_icon="🔄")
    st.title("🔄 JSON to Template Converter")
    st.markdown("DiscohookのJSON投稿をテンプレート形式に変換します")
    
    # 入力セクション
    st.header("入力")
    json_input = st.text_area(
        "Discohook JSONを貼り付けてください",
        height=300,
        help="Discohookで作成したJSON投稿をそのまま貼り付けてください"
    )
    
    template_name = st.text_input("テンプレート名", placeholder="豊作サモン テンプレート")
    
    # テンプレ名から自動的に説明文を生成
    if template_name:
        template_description = f"{template_name}用のDiscord投稿テンプレート"
        st.text_input("テンプレート説明", value=template_description, disabled=True)
    else:
        template_description = ""
    
    if st.button("変換", type="primary"):
        if not json_input.strip():
            st.error("JSONを入力してください")
            return
            
        if not template_name.strip():
            st.error("テンプレート名を入力してください")
            return
            
        template, error = json_to_template(json_input, template_name, template_description)
        
        if error:
            st.error(f"変換エラー: {error}")
        else:
            st.success("変換成功！")
            
            # 結果表示
            st.header("変換結果")
            template_json = json.dumps([template], indent=2, ensure_ascii=False)
            
            st.text_area(
                "生成されたテンプレート",
                value=template_json,
                height=400,
                help="このJSONをdata/discord-template.jsonに追加してください"
            )
            
            # 変数情報表示（variablesセクションが削除されたためコメントアウト）
            # st.subheader("抽出された変数")
            # for var_name, var_desc in template["variables"].items():
            #     st.write(f"- `{{{var_name}}}`: {var_desc}")
            
            # 保存オプション
            st.subheader("テンプレートの保存")
            if st.button("テンプレートファイルに追加"):
                # 既存のテンプレートを読み込み
                existing_templates = _load_json_file(DISCORD_TEMPLATE_FILE, [])
                
                # 重複チェック
                existing_names = [t["name"] for t in existing_templates]
                if template_name in existing_names:
                    st.warning("同じ名前のテンプレートが既に存在します。上書きしますか？")
                    if st.button("上書き保存"):
                        # 既存のものを削除して追加
                        existing_templates = [t for t in existing_templates if t["name"] != template_name]
                        existing_templates.append(template)
                        _save_json_file(DISCORD_TEMPLATE_FILE, existing_templates)
                        st.success("テンプレートを上書き保存しました")
                else:
                    existing_templates.append(template)
                    _save_json_file(DISCORD_TEMPLATE_FILE, existing_templates)
                    st.success("テンプレートを追加保存しました")
    
    # 使い方ガイド
    with st.expander("使い方ガイド"):
        st.markdown("""
        ### 使い方
        
        1. **Discohookで投稿を作成**
           - DiscohookのWeb UIで通常通り投稿を作成
           - 送信する代わりにJSONをコピー
        
        2. **JSONを貼り付け**
           - 左側のテキストエリアにJSONを貼り付け
           - テンプレート名と説明を入力
        
        3. **変換実行**
           - 「変換」ボタンをクリック
           - 自動的に変数が抽出されます
        
        4. **テンプレート保存**
           - 生成されたテンプレートをファイルに保存
           - Discord投稿作成機能で使用可能に
        
        ### 変数命名規則
        
        テンプレート内で使用できる変数：
        - `{event_name}`: イベント名
        - `{start_date}`: 開始日
        - `{featured_hero_1_ja}`: 注目英雄1（日本語）
        - `{non_featured_hero_1_ja}`: 非注目英雄1（日本語）
        - など...
        
        変数は自動的に抽出され、`{variable}`形式で使用できます。
        """)
    
    # サンプルJSON
    with st.expander("サンプルJSON"):
        sample_json = '''{
  "content": "<@&988300145064046702>明日から豊作サモン",
  "embeds": [
    {
      "title": "{event_title_ja}",
      "description": "{start_date_full} {start_time_12h} ～ {duration_days}日間",
      "url": "{event_url}",
      "color": 13632027,
      "footer": {
        "text": "BirksG",
        "icon_url": "https://example.com/icon.png"
      }
    }
  ]
}'''
        st.text_area("サンプルJSON", value=sample_json, height=200)

if __name__ == "__main__":
    main()
