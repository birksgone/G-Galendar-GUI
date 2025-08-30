import json
import shutil
from pathlib import Path

# --- Configuration ---
# Please adjust these paths if necessary.

# The JSON file containing the icon filenames.
RULES_FILE_PATH = Path("data/type_mapping_rules.json")

# The source directory where all your original icon files are stored.
ICON_SOURCE_DIR = Path("D:/KB/_all_link_images/Sprite/")

# The destination directory where the necessary icons will be copied.
# This folder will be created if it doesn't exist.
DESTINATION_DIR = Path("D:/KB/_all_link_images/toFTP/")

# --- Main Script Logic ---
def collect_icons():
    """
    Reads the rules JSON, finds the specified icon files,
    and copies them to the destination folder for FTP upload.
    """
    print("--- Icon Collector Script Started ---")

    # 1. Ensure the destination directory exists
    DESTINATION_DIR.mkdir(exist_ok=True)
    print(f"Destination folder is: {DESTINATION_DIR}")

    # 2. Load the rules JSON file
    if not RULES_FILE_PATH.exists():
        print(f"Error: Rules file not found at '{RULES_FILE_PATH}'")
        return

    try:
        with open(RULES_FILE_PATH, 'r', encoding='utf-8') as f:
            rules = json.load(f)
        print(f"Successfully loaded {len(rules)} rules from JSON.")
    except json.JSONDecodeError as e:
        print(f"Error: Failed to decode JSON from '{RULES_FILE_PATH}'. Details: {e}")
        return

    # 3. Extract unique icon filenames
    icon_filenames = set()
    for rule in rules:
        icon_file = rule.get("icon")
        if icon_file: # Make sure it's not None or an empty string
            icon_filenames.add(icon_file)
            
    if not icon_filenames:
        print("No icon filenames found in the JSON file.")
        return
        
    print(f"Found {len(icon_filenames)} unique icon filenames to collect.")

    # 4. Copy files from source to destination
    copied_count = 0
    not_found_count = 0
    not_found_list = []

    for filename in sorted(list(icon_filenames)):
        source_path = ICON_SOURCE_DIR / filename
        destination_path = DESTINATION_DIR / filename

        if source_path.exists():
            try:
                shutil.copy2(source_path, destination_path)
                print(f"  -> Copied: {filename}")
                copied_count += 1
            except Exception as e:
                print(f"  -> Error copying {filename}: {e}")
        else:
            print(f"  -> Not Found: {filename}")
            not_found_count += 1
            not_found_list.append(filename)

    # 5. Print a summary
    print("\n--- Summary ---")
    print(f"Successfully copied: {copied_count} files.")
    print(f"Files not found: {not_found_count} files.")
    
    if not_found_list:
        print("\nThe following files were not found in the source directory:")
        for filename in not_found_list:
            print(f"  - {filename}")

    print("\n--- Script Finished ---")


if __name__ == "__main__":
    collect_icons()