import pandas as pd
import numpy as np

def _are_different(val1, val2):
    """Helper to compare values, treating NaNs as equal."""
    if pd.isna(val1) and pd.isna(val2):
        return False
    if pd.isna(val1) or pd.isna(val2):
        return True
    return val1 != val2

def compare_dataframes(current_df, previous_df):
    hero_cols_h = [f'H{i}' for i in range(1, 7)]
    hero_cols_c = [f'C{i}' for i in range(1, 7)]
    date_cols = ['startDate', 'endDate']

    # Initialize the new column with a default value
    current_df['original_startDate'] = np.nan

    # Stage 1: Initial diff on diff_id
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

            # This block only runs for rows that matched on diff_id, 
            # meaning they are not date-moved events.
            for col in date_cols:
                if _are_different(row[f'{col}_curr'], row[f'{col}_prev']):
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

    # Stage 2: Find moved events and perform detailed diff on them
    new_rows = result_df[result_df['_diff_status'] == 'new'].copy()
    deleted_rows = result_df[result_df['_diff_status'] == 'deleted'].copy()

    if not new_rows.empty and not deleted_rows.empty and 'unique_id' in result_df.columns:
        new_rows.dropna(subset=['unique_id'], inplace=True)
        deleted_rows.dropna(subset=['unique_id'], inplace=True)

        new_rows.loc[:, 'unique_id'] = new_rows['unique_id'].astype(str).str.strip()
        deleted_rows.loc[:, 'unique_id'] = deleted_rows['unique_id'].astype(str).str.strip()

        new_id_to_idx_map = pd.Series(new_rows.index, index=new_rows['unique_id']).to_dict()
        del_id_to_idx_map = pd.Series(deleted_rows.index, index=deleted_rows['unique_id']).to_dict()

        common_ids = set(new_id_to_idx_map.keys()) & set(del_id_to_idx_map.keys())
        
        matched_deleted_indices = []
        for uid in common_ids:
            new_idx = new_id_to_idx_map[uid]
            del_idx = del_id_to_idx_map[uid]

            new_event_data = new_rows.loc[new_idx]
            deleted_event_data = deleted_rows.loc[del_idx]
            
            changed_cols = set()

            if _are_different(new_event_data['startDate'], deleted_event_data['startDate']) or _are_different(new_event_data['endDate'], deleted_event_data['endDate']):
                changed_cols.add('dates')

            new_h = set(new_event_data[hero_cols_h].dropna())
            del_h = set(deleted_event_data[hero_cols_h].dropna())
            if new_h != del_h:
                changed_cols.add('featured_heroes')

            new_c = set(new_event_data[hero_cols_c].dropna())
            del_c = set(deleted_event_data[hero_cols_c].dropna())
            if new_c != del_c:
                changed_cols.add('non_featured_heroes')
            
            if changed_cols:
                result_df.loc[new_idx, '_diff_status'] = 'shifted'
                result_df.loc[new_idx, 'original_startDate'] = deleted_event_data['startDate']
                result_df.at[new_idx, '_changed_columns'] = list(changed_cols)
                matched_deleted_indices.append(del_idx)
        
        if matched_deleted_indices:
            result_df.drop(matched_deleted_indices, inplace=True)

    # Final sort
    result_df['sort_key'] = pd.to_datetime(result_df['startDate'], errors='coerce')
    result_df.sort_values(by='sort_key', inplace=True, na_position='last')
    result_df.drop(columns='sort_key', inplace=True)
    
    return result_df