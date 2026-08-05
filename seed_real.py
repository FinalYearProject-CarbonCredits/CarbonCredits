"""
Compatibility stub: call backend seeding from repository root.

Usage:
  python seed_real.py

This file delegates the real seeding work to `backend.main.seed_database()`.
"""

from backend.main import seed_database

if __name__ == "__main__":
    seed_database()
