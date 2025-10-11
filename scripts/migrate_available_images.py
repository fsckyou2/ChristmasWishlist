#!/usr/bin/env python3
"""
Migration script to add available_images column to wishlist_items table.

This migration adds:
1. available_images column to wishlist_items table (TEXT field for JSON array)

This column stores multiple image URLs scraped from product pages, allowing users
to select which image they want to use.

Run this script after deploying the code changes for the image selection feature.

Usage:
    python scripts/migrate_available_images.py

Or in Docker:
    docker exec christmas-wishlist python scripts/migrate_available_images.py
"""

import sys
import os

# Add parent directory to path to import app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app, db  # noqa: E402
from sqlalchemy import inspect, text  # noqa: E402

app = create_app()


def column_exists(table_name, column_name):
    """Check if a column exists in a table"""
    inspector = inspect(db.engine)
    columns = [col["name"] for col in inspector.get_columns(table_name)]
    return column_name in columns


def migrate():
    """Run the migration"""
    with app.app_context():
        print("Starting available_images migration...")

        # Check if available_images column exists in wishlist_items
        if column_exists("wishlist_items", "available_images"):
            print("✓ available_images column already exists in wishlist_items")
        else:
            print("Adding available_images column to wishlist_items...")
            db.session.execute(
                text(
                    """
                ALTER TABLE wishlist_items
                ADD COLUMN available_images TEXT
            """
                )
            )
            db.session.commit()
            print("✓ Added available_images column")

        print("\n✅ Migration completed successfully!")
        print("\nNext steps:")
        print("1. Restart your application")
        print("2. Test scraping a product URL with multiple images")
        print("3. Verify image selection feature works correctly")


if __name__ == "__main__":
    try:
        migrate()
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback

        traceback.print_exc()
        exit(1)
