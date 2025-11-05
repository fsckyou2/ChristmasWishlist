#!/usr/bin/env python3
"""
Migration: Add wishlist_delegates table

This migration creates a table to track users who can manage proxy wishlists
on behalf of others (e.g., parents managing their kids' wishlists).

Delegates can add/edit/remove items but cannot see who claimed items.
"""

import sys
import os

# Add the parent directory to sys.path to allow importing app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app, db  # noqa: E402
from sqlalchemy import text  # noqa: E402


def migrate():
    """Add wishlist_delegates table"""
    app = create_app()

    with app.app_context():
        # Check if table already exists
        result = db.session.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='wishlist_delegates'")
        )
        if result.fetchone():
            print("[OK] wishlist_delegates table already exists, skipping migration")
            return

        print("Creating wishlist_delegates table...")

        # Create the wishlist_delegates table
        db.session.execute(
            text(
                """
            CREATE TABLE wishlist_delegates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                proxy_wishlist_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                can_add_items BOOLEAN NOT NULL DEFAULT 1,
                can_edit_items BOOLEAN NOT NULL DEFAULT 1,
                can_remove_items BOOLEAN NOT NULL DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (proxy_wishlist_id) REFERENCES proxy_wishlists (id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                UNIQUE(proxy_wishlist_id, user_id)
            )
        """
            )
        )

        db.session.commit()
        print("[OK] wishlist_delegates table created successfully")


if __name__ == "__main__":
    try:
        migrate()
        print("\n[OK] Migration completed successfully")
    except Exception as e:
        print(f"\n[ERROR] Migration failed: {e}")
        sys.exit(1)
