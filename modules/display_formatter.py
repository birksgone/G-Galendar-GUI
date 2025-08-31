import pandas as pd
import re

BASE_ICON_URL = "https://bbcamp.info/wp-content/uploads/camp-img/calendar_type_icon/"

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

def _check_condition(row, condition):
    col = condition.get('column')
    op = condition.get('operator')
    val = condition.get('value')
    if col not in row or pd.isna(row[col]): return False
    cell_value = str(row[col])
    if op == 'equals': return cell_value == str(val)
    if op == 'contains': return str(val) in cell_value
    if op == 'starts_with': return cell_value.startswith(str(val))
    if op == 'ends_with': return cell_value.endswith(str(val))
    if op == "matches": return bool(re.search(val, cell_value))
    return False

def _get_display_info(row, rules):
    for rule in sorted(rules, key=lambda x: x.get('priority', float('inf'))):
        conditions = rule.get('conditions', [])
        if all(_check_condition(row, cond) for cond in conditions):
            display_name = rule.get('output', row.get('type', ''))
            icon_filename = rule.get('icon', '')
            icon_url = f"{BASE_ICON_URL}{icon_filename}" if icon_filename else None
            return pd.Series([display_name, icon_url])
    return pd.Series([row.get('type', ''), None])

def _translate_and_format_heroes(df, prefix, lang_map):
    hero_lists = []
    num_cols = 6
    for _, row in df.iterrows():
        heroes = []
        for i in range(1, num_cols + 1):
            hero_col = f"{prefix}{i}"
            new_flag_col = f"{hero_col}_new"
            if hero_col in row and pd.notna(row[hero_col]):
                hero_id = str(row[hero_col])
                hero_name = lang_map.get(hero_id.lower(), hero_id)
                if new_flag_col in row and row[new_flag_col] == True:
                    hero_name += " 🆕"
                heroes.append(hero_name)
        hero_lists.append(heroes if heroes else [])
    return hero_lists

def format_dataframe_for_display(df, type_mapping_rules, en_map, ja_map, timezone):
    df_copy = df.copy()

    df_copy[['Display Type', 'Icon']] = df_copy.apply(
        _get_display_info, args=(type_mapping_rules,), axis=1
    )
    df_copy['Event Name'] = df_copy['event']
    
    df_copy['Start Time'] = convert_posix_to_datetime(df_copy['startDate'], timezone)
    df_copy['End Time'] = convert_posix_to_datetime(df_copy['endDate'], timezone)
    df_copy['Duration'] = calculate_duration(df_copy['Start Time'], df_copy['End Time'])

    df_copy['Featured Heroes (EN)'] = _translate_and_format_heroes(df_copy, 'H', en_map)
    df_copy['Non-Featured Heroes (EN)'] = _translate_and_format_heroes(df_copy, 'C', en_map)
    df_copy['Featured Heroes (JA)'] = _translate_and_format_heroes(df_copy, 'H', ja_map)
    df_copy['Non-Featured Heroes (JA)'] = _translate_and_format_heroes(df_copy, 'C', ja_map)

    return df_copy

def to_html_table(df, header_labels=None):
    if header_labels is None: header_labels = {}
    
    def sanitize_for_classname(text):
        text = text.lower()
        text = re.sub(r'[\s\(\)]+', '-', text)
        text = re.sub(r'[^a-z0-9-]', '', text)
        return f"col-{text.strip('-')}"
    
    table_html = '<table class="styled-table">'
    
    header_cells = []
    col_classnames = []
    for col in df.columns:
        classname = sanitize_for_classname(col)
        col_classnames.append(classname)
        display_name = header_labels.get(col, col)
        header_cells.append(f'<th class="{classname}">{display_name}</th>')
    
    header_html = "".join(header_cells)
    table_html += f"<thead><tr>{header_html}</tr></thead>"
    
    body_rows_html = []
    for index, row in df.iterrows():
        diff_status = row.get('_diff_status', 'unchanged')
        changed_cols = row.get('_changed_columns', [])
        row_class = f'diff-{diff_status}'
        row_html = f'<tr class="{row_class}">'
        
        for i, col_name in enumerate(df.columns):
            cell_value = row[col_name]
            classname = col_classnames[i]
            cell_classes = [classname]
            
            if diff_status == 'modified':
                if 'dates' in changed_cols and col_name in ['Start Time', 'End Time']:
                    cell_classes.append('diff-cell-highlight-date')
                if 'featured_heroes' in changed_cols and 'Featured Heroes' in col_name:
                    cell_classes.append('diff-cell-highlight-hero')
                if 'non_featured_heroes' in changed_cols and 'Non-Featured Heroes' in col_name:
                    cell_classes.append('diff-cell-highlight-hero-nonfeat')
            
            cell_content = ""
            if isinstance(cell_value, list):
                cell_content = "<br>".join(map(str, cell_value))
            elif isinstance(cell_value, str):
                if cell_value.startswith("http"):
                    cell_content = f'<img src="{cell_value}" class="icon-image">'
                else:
                    cell_content = cell_value.replace("\n", "<br>")
            else:
                cell_content = str(cell_value) if pd.notna(cell_value) else ""
            
            row_html += f'<td class="{" ".join(cell_classes)}">{cell_content}</td>'
        row_html += "</tr>"
        body_rows_html.append(row_html)
    
    body_html = "".join(body_rows_html)
    table_html += f"<tbody>{body_html}</tbody>"
    table_html += "</table>"
    return table_html