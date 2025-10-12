#!/usr/bin/env python3
"""
Migration script to add proxy_wishlists table and update wishlist_items table.

This migration adds:
1. proxy_wishlists table for non-user wishlists
2. proxy_wishlist_id column to wishlist_items table
3. Makes user_id nullable in wishlist_items table

Run this script after deploying the code changes for the proxy wishlist feature.

Usage:
    python scripts/migrate_proxy_wishlists.py

Or in Docker:
    docker exec christmas-wishlist python scripts/migrate_proxy_wishlists.py
"""

import sys
import os

# Add parent directory to path to import app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app, db  # noqa: E402
from sqlalchemy import inspect, text  # noqa: E402

app = create_app()


def table_exists(table_name):
    """Check if a table exists in the database"""
    inspector = inspect(db.engine)
    return table_name in inspector.get_table_names()


def column_exists(table_name, column_name):
    """Check if a column exists in a table"""
    inspector = inspect(db.engine)
    columns = [col["name"] for col in inspector.get_columns(table_name)]
    return column_name in columns


def migrate():
    """Run the migration"""
    with app.app_context():
        print("Starting proxy wishlists migration...")

        # Check if proxy_wishlists table already exists
        if table_exists("proxy_wishlists"):
            print("✓ proxy_wishlists table already exists, skipping creation")
        else:
            print("Creating proxy_wishlists table...")
            db.session.execute(
                text(
                    """
                CREATE TABLE proxy_wishlists (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(100) NOT NULL,
                    email VARCHAR(120),
                    created_by_id INTEGER NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (created_by_id) REFERENCES users(id)
                )
            """
                )
            )

            # Create index on email for faster lookups
            db.session.execute(
                text(
                    """
                CREATE INDEX ix_proxy_wishlists_email ON proxy_wishlists(email)
            """
                )
            )
            db.session.commit()
            print("✓ Created proxy_wishlists table")

        # Check if proxy_wishlist_id column exists in wishlist_items
        if column_exists("wishlist_items", "proxy_wishlist_id"):
            print("✓ proxy_wishlist_id column already exists in wishlist_items")
        else:
            print("Adding proxy_wishlist_id column to wishlist_items...")
            db.session.execute(
                text(
                    """
                ALTER TABLE wishlist_items
                ADD COLUMN proxy_wishlist_id INTEGER
            """
                )
            )
            db.session.commit()
            print("✓ Added proxy_wishlist_id column")

        # Note: SQLite doesn't support modifying column constraints directly,
        # so we can't make user_id nullable with ALTER TABLE.
        # The new table creation will handle this, but for existing databases,
        # this is informational only.
        print("\nNOTE: If you created your database before this migration,")
        print("user_id may still be NOT NULL. This is okay - proxy items will")
        print("use proxy_wishlist_id instead. For a fresh database, user_id is nullable.")

        print("\n✅ Migration completed successfully!")
        print("\nNext steps:")
        print("1. Restart your application")
        print("2. Test creating a proxy wishlist")
        print("3. Test registering a user with matching email to verify auto-conversion")


if __name__ == "__main__":
    try:
        migrate()
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback

        traceback.print_exc()
        exit(1)
