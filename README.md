# Project Samarth — Local Q&A prototype

A local prototype: an intelligent Q&A web app that answers agriculture & climate questions using local CSV datasets (origin: data.gov.in).  
This repository contains a Flask backend, simple CSV loaders, a lightweight front-end UI, visualization support and *provenance* (dataset names / rows used) for traceability.

> Author / Owner: `d0k7`  
> Note: this is an educational prototype focused on ingesting local CSV files and answering structured questions (e.g. “Compare the average annual climate metric in StateA and StateB for the last 5 years.”).

---

## Features

- Read local CSV files (example dataset files included under `data/`) and detect relevant columns.
- Compute simple metrics (e.g., average annual climate metric), aggregate crop production, generate a small bar chart (base64 PNG) and produce traceable provenance JSON.
- Minimal, responsive UI with query box, results, tables and provenance pane.
- Robust heuristics for column detection (normalization, fallbacks) and verbose provenance when detection fails.

---

## Repository structure

.
├── app/
│ ├── init.py
│ ├── analytics.py
│ ├── data_fetching.py
│ ├── loaders.py # CSV loaders (adapt these for new dataset schemas)
│ ├── query_executor.py # Core question -> data mapping & answer generation
│ ├── routes.py # Flask endpoints (/ and /api/query)
│ ├── utils.py # helper functions (plot -> base64, etc.)
│ ├── static/
│ │ └── style.css
│ └── templates/
│ └── index.html
├── data/ # Local CSVs (optional; may be gitignored)
├── scripts/
│ └── diagnose_data.py # Data diagnosis helper (inspects CSV structure)
├── requirements.txt
├── app.py # app entrypoint (runs Flask)
├── README.md # <-- you are here
└── .gitignore



---

## Prerequisites

- Python 3.10+ (3.11 tested)
- pip
- git

> Windows users: PowerShell examples are provided. On macOS/Linux use `bash` commands (small changes: `source .samarth/bin/activate` instead of `.\.samarth\Scripts\Activate.ps1`).

---

## Quick start (Windows PowerShell)

Open PowerShell in the project root (e.g. `C:\Users\dheer\Dropbox\project-samarth`):

```powershell
# 1) Create virtual environment (one time)
python -m venv .samarth

# 2) Activate it
.\.samarth\Scripts\Activate.ps1

# 3) Upgrade pip and install requirements
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# NOTE: If you see numpy/matplotlib errors (common on Windows), run:
python -m pip install --no-cache-dir --force-reinstall "numpy<2" matplotlib

# 4) Run the app
python app.py


Usage examples / sample queries

Examples you can paste into the UI query box:

list states

Compare the average annual climate metric in StateA and StateB for the last 5 years.

Top 3 crops in All India for last 5 years

Identify district in StateA with the highest production of Rice in the most recent year available

Analyze the production trend of Wheat in All India over the last decade

