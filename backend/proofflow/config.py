from pathlib import Path
import os

BACKEND_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = BACKEND_ROOT / "data"
DEFAULT_DB_PATH = DEFAULT_DATA_DIR / "proofflow.db"


def get_db_path() -> Path:
    configured_path = os.getenv("PROOFFLOW_DB_PATH")
    if configured_path:
        return Path(configured_path).expanduser().resolve()
    return DEFAULT_DB_PATH


def get_data_dir() -> Path:
    configured_path = os.getenv("PROOFFLOW_DATA_DIR")
    if configured_path:
        return Path(configured_path).expanduser().resolve()
    return DEFAULT_DATA_DIR
