# Database Migration Guide

This guide covers how to handle database schema changes in this project.

## Current Migration Status

### Migration: Purchase Fields (v1.3.0)

**Date**: 2025-10-10
**Changes**:
- Renamed `acquired` field to `purchased` in Purchase model
- Added new `received` field for tracking online order arrivals
- Retained `wrapped` field

**Status**: Migration script available at `scripts/migrate_purchase_fields.py`

## Running Migrations

### For Docker Deployments

If you're upgrading from a version before v1.3.0:

```bash
# Method 1: Run migration script (preserves existing data)
docker exec christmas-wishlist python scripts/migrate_purchase_fields.py

# Then restart the container
docker restart christmas-wishlist
```

### For Local Development

```bash
# Activate virtual environment
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Run migration script
python scripts/migrate_purchase_fields.py

# Restart the app
python run.py
```

### For Fresh Installations

If you're doing a fresh installation (no existing data):

```bash
# Just start the container - it will create tables automatically
docker compose up -d --build
```

The migration script is safe to run multiple times - it will detect if the migration has already been applied.

## Migration Script Output

When you run the migration, you'll see:

```
============================================================
Purchase Fields Migration Script
============================================================
Current columns in 'purchases' table: [...]

🔄 Starting migration...
   Adding 'purchased' column...
   Adding 'received' column...
   Copying data from 'acquired' to 'purchased'...
   Recreating table to remove 'acquired' column...

✅ Migration completed successfully!
   - Added 'purchased' column
   - Added 'received' column
   - Migrated data from 'acquired' to 'purchased'
   - Removed 'acquired' column
```

If the migration was already applied:
```
✅ Migration already applied - purchased and received columns exist
```

## About Database Migrations

This project **does not use Flask-Migrate/Alembic** for automatic migrations. Instead:

1. Schema changes are made directly in `app/models.py`
2. Migration scripts are provided in `scripts/` directory
3. For development, you can delete the database and restart (loses data)
4. For production, run the provided migration scripts (preserves data)

### Why No Flask-Migrate?

This keeps the project simpler for:
- Small family applications
- Docker deployments
- SQLite databases
- Quick development iterations

For production deployments with complex migration needs, consider adding Flask-Migrate.

## Creating New Migrations

If you need to make database schema changes in the future:

1. **Update the model** in `app/models.py`

2. **Create a migration script** in `scripts/migrate_*.py`:
   ```python
   from app import create_app, db

   def migrate():
       app = create_app()
       with app.app_context():
           # Your migration code here
           db.session.execute(db.text("ALTER TABLE ..."))
           db.session.commit()

   if __name__ == "__main__":
       migrate()
   ```

3. **Test the migration**:
   ```bash
   # Test locally first
   python scripts/migrate_your_change.py

   # Test in Docker
   docker exec christmas-wishlist python scripts/migrate_your_change.py
   ```

4. **Document the migration** in this file

5. **Add instructions** to release notes

## Troubleshooting

### "no such column" Error

**Symptom**:
```
sqlite3.OperationalError: no such column: purchases.purchased
```

**Solution**: Run the migration script
```bash
docker exec christmas-wishlist python scripts/migrate_purchase_fields.py
docker restart christmas-wishlist
```

### Migration Script Not Found

**Symptom**:
```
python: can't open file '/app/scripts/migrate_purchase_fields.py'
```

**Solution**: Copy the script to the container
```bash
docker cp scripts/migrate_purchase_fields.py christmas-wishlist:/app/scripts/
docker exec christmas-wishlist python scripts/migrate_purchase_fields.py
```

### Fresh Database After Docker Rebuild

**Symptom**: All data is gone after `docker compose down -v` or rebuild

**Solution**: This is expected behavior. The database is stored in a Docker volume.
- Use `docker compose down` (without `-v`) to preserve data
- For persistence, mount the database to a host directory in `docker-compose.yml`

## Production Deployment Notes

When deploying updates to production:

1. **Backup your database** before running migrations:
   ```bash
   docker cp christmas-wishlist:/app/instance/app.db ./backup-app.db
   ```

2. **Run the migration**:
   ```bash
   docker exec christmas-wishlist python scripts/migrate_purchase_fields.py
   ```

3. **Verify the migration**:
   ```bash
   docker logs christmas-wishlist
   # Should show no errors
   ```

4. **Restart the application**:
   ```bash
   docker restart christmas-wishlist
   ```

5. **Test the application** to ensure everything works

If something goes wrong, restore from backup:
```bash
docker cp ./backup-app.db christmas-wishlist:/app/instance/app.db
docker restart christmas-wishlist
```

## See Also

- `VERSIONING.md` - Version numbering and release process
- `CLAUDE.md` - Architecture overview and database section
- `scripts/migrate_purchase_fields.py` - Current migration script
