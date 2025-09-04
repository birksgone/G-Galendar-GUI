# modules/translation_engine.py

import pandas as pd
import re

def _generate_final_names(row, hero_en_to_key_map, dragon_en_to_key_map, key_to_ja_map):
    hero_id = row['id']
    eng_name = row['heroname_en']

    if isinstance(eng_name, str) and eng_name.startswith('dragon_'):
        # This is a dragon. The lookup key is the ID-like name (e.g., 'dragon_firewing')
        lookup_key = eng_name
        
        hero_key = dragon_en_to_key_map.get(lookup_key)
        if hero_key is None:
            hero_key = hero_en_to_key_map.get(lookup_key)
            
        if hero_key:
            # The display name needs to be cleaned up.
            display_name = eng_name.replace('dragon_', '').replace('_', ' ').title()
            jp_name = key_to_ja_map.get(hero_key, display_name)
            return {'en': display_name, 'ja': jp_name}
        else:
            # Fallback, but still clean up the name for display.
            display_name = eng_name.replace('dragon_', '').replace('_', ' ').title()
            return {'en': display_name, 'ja': display_name}

    # Original logic for non-dragons
    base_eng_name = eng_name
    costume_part = ""
    costume_match = re.match(r'^(.*)\s(C(\d*))$', str(eng_name))
    if costume_match:
        base_eng_name = costume_match.group(1)
        costume_part = costume_match.group(2)

    hero_key = hero_en_to_key_map.get(base_eng_name)
    if hero_key is None:
        hero_key = dragon_en_to_key_map.get(base_eng_name)

    jp_base_name = key_to_ja_map.get(hero_key, base_eng_name)
    
    if isinstance(hero_id, str) and hero_id.startswith("mimic_"):
        jp_cleaned_base = re.sub(r'<.*>', '', str(jp_base_name)).strip()
        
        element = hero_id.split('_')[-1]
        en_suffix = {"red": " <Fire>", "blue": " <Ice>", "green": " <Nature>", "yellow": " <Holy>", "purple": " <Dark>"}.get(element, "")
        jp_suffix = {"red": "<炎>", "blue": "<氷>", "green": "<自然>", "yellow": "<聖>", "purple": "<闇>"}.get(element, "")
        
        return {'en': f"{eng_name}{en_suffix}", 'ja': f"{jp_cleaned_base}{jp_suffix}"}

    if costume_part:
        costume_num_str = costume_part.replace('C', '').strip()
        jp_suffix = "-コス" if costume_num_str == "" else f"-コス{costume_num_str}"
        final_jp_name = jp_base_name + jp_suffix
        return {'en': eng_name, 'ja': final_jp_name}

    return {'en': eng_name, 'ja': jp_base_name}

def create_translation_dicts(hero_master_df, g_sheet_df):
    heroes_df = g_sheet_df[g_sheet_df['id'].str.startswith('heroes.')]
    dragons_df = g_sheet_df[g_sheet_df['id'].str.startswith('dragons.')]

    hero_en_to_key_map = pd.Series(heroes_df.id.values, index=heroes_df.hero_en).to_dict()
    dragon_en_to_key_map = pd.Series(dragons_df.id.values, index=dragons_df.hero_en).to_dict()

    key_to_ja_text_map = pd.Series(g_sheet_df.hero_ja.values, index=g_sheet_df.id).to_dict()
    
    final_names = hero_master_df.apply(
        _generate_final_names, axis=1, 
        hero_en_to_key_map=hero_en_to_key_map, 
        dragon_en_to_key_map=dragon_en_to_key_map, 
        key_to_ja_map=key_to_ja_text_map
    )
    final_names_df = pd.DataFrame(final_names.tolist(), index=hero_master_df.index)
    # 'ID' -> 'id'
    final_df = pd.concat([hero_master_df['id'], final_names_df], axis=1)

    # 'ID' -> 'id'
    english_map = pd.Series(final_df.en.values, index=final_df.id).to_dict()
    japanese_map = pd.Series(final_df.ja.values, index=final_df.id).to_dict()
    return english_map, japanese_map