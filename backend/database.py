import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env file if present (before reading env vars)
_env_path = Path(__file__).resolve().parent / ".env"
if _env_path.exists():
    load_dotenv(_env_path)

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# PostgreSQL in production: postgresql://user:pass@host:5432/carbonchain
# SQLite for local demo (default)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./carbonchain_mumbai.db")

_connect_args = {}
_pool_kwargs = {"pool_pre_ping": True}

if DATABASE_URL.startswith("sqlite"):
    _connect_args = {"check_same_thread": False}
else:
    # PostgreSQL connection pool settings
    _pool_kwargs.update({
        "pool_size": 10,
        "max_overflow": 20,
        "pool_recycle": 1800,
    })

engine = create_engine(DATABASE_URL, connect_args=_connect_args, **_pool_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def is_postgresql() -> bool:
    return DATABASE_URL.startswith("postgresql")


def database_info() -> dict:
    return {
        "driver": "postgresql" if is_postgresql() else "sqlite",
        "url_masked": DATABASE_URL.split("@")[-1] if "@" in DATABASE_URL else DATABASE_URL,
    }
