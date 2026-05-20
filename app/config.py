from pathlib import Path
from dotenv import load_dotenv
import os

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/project_radar.sqlite")

DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"

DOCS_DIR = BASE_DIR / "docs"
REPORTS_DIR = BASE_DIR / "reports"

OUTPUT_JSON = BASE_DIR / os.getenv("OUTPUT_JSON", "docs/data.json")
OUTPUT_HTML = BASE_DIR / os.getenv("OUTPUT_HTML", "docs/index.html")
