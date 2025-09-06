import streamlit as st
import pandas as pd
import json
import re
from pathlib import Path
from datetime import date

from modules.display_formatter import format_dataframe_for_display, to_html_table


# --- Config Helpers ---
DATA_DIR = Path("data")
CONFIG_FILE = DATA_DIR / "config.json"


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
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# --- Template Loader ---
def load_template(template_path: Path | None = None) -> dict:
    if template_path is None:
        template_path = Path("data/forum-template.txt")

    templates: dict[str, str] = {}
    if not template_path.exists():
        return templates

    content = template_path.read_text(encoding="utf-8")
    # Only split on [key] that starts on a new line
    pattern = re.compile(r"\[(.*?)\]\s*([\s\S]*?)(?=\n\s*\[|\Z)")
    matches = pattern.findall(content)
    for key, value in matches:
        templates[key.strip()] = value.strip()
    return templates


# --- Template Processor ---
def process_custom_template(template_str: str, data_dict: dict) -> str:
    output = ""
    i = 0
    while i < len(template_str):
        char = template_str[i]
        if char == "\\":  # Escape character
            if i + 1 < len(template_str):
                output += template_str[i + 1]
                i += 2
            else:
                output += char
                i += 1
        elif char == "{":
            end_brace = template_str.find("}", i)
            if end_brace != -1:
                key = template_str[i + 1 : end_brace]
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


# --- Main Renderer ---
def render_forum_post_creator(diff_df_raw: pd.DataFrame, en_map: dict, ja_map: dict, timezone: str = "UTC") -> None:
    """
    Renders the Forum Post Creator UI inside the main app.

    - diff_df_raw: dataframe filtered to changed rows (expects '_diff_status' column)
    - en_map / ja_map: translation maps
    - timezone: formatting timezone to pass to display formatter
    """
    st.header("✍️ Forum Post Creator")

    if diff_df_raw is None or diff_df_raw.empty:
        st.info("No differences to post. Make some changes or adjust selection.")
        return

    config = _load_json_file(CONFIG_FILE)
    templates = load_template()

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
                key="forum_post_start_date",
            )
        with col2:
            end_date_filter = st.date_input(
                "End date",
                value=end_date_value,
                min_value=min_date,
                max_value=max_date,
                key="forum_post_end_date",
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

    # Table view (standard columns) - Exclude Event Name column as requested
    st.subheader("Difference Data (Standard View)")
    standard_cols = [
        "Icon",
        "Display Type",
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
        "_diff_status": "Diff Status",
    }

    html_table = to_html_table(table_view_df, header_labels, columns_to_display=standard_cols)
    st.markdown(html_table, unsafe_allow_html=True)

    # Generated post texts
    st.subheader("Generated Post Text")

    if filtered_display_df.empty:
        st.info("No events match the selected date range.")
        return

    all_en_texts: list[str] = []
    all_ja_texts: list[str] = []

    for index, row in filtered_display_df.iterrows():
        st.markdown(f"--- Event: **{row.get('Event Name', '')}** (`{row.get('_diff_status', '')}`) ---")
        status = row.get("_diff_status", "unchanged")
        en_template_key = f"{status}_en"
        ja_template_key = f"{status}_ja"

        en_template_str = templates.get(en_template_key, f"**English template for '{status}' not found.**")
        ja_template_str = templates.get(ja_template_key, f"**Japanese template for '{status}' not found.**")

        template_data = row.to_dict()
        
        # デバッグ: 利用可能なテンプレート変数を表示
        with st.expander(f"🔍 Debug: Available Template Variables for {row.get('Event Name', '')}"):
            st.write("**Available variables:**")
            for key, value in template_data.items():
                if key.startswith('event_title') or key in ['Event Name', 'Display Type', 'start_date_iso', 'end_date_iso', 'Duration']:
                    st.write(f"- `{key}`: `{value}` (type: {type(value).__name__})")
        
        # テンプレート処理前にDisplay Typeをevent_titleで上書き（後方互換性のため）
        if 'event_title_en' in template_data:
            template_data['Display Type'] = template_data['event_title_en']
        
        en_text = process_custom_template(en_template_str, template_data)
        ja_text = process_custom_template(ja_template_str, template_data)
        
        # 日本語テンプレートではDisplay Typeを日本語イベント名で上書き
        if 'event_title_ja' in template_data:
            ja_template_data = template_data.copy()
            ja_template_data['Display Type'] = ja_template_data['event_title_ja']
            ja_text = process_custom_template(ja_template_str, ja_template_data)

        all_en_texts.append(en_text)
        all_ja_texts.append(ja_text)

        col1, col2 = st.columns(2)
        with col1:
            st.text_area("English Post", value=en_text, height=150, key=f"en_{index}")
        with col2:
            st.text_area("Japanese Post", value=ja_text, height=150, key=f"ja_{index}")

    st.subheader("📝 Summary for Copy & Paste")
    summary_en = "\r\n".join(all_en_texts)
    summary_ja = "\r\n".join(all_ja_texts)

    col1, col2 = st.columns(2)
    with col1:
        st.text_area("English Summary", value=summary_en, height=300, key="summary_en")
    with col2:
        st.text_area("Japanese Summary", value=summary_ja, height=300, key="summary_ja")
