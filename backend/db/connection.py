import psycopg2
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from parent folder
env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

DB_CONFIG = {
    'host': os.getenv('DB_HOST'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'dbname': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
}

BASE_DIR = Path(__file__).parent.parent
STORAGE_DIR = BASE_DIR / 'storage' / 'images'
STORAGE_DIR.mkdir(parents=True, exist_ok=True)


def get_conn():
    """Get a connection to the database."""
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = False
    return conn
