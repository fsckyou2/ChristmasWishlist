#!/usr/bin/env python3
"""
One-time migration to update Purchase model fields:
- Rename 'acquired' to 'purchased'
- Add new 'received' field

Run this script once to migrate existing database:
    python scripts/migrate_purchase_fields.py

Or in Docker:
    docker exec christmas-wishlist python scripts/migrate_purchase_fields.py
"""

import sys
import os

# Add parent directory to path to import app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app, db


def migrate():
    """Migrate Purchase table to add purchased/received fields"""
    app = create_app()

    with app.app_context():
        # Check if migration is needed
        inspector = db.inspect(db.engine)
        columns = [col["name"] for col in inspector.get_columns("purchases")]

        print("Current columns in 'purchases' table:", columns)

        if "purchased" in columns and "received" in columns:
            print("✅ Migration already applied - purchased and received columns exist")
            return

        if "acquired" not in columns:
            print("⚠️  WARNING: Neither 'acquired' nor 'purchased' column found")
            print("    This might be a fresh database. Creating new schema...")
            db.create_all()
            return

        print("\n🔄 Starting migration...")

        # SQLite doesn't support ALTER COLUMN, so we need to:
        # 1. Add new columns
        # 2. Copy data
        # 3. Drop old column (requires table recreation in SQLite)

        try:
            # Step 1: Add new columns if they don't exist
            if "purchased" not in columns:
                print("   Adding 'purchased' column...")
                db.session.execute(db.text("ALTER TABLE purchases ADD COLUMN purchased BOOLEAN DEFAULT 0"))

            if "received" not in columns:
                print("   Adding 'received' column...")
                db.session.execute(db.text("ALTER TABLE purchases ADD COLUMN received BOOLEAN DEFAULT 0"))

            db.session.commit()

            # Step 2: Copy data from acquired to purchased
            if "acquired" in columns:
                print("   Copying data from 'acquired' to 'purchased'...")
                db.session.execute(db.text("UPDATE purchases SET purchased = acquired"))
                db.session.commit()

            # Step 3: For SQLite, we need to recreate the table to drop the column
            print("   Recreating table to remove 'acquired' column...")

            # Create temporary table with new schema
            db.session.execute(
                db.text(
                    """
                CREATE TABLE purchases_new (
                    id INTEGER PRIMARY KEY,
                    wishlist_item_id INTEGER NOT NULL,
                    purchased_by_id INTEGER NOT NULL,
                    quantity INTEGER NOT NULL DEFAULT 1,
                    purchased BOOLEAN DEFAULT 0,
                    received BOOLEAN DEFAULT 0,
                    wrapped BOOLEAN DEFAULT 0,
                    created_at DATETIME,
                    updated_at DATETIME,
                    FOREIGN KEY (wishlist_item_id) REFERENCES wishlist_items(id),
                    FOREIGN KEY (purchased_by_id) REFERENCES users(id)
                )
            """
                )
            )

            # Copy data to new table
            db.session.execute(
                db.text(
                    """
                INSERT INTO purchases_new
                (id, wishlist_item_id, purchased_by_id, quantity, purchased, received, wrapped, created_at, updated_at)
                SELECT id, wishlist_item_id, purchased_by_id, quantity, purchased, received, wrapped, created_at, updated_at
                FROM purchases
            """
                )
            )

            # Drop old table and rename new one
            db.session.execute(db.text("DROP TABLE purchases"))
            db.session.execute(db.text("ALTER TABLE purchases_new RENAME TO purchases"))

            db.session.commit()

            print("\n✅ Migration completed successfully!")
            print("   - Added 'purchased' column")
            print("   - Added 'received' column")
            print("   - Migrated data from 'acquired' to 'purchased'")
            print("   - Removed 'acquired' column")

        except Exception as e:
            print(f"\n❌ Migration failed: {e}")
            db.session.rollback()
            raise


if __name__ == "__main__":
    print("=" * 60)
    print("Purchase Fields Migration Script")
    print("=" * 60)
    migrate()
