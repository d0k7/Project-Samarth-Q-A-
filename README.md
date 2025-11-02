# Project Samarth - Prototype

Quick start:
1. Create virtualenv & install deps:
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt

2. Copy `.env.example` to `.env` and add DATA_GOV_API_KEY if you have one.

3. Run:
   $env:FLASK_APP="app"
   flask run

4. Open http://127.0.0.1:5000

Notes:
- The app will use sample CSVs under `data/` if present; otherwise it creates tiny sample tables.
- To use live data.gov.in, add `DATA_GOV_API_KEY` and run `python .\scripts\discover_resources.py` to list candidate resources, then update `scripts\etl_fetch_and_normalize.py` with chosen resource_id(s).
