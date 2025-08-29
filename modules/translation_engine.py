# modules/translation_engine.py

import pandas as pd
import re

def _generate_final_names(row):
    """
    A helper function to generate final English and Japanese names based on rules.
    This function processes a single row of the merged hero data.
    """
    hero_id = row['ID']
    eng_name = row['Name']
    jp_base_name = row['TEXT']

    # Use English name as a fallback if Japanese name is missing
    if pd.isna(jp_base_name):
        jp_base_name = eng_name

    # --- Rule 1 (Highest Priority): Mimics ---
    if isinstance(hero_id, str) and hero_id.startswith("mimic_"):
        element = hero_id.split('_')[-1]
        
        eng_suffix_map = {"red": " <Fire>", "blue": " <Ice>", "green": " <Nature>", "yellow": " <Holy>", "purple": " <Dark>"}
        jp_suffix_map = {"red": "<炎>", "blue": "<氷>", "green": "<自然>", "yellow": "<聖>", "purple": "<闇>"}
        
        final_eng_name = f"{eng_name}{eng_suffix_map.get(element, '')}"
        final_jp_name = f"{jp_base_name}{jp_suffix_map.get(element, '')}"
        
        return {'en': final_eng_name, 'ja': final_jp_name}

    # --- Rule 2: Costumes ---
    costume_match = re.match(r'^(.*)\sC(\d*)$', str(eng_name))
    if costume_match:
        costume_num_str = costume_match.group(2)
        
        # ★★★ Corrected: Always use the jp_base_name for the root ★★★
        jp_root_name = jp_base_name 
        jp_suffix = "-コス" if costume_num_str == "" else f"-コス{costume_num_str}"
            
        final_eng_name = eng_name
        final_jp_name = jp_root_name + jp_suffix
        
        return {'en': final_eng_name, 'ja': final_jp_name}

    # --- Rule 3 (Default): Standard Heroes ---
    return {'en': eng_name, 'ja': jp_base_name}


def create_translation_dicts(hero_master_df, ja_df):
    """
    Creates comprehensive translation dictionaries for English and Japanese hero names.
    """
    hero_master_df['merge_key'] = hero_master_df['parentHeroId'].fillna(hero_master_df['ID'])
    merged_df = hero_master_df.merge(ja_df, left_on='merge_key', right_on='KEY', how='left')
    
    final_names = merged_df.apply(_generate_final_names, axis=1)
    final_names_df = pd.DataFrame(final_names.tolist(), index=merged_df.index)

    final_df = pd.concat([merged_df['ID'], final_names_df], axis=1)

    english_map = pd.Series(final_df.en.values, index=final_df.ID).to_dict()
    japanese_map = pd.Series(final_df.ja.values, index=final_df.ID).to_dict()

    return english_map, japanese_map