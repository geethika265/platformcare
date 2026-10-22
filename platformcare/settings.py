import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

def db_path():
    return Path(os.getenv("PLATFORM_DB", str(ROOT / "data/platform.db")))

def token():
    return os.getenv("PLATFORM_TOKEN", "local-demo-change-me")
