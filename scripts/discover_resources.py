"""
Small helper to note candidate resource IDs from data.gov.in.

Usage:
  python scripts/discover_resources.py
"""
import os
from dotenv import load_dotenv
load_dotenv()
API_KEY = os.getenv("DATA_GOV_API_KEY", "")

def main():
    if not API_KEY:
        print("No DATA_GOV_API_KEY set. Add it to .env to use this script.")
        return
    print("Use data.gov.in website to find resource_id for:")
    print("- Crop production statistics (state/district level)")
    print("- IMD rainfall / sub-divisional monthly rainfall")
    print("- Administrative codes / district lists")
    print("")
    print("Open https://data.gov.in and search 'crop production', 'IMD rainfall' and copy the resource_id(s) into scripts/etl_fetch_and_normalize.py")

if __name__ == "__main__":
    main()
