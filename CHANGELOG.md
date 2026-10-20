# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Security
- Registration is invite-only (single-use, expiring invite links; admin page and `flask create-invite`)
- Surprise protection: owners can no longer see claims or custom gifts on their own list via the browse view,
  digest emails, JSON responses or admin pages; hidden items return 404 to the owner
- Stored XSS fixed: all item writes validated (http/https only), `|safe` removed, image picker built with DOM APIs,
  nonce-based Content-Security-Policy, no inline event handlers
- Product scraper hardened against SSRF (no private/LAN addresses, re-checked per connection and redirect, size cap);
  ScraperAPI over HTTPS; client-side scraping through third-party CORS proxies removed
- `/wishlist/merge-items` now requires permission to delete the source item
- App-wide CSRF protection; logout, impersonate and stop-impersonate are POST-only
- Rate limiting on login, magic links, registration, passkey login and scraping
- Magic links are single-use and need a confirm click (mail scanners can't consume them)
- Production config is the default and refuses weak `SECRET_KEY`s; WebAuthn origin pinned to `APP_URL`
- Emails rendered from autoescaped templates; internal errors no longer returned to clients
- Dependencies updated (Flask 3.1, Werkzeug 3.1.9, gunicorn 26, requests 2.34, ...); pip-audit and Dependabot in CI

### Changed
- BREAKING: container runs as uid/gid 568 (read-only root filesystem supported); the data directory must be writable by 568
- BREAKING: `SECRET_KEY` must be at least 32 characters in production; `APP_ENV` replaces `FLASK_ENV` (still honoured)
- BREAKING: database migrations moved to Alembic; `flask init-db` adopts v3.5.2 databases automatically
- Authorization rules centralised in `app/policy.py`; item logic in `app/services.py`; validation in `app/validation.py`
- `Purchase` model renamed to `Claim` (database table unchanged); legacy `/purchase` and `/unpurchase` routes removed
- Daily digest timezone is explicit (`DIGEST_TIMEZONE`, defaults to `TZ`)
- Multi-stage Docker image without compilers or dev dependencies; `/healthz` endpoint
- Docs reorganised under `docs/`

### Removed
- Legacy migration scripts (replaced by Alembic), unused templates, service worker, `quickstart.sh`


## [1.1.0] - 2025-10-09


### Added
- Semantic versioning system
- Automated version bumping script
- Docker Hub deployment workflow
- Continuous Integration with GitHub Actions
## [1.0.0] - TBD

### Added
- Passwordless authentication with magic links
- Wishlist management (add, edit, delete items)
- URL scraping for product information (eBay, Amazon, Walmart)
- Gift claiming system (track who's buying what)
- Acquired/wrapped status tracking for gifts
- Daily digest emails for wishlist changes
- Admin panel with user impersonation
- WebAuthn/Passkey support (infrastructure ready)
- Table view with inline editing
- Reverse proxy support (Nginx/Apache)
- Docker support with multi-stage builds
- Comprehensive test suite (76% coverage)

### Security
- CSRF protection on forms
- Secure session cookies
- SQL injection protection via SQLAlchemy ORM
- XSS protection via Jinja2 autoescaping

[unreleased]: https://github.com/yourusername/christmas-wishlist/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/yourusername/christmas-wishlist/releases/tag/v1.0.0
