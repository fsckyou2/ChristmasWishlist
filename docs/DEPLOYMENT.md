# Deploying on TrueNAS SCALE

The app runs as a custom (compose) app with two services from the same image: `web` (gunicorn) and `scheduler`
(daily digest). The SQLite database lives in a dataset mounted at `/app/instance`.

## Upgrading from v3.x

v4 changes how the container runs, so follow these steps once.

1. **Stop the app and back up the database.** Copy `wishlist.db` out of the dataset (for example to
   `wishlist.db.backup-YYYYMMDD`) or snapshot the dataset.
2. **Let the app user write the dataset.** The container no longer runs as root; it runs as uid/gid **568**
   (TrueNAS's built-in `apps` user). In the TrueNAS UI: Datasets → the wishlist dataset → Permissions → Edit.
   Add an ACL entry for user `apps` with **Modify**, tick **Apply permissions recursively**, and save. This covers
   the existing `wishlist.db` too.
3. **Generate a new `SECRET_KEY`** of at least 32 characters. The app refuses to start with a shorter one.
   Rotating it logs everyone out once.
   ```bash
   python3 -c "import secrets; print(secrets.token_urlsafe(48))"
   ```
4. **Update the app's compose YAML** (Apps → wishlist → Edit) along the lines of the example below:
   - Pin the image to a version (no `:latest`, no `pull_policy: always`) and use the same tag for both services.
   - Replace `FLASK_ENV` with `APP_ENV=production`.
   - Remove `SCHEDULER_ENABLED`, `PASSWORD_RESET_TOKEN_EXPIRY`, `NVIDIA_VISIBLE_DEVICES` and `group_add`.
   - Add `read_only`, `tmpfs`, `cap_drop` and `security_opt`.
5. **Start it** and check the web container's logs for:
   ```
   Adopting existing pre-Alembic database at revision 0001_baseline
   Running upgrade 0001_baseline -> 0002_invites_logins
   Database schema is up to date.
   ```
6. **Invite people.** Registration is invite-only. Log in as the admin, go to Admin → Registration Invites, and
   create one link per person. Existing accounts are unaffected.

**Rollback:** stop the app, restore the backed-up `wishlist.db`, and set the image back to the v3.5.2 tag.

## Example compose

```yaml
x-wishlist: &wishlist
  image: fsckyou2/christmas-wishlist:4.0.0   # pin; bump deliberately
  restart: unless-stopped
  read_only: true
  tmpfs: [/tmp]
  cap_drop: [ALL]
  security_opt: ["no-new-privileges:true"]
  volumes:
    - /mnt/<pool>/appconfigs/wishlist:/app/instance
  environment: &env
    APP_ENV: production
    SECRET_KEY: "<48+ random characters>"
    APP_NAME: Scimone Christmas Wishlist
    APP_URL: https://wishlist.example.net
    WEBAUTHN_RP_ID: wishlist.example.net
    TRUSTED_PROXY_COUNT: "1"
    DATABASE_URL: sqlite:///wishlist.db
    TZ: America/New_York
    DAILY_DIGEST_HOUR: "9"
    MAGIC_LINK_TOKEN_EXPIRY: "1800"
    ADMIN_EMAIL: admin@example.net
    ADMIN_NAME: Admin Name
    MAIL_SERVER: smtp.mailgun.org
    MAIL_PORT: "587"
    MAIL_USE_TLS: "True"
    MAIL_USERNAME: wishlist@mg.example.net
    MAIL_PASSWORD: "<mailgun password>"
    MAIL_DEFAULT_SENDER: wishlist@example.net
    SCRAPER_API_KEY: "<optional>"

services:
  wishlist:
    <<: *wishlist
    ports:
      - "5000:5000"   # see "Network exposure" below

  scheduler:
    <<: *wishlist
    command: ["scheduler"]
    depends_on:
      wishlist:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "python", "/app/healthcheck_scheduler.py"]
      interval: 30s
      timeout: 10s
      retries: 3
```

## Network exposure

`X-Forwarded-*` headers from one proxy hop are trusted (`TRUSTED_PROXY_COUNT=1`), so ideally only that proxy can
reach port 5000:

- **Behind Caddy on the same host:** don't publish the port. Join the wishlist service to Caddy's Docker network and
  point Caddy at `wishlist:5000`.
- **Behind a tunnel (e.g. Pangolin/newt) from another LAN host:** the port must stay published. Anything else on the
  LAN can then spoof forwarded headers. Since v4 that only affects rate-limit keys (emails and passkeys use
  `APP_URL`), but restrict access with a firewall rule if you can.

## Day-to-day

```bash
# from the TrueNAS shell (container names may differ)
docker exec <web-container> flask create-invite --note "Cousin Sam"
docker exec <web-container> flask send-digest
docker logs <web-container>
```
