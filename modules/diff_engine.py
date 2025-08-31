import pandas as pd
import numpy as np

def compare_dataframes(current_df, previous_df):
    hero_cols_h = [f'H{i}' for i in range(1, 7)]
    hero_cols_c = [f'C{i}' for i in range(1, 7)]
    date_cols = ['startDate', 'endDate']
    
    merged_df = pd.merge(
        current_df.add_suffix('_curr'),
        previous_df.add_suffix('_prev'),
        left_on='diff_id_curr',
        right_on='diff_id_prev',
        how='outer'
    )
    
    diff_rows = []
    for _, row in merged_df.iterrows():
        is_new = pd.isna(row['diff_id_prev'])
        is_deleted = pd.isna(row['diff_id_curr'])
        
        status = ''
        changed_cols = set()
        row_data = {}
        
        if is_new:
            status = 'new'
            for col in current_df.columns:
                row_data[col] = row[f'{col}_curr']
        elif is_deleted:
            status = 'deleted'
            for col in previous_df.columns:
                row_data[col] = row[f'{col}_prev']
        else:
            status = 'unchanged'
            for col in current_df.columns:
                row_data[col] = row[f'{col}_curr']

            for col in date_cols:
                if row[f'{col}_curr'] != row[f'{col}_prev']:
                    status = 'modified'
                    changed_cols.add('dates')

            curr_h = set(row[[f'{h}_curr' for h in hero_cols_h]].dropna())
            prev_h = set(row[[f'{h}_prev' for h in hero_cols_h]].dropna())
            if curr_h != prev_h:
                status = 'modified'
                changed_cols.add('featured_heroes')

            curr_c = set(row[[f'{c}_curr' for c in hero_cols_c]].dropna())
            prev_c = set(row[[f'{c}_prev' for c in hero_cols_c]].dropna())
            if curr_c != prev_c:
                status = 'modified'
                changed_cols.add('non_featured_heroes')

        row_data['_diff_status'] = status
        row_data['_changed_columns'] = list(changed_cols)
        diff_rows.append(row_data)

    result_df = pd.DataFrame(diff_rows)
    
    result_df['sort_key'] = pd.to_datetime(result_df['startDate'], errors='coerce')
    result_df.sort_values(by='sort_key', inplace=True, na_position='last')
    result_df.drop(columns='sort_key', inplace=True)
    
    return result_df