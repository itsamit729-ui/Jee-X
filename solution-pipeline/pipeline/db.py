"""Database connection for export/publish (only the machine that owns the database needs this).

Reads DATABASE_URL and DB_SSL_CA from the environment or from solution-pipeline/.env.
"""

import os
from pathlib import Path

from common import HOME


def load_env():
    env = HOME / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def engine():
    load_env()
    from sqlalchemy import create_engine

    url = os.environ.get("DATABASE_URL")
    if not url or not url.startswith("mysql"):
        raise SystemExit("Set DATABASE_URL (mysql+pymysql://...) in solution-pipeline/.env")
    connect_args = {}
    ca = os.environ.get("DB_SSL_CA")
    if ca:
        ca_path = Path(ca) if Path(ca).is_absolute() else (HOME / ca)
        if not ca_path.exists():
            raise SystemExit(f"DB_SSL_CA file not found: {ca_path}")
        connect_args = {"ssl": {"ca": str(ca_path)}}
    return create_engine(url, connect_args=connect_args, pool_pre_ping=True, pool_recycle=280)


VERIFIED_NOTE = "verified-solution"  # prefix of question_revisions.change_note written by publish.py
