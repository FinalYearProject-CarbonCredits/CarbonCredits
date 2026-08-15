"""PostgreSQL backup utility for CarbonChain.

Usage:
    python scripts/backup_db.py                   # Backup using DATABASE_URL from .env
    python scripts/backup_db.py --keep 7          # Keep only the latest 7 backups
    python scripts/backup_db.py --dir /path/to    # Custom backup directory

Requires pg_dump on PATH. Skips silently if DATABASE_URL is SQLite.
"""

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

# Load .env from backend/
_root = Path(__file__).resolve().parent.parent
_env_path = _root / ".env"
if _env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(_env_path)


def parse_pg_url(url: str) -> dict:
    """Extract host, port, user, password, dbname from a PostgreSQL URL."""
    parsed = urlparse(url)
    return {
        "host": parsed.hostname or "localhost",
        "port": str(parsed.port or 5432),
        "user": parsed.username or "postgres",
        "password": parsed.password or "",
        "dbname": parsed.path.lstrip("/"),
    }


def run_backup(backup_dir: Path, keep: int = 30):
    db_url = os.getenv("DATABASE_URL", "")
    if not db_url.startswith("postgresql"):
        print("[backup] DATABASE_URL is not PostgreSQL — skipping backup.")
        return

    backup_dir.mkdir(parents=True, exist_ok=True)
    pg = parse_pg_url(db_url)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"carbonchain_{timestamp}.sql.gz"
    filepath = backup_dir / filename

    env = os.environ.copy()
    if pg["password"]:
        env["PGPASSWORD"] = pg["password"]

    cmd = [
        "pg_dump",
        "-h", pg["host"],
        "-p", pg["port"],
        "-U", pg["user"],
        "-d", pg["dbname"],
        "--no-owner",
        "--no-acl",
        "-F", "c",  # custom format (compressed)
        "-f", str(filepath),
    ]

    print(f"[backup] Backing up {pg['dbname']}@{pg['host']}:{pg['port']} ...")
    try:
        subprocess.run(cmd, env=env, check=True, capture_output=True, text=True)
        size_mb = filepath.stat().st_size / (1024 * 1024)
        print(f"[backup] ✓ Saved: {filepath} ({size_mb:.2f} MB)")
    except FileNotFoundError:
        print("[backup] ✗ pg_dump not found on PATH. Install PostgreSQL client tools.")
        return
    except subprocess.CalledProcessError as e:
        print(f"[backup] ✗ pg_dump failed: {e.stderr}")
        return

    # Prune old backups
    backups = sorted(backup_dir.glob("carbonchain_*.sql*"), key=lambda p: p.stat().st_mtime)
    if len(backups) > keep:
        for old in backups[:-keep]:
            old.unlink()
            print(f"[backup] Pruned old backup: {old.name}")

    print(f"[backup] Done. {len(list(backup_dir.glob('carbonchain_*.sql*')))} backup(s) retained.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Backup CarbonChain PostgreSQL database")
    parser.add_argument("--dir", default=str(_root / "data" / "backups"), help="Backup directory")
    parser.add_argument("--keep", type=int, default=30, help="Number of backups to retain")
    args = parser.parse_args()
    run_backup(Path(args.dir), args.keep)
