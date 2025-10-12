#!/usr/bin/env python3
"""
Migration script to make email column nullable in users table.

This is required for username-only users (without email addresses).

For SQLite, this requires recreating the table since ALTER COLUMN is not supported.

Usage:
    python scripts/migrate_email_nullable.py

Or in Docker:
    docker exec christmas-wishlist python scripts/migrate_email_nullable.py
"""

import sys
import os

# Add parent directory to path to import app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import text  # noqa: E402
from flask import Flask  # noqa: E402
from flask_sqlalchemy import SQLAlchemy  # noqa: E402

# Create a minimal app for migration
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///instance/app.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)


def migrate():
    """Run the migration"""
    with app.app_context():
        print("Starting email nullable migration...")

        # Check if we're using SQLite
        if "sqlite" in str(db.engine.url).lower():
            print("Detected SQLite - using table recreation method...")

            # Step 1: Create new table with correct schema
            print("Creating new users table...")
            db.session.execute(
                text(
                    """
                CREATE TABLE users_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email VARCHAR(120),
                    name VARCHAR(100) NOT NULL,
                    is_admin BOOLEAN DEFAULT 0,
                    created_at DATETIME,
                    updated_at DATETIME,
                    has_seen_tour BOOLEAN DEFAULT 0,
                    username VARCHAR(80),
                    password_hash VARCHAR(255)
                )
            """
                )
            )
            db.session.commit()
            print("✓ Created users_new table")

            # Step 2: Copy data from old table to new table
            print("Copying data from users to users_new...")
            db.session.execute(
                text(
                    """
                INSERT INTO users_new (
                    id, email, name, is_admin, created_at, updated_at,
                    has_seen_tour, username, password_hash
                )
                SELECT id, email, name, is_admin, created_at, updated_at,
                       has_seen_tour, username, password_hash
                FROM users
            """
                )
            )
            db.session.commit()
            print("✓ Copied data")

            # Step 3: Drop old table
            print("Dropping old users table...")
            db.session.execute(text("DROP TABLE users"))
            db.session.commit()
            print("✓ Dropped old table")

            # Step 4: Rename new table to users
            print("Renaming users_new to users...")
            db.session.execute(text("ALTER TABLE users_new RENAME TO users"))
            db.session.commit()
            print("✓ Renamed table")

            # Step 5: Recreate indexes
            print("Recreating indexes...")
            db.session.execute(text("CREATE UNIQUE INDEX idx_users_email ON users (email) WHERE email IS NOT NULL"))
            db.session.commit()
            print("✓ Created email index")

            db.session.execute(
                text("CREATE UNIQUE INDEX idx_users_username ON users (username) WHERE username IS NOT NULL")
            )
            db.session.commit()
            print("✓ Created username index")

        else:
            # For PostgreSQL/MySQL - simple ALTER
            print("Using ALTER COLUMN for non-SQLite database...")
            db.session.execute(text("ALTER TABLE users ALTER COLUMN email DROP NOT NULL"))
            db.session.commit()
            print("✓ Made email column nullable")

        # Verify the change
        result = db.session.execute(text("PRAGMA table_info(users)"))
        for row in result:
            if row[1] == "email":
                if row[3] == 0:  # NOT NULL field
                    print("✅ Email column is now nullable!")
                else:
                    print("❌ Email column is still NOT NULL")

        print("\n✅ Migration completed successfully!")
        print("\nNext steps:")
        print("1. Restart your application")
        print("2. Test creating a username/password account without email")


if __name__ == "__main__":
    try:
        migrate()
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback

        traceback.print_exc()
        exit(1)
