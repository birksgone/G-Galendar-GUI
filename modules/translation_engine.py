# modules/translation_engine.py

import pandas as pd

def create_translation_dicts(hero_master_df, g_sheet_df):
    """
    Creates translation dictionaries from the hero master data.
    """
    if g_sheet_df is None or g_sheet_df.empty:
        return {}, {}

    # The hero_master file is the single source of truth for translations.
    # It contains id, hero_en, and hero_ja columns.
    
    # Create a map from hero ID to English name.
    en_map = pd.Series(g_sheet_df.hero_en.values, index=g_sheet_df.id).to_dict()
    
    # Create a map from hero ID to Japanese name.
    ja_map = pd.Series(g_sheet_df.hero_ja.values, index=g_sheet_df.id).to_dict()
    
    return en_map, ja_map
