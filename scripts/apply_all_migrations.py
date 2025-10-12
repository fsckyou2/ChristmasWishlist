#!/usr/bin/env python3
"""
Apply all database migrations in order.

This script runs all migration scripts in sequential order, handling errors gracefully.
Each migration is idempotent (can be run multiple times safely).

Usage:
    python scripts/apply_all_migrations.py

Or in Docker:
    docker exec christmas-wishlist python scripts/apply_all_migrations.py
"""

import sys
import os
import glob

# Skip admin user creation during migrations to avoid schema mismatch errors
os.environ["SKIP_ADMIN_CREATION"] = "true"

# Add parent directory to path to import app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Get all numbered migration scripts in order
scripts_dir = os.path.dirname(os.path.abspath(__file__))
migration_pattern = os.path.join(scripts_dir, "[0-9][0-9][0-9]_migrate_*.py")
migration_files = sorted(glob.glob(migration_pattern))

if not migration_files:
    print("❌ No migration scripts found!")
    print(f"   Looking in: {scripts_dir}")
    print("   Pattern: [0-9][0-9][0-9]_migrate_*.py")
    sys.exit(1)

print("=" * 80)
print("DATABASE MIGRATION RUNNER")
print("=" * 80)
print(f"\nFound {len(migration_files)} migration(s) to apply:\n")

for i, filepath in enumerate(migration_files, 1):
    filename = os.path.basename(filepath)
    print(f"  {i}. {filename}")

print("\n" + "=" * 80)
print("Starting migrations...")
print("=" * 80 + "\n")

successful_migrations = []
failed_migrations = []
skipped_migrations = []

for filepath in migration_files:
    filename = os.path.basename(filepath)
    migration_number = filename.split("_")[0]
    migration_name = filename.replace(".py", "").replace(f"{migration_number}_", "")

    print(f"\n{'=' * 80}")
    print(f"[{migration_number}] {migration_name}")
    print("=" * 80)

    try:
        # Import and run the migration
        # We use exec to run the migration script
        with open(filepath, "r") as f:
            script_content = f.read()

        # Create a namespace for the migration
        migration_namespace = {
            "__name__": "__main__",
            "__file__": filepath,
        }

        # Execute the migration script
        exec(script_content, migration_namespace)

        # Check if migration was successful by looking for the migrate function
        if "migrate" in migration_namespace:
            print(f"\n✅ [{migration_number}] Migration completed successfully")
            successful_migrations.append(filename)
        else:
            print(f"\n⚠️  [{migration_number}] Migration script ran but no migrate() function found")
            skipped_migrations.append(filename)

    except SystemExit as e:
        # Migration script called exit() - treat as failure if exit code != 0
        if e.code != 0:
            print(f"\n❌ [{migration_number}] Migration failed with exit code {e.code}")
            failed_migrations.append(filename)
        else:
            print(f"\n✅ [{migration_number}] Migration completed")
            successful_migrations.append(filename)

    except Exception as e:
        print(f"\n❌ [{migration_number}] Migration failed with error:")
        print(f"   {type(e).__name__}: {str(e)}")
        failed_migrations.append(filename)

        # Check if running in interactive mode
        import sys

        if sys.stdin.isatty():
            # Interactive mode - ask user
            print(f"\n⚠️  Failed on migration: {filename}")
            response = input("   Continue with remaining migrations? (y/n): ").lower().strip()
            if response != "y":
                print("\n🛑 Migration process stopped by user")
                break
        else:
            # Non-interactive mode (Docker/automated) - stop on first failure
            print(f"\n⚠️  Failed on migration: {filename}")
            print("🛑 Stopping migration process (non-interactive mode)")
            break

# Print summary
print("\n" + "=" * 80)
print("MIGRATION SUMMARY")
print("=" * 80)

print(f"\n✅ Successful: {len(successful_migrations)}")
for filename in successful_migrations:
    print(f"   - {filename}")

if skipped_migrations:
    print(f"\n⚠️  Skipped: {len(skipped_migrations)}")
    for filename in skipped_migrations:
        print(f"   - {filename}")

if failed_migrations:
    print(f"\n❌ Failed: {len(failed_migrations)}")
    for filename in failed_migrations:
        print(f"   - {filename}")

print("\n" + "=" * 80)

if failed_migrations:
    print("❌ Some migrations failed. Please review the errors above.")
    sys.exit(1)
else:
    print("✅ All migrations completed successfully!")
    print("\nNext steps:")
    print("1. Restart your application")
    print("2. Test all features to ensure migrations worked correctly")
    sys.exit(0)
