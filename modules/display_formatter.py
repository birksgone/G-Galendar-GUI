import streamlit as st
import pandas as pd
import base64
from pathlib import Path
import re
import json

ICON_BASE_DIR = Path("D:/KB/_all_link_images/Sprite/")
RULES_FILE = Path("data/type_mapping_rules.json")

def _check_condition(condition, row):
    col, op, val = condition.get("column"), condition.get("operator"), condition.get("value")
    cell_value = str(row.get(col, ''))
    if op == "equals": return cell_value == val
    if op == "contains": return val in cell_value
    if op == "matches": return bool(re.search(val, cell_value))
    return False

def _find_matching_rule(row, rules):
    sorted_rules = sorted(rules, key=lambda r: r.get("priority", 9999))
    for rule in sorted_rules:
        conditions = rule.get("conditions", [])
        if all(_check_condition(cond, row) for cond in conditions):
            return rule.get("output"), rule.get("icon")
    return row.get('type', ''), None

@st.cache_data
def _image_to_html(icon_filename):
    if not icon_filename or pd.isna(icon_filename): return ""
    image_path = ICON_BASE_DIR / str(icon_filename)
    try:
        with open(image_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode()
        return f'<img src="data:image/png;base64,{encoded}" width="24" style="display: block; margin: auto; object-fit: contain;">'
    except FileNotFoundError: return "❓"

def convert_posix_to_datetime(series, target_tz='UTC'):
    utc_time = pd.to_datetime(series + 946684800, unit='s', errors='coerce').dt.tz_localize('UTC')
    return utc_time.dt.tz_convert('Asia/Tokyo') if target_tz == 'JST' else utc_time

def calculate_duration(start_s, end_s):
    delta = end_s - start_s
    def format_delta(td):
        if pd.isna(td): return ""
        d, s = td.days, td.seconds
        h = s // 3600
        parts = [f"{d}d"] if d > 0 else []
        if h > 0: parts.append(f"{h}h")
        return " ".join(parts) if parts else ""
    return delta.apply(format_delta)

def format_dataframe_for_display(df, en_map, ja_map):
    rules = []
    if RULES_FILE.exists():
        with open(RULES_FILE, 'r', encoding='utf-8') as f:
            rules = json.load(f)
    
    results = df.apply(lambda row: _find_matching_rule(row, rules), axis=1)
    df[['Display Type', 'Icon File']] = pd.DataFrame(results.tolist(), index=df.index)
    df['Icon'] = df['Icon File'].apply(_image_to_html)
    
    hero_cols = [c for c in ['H1', 'H2', 'H3', 'H4', 'H5', 'H6'] if c in df.columns]
    non_feat_cols = [c for c in ['C1', 'C2', 'C3', 'C4', 'C5', 'C6'] if c in df.columns]
    all_hero_cols = [c for c in ['advertisedHero'] if c in df.columns] + hero_cols + non_feat_cols

    for col in all_hero_cols:
        if col in df.columns:
            df[f'{col} (JP)'] = df[col].map(ja_map).fillna('')
            df[f'{col} (EN)'] = df[col].map(en_map).fillna('')

    df['Featured Heroes (JP)'] = df[[f'{c} (JP)' for c in hero_cols]].apply(lambda r: '\n'.join(v for v in r if v), axis=1)
    df['Featured Heroes (EN)'] = df[[f'{c} (EN)' for c in hero_cols]].apply(lambda r: '\n'.join(v for v in r if v), axis=1)
    df['Other Heroes (JP)'] = df[[f'{c} (JP)' for c in non_feat_cols]].apply(lambda r: '\n'.join(v for v in r if v), axis=1)
    df['Other Heroes (EN)'] = df[[f'{c} (EN)' for c in non_feat_cols]].apply(lambda r: '\n'.join(v for v in r if v), axis=1)
         
    return df