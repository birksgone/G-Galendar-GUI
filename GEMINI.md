# G-Calendar GUI

## Project Overview

This project is a Python-based web application that uses the Streamlit framework to provide a graphical user interface (GUI) for managing and viewing complex event calendar data. The data is originally managed in Google Sheets and is processed locally by this tool.

The main functionalities of the application are:

*   **Dynamic Event Calendar Display**: It displays event data in a clean, table format for a specified period. It also supports real-time switching between UTC and JST timezones.
*   **Powerful Diff Highlight Feature**: It compares two different data points (e.g., `V7900R-2025-08-29` vs `V7803R-2025-08-25`) and highlights new additions, deletions, and modifications with intuitive color-coding.
*   **Flexible Display Customization**: It offers presets for "Standard" (main columns only) and "All Columns" (all data columns) views. Users can also individually select which columns to display.
*   **Automatic Hero Name Translation**: It automatically translates hero IDs like `H1` and `C1` into their corresponding English and Japanese names.
*   **New Hero Display**: It automatically adds a "🆕" emoji to newly introduced heroes.

## Building and Running

To run this project, you need to have Python and the required libraries installed.

1.  **Install Libraries**:
    The `README.md` file recommends creating a `requirements.txt` file with the following content:

    ```txt
    streamlit
    pandas
    gspread
    oauth2client
    google-auth-httplib2
    ```

    You can install these libraries using pip:

    ```bash
    pip install -r requirements.txt
    ```

2.  **Set up Authentication**:
    To access the Google Sheets API, you need to set up `gspread` authentication. Place the authentication JSON file (e.g., `service_account.json`) downloaded from Google Cloud in the `/.config/gspread/` directory.

3.  **Run the Application**:
    To start the application, run the following command in the project's root directory:

    ```bash
    streamlit run app.py
    ```

## Development Conventions

*   **Modular Structure**: The application is divided into several modules, each with a specific responsibility:
    *   `data_loader.py`: Loads all data (CSV, Google Sheets).
    *   `diff_engine.py`: Compares two datasets and generates diff information.
    *   `display_formatter.py`: Formats data for display (translation, HTML table generation, etc.).
    *   `translation_engine.py`: Creates a translation dictionary for hero names.
*   **Configuration Files**: The application uses JSON files for configuration:
    *   `data/config.json`: Remembers the application's state (selected folder names, columns, etc.).
    *   `data/type_mapping_rules.json`: Defines rules for display names and icons.
*   **Styling**: The application's appearance is defined in the `styles.css` file.
*   **Caching**: The application uses Streamlit's `@st.cache_data` decorator to cache data and improve performance.
*   **History**: The application keeps a history of used folder names in `data/.history_event.log`.
