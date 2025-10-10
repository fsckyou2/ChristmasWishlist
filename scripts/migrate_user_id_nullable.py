#!/usr/bin/env python3
"""
Migration script to make user_id nullable in wishlist_items table.

This migration recreates the wishlist_items table with user_id as nullable,
which is required for proxy wishlist items (items that don't belong to a user yet).

IMPORTANT: This migration preserves all existing data.

Run this script after deploying the code changes for the proxy wishlist feature.

Usage:
    python scripts/migrate_user_id_nullable.py

Or in Docker:
    docker exec christmas-wishlist python scripts/migrate_user_id_nullable.py
"""

import sys
import os

# Add parent directory to path to import app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app, db  # noqa: E402
from sqlalchemy import inspect, text  # noqa: E402

app = create_app()


def check_user_id_nullable():
    """Check if user_id column is nullable"""
    inspector = inspect(db.engine)
    columns = {col["name"]: col for col in inspector.get_columns("wishlist_items")}

    if "user_id" in columns:
        return columns["user_id"]["nullable"]
    return None


def migrate():
    """Run the migration"""
    with app.app_context():
        print("Starting user_id nullable migration...")

        # Check if user_id is already nullable
        is_nullable = check_user_id_nullable()

        if is_nullable is True:
            print("✓ user_id column is already nullable")
            print("\n✅ Migration not needed - already applied!")
            return
        elif is_nullable is None:
            print("❌ Error: wishlist_items table or user_id column not found")
            return

        print("Making user_id column nullable in wishlist_items...")
        print("\nThis will:")
        print("1. Create a new temporary table with user_id as nullable")
        print("2. Copy all existing data")
        print("3. Drop the old table")
        print("4. Rename the new table")
        print("\nAll data will be preserved.\n")

        # SQLite doesn't support ALTER COLUMN, so we need to recreate the table
        # Step 1: Create new table with user_id nullable
        db.session.execute(
            text(
                """
            CREATE TABLE wishlist_items_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                proxy_wishlist_id INTEGER,
                added_by_id INTEGER,
                name VARCHAR(200) NOT NULL,
                url VARCHAR(500),
                description TEXT,
                price FLOAT,
                image_url VARCHAR(500),
                available_images TEXT,
                quantity INTEGER DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (proxy_wishlist_id) REFERENCES proxy_wishlists(id),
                FOREIGN KEY (added_by_id) REFERENCES users(id)
            )
        """
            )
        )

        # Step 2: Copy all data from old table to new table
        db.session.execute(
            text(
                """
            INSERT INTO wishlist_items_new
                (id, user_id, proxy_wishlist_id, added_by_id, name, url, description,
                 price, image_url, available_images, quantity, created_at, updated_at)
            SELECT
                id, user_id, proxy_wishlist_id, added_by_id, name, url, description,
                price, image_url, available_images, quantity, created_at, updated_at
            FROM wishlist_items
        """
            )
        )

        # Step 3: Drop old table
        db.session.execute(text("DROP TABLE wishlist_items"))

        # Step 4: Rename new table
        db.session.execute(text("ALTER TABLE wishlist_items_new RENAME TO wishlist_items"))

        # Step 5: Recreate indexes (SQLite doesn't copy indexes automatically)
        # Note: Foreign key indexes are automatically created by SQLite

        db.session.commit()
        print("✓ Successfully made user_id column nullable")

        print("\n✅ Migration completed successfully!")
        print("\nNext steps:")
        print("1. Restart your application")
        print("2. Test creating a proxy wishlist")
        print("3. Test adding items to proxy wishlists")


if __name__ == "__main__":
    try:
        migrate()
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback

        traceback.print_exc()
        exit(1)
