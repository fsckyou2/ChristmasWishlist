#!/usr/bin/env python3
"""
Migration to add has_seen_tour field to users table

Adds has_seen_tour boolean column to track if users have completed the welcome tour

Run this script:
    python scripts/migrate_user_tour.py

Or in Docker:
    docker exec christmas-wishlist python scripts/migrate_user_tour.py
"""

import sys
import os

# Add parent directory to path to import app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app, db  # noqa: E402


def migrate():
    """Add has_seen_tour column to users table"""
    app = create_app()

    with app.app_context():
        print("=" * 60)
        print("User Tour Migration Script")
        print("=" * 60)

        # Check if column already exists
        inspector = db.inspect(db.engine)
        columns = [col["name"] for col in inspector.get_columns("users")]
        print(f"Current columns in 'users' table: {columns}")

        if "has_seen_tour" in columns:
            print("\n✅ Migration already applied - has_seen_tour column exists")
            return

        print("\n🔄 Starting migration...")
        print("   Adding 'has_seen_tour' column...")

        try:
            # Add the column with default value False
            db.session.execute(
                db.text(
                    """
                ALTER TABLE users ADD COLUMN has_seen_tour BOOLEAN DEFAULT 0
            """
                )
            )

            db.session.commit()

            print("\n✅ Migration completed successfully!")
            print("   - Added 'has_seen_tour' column")
            print("   - Existing users will see tour on next login")
            print("   - New users will see tour on first login")

        except Exception as e:
            print(f"\n❌ Migration failed: {e}")
            db.session.rollback()
            raise


if __name__ == "__main__":
    migrate()
