"""Schema ownership: migration files live next to this module and are applied by
the recorder (`services/message_store.py`) on its first database connection."""

from pathlib import Path

SCHEMA_VERSION = 1
MIGRATIONS_DIR = Path(__file__).parent / "migrations"
