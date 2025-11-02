"""
Example ETL runner: update resource_id values and run to fetch CSVs into data/.
Edit the resource ids below (found from data.gov.in portal).
"""
import os
from dotenv import load_dotenv
load_dotenv()
from app.data_fetching import fetch_datagov_resource
from app.config import Config

API_KEY = os.getenv("DATA_GOV_API_KEY", "")
DATA_DIR = Config.DATA_DIR

CROP_RESOURCE_ID = "REPLACE_WITH_CROP_RESOURCE_ID"
RAIN_RESOURCE_ID = "REPLACE_WITH_RAIN_RESOURCE_ID"

def run():
    os.makedirs(DATA_DIR, exist_ok=True)
    if API_KEY and not CROP_RESOURCE_ID.startswith("REPLACE"):
        print("Fetching crop production...")
        df, meta = fetch_datagov_resource(CROP_RESOURCE_ID, API_KEY, dest_filename="crop_production.csv")
        print("fetched rows:", meta)
    else:
        print("Skipping crop fetch — set API key and CROP_RESOURCE_ID.")

    if API_KEY and not RAIN_RESOURCE_ID.startswith("REPLACE"):
        print("Fetching rainfall...")
        df, meta = fetch_datagov_resource(RAIN_RESOURCE_ID, API_KEY, dest_filename="rainfall.csv")
        print("fetched rows:", meta)
    else:
        print("Skipping rainfall fetch — set API key and RAIN_RESOURCE_ID.")

if __name__ == "__main__":
    run()
