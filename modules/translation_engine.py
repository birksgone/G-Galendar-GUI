# modules/translation_engine.py

import pandas as pd
import re

def _generate_final_names(row, en_to_key_map, key_to_ja_map):
    """
    Generates final English and Japanese names for a single hero row.
    """
    hero_id = row['ID']
    eng_name = row['Name'] # This is the structured English name like "Vivica C3"
    
    # --- Deconstruct English Name ---
    base_eng_name = eng_name
    costume_part = ""
    costume_match = re.match(r'^(.*)\s(C(\d*))$', str(eng_name))
    if costume_match:
        base_eng_name = costume_match.group(1) # e.g., "Vivica"
        costume_part = costume_match.group(2)  # e.g., "C3"

    # --- Translate using dictionaries ---
    hero_key = en_to_key_map.get(base_eng_name)
    jp_base_name = key_to_ja_map.get(hero_key, base_eng_name)
    
    # --- Rule 1: Mimics (as a special case, name is modified after lookup) ---
    if isinstance(hero_id, str) and hero_id.startswith("mimic_"):
        element = hero_id.split('_')[-1]
        en_suffix = {"red": " <Fire>", "blue": " <Ice>", "green": " <Nature>", "yellow": " <Holy>", "purple": " <Dark>"}.get(element, "")
        jp_suffix = {"red": "<炎>", "blue": "<氷>", "green": "<自然>", "yellow": "<聖>", "purple": "<闇>"}.get(element, "")
        
        return {'en': f"{base_eng_name}{en_suffix}", 'ja': f"{jp_base_name}{jp_suffix}"}

    # --- Rule 2: Costumes ---
    if costume_part:
        costume_num_str = costume_part.replace('C', '').strip()
        jp_suffix = "-コス" if costume_num_str == "" else f"-コス{costume_num_str}"
        final_jp_name = jp_base_name + jp_suffix
        return {'en': eng_name, 'ja': final_jp_name}

    # --- Rule 3 (Default): Standard Heroes ---
    return {'en': eng_name, 'ja': jp_base_name}


def create_translation_dicts(hero_master_df, g_sheet_df):
    """
    Creates translation dictionaries using the live Google Sheet data. 
    """
    # Use specified column names, fall back to indices
    g_sheet_df.columns = ['hero_ja', 'id', 'hero_en'] + list(g_sheet_df.columns[3:])
    
    # Create the necessary mapping dictionaries
    en_text_to_key_map = pd.Series(g_sheet_df.id.values, index=g_sheet_df.hero_en).to_dict()
    key_to_ja_text_map = pd.Series(g_sheet_df.hero_ja.values, index=g_sheet_df.id).to_dict()
    
    # Apply the translation logic to each row of the hero master
    final_names = hero_master_df.apply(
        _generate_final_names, 
        axis=1, 
        en_to_key_map=en_text_to_key_map, 
        key_to_ja_map=key_to_ja_text_map
    )
    final_names_df = pd.DataFrame(final_names.tolist(), index=hero_master_df.index)

    # Combine with the original IDs to create the final maps
    final_df = pd.concat([hero_master_df['ID'], final_names_df], axis=1)

    english_map = pd.Series(final_df.en.values, index=final_df.ID).to_dict()
    japanese_map = pd.Series(final_df.ja.values, index=final_df.ID).to_dict()

    return english_map, japanese_map