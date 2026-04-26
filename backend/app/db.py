from proofflow.config import get_db_path
from proofflow.db import connect

DATABASE_PATH = get_db_path()


def get_connection():
    return connect(DATABASE_PATH)
