#!/usr/bin/env python3
"""
Migration script to add the 'broadcasted' column to the offers table.
Run this once to update existing databases.
"""

import sqlite3
import os
from pathlib import Path

DB_PATH = Path(__file__).parent / "app_data.db"


def migrate():
    """Add broadcasted column to offers table if it doesn't exist."""
    if not DB_PATH.exists():
        print(f"Database not found at {DB_PATH}")
        print("The column will be created automatically on next app startup.")
        return

    try:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        # Check if broadcasted column already exists
        cursor.execute("PRAGMA table_info(offers)")
        columns = [column[1] for column in cursor.fetchall()]

        if "broadcasted" in columns:
            print("✓ Column 'broadcasted' already exists")
            conn.close()
            return

        # Add the broadcasted column
        cursor.execute(
            "ALTER TABLE offers ADD COLUMN broadcasted BOOLEAN DEFAULT FALSE"
        )
        conn.commit()
        print("✓ Successfully added 'broadcasted' column to offers table")
        print("✓ All existing offers set to broadcasted=FALSE")

        conn.close()
    except sqlite3.Error as e:
        print(f"✗ Database error: {e}")
        raise


if __name__ == "__main__":
    print("=" * 60)
    print("MIGRATION: Add 'broadcasted' column to offers table")
    print("=" * 60)
    migrate()
    print("=" * 60)
    print("✓ Migration complete")
    print("=" * 60)
