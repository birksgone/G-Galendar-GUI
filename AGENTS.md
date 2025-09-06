# Repository Guidelines

## Project Structure & Module Organization
- `app.py`: Main Streamlit app. Loads data, computes diffs, toggles “Show changes only” to render the forum‑post view inline.
- `modules/`: Core logic split by concern:
  - `data_loader.py`, `diff_engine.py`, `display_formatter.py`, `translation_engine.py`: load, compare, and format data.
  - `forum_post_creator.py`: forum post templating and UI renderer used by `app.py`.
- `data/`: Local cache and config (e.g., `config.json`, `type_mapping_rules.json`, downloaded `hero_master.csv`, optional `forum-template.txt`).
- `pages/`: Legacy page(s); main workflow now lives in `app.py`.

## Build, Test, and Development Commands
- Create venv: `python -m venv .venv` then `.\.venv\Scripts\Activate` (Windows) or `source .venv/bin/activate` (Unix).
- Install deps (no lockfile): `pip install streamlit pandas gspread oauth2client google-auth-httplib2 google-api-python-client`.
- Run app: `streamlit run app.py`.
- Optional lint/format (if installed): `black .` and `ruff check .`.

## Coding Style & Naming Conventions
- Python, 4‑space indent, PEP 8 style; prefer type hints and short, single‑purpose functions.
- Modules/variables: snake_case; classes: PascalCase; constants: UPPER_SNAKE_CASE.
- Keep UI code thin; put data/formatting logic in `modules/` and return DataFrames or plain dicts.

## Testing Guidelines
- No formal test suite. Validate via the UI:
  - Load a “Latest Data” folder and a “Previous Data” folder; confirm diff highlights and timezone toggle.
  - Switch the radio to “Show changes only” and verify forum post table and generated texts.
  - Ensure `data/forum-template.txt` keys (e.g., `[new_en]`, `[new_ja]`, `[changed_en]`) render without missing placeholders.
- Use small sample CSVs in `data/` for quick iterations.

## Commit & Pull Request Guidelines
- Commits: small and scoped. Suggested format: `feat: …`, `fix: …`, `refactor: …`, `docs: …`.
- PRs: include summary, screenshots/GIFs of UI states, reproduction steps, and linked issues. Note any data or config assumptions.

## Security & Configuration Tips
- Place Google service account JSON as `client_secret.json` in the repo root (kept private). Ensure it remains git‑ignored.
- External data lives under versioned folders (see Project Overview). Avoid hard‑coding local absolute paths in new code.

