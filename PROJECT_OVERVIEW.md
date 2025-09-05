# Project Overview

This document outlines the architecture and data flow of the G-Calendar-GUI application.

## 1. Application Purpose

The application provides a web-based interface to view and compare event calendar data. It highlights differences between two data versions and provides flexible display options, including translation of hero names between English and Japanese.

## 2. Data Flow

The application uses two main sources of data:

### a. Local Event Data

-   **Location:** Event data is stored in local directories. The base path is configured as `D:/PyScript/EMP Extract/`.
-   **Structure:** Inside the base path, there are folders for each data version (e.g., `V7900R-2025-09-03`). The application user selects these folders in the UI.
-   **File Format:** Each event folder contains a main CSV file named `calendar-export-{folder_name}.csv` (e.g., `calendar-export-V7900R-2025-09-03.csv`). This file contains the detailed event schedule.

### b. Hero & Translation Data

-   **Source:** Hero master data and name translations are managed in a single CSV file stored on Google Drive.
-   **File ID:** `1rpfF-gNclicG0wwtY_EMKKdlqsRBSKjB`
-   **File Name:** `hero_master.csv`
-   **Access:** The application uses a Google Service Account (`client_secret.json`) to access and download this file.
-   **Local Cache:** When the application runs, it downloads the latest version of `hero_master.csv` and saves it to the local `data/` directory. This local copy is then used for all hero data processing and translations.
-   **Columns:** The CSV file contains the following important columns:
    -   `id`: The unique identifier for the hero or dragon (e.g., `fire_god_zidane`, `dragon_firewing`).
    -   `heroname_en`: The English name.
    -   `heroname_ja`: The Japanese name.

## 3. Core Modules

-   `app.py`: The main Streamlit application script. It handles the UI, user input, and orchestrates the calls to other modules.
-   `modules/data_loader.py`: Responsible for loading all data. It reads the local event CSVs and downloads the hero data from Google Drive.
-   `modules/translation_engine.py`: Handles the translation of hero and dragon names. It creates translation maps from the `hero_master.csv` data.
-   `modules/diff_engine.py`: Compares two versions of the event data and identifies differences.
-   `modules/display_formatter.py`: Formats the data for display in the UI, including generating the final HTML table.

## 4. Execution Flow

1.  The user launches the app via `streamlit run app.py`.
2.  The user selects the "Latest Data" folder (and optionally a "Previous Data" folder) in the sidebar.
3.  When the "Load Data" button is clicked, `app.py` calls `modules.data_loader.load_all_data`.
4.  `data_loader.py`:
    -   Downloads the latest `hero_master.csv` from Google Drive to `data/hero_master.csv`.
    -   Loads the local `calendar-export-*.csv` file(s).
    -   Loads the `data/hero_master.csv` into a DataFrame.
    -   Returns all data in a dictionary.
5.  `app.py` then passes the data to `translation_engine.py` and `diff_engine.py` for processing.
6.  The final, processed data is displayed in a formatted table in the UI.
