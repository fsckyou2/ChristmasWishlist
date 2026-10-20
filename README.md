# 🎄 Christmas Wishlist

A family wishlist app: everyone keeps a list, browses everyone else's, and claims gifts so nobody buys the same thing twice, without ever spoiling their own surprises.

## ✨ Features

### For Users
- **Wishlists**: Add items manually or auto-fill from a product URL (Amazon, eBay, Walmart, most shops with Open Graph tags)
- **Claims**: Claim some or all of an item's quantity; track purchased / received / wrapped in "My Gifts for Others"
- **Surprise-safe**: You never see claims, claimers, or surprise gifts on your own list: not in pages, not in emails, not even as an admin
- **Custom gifts**: Add a surprise gift to someone's list; everyone but them can see it, so nobody duplicates it
- **Proxy wishlists**: Keep a list for someone without an account (e.g. a small child), optionally managed by delegates
- **Daily digest email**: What changed on other people's lists in the last day
- **Passwordless login**: Single-use magic links and passkeys; username/password also supported
- **Mobile-friendly**: Responsive, installable as a PWA

### For Administrators
- **Invite-only registration**: Create single-use invite links (Admin → Registration Invites, or `flask create-invite`)
- **User management**: Edit, delete, grant/revoke admin, send login links, impersonate (you see exactly what they see)
- **Proxy wishlists and delegates**: Merge a proxy list into a real account; manage delegate permissions
- **Claims and items overview**: Everything except your own list's surprises

## 🚀 Quick Start

### Prerequisites
- Docker (or Podman) with Compose
- An SMTP provider for email (Mailgun by default)
- A TLS reverse proxy (Caddy, nginx) in front of the app for anything beyond local testing

### Docker
```bash
git clone https://github.com/fsckyou2/ChristmasWishlist.git
cd ChristmasWishlist
cp .env.example .env    # set SECRET_KEY (>= 32 random chars), APP_URL, mail settings, ADMIN_EMAIL
docker compose up -d --build
```

The app listens on `127.0.0.1:5000`. On first start it creates the database and the `ADMIN_EMAIL` user. Then:

1. Log in as the admin with a magic link (enter `ADMIN_EMAIL` on the login page).
2. Go to **Admin → Registration Invites** and create an invite for each family member, or run:
   ```bash
   docker compose exec web flask create-invite --note "Aunt Rebecca"
   ```
3. Send each person their link. Each link works once and expires after `INVITE_EXPIRY_DAYS` (30 by default).

For TrueNAS SCALE, see [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

### Local Development
```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env              # set APP_ENV=development, APP_URL=http://localhost:5000, WEBAUTHN_RP_ID=localhost
flask --app run:app init-db
flask --app run:app bootstrap-admin
APP_ENV=development python run.py
```

## ⚙️ Configuration

All settings come from environment variables; [.env.example](.env.example) documents each one. The important ones:

| Variable | Notes |
|---|---|
| `APP_ENV` | `production` (default) or `development`. `FLASK_ENV` is still honoured. |
| `SECRET_KEY` | Required in production, at least 32 random characters. The app refuses to start otherwise. |
| `APP_URL` | Public URL. Used in emails and as the passkey (WebAuthn) origin. |
| `WEBAUTHN_RP_ID` | Bare domain of `APP_URL`. |
| `TRUSTED_PROXY_COUNT` | Reverse proxies whose `X-Forwarded-*` headers are trusted (default 1). Only expose the app port to that proxy. |
| `ADMIN_EMAIL`, `ADMIN_NAME` | First admin, created on start if missing. |
| `MAIL_*` | SMTP settings. |
| `DAILY_DIGEST_HOUR` | Hour (0-23) in the container's `TZ` (or `DIGEST_TIMEZONE`). |
| `SCRAPER_API_KEY` | Optional ScraperAPI key for Amazon/Etsy auto-fill. |
| `RATELIMIT_STORAGE_URI` | Optional shared rate-limit store (e.g. Redis). The default is per-worker memory. |

## 📖 User Guide

1. **Join**: Open the invite link you were sent and register with email (magic-link login) or a username and password. If someone already kept a proxy list for you, it's merged into your account.
2. **Build your list**: My Wishlist → Add Item. Paste a product URL and click **Auto-Fill**, or type the details. The table view is handy for quick edits.
3. **Browse and claim**: Browse Wishlists → pick a person → **Claim Gift**. You can claim part of a quantity.
4. **Surprise gifts**: On someone's list, **Add Custom Gift** adds something they didn't ask for. It's claimed by you and hidden from them.
5. **Track your gifts**: My Gifts for Others shows everything you've claimed, grouped by person, with purchased / received / wrapped checkboxes.
6. **Log in later**: Enter your email for a one-time login link, use a passkey (Account Settings → Passkeys), or your username and password.

## 🛡️ Admin Commands

```bash
docker compose exec web flask create-invite --note "Grandma" --days 14   # print a single-use invite link
docker compose exec web flask send-digest                                # send the daily digest now
docker compose exec web flask init-db                                    # migrate the database (runs on every start)
```

## 🧪 Testing

```bash
pip install -r requirements-dev.txt
pytest
```

Or in a container: `docker build --target dev -t wishlist:dev . && docker run --rm wishlist:dev pytest`.

`tests/test_security.py` holds the surprise-protection, authorization, XSS, SSRF, CSRF and rate-limit regression tests. CI also checks formatting (black), lint (flake8), that migrations match the models, known-vulnerable dependencies (pip-audit), and that the image starts rootless on a read-only filesystem.

## 🏗️ Project Structure

```
app/
├── __init__.py        App factory, extensions, security headers (CSP)
├── policy.py          Who can see/do what, including surprise protection. Start here for permissions.
├── services.py        Item create/update/merge/delete and digest change tracking
├── validation.py      Input validation shared by forms, JSON endpoints and templates
├── net.py             SSRF-safe outbound HTTP for the product scraper
├── models.py          User, WishlistItem, Claim, ProxyWishlist, WishlistDelegate, Invite, Passkey, WishlistChange
├── email.py           Email sending (bodies in templates/email/)
├── scheduler.py       Periodic jobs (daily digest)
├── cli.py             init-db, bootstrap-admin, create-invite, send-digest
├── routes/            auth, wishlist, admin, passkey, scraper, main
├── static/js/         app.js (CSRF + UI behaviour), image-selector.js, passkey.js, scraper.js
└── templates/
migrations/            Alembic migrations (see docs/MIGRATIONS.md)
scheduler_worker.py    Scheduler process (runs in its own container)
docker-entrypoint.sh   web | scheduler | any command
docs/                  Deployment, reverse proxy, migrations, release process
```

## 🔒 Security

See [SECURITY.md](SECURITY.md) for the security model and deployment checklist.

## 🐛 Troubleshooting

- **Container exits with "SECRET_KEY must be set..."**: Set a random `SECRET_KEY` of at least 32 characters.
- **`PermissionError` / "unable to open database file"**: The container runs as uid/gid 568, which must be able to write the database directory. See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).
- **"This database predates v3.5.2"**: Run the v3.5.2 image once to apply its legacy migrations, then upgrade.
- **Email not sending**: Check the `MAIL_*` settings and `docker logs christmas-wishlist`; failures are logged.
- **Passkeys fail**: `APP_URL` must be the exact public origin and `WEBAUTHN_RP_ID` its domain.
- **Digest not arriving**: `docker logs christmas-wishlist-scheduler`, or trigger it with `flask send-digest`.

## 📄 License

Provided as-is for personal and educational use.

---

**Happy Holidays! 🎄**
