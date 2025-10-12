# Database Migrations

This directory contains all database migration scripts for the Christmas Wishlist application.

## Migration System

All migration scripts are numbered in order of application:

```
001_migrate_purchase_fields.py        - Rename 'acquired' to 'purchased', add 'received' field
002_migrate_user_tour.py              - Add has_seen_tour field to users
003_migrate_wishlist_changes_cascade.py - Add CASCADE DELETE to wishlist_changes
004_migrate_custom_gifts.py           - Add added_by_id to track custom gifts
005_migrate_available_images.py       - Add available_images column for image selection
006_migrate_proxy_wishlists.py        - Create proxy_wishlists table
007_migrate_user_id_nullable.py       - Make user_id nullable in wishlist_items
008_migrate_username_password.py      - Add username and password_hash columns
009_migrate_email_nullable.py         - Make email nullable for username-only users
```

## Running Migrations

### Apply All Migrations (Recommended)

To apply all migrations in order:

```bash
# Local
python scripts/apply_all_migrations.py

# Docker
docker exec christmas-wishlist python scripts/apply_all_migrations.py
```

This script:
- ✅ Runs migrations in sequential order
- ✅ Handles errors gracefully
- ✅ Shows detailed progress and summary
- ✅ Each migration is idempotent (safe to run multiple times)
- ✅ Prompts to continue if a migration fails

### Run Individual Migration

To run a specific migration:

```bash
# Local
python scripts/001_migrate_purchase_fields.py

# Docker
docker exec christmas-wishlist python scripts/001_migrate_purchase_fields.py
```

## Migration Best Practices

### Creating New Migrations

When creating a new migration:

1. **Number it sequentially**: Use next available number (e.g., `010_migrate_feature_name.py`)
2. **Make it idempotent**: Check if migration is already applied
3. **Preserve data**: Always copy existing data when recreating tables
4. **Handle failures**: Use try/except and rollback on errors
5. **Document changes**: Include clear docstring explaining what changes

### Migration Template

```python
#!/usr/bin/env python3
"""
Migration to [describe what this migration does]

Adds/Modifies:
1. [First change]
2. [Second change]

Run this script:
    python scripts/###_migrate_feature_name.py

Or in Docker:
    docker exec christmas-wishlist python scripts/###_migrate_feature_name.py
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app, db  # noqa: E402
from sqlalchemy import inspect, text  # noqa: E402

app = create_app()

def migrate():
    """Run the migration"""
    with app.app_context():
        print("Starting [feature_name] migration...")

        # Check if already applied
        inspector = inspect(db.engine)
        columns = [col["name"] for col in inspector.get_columns("table_name")]

        if "new_column" in columns:
            print("✓ Migration already applied")
            return

        print("Applying migration...")

        try:
            # Your migration code here
            db.session.execute(text("ALTER TABLE ..."))
            db.session.commit()

            print("✅ Migration completed successfully!")

        except Exception as e:
            print(f"❌ Migration failed: {e}")
            db.session.rollback()
            raise

if __name__ == "__main__":
    migrate()
```

## SQLite Limitations

SQLite has limited `ALTER TABLE` support. To modify constraints or rename columns:

1. Create new table with desired schema
2. Copy all data from old table
3. Drop old table
4. Rename new table
5. Recreate indexes

Example pattern used in several migrations:

```python
# Create new table
db.session.execute(text("CREATE TABLE table_new (...)"))

# Copy data
db.session.execute(text("INSERT INTO table_new SELECT ... FROM table"))

# Drop old, rename new
db.session.execute(text("DROP TABLE table"))
db.session.execute(text("ALTER TABLE table_new RENAME TO table"))

# Recreate indexes
db.session.execute(text("CREATE INDEX ..."))
```

## Testing Migrations

Before applying to production:

1. **Backup your database**
2. **Test on development database first**
3. **Run all tests after migration**: `pytest`
4. **Verify data integrity**: Check that existing data is preserved
5. **Test rollback**: Restore backup if something goes wrong

## Troubleshooting

### Migration Already Applied

If a migration detects it's already applied, it will print:
```
✓ Migration already applied - [feature] exists
```

This is safe and means the migration can be skipped.

### Migration Failed

If a migration fails:

1. Check the error message for details
2. Check database state (table might be partially created)
3. May need to manually rollback changes
4. Restore from backup if needed
5. Fix the migration script and try again

### Common Issues

**Foreign key constraint errors**:
- Check that referenced tables/columns exist
- Ensure data being copied is valid

**Column already exists**:
- Migration was partially applied
- Check if migration should be skipped or completed

**Data loss**:
- Always backup before running migrations
- Verify `INSERT INTO ... SELECT` statements copy all columns
- Test on copy of production data first

## Production Deployment

When deploying to production:

```bash
# 1. Backup database
cp instance/app.db instance/app.db.backup

# 2. Run migrations
docker exec christmas-wishlist python scripts/apply_all_migrations.py

# 3. Restart application
docker restart christmas-wishlist

# 4. Run tests
docker exec christmas-wishlist pytest

# 5. Verify functionality
# Test critical features in the UI
```

If migrations fail:
```bash
# Restore backup
cp instance/app.db.backup instance/app.db

# Restart application
docker restart christmas-wishlist
```

## Migration History

Each migration corresponds to a feature or fix:

- **001**: Purchase status tracking improvements
- **002**: Welcome tour feature
- **003**: User deletion cascade fix
- **004**: Custom gift tracking
- **005**: Multi-image selection
- **006**: Proxy wishlists for non-users
- **007**: Support proxy wishlist items
- **008**: Username/password authentication
- **009**: Optional email addresses

See individual migration files for detailed change descriptions.
