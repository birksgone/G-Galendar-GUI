import streamlit as st
import pandas as pd
import re
import base64
from pathlib import Path

def _check_condition(condition, row):
    """Checks if a single condition is met by the data row."""
    col = condition.get("column")
    op = condition.get("operator")
    val = condition.get("value")
    
    cell_value = str(row.get(col, ''))

    if op == "equals":
        return cell_value == val
    if op == "contains":
        return val in cell_value
    if op == "matches":
        return bool(re.search(val, cell_value))
    return False

def _find_matching_rule(row, rules):
    """Finds the first rule that matches the data row."""
    # Sort rules by priority, ascending
    sorted_rules = sorted(rules, key=lambda r: r.get("priority", 9999))
    
    for rule in sorted_rules:
        conditions = rule.get("conditions", [])
        # All conditions for a rule must be true
        if all(_check_condition(cond, row) for cond in conditions):
            return rule.get("output"), rule.get("icon")
            
    # If no rule matches, return a default
    return row.get('type', ''), None


def apply_formatting_rules(df, rules):
    """Applies all formatting rules to the dataframe to create new display columns."""
    if not rules:
        df['Display Type'] = df['type']
        df['Icon File'] = ''
        return df

    results = df.apply(lambda row: _find_matching_rule(row, rules), axis=1)
    
    # The result is a Series of tuples, expand it into two new columns
    df[['Display Type', 'Icon File']] = pd.DataFrame(results.tolist(), index=df.index)
    
    return df

@st.cache_data
def image_to_base64(image_path):
    """Converts a local image file to a Base64 encoded string."""
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except (FileNotFoundError, TypeError):
        return None # Return None if path is invalid or file not found