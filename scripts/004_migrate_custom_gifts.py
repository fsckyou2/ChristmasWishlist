#!/usr/bin/env python3
"""
Migration to add custom gift tracking to wishlist_items

Adds added_by_id column to track who added an item (owner vs. other users)

Run this script:
    python scripts/migrate_custom_gifts.py

Or in Docker:
    docker exec christmas-wishlist python scripts/migrate_custom_gifts.py
"""

import sys
import os

# Add parent directory to path to import app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app, db  # noqa: E402


def migrate():
    """Add added_by_id column to wishlist_items"""
    app = create_app()

    with app.app_context():
        print("=" * 60)
        print("Custom Gifts Migration Script")
        print("=" * 60)

        # Check if column already exists
        inspector = db.inspect(db.engine)
        columns = [col["name"] for col in inspector.get_columns("wishlist_items")]
        print(f"Current columns in 'wishlist_items' table: {columns}")

        if "added_by_id" in columns:
            print("\n✅ Migration already applied - added_by_id column exists")
            return

        print("\n🔄 Starting migration...")
        print("   Adding 'added_by_id' column...")

        try:
            # SQLite doesn't support adding foreign key columns directly
            # We need to recreate the table

            # Step 1: Create new table with added_by_id
            print("   Creating new table with added_by_id column...")
            db.session.execute(
                db.text(
                    """
                CREATE TABLE wishlist_items_new (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    added_by_id INTEGER,
                    name VARCHAR(200) NOT NULL,
                    url VARCHAR(500),
                    description TEXT,
                    price FLOAT,
                    image_url VARCHAR(500),
                    quantity INTEGER DEFAULT 1,
                    created_at DATETIME,
                    updated_at DATETIME,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    FOREIGN KEY (added_by_id) REFERENCES users(id)
                )
            """
                )
            )

            # Step 2: Copy data from old table (added_by_id will be NULL for all existing items)
            print("   Copying data from old table...")
            db.session.execute(
                db.text(
                    """
                INSERT INTO wishlist_items_new
                (id, user_id, added_by_id, name, url, description, price, image_url, quantity, created_at, updated_at)
                SELECT id, user_id, NULL, name, url, description, price, image_url, quantity, created_at, updated_at
                FROM wishlist_items
            """
                )
            )

            # Step 3: Drop old table
            print("   Dropping old table...")
            db.session.execute(db.text("DROP TABLE wishlist_items"))

            # Step 4: Rename new table
            print("   Renaming new table...")
            db.session.execute(db.text("ALTER TABLE wishlist_items_new RENAME TO wishlist_items"))

            db.session.commit()

            print("\n✅ Migration completed successfully!")
            print("   - Added 'added_by_id' column")
            print("   - Existing items have NULL added_by_id (owner-added)")
            print("   - New custom gifts will have added_by_id set to the gifter")

        except Exception as e:
            print(f"\n❌ Migration failed: {e}")
            db.session.rollback()
            raise


if __name__ == "__main__":
    migrate()
