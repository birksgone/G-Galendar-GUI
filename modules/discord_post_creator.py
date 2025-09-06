import streamlit as st
import pandas as pd
import json
import re
from pathlib import Path
from datetime import date
import copy

from modules.display_formatter import format_dataframe_for_display


# --- Config Helpers ---
DATA_DIR = Path("data")
CONFIG_FILE = DATA_DIR / "config.json"
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


# --- Discord Template Loader ---
def load_discord_templates(template_path: Path | None = None) -> list:
    if template_path is None:
        template_path = DISCORD_TEMPLATE_FILE

    if not template_path.exists():
        return []
    
    try:
        return _load_json_file(template_path, [])
    except:
        return []


# --- JSON Template Processor ---
def process_json_template(template_obj: dict, data_dict: dict) -> dict:
    """
    Recursively process a JSON template object and replace {variables} with actual values.
    """
    if isinstance(template_obj, dict):
        result = {}
        for key, value in template_obj.items():
            result[key] = process_json_template(value, data_dict)
        return result
    elif isinstance(template_obj, list):
        return [process_json_template(item, data_dict) for item in template_obj]
    elif isinstance(template_obj, str):
        # Process string template with {variable} replacement
        output = ""
        i = 0
        while i < len(template_obj):
            char = template_obj[i]
            if char == "\\":  # Escape character
                if i + 1 < len(template_obj):
                    output += template_obj[i + 1]
                    i += 2
                else:
                    output += char
                    i += 1
            elif char == "{":
                end_brace = template_obj.find("}", i)
                if end_brace != -1:
                    key = template_obj[i + 1 : end_brace]
                    value = data_dict.get(key)
                    if value is not None:
                        output += str(value) if pd.notna(value) else ""
                    else:
                        # If key not found, keep literal text
                        output += f"{{{key}}}"
                    i = end_brace + 1
                else:
                    output += char
                    i += 1
            else:
                output += char
                i += 1
        return output
    else:
        return template_obj


# --- Main Renderer ---
def render_discord_post_creator(diff_df_raw: pd.DataFrame, en_map: dict, ja_map: dict, timezone: str = "UTC") -> None:
    """
    Renders the Discord Post Creator UI inside the main app.

    - diff_df_raw: dataframe filtered to changed rows (expects '_diff_status' column)
    - en_map / ja_map: translation maps
    - timezone: formatting timezone to pass to display formatter
    """
    st.header("🤖 Discord Post Creator")

    if diff_df_raw is None or diff_df_raw.empty:
        st.info("No differences to post. Make some changes or adjust selection.")
        return

    config = _load_json_file(CONFIG_FILE)
    templates = load_discord_templates()

    # Load rules if present
    rules_path = Path("data/type_mapping_rules.json")
    rules = []
    if rules_path.exists():
        try:
            rules = json.loads(rules_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            rules = []

    # Full dataframe with all columns for templating
    display_df_all_cols = format_dataframe_for_display(diff_df_raw, rules, en_map, ja_map, timezone=timezone)
    
    # Add template-friendly hero columns (without HTML line breaks)
    display_df_all_cols['Featured Heroes (EN) Template'] = display_df_all_cols['Featured Heroes (EN)'].str.replace('<br>', ', ')
    display_df_all_cols['Non-Featured Heroes (EN) Template'] = display_df_all_cols['Non-Featured Heroes (EN)'].str.replace('<br>', ', ')
    display_df_all_cols['Featured Heroes (JA) Template'] = display_df_all_cols['Featured Heroes (JA)'].str.replace('<br>', '、')
    display_df_all_cols['Non-Featured Heroes (JA) Template'] = display_df_all_cols['Non-Featured Heroes (JA)'].str.replace('<br>', '、')

    # Date filter
    st.subheader("Filter by Date Range")
    if not display_df_all_cols.empty and "Start Time" in display_df_all_cols.columns:
        min_date = display_df_all_cols["Start Time"].min().date()
        max_date = display_df_all_cols["Start Time"].max().date()

        start_date_str = config.get("post_start", min_date.isoformat())
        end_date_str = config.get("post_end", max_date.isoformat())

        try:
            start_date_value = date.fromisoformat(start_date_str)
        except (ValueError, TypeError):
            start_date_value = min_date
        try:
            end_date_value = date.fromisoformat(end_date_str)
        except (ValueError, TypeError):
            end_date_value = max_date

        start_date_value = max(min_date, min(start_date_value, max_date))
        end_date_value = max(min_date, min(end_date_value, max_date))

        col1, col2 = st.columns(2)
        with col1:
            start_date_filter = st.date_input(
                "Start date",
                value=start_date_value,
                min_value=min_date,
                max_value=max_date,
                key="discord_post_start_date",
            )
        with col2:
            end_date_filter = st.date_input(
                "End date",
                value=end_date_value,
                min_value=min_date,
                max_value=max_date,
                key="discord_post_end_date",
            )

        changed = False
        if start_date_filter.isoformat() != config.get("post_start"):
            config["post_start"] = start_date_filter.isoformat()
            changed = True
        if end_date_filter.isoformat() != config.get("post_end"):
            config["post_end"] = end_date_filter.isoformat()
            changed = True
        if changed:
            _save_json_file(CONFIG_FILE, config)

        mask = (
            (display_df_all_cols["Start Time"].dt.date >= start_date_filter)
            & (display_df_all_cols["Start Time"].dt.date <= end_date_filter)
        )
        filtered_display_df = display_df_all_cols[mask]
    else:
        filtered_display_df = display_df_all_cols

    # Template selection
    st.subheader("Template Selection")
    if not templates:
        st.error("No Discord templates found. Please create templates in data/discord-template.json")
        return

    template_names = [t["name"] for t in templates]
    selected_template_name = st.selectbox(
        "Choose a template",
        template_names,
        key="discord_template_select"
    )

    selected_template = next((t for t in templates if t["name"] == selected_template_name), None)
    if not selected_template:
        st.error("Selected template not found")
        return

    # テンプレート変数情報の表示を削除（JSONを見れば分かるため）

    # Event selection
    st.subheader("Event Selection")
    if filtered_display_df.empty:
        st.info("No events match the selected date range.")
        return

    event_options = filtered_display_df["Event Name"].tolist()
    selected_event = st.selectbox(
        "Select an event to generate post for",
        event_options,
        key="discord_event_select"
    )

    event_row = filtered_display_df[filtered_display_df["Event Name"] == selected_event].iloc[0]
    event_data = event_row.to_dict()
    
    # Add template variables mapping from display_formatter columns
    # Map display column names to template variable names
    template_mapping = {
        'Event Name': 'event_name',
        'event_title_en': 'event_title_en',
        'event_title_ja': 'event_title_ja',
        'start_date_md': 'start_date_md',
        'Duration': 'duration_days',
        'start_date_iso': 'start_date_iso',
        'end_date_iso': 'end_date_iso',
        'Featured Heroes (EN)': 'featured_heroes_en',
        'Non-Featured Heroes (EN)': 'non_featured_heroes_en',
        'questline': 'questline',
        'banner': 'banner_url',
        'url': 'event_url'
    }
    
    # Add mapped variables
    for display_col, template_var in template_mapping.items():
        if display_col in event_data:
            event_data[template_var] = event_data[display_col]
    
    # Extract days from duration
    if 'duration_days' in event_data and isinstance(event_data['duration_days'], str):
        duration_str = event_data['duration_days']
        if 'd' in duration_str:
            days = duration_str.split('d')[0]
            event_data['duration_days'] = days
    
    # Extract individual featured heroes - remove HTML <br> tags first
    if 'featured_heroes_en' in event_data and isinstance(event_data['featured_heroes_en'], str):
        # Remove HTML <br> tags and split by comma
        clean_heroes = event_data['featured_heroes_en'].replace('<br>', ', ')
        heroes = [h.strip() for h in clean_heroes.split(',') if h.strip()]
        for i, hero in enumerate(heroes[:2], 1):
            event_data[f'featured_hero_{i}_en'] = hero
    
    # Extract individual featured heroes in Japanese
    if 'Featured Heroes (JA)' in event_data and isinstance(event_data['Featured Heroes (JA)'], str):
        # Remove HTML <br> tags and split by comma
        clean_heroes_ja = event_data['Featured Heroes (JA)'].replace('<br>', '、')
        heroes_ja = [h.strip() for h in clean_heroes_ja.split('、') if h.strip()]
        for i, hero in enumerate(heroes_ja[:2], 1):
            event_data[f'featured_hero_{i}_ja'] = hero

    # Extract individual non-featured heroes in Japanese for Discord format
    if 'Non-Featured Heroes (JA) Template' in event_data and isinstance(event_data['Non-Featured Heroes (JA) Template'], str):
        non_featured_heroes_ja = event_data['Non-Featured Heroes (JA) Template']
        if non_featured_heroes_ja and pd.notna(non_featured_heroes_ja) and non_featured_heroes_ja.strip():
            # Split non-featured heroes and add to event_data
            non_featured_list = [h.strip() for h in non_featured_heroes_ja.split('、') if h.strip()]
            for i, hero in enumerate(non_featured_list[:6], 1):  # Max 6 heroes
                event_data[f'non_featured_hero_{i}_ja'] = hero
            event_data['has_non_featured_heroes'] = True
            
            # Generate non-featured section for Discord template
            non_featured_section = "**非注目追加**\n"
            for i, hero in enumerate(non_featured_list[:4], 1):  # Max 4 heroes for display
                # Assign appropriate emoji based on hero position
                emoji = "<:emblemice:989041535691673624>"
                if i == 2:
                    emoji = "<:emblemholy:989041571167101022>"
                elif i == 3:
                    emoji = "<:emblemfire:989041476833017886>"
                elif i == 4:
                    emoji = "<:emblemice:989041535691673624>"
                
                non_featured_section += f"- {emoji} [{hero}](https://bbcamp.info/herodb/hero{i})\n"
            event_data['non_featured_section'] = non_featured_section
        else:
            event_data['has_non_featured_heroes'] = False
            event_data['non_featured_section'] = ""
    else:
        event_data['has_non_featured_heroes'] = False
        event_data['non_featured_section'] = ""
    
    # Add weekday and time information if Start Time is available
    if 'Start Time' in event_data and pd.notna(event_data['Start Time']):
        try:
            start_date = event_data['Start Time']
            # Convert Timestamp to datetime object for reliable formatting
            if hasattr(start_date, 'date'):
                # Get the date part only
                date_part = start_date.date()
                # Japanese weekday names
                weekdays = ["月", "火", "水", "木", "金", "土", "日"]
                weekday_num = date_part.weekday()
                event_data['start_date_weekday'] = weekdays[weekday_num]
                
                # Format: 2025/9/20 (火) - manually format to avoid strftime issues
                year = date_part.year
                month = date_part.month
                day = date_part.day
                event_data['start_date_full'] = f"{year}/{month}/{day} ({event_data['start_date_weekday']})"
                
                # Also ensure start_date_iso is properly formatted string
                if 'start_date_iso' not in event_data or not isinstance(event_data['start_date_iso'], str):
                    event_data['start_date_iso'] = f"{year}-{month:02d}-{day:02d}"
                
                # Add time formatting for Discord (UTC to JST conversion + 12-hour format with AM/PM)
                if hasattr(start_date, 'time'):
                    time_part = start_date.time()
                    hour = time_part.hour
                    minute = time_part.minute
                    
                    # Convert UTC to JST (+9 hours)
                    jst_hour = (hour + 9) % 24
                    
                    # Convert to 12-hour format with AM/PM
                    if jst_hour == 0:
                        event_data['start_time_12h'] = f"12:{minute:02d}AM"
                    elif jst_hour < 12:
                        event_data['start_time_12h'] = f"{jst_hour}:{minute:02d}AM"
                    elif jst_hour == 12:
                        event_data['start_time_12h'] = f"12:{minute:02d}PM"
                    else:
                        event_data['start_time_12h'] = f"{jst_hour-12}:{minute:02d}PM"
                    
                    # Also add 24-hour format
                    event_data['start_time_24h'] = f"{jst_hour:02d}:{minute:02d}"
                    
        except (ValueError, TypeError, AttributeError) as e:
            st.error(f"Error processing date: {str(e)}")
            # Fallback to start_date_iso if available
            if 'start_date_iso' in event_data and isinstance(event_data['start_date_iso'], str):
                try:
                    from datetime import datetime
                    start_date = datetime.fromisoformat(event_data['start_date_iso'])
                    weekdays = ["月", "火", "水", "木", "金", "土", "日"]
                    weekday_num = start_date.weekday()
                    event_data['start_date_weekday'] = weekdays[weekday_num]
                    event_data['start_date_full'] = f"{start_date.year}/{start_date.month}/{start_date.day} ({event_data['start_date_weekday']})"
                except (ValueError, TypeError):
                    pass
    else:
        # Fallback: if Start Time is not available, try to create start_date_full from other date fields
        if 'start_date_iso' in event_data and isinstance(event_data['start_date_iso'], str):
            try:
                from datetime import datetime
                start_date = datetime.fromisoformat(event_data['start_date_iso'])
                weekdays = ["月", "火", "水", "木", "金", "土", "日"]
                weekday_num = start_date.weekday()
                event_data['start_date_weekday'] = weekdays[weekday_num]
                event_data['start_date_full'] = f"{start_date.year}/{start_date.month}/{start_date.day} ({event_data['start_date_weekday']})"
            except (ValueError, TypeError):
                pass

    # Table view (standard columns) - same as forum_post_creator
    st.subheader("Difference Data (Standard View)")
    standard_cols = [
        "Icon",
        "Display Type",
        "Event Name",
        "Start Time",
        "End Time",
        "Duration",
        "Featured Heroes (EN)",
        "Non-Featured Heroes (EN)",
        "Featured Heroes (JA)",
        "Non-Featured Heroes (JA)",
        "_diff_status",
    ]

    table_view_df = filtered_display_df[[c for c in standard_cols if c in filtered_display_df.columns]].copy()

    dt_format = "%Y-%m-%d %H:%M"
    for col in ["Start Time", "End Time"]:
        if col in table_view_df.columns and pd.api.types.is_datetime64_any_dtype(table_view_df[col]):
            table_view_df[col] = table_view_df[col].dt.strftime(dt_format)

    header_labels = {
        "Icon": "Icon",
        "Display Type": "Type",
        "Start Time": "Start",
        "End Time": "End",
        "Duration": "Days",
        "Featured Heroes (EN)": "Feat.(EN)",
        "Non-Featured Heroes (EN)": "Non-Feat.(EN)",
        "Featured Heroes (JA)": "Feat.(JA)",
        "Non-Featured Heroes (JA)": "Non-Feat.(JA)",
        "Event Name": "Event ID",
        "_diff_status": "Diff Status",
    }

    from modules.display_formatter import to_html_table
    html_table = to_html_table(table_view_df, header_labels, columns_to_display=standard_cols)
    st.markdown(html_table, unsafe_allow_html=True)

    # Generate Discord post
    st.subheader("Generated Discord Post")
    
    try:
        # デバッグ: テンプレート処理前のデータを詳細表示
        with st.expander("🔍 Debug: Raw Event Data (Before Template Processing)"):
            st.write("**All available data:**")
            for key, value in event_data.items():
                st.write(f"- `{key}`: `{value}` (type: {type(value).__name__})")
            
            st.write("**Template variables that should be available:**")
            template_vars = selected_template.get("variables", {})
            for var_name in template_vars.keys():
                value = event_data.get(var_name)
                st.write(f"- `{var_name}`: `{value}` (exists: {var_name in event_data})")
        
        # テンプレート処理
        generated_post = process_json_template(selected_template["template"], event_data)
        
        # デバッグ: テンプレート処理後の結果を表示
        with st.expander("🔍 Debug: Template Processing Result"):
            st.write("**Processed template result:**")
            st.json(generated_post)
            
            # 元のテンプレートと比較
            st.write("**Original template structure:**")
            st.json(selected_template["template"])
            
            # 変数置換の詳細を表示
            st.write("**Variable replacement details:**")
            template_vars = selected_template.get("variables", {})
            for var_name in template_vars.keys():
                value = event_data.get(var_name)
                st.write(f"- `{{{var_name}}}` → `{value}` (exists: {var_name in event_data}, type: {type(value).__name__ if value is not None else 'None'})")
        
        # Display JSON with Streamlit's built-in copy functionality
        json_str = json.dumps(generated_post, indent=2, ensure_ascii=False)
        
        # デバッグ: 最終的なJSON文字列を表示
        with st.expander("🔍 Debug: Final JSON String"):
            st.text_area("Final JSON string", value=json_str, height=200)
        
        # Single text area for editing and copying
        edited_json = st.text_area(
            "JSON Output (Copy using button in top-right corner)", 
            value=json_str, 
            height=300, 
            key="discord_json_output",
            help="Copy the JSON using the button in the top-right corner of this text area"
        )

        # Hero list for easy copying to Discohook
        st.subheader("📋 Hero List for Discohook Copy")
        
        # Generate hero list text in Discohook editor format
        hero_list_text = ""
        
        # Featured heroes with emojis and links
        if 'featured_hero_1_ja' in event_data and event_data['featured_hero_1_ja']:
            hero_list_text += "**注目英雄**\n"
            if 'featured_hero_1_ja' in event_data:
                # First featured hero gets holy emblem (🆕 is already added by display_formatter)
                hero_list_text += f"- <:emblemholy:989041571167101022> [{event_data['featured_hero_1_ja']}](https://bbcamp.info/herodb/justice5)\n"
            if 'featured_hero_2_ja' in event_data:
                # Second featured hero gets fire emblem
                hero_list_text += f"- <:emblemfire:989041476833017886> [{event_data['featured_hero_2_ja']}](https://bbcamp.info/herodb/elena5)\n"
            hero_list_text += "\n"
        
        # Non-featured heroes with emojis and links (🆕 is already added by display_formatter)
        if event_data.get('has_non_featured_heroes', False):
            hero_list_text += "**非注目追加**\n"
            emojis = [
                "<:emblemice:989041535691673624>",
                "<:emblemholy:989041571167101022>", 
                "<:emblemfire:989041476833017886>",
                "<:emblemice:989041535691673624>"
            ]
            
            for i in range(1, 5):  # Max 4 heroes for display
                hero_key = f'non_featured_hero_{i}_ja'
                if hero_key in event_data and event_data[hero_key]:
                    emoji = emojis[i-1] if i-1 < len(emojis) else "<:emblemice:989041535691673624>"
                    hero_list_text += f"- {emoji} [{event_data[hero_key]}](https://bbcamp.info/herodb/hero{i})\n"
        
        st.text_area(
            "Hero List (Copy to Discohook Editor)",
            value=hero_list_text,
            height=200,
            key="hero_list_copy",
            help="このテキストをDiscohookエディタの該当箇所にコピーして使用できます（🆕絵文字は既にヒーロー名に含まれています）"
        )
        
        # Also show simple hero names for reference
        st.subheader("📋 Simple Hero Names (参考)")
        simple_hero_text = ""
        if 'featured_hero_1_ja' in event_data:
            simple_hero_text += "注目英雄:\n"
            if 'featured_hero_1_ja' in event_data:
                simple_hero_text += f"- {event_data['featured_hero_1_ja']}\n"
            if 'featured_hero_2_ja' in event_data:
                simple_hero_text += f"- {event_data['featured_hero_2_ja']}\n"
            simple_hero_text += "\n"
        
        if event_data.get('has_non_featured_heroes', False):
            simple_hero_text += "非注目追加:\n"
            for i in range(1, 7):
                hero_key = f'non_featured_hero_{i}_ja'
                if hero_key in event_data and event_data[hero_key]:
                    simple_hero_text += f"- {event_data[hero_key]}\n"
        
        st.text_area(
            "Simple Hero Names",
            value=simple_hero_text,
            height=150,
            key="simple_hero_list",
            help="シンプルなヒーロー名リスト（参考用）"
        )
            
    except Exception as e:
        st.error(f"Error generating Discord post: {str(e)}")
        st.exception(e)


# For testing
if __name__ == "__main__":
    # Test with sample data
    sample_data = {
        "event_name": "テストイベント",
        "start_date_md": "9/7",
        "duration_days": "7",
        "event_url": "https://example.com",
        "banner_url": "https://example.com/banner.png",
        "featured_hero_1": "テスト英雄1",
        "featured_hero_2": "テスト英雄2"
    }
    
    test_template = {
        "content": "<@&988300145064046702>明日から{event_name}",
        "embeds": [
            {
                "title": "{event_name}",
                "description": "{start_date_md} (火) 4PM ～ {duration_days}日間",
                "url": "{event_url}"
            }
        ]
    }
    
    result = process_json_template(test_template, sample_data)
    print(json.dumps(result, indent=2, ensure_ascii=False))
