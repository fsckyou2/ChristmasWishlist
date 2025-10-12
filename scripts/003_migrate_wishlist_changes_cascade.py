#!/usr/bin/env python3
"""
Migration to add CASCADE DELETE to wishlist_changes.user_id foreign key

This allows wishlist_changes to be automatically deleted when a user is deleted.

Run this script:
    python scripts/migrate_wishlist_changes_cascade.py

Or in Docker:
    docker exec christmas-wishlist python scripts/migrate_wishlist_changes_cascade.py
"""

import sys
import os

# Add parent directory to path to import app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app, db  # noqa: E402


def migrate():
    """Add CASCADE DELETE to wishlist_changes foreign key"""
    app = create_app()

    with app.app_context():
        print("Checking wishlist_changes table...")

        # Check if table exists
        inspector = db.inspect(db.engine)
        if "wishlist_changes" not in inspector.get_table_names():
            print("✅ Table doesn't exist yet - will be created with correct schema")
            return

        print("\n🔄 Starting migration to add CASCADE DELETE...")

        try:
            # SQLite doesn't support modifying foreign keys directly
            # We need to recreate the table

            # Step 1: Create new table with CASCADE DELETE
            print("   Creating new table with CASCADE constraint...")
            db.session.execute(
                db.text(
                    """
                CREATE TABLE wishlist_changes_new (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    change_type VARCHAR(50) NOT NULL,
                    item_name VARCHAR(200) NOT NULL,
                    item_id INTEGER,
                    created_at DATETIME,
                    notified BOOLEAN,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """
                )
            )

            # Step 2: Copy data from old table
            print("   Copying data...")
            db.session.execute(
                db.text(
                    """
                INSERT INTO wishlist_changes_new
                (id, user_id, change_type, item_name, item_id, created_at, notified)
                SELECT id, user_id, change_type, item_name, item_id, created_at, notified
                FROM wishlist_changes
            """
                )
            )

            # Step 3: Drop old table
            print("   Dropping old table...")
            db.session.execute(db.text("DROP TABLE wishlist_changes"))

            # Step 4: Rename new table
            print("   Renaming new table...")
            db.session.execute(db.text("ALTER TABLE wishlist_changes_new RENAME TO wishlist_changes"))

            # Step 5: Recreate indexes
            print("   Recreating indexes...")
            db.session.execute(db.text("CREATE INDEX ix_wishlist_changes_created_at ON wishlist_changes(created_at)"))
            db.session.execute(db.text("CREATE INDEX ix_wishlist_changes_notified ON wishlist_changes(notified)"))

            db.session.commit()

            print("\n✅ Migration completed successfully!")
            print("   - Added CASCADE DELETE to user_id foreign key")
            print("   - Users can now be deleted without constraint errors")

        except Exception as e:
            print(f"\n❌ Migration failed: {e}")
            db.session.rollback()
            raise


if __name__ == "__main__":
    print("=" * 60)
    print("WishlistChange CASCADE DELETE Migration")
    print("=" * 60)
    migrate()
