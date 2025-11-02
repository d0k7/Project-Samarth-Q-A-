# app/config.py
import os
from dotenv import load_dotenv
load_dotenv()

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(BASE_DIR, "data")

class Config:
    DATA_GOV_API_KEY = os.getenv("DATA_GOV_API_KEY", "")
    PORT = int(os.getenv("PORT", 5000))
    DATA_DIR = DATA_DIR
