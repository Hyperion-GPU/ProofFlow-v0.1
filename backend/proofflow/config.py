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


def get_api_key() -> str | None:
    """Return the API key if PROOFFLOW_API_KEY is set, else None (no auth)."""
    return os.getenv("PROOFFLOW_API_KEY") or None


def get_rate_limit() -> int | None:
    """Return max requests/minute if PROOFFLOW_RATE_LIMIT is set, else None."""
    val = os.getenv("PROOFFLOW_RATE_LIMIT")
    return int(val) if val else None


def test_commands_enabled() -> bool:
    """Return True when AgentGuard test_command execution is explicitly enabled."""
    return os.getenv("PROOFFLOW_ENABLE_TEST_COMMANDS", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
