# TrueNAS Apps Deployment Guide

This guide is specifically for deploying Christmas Wishlist using TrueNAS Scale Apps.

## Initial Deployment

1. **Add the app** through TrueNAS Scale Apps interface
2. **Configure environment variables**:
   - `SECRET_KEY` - Random secret key (generate with `openssl rand -hex 32`)
   - `MAIL_USERNAME` - Your Mailgun username
   - `MAIL_PASSWORD` - Your Mailgun password
   - `MAIL_DEFAULT_SENDER` - Your sender email
   - `APP_URL` - Your app URL (e.g., `https://wishlist.example.com`)
   - `ADMIN_EMAIL` - Your admin email
   - `ADMIN_NAME` - Your admin name

3. **Start the app** - The database will be created automatically

4. **Access the app** and verify it's working

## Upgrading to New Versions

When upgrading from an older version, you may need to run database migrations.

### How to Check if Migration is Needed

After upgrading, check the container logs:

```bash
# In TrueNAS Shell
k3s kubectl logs -n ix-<app-name> <pod-name>
```

If you see a warning like:
```
⚠️  WARNING: Database migration required!
Your database is missing the 'proxy_wishlist_id' column.
```

Then you need to run the migration.

### Running Migrations via TrueNAS

1. **Open the TrueNAS web interface**

2. **Navigate to Apps** → Find your Christmas Wishlist app

3. **Click the three dots** (⋮) → **Shell**

4. **Run the migration command** in the terminal:
   ```bash
   cd /app
   python scripts/migrate_proxy_wishlists.py
   ```

5. **Restart the app**:
   - Go back to Apps
   - Click the three dots (⋮) → **Stop**
   - Wait a few seconds
   - Click **Start**

6. **Verify** the warning is gone by checking logs again

### Migration Scripts by Version

Run these migrations in order if upgrading from older versions:

**v1.3.0 → v1.4.0**:
```bash
cd /app
python scripts/migrate_purchase_fields.py
python scripts/migrate_wishlist_changes_cascade.py
```

**v1.4.0 → v1.5.0**:
```bash
cd /app
python scripts/migrate_custom_gifts.py
python scripts/migrate_available_images.py
python scripts/migrate_proxy_wishlists.py
python scripts/migrate_user_id_nullable.py
```

**IMPORTANT**: The `migrate_user_id_nullable.py` script is **critical** for proxy wishlists to work. Without it, you'll get "NOT NULL constraint failed" errors when adding items to proxy wishlists.

**Fresh install**: No migrations needed - all tables are created automatically!

## Troubleshooting

### App won't start after upgrade

**Symptom**: App crashes or shows errors in logs

**Solution**: The app is designed to start even without migrations. Check the logs for specific errors.

### Migration script not found

**Symptom**: `python: can't open file '/app/scripts/migrate_proxy_wishlists.py'`

**Solution**: The migration script should be included in the Docker image. If it's missing:
1. Check you're using the latest image
2. Rebuild the app with `docker pull` to get the latest version

### "Can't see proxy wishlists feature"

**Symptom**: No "Create Wishlist for Non-User" button visible

**Solution**:
1. Check if migration was run (look for warning in logs)
2. Run the migration script as shown above
3. Restart the app

### "NOT NULL constraint failed: wishlist_items.user_id"

**Symptom**: Error when trying to add items to proxy wishlists

**Solution**: This means the `migrate_user_id_nullable.py` migration hasn't been run yet.
```bash
# In TrueNAS Shell, access the app's shell
cd /app
python scripts/migrate_user_id_nullable.py
# Then restart the app
```

This migration makes the `user_id` column nullable, which is required for proxy wishlist items.

### Database corruption after migration

**Symptom**: App shows errors or data is missing

**Solution**:
1. Stop the app
2. Restore from TrueNAS snapshot (if you created one)
3. Or restore from database backup:
   ```bash
   # In TrueNAS Shell, access the app's shell
   cd /app/instance
   # Remove corrupted database
   rm app.db
   # Copy backup
   cp /path/to/backup/app.db ./app.db
   ```
4. Restart the app

## Best Practices

### Before Upgrading

1. **Create a TrueNAS snapshot** of the app's dataset
2. **Or backup the database manually**:
   ```bash
   # In app shell
   cd /app/instance
   cp app.db app.db.backup-$(date +%Y%m%d)
   ```

### After Upgrading

1. **Check logs** for migration warnings
2. **Run required migrations** via shell
3. **Restart the app**
4. **Test functionality** to ensure everything works

### Data Persistence

The database is stored at `/app/instance/app.db` inside the container. Make sure this is mapped to a TrueNAS dataset for persistence:

- **Recommended**: Configure a host path volume in TrueNAS Apps for `/app/instance`
- This ensures your data survives app updates and restarts

## Getting Help

If you encounter issues:

1. **Check the logs** first - most errors are explained there
2. **Review MIGRATION_GUIDE.md** for detailed migration documentation
3. **Create an issue** on GitHub with:
   - Your TrueNAS Scale version
   - App version
   - Error logs
   - Steps to reproduce

## Version History

- **v1.5.0** (2025-10-10): Added proxy wishlists feature - requires migration
- **v1.4.0** (2025-10-10): Added custom gifts feature - requires migration
- **v1.3.0** (2025-10-10): Updated purchase tracking fields - requires migration
- **v1.0.0** (2024): Initial release
