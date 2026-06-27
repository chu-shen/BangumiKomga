"""
Centralized path constants for the BangumiKomga project.

All runtime data paths (database, logs, archivedata) are defined here
so that every module uses the same PROJECT_ROOT-based absolute paths,
regardless of the current working directory.

Import this module freely — it has zero dependencies on other project modules.
"""
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATA_DIR = os.path.join(PROJECT_ROOT, "data")
LOG_DIR = os.path.join(DATA_DIR, "logs")
ARCHIVE_DIR = os.path.join(DATA_DIR, "archivedata")

DB_FILENAME = "recordsRefreshed.db"
DB_PATH = os.path.join(DATA_DIR, DB_FILENAME)

LOG_FILENAME = "refreshMetadata.log"
LOG_PATH = os.path.join(LOG_DIR, LOG_FILENAME)


def ensure_directories():
    """
    Create all runtime data directories if they don't exist.
    Idempotent — safe to call from multiple places (prepare_procedure, init_sqlite3, etc.).
    """
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
