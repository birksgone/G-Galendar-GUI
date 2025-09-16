import pandas as pd
import re

BASE_ICON_URL = "https://bbcamp.info/wp-content/uploads/camp-img/calendar_type_icon/"

def convert_posix_to_datetime(series, target_tz='UTC'):
    # Handle overflow by filtering out values that would cause FloatingPointError
    max_safe_timestamp = 2**53 - 1  # Maximum safe integer in JavaScript (also prevents overflow)
    
    # Create a mask for values that won't cause overflow
    safe_mask = (series + 946684800) <= max_safe_timestamp
    
    # Convert only safe values, others will be NaT
    safe_values = series[safe_mask] + 946684800
    utc_time = pd.to_datetime(safe_values, unit='s', errors='coerce')
    
    # Apply timezone localization only to non-NaT values
    if not utc_time.empty:
        utc_time = utc_time.dt.tz_localize('UTC')
    
    # Create result series with NaT for overflow values
    result = pd.Series(pd.NaT, index=series.index, dtype='datetime64[ns, UTC]')
    result[safe_mask] = utc_time
    
    # Convert to proper timezone only if there are valid datetime values
    if not result.empty and result.notna().any():
        if target_tz == 'JST':
            result = result.dt.tz_convert('Asia/Tokyo')
        else:
            result = result.dt.tz_convert('UTC')
    
    return result

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
            post_name = rule.get('post_name', display_name)
            icon_filename = rule.get('icon', '')
            icon_url = f"{BASE_ICON_URL}{icon_filename}" if icon_filename else None
            return pd.Series([display_name, icon_url, post_name])
    default_type = row.get('type', '')
    return pd.Series([default_type, None, default_type])

def _translate_and_format_heroes(df, prefix, lang_map, separator):
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
        # Use line breaks for HTML display, but keep original separators for internal use
        if separator in [", ", "、"]:  # These are the display separators
            hero_lists.append("<br>".join(heroes) if heroes else "")
        else:
            hero_lists.append(separator.join(heroes) if heroes else "")
    return hero_lists

def format_dataframe_for_display(df, type_mapping_rules, en_map, ja_map, timezone):
    df_copy = df.copy()

    df_copy[['Display Type', 'Icon', 'Post Name']] = df_copy.apply(
        _get_display_info, args=(type_mapping_rules,), axis=1
    )
    df_copy['Event Name'] = df_copy['Post Name']
    
    # Add English and Japanese event titles from mapping rules
    def _get_event_titles(row, rules):
        for rule in sorted(rules, key=lambda x: x.get('priority', float('inf'))):
            conditions = rule.get('conditions', [])
            if all(_check_condition(row, cond) for cond in conditions):
                event_title_en = rule.get('event_title_en', row.get('Post Name', ''))
                event_title_ja = rule.get('event_title_ja', row.get('Post Name', ''))
                return pd.Series([event_title_en, event_title_ja])
        return pd.Series([row.get('Post Name', ''), row.get('Post Name', '')])
    
    df_copy[['event_title_en', 'event_title_ja']] = df_copy.apply(
        _get_event_titles, args=(type_mapping_rules,), axis=1
    )
    
    df_copy['Start Time'] = convert_posix_to_datetime(df_copy['startDate'], timezone)
    df_copy['End Time'] = convert_posix_to_datetime(df_copy['endDate'], timezone)

    # Add pre-formatted ISO date and time columns for templating
    df_copy['start_date_iso'] = df_copy['Start Time'].apply(lambda x: x.strftime('%Y-%m-%d') if pd.notna(x) else '')
    df_copy['start_time_iso'] = df_copy['Start Time'].apply(lambda x: x.strftime('%H:%M:%S') if pd.notna(x) else '')
    df_copy['end_date_iso'] = df_copy['End Time'].apply(lambda x: x.strftime('%Y-%m-%d') if pd.notna(x) else '')
    df_copy['end_time_iso'] = df_copy['End Time'].apply(lambda x: x.strftime('%H:%M:%S') if pd.notna(x) else '')
    df_copy['start_date_md'] = df_copy['Start Time'].apply(lambda x: f"{x.month}/{x.day}" if pd.notna(x) else "")
    df_copy['end_date_md'] = df_copy['End Time'].apply(lambda x: f"{x.month}/{x.day}" if pd.notna(x) else "")

    # Handle original start date for shifted events
    if 'original_startDate' in df_copy.columns:
        original_start_time = convert_posix_to_datetime(df_copy['original_startDate'], timezone)
        
        def format_en_date(dt):
            if pd.isna(dt):
                return ""
            return dt.strftime('%b ') + str(dt.day)

        df_copy['original_start_date_iso'] = original_start_time.apply(lambda x: x.strftime('%Y-%m-%d') if pd.notna(x) else '')
        df_copy['original_start_date_iso_md'] = original_start_time.apply(lambda x: f"{x.month}/{x.day}" if pd.notna(x) else "")
        df_copy['original_start_date_iso_en'] = original_start_time.apply(format_en_date)
    else:
        df_copy['original_start_date_iso'] = ""
        df_copy['original_start_date_iso_md'] = ""
        df_copy['original_start_date_iso_en'] = ""

    df_copy['Duration'] = calculate_duration(df_copy['Start Time'], df_copy['End Time'])

    df_copy['Featured Heroes (EN)'] = _translate_and_format_heroes(df_copy, 'H', en_map, ", ")
    df_copy['Non-Featured Heroes (EN)'] = _translate_and_format_heroes(df_copy, 'C', en_map, ", ")
    df_copy['Featured Heroes (JA)'] = _translate_and_format_heroes(df_copy, 'H', ja_map, "、")
    df_copy['Non-Featured Heroes (JA)'] = _translate_and_format_heroes(df_copy, 'C', ja_map, "、")

    return df_copy

def to_html_table(df, header_labels=None, columns_to_display=None, data_dir=None):
    if header_labels is None: header_labels = {}

    if columns_to_display is None:
        internal_cols = ['_diff_status', '_changed_columns']
        columns_to_display = [col for col in df.columns if col not in internal_cols]

    def sanitize_for_classname(text):
        text = str(text)
        text = text.lower()
        text = re.sub(r'[\s\(\)\.]+', '-', text)
        text = re.sub(r'[^a-z0-g-]', '', text)
        return f"col-{text.strip('-')}"

    table_html = '<table class="styled-table">'

    header_cells = []
    col_classnames = {col: sanitize_for_classname(header_labels.get(col, col)) for col in columns_to_display}
    for col in columns_to_display:
        display_name = header_labels.get(col, col)
        header_cells.append(f'<th class="{col_classnames[col]}">{display_name}</th>')
    
    header_html = "".join(header_cells)
    table_html += f"<thead><tr>{header_html}</tr></thead>"

    body_rows_html = []
    for index, row in df.iterrows():
        diff_status = row.get('_diff_status', 'unchanged')
        changed_cols = row.get('_changed_columns', [])
        row_class = f'diff-{diff_status}'
        row_html = f'<tr class="{row_class}">'
        
        for col_name in columns_to_display:
            cell_value = row.get(col_name)
            classname = col_classnames[col_name]
            cell_classes = [classname]
            
            if diff_status == 'modified':
                if 'dates' in changed_cols and col_name in ['Start Time', 'End Time']:
                    cell_classes.append('diff-cell-highlight-date')
                if 'featured_heroes' in changed_cols and 'Featured Heroes' in col_name:
                    cell_classes.append('diff-cell-highlight-hero')
                if 'non_featured_heroes' in changed_cols and 'Non-Featured Heroes' in col_name:
                    cell_classes.append('diff-cell-highlight-hero-nonfeat')
            
            cell_content = ""
            if col_name == 'questline' and data_dir and isinstance(cell_value, str) and cell_value.startswith("img_gen="):
                # action=generate_image パラメータを追加し、メインアプリのルートを指すように修正
                params = f"action=generate_image&data_dir={data_dir}&{cell_value}"
                cell_content = f'<a href="/?{params}" target="_self">Generate Image</a>'
            elif isinstance(cell_value, list):
                cell_content = "<br>".join(map(str, cell_value))
            elif isinstance(cell_value, str):
                if cell_value.startswith(BASE_ICON_URL):
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
