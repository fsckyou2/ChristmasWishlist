# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Code Quality

```bash
# Format code with black
black app/ tests/ config.py run.py

# Check formatting
black --check --diff app/ tests/ config.py run.py

# Lint with flake8
flake8 app/ tests/ config.py run.py

# Run in Docker
docker exec christmas-wishlist black app/ tests/ config.py run.py
docker exec christmas-wishlist flake8 app/ tests/ config.py run.py
```

### Docker (Recommended)
```bash
# Build and start container
docker compose up -d --build

# Stop and remove container
docker compose down

# Clean volumes (WARNING: deletes database)
docker compose down -v

# View logs
docker logs christmas-wishlist

# Access container shell
docker exec -it christmas-wishlist bash

# Run tests in container
docker exec christmas-wishlist pytest

# Run single test
docker exec christmas-wishlist pytest tests/test_wishlist.py::TestWishlistRoutes::test_add_item

# Run tests with coverage
docker exec christmas-wishlist pytest --cov=app --cov-report=html

# Manually trigger daily digest email
docker exec christmas-wishlist flask send-digest

# Copy files to container (for WSL2 sync issues)
docker cp <local-file> christmas-wishlist:/app/<dest-path>
```

### Local Development
```bash
# Setup
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run application
python run.py

# Run tests
pytest

# Run single test
pytest tests/test_wishlist.py::TestWishlistRoutes::test_add_item

# Run with coverage
pytest --cov=app --cov-report=html
```

## Architecture Overview

### Application Factory Pattern
The app uses Flask's application factory pattern (`create_app()` in `app/__init__.py`). Configuration is loaded from `config.py` with environment-specific classes (Development, Testing, Production).

### Database Models (app/models.py)
- **User**: Passwordless authentication via magic links. Supports admin impersonation (see `load_user()` function).
- **WishlistItem**: Items on users' wishlists. Has computed properties `total_purchased` and `is_fully_purchased`.
- **Purchase**: Renamed to "Claim" in UI but kept as "Purchase" in code. Tracks who claimed what gift to give to whom. Has `acquired` and `wrapped` boolean fields for gift tracking.
- **WishlistChange**: Tracks changes for daily digest emails. Has `notified` flag to track which changes were included in digests.
- **Passkey**: WebAuthn/passkey credentials (future feature).

### Routing Structure (app/routes/)
- **auth.py**: Passwordless magic link authentication
- **wishlist.py**: Wishlist CRUD operations
  - `/wishlist/my-list` - Card view
  - `/wishlist/my-list/table` - Editable table view
  - `/wishlist/add-empty` - JSON endpoint to add empty row
  - `/wishlist/update-item/<id>` - JSON endpoint for quick updates
  - `/wishlist/add-item-from-scraped-data` - JSON endpoint for URL scraping in table view
  - `/wishlist/claim/<id>` - Claim item as gift (UI says "claim", code says "purchase")
- **admin.py**: Admin panel with user management and impersonation
- **scraper.py**: Server-side URL scraping (Amazon, eBay, Walmart, generic)
- **passkey.py**: WebAuthn/passkey authentication (future feature)
- **main.py**: Home page and basic routes

### API Endpoint Patterns

**Form-based endpoints** (require CSRF token, use Flask-WTF forms):
- `/wishlist/add` (WishlistItemForm)
- `/wishlist/edit/<id>` (WishlistItemForm)

**JSON endpoints** (no CSRF, use `request.get_json()`):
- `/wishlist/add-empty` - Creates empty item, returns JSON
- `/wishlist/update-item/<id>` - Updates item fields from JSON
- `/wishlist/add-item-from-scraped-data` - Adds item from scraped data
- `/wishlist/update-claim-status/<id>` - Updates acquired/wrapped status
- `/scraper/scrape` - Scrapes URL, returns product data

All JSON endpoints use `@login_required` decorator for authentication.

### Web Scraping Architecture
Two-tier scraping system:
1. **Client-side** (`app/static/js/scraper.js`): Attempts scraping in browser (for sites blocking server IPs)
2. **Server-side** (`app/routes/scraper.py`): POST to `/scraper/scrape` endpoint with site-specific scrapers:
   - `scrape_ebay()` - Multiple selector fallbacks for eBay's dynamic HTML
   - `scrape_amazon()` - Amazon product pages
   - `scrape_walmart()` - Walmart product pages
   - `scrape_generic()` - Fallback using Open Graph meta tags

**Known limitation**: Etsy has bot protection and returns an error message directing users to manual entry.

### Email System (app/email.py)
- **send_magic_link_email()**: Passwordless login
- **send_daily_digest()**: Aggregates WishlistChange records, groups by user, sends one email per recipient
- Uses Flask-Mail with Mailgun SMTP (configurable in .env)

### Scheduler (app/scheduler.py)
- Uses APScheduler with BackgroundScheduler
- Runs daily digest at hour specified in `DAILY_DIGEST_HOUR` config (UTC)
- Initialized in `create_app()` factory

### Reverse Proxy Support
- ProxyFix middleware configured for X-Forwarded-* headers (see `app/__init__.py`)
- Supports HTTPS behind Nginx/Apache
- Environment variables: `SESSION_COOKIE_SECURE`, `PREFERRED_URL_SCHEME`, `WEBAUTHN_RP_ID`

## Testing Architecture

### Test Configuration
- `pytest.ini`: Configured with coverage, verbose output, and HTML reports
- `config.py` TestingConfig: Uses in-memory SQLite, disables CSRF for easier testing

### Test Patterns
```python
# Login helper (most tests need this)
def login_user(self, client, app, user):
    with app.app_context():
        token = user.generate_magic_link_token()
    client.get(f'/auth/magic-login/{token}')

# Test JSON endpoints
response = client.post('/wishlist/add-item-from-scraped-data',
                       data=json.dumps({...}),
                       content_type='application/json')
data = json.loads(response.data)

# Verify database changes
with app.app_context():
    item = WishlistItem.query.filter_by(name='Test').first()
    assert item is not None
```

### Common Test Fixtures (conftest.py)
- `app`: Flask application in testing mode
- `client`: Flask test client
- `user`: Test user instance
- `other_user`: Second user for multi-user tests

## Important Implementation Details

### Terminology: "Purchase" vs "Claim"
The database models and code use "Purchase" but the UI displays "Claim" to users. This reflects a terminology change during development. When adding new features:
- Use "purchase" in code, models, variable names
- Use "claim" in templates, UI text, user-facing messages

### Change Tracking for Daily Digest
When modifying wishlist items, always track changes:
```python
item.name = new_name
change = WishlistChange(
    user_id=current_user.id,
    change_type='updated',  # 'added', 'updated', or 'deleted'
    item_name=item.name,
    item_id=item.id
)
db.session.add(change)
db.session.commit()
```

### Admin Impersonation
Admin users can impersonate other users (see `app/models.py` load_user()). The session stores `impersonate_user_id` which overrides the logged-in user. This is transparent to routes using `current_user`.

### Table View Auto-Save
The table view (`my_list_table.html`) has JavaScript that auto-saves on blur. It stores original values in `data-originalValue` attributes to avoid unnecessary saves. The "Save" button is also manually clickable.

### URL Scraping Edge Cases
- **eBay**: Handles JSON-encoded URLs in HTML (see fix for JSON parse errors)
- **Etsy**: Returns error message, not supported due to bot protection
- **Generic**: Falls back to Open Graph meta tags

### Docker Volume Sync (WSL2)
On WSL2, file sync between host and Docker volumes can be delayed. If tests fail to find newly modified files, use `docker cp` to manually copy files into the container.

## Configuration

### Required Environment Variables (.env)
```bash
SECRET_KEY=<random-secret-key>
MAIL_USERNAME=<mailgun-username>
MAIL_PASSWORD=<mailgun-password>
MAIL_DEFAULT_SENDER=<sender-email>
APP_URL=http://localhost:5000
ADMIN_EMAIL=<admin-email>
ADMIN_NAME=<admin-name>
```

### Optional Variables
- `DATABASE_URL` - Defaults to SQLite
- `DAILY_DIGEST_HOUR` - Hour (0-23 UTC) for daily emails, default 9
- `PASSWORD_RESET_TOKEN_EXPIRY` - Seconds, default 3600
- `MAGIC_LINK_TOKEN_EXPIRY` - Seconds, default 1800
- `SESSION_COOKIE_SECURE` - Set to True for HTTPS, default False
- `PREFERRED_URL_SCHEME` - http or https, default http
- `WEBAUTHN_RP_ID` - Domain for passkeys, default localhost

## Database Migrations

This project does not use Flask-Migrate/Alembic. Database schema changes are handled via:
1. Modify models in `app/models.py`
2. Delete database file (SQLite) or drop tables
3. Restart app to recreate tables via `db.create_all()`

For production deployments, consider adding Flask-Migrate for proper migrations.

## Continuous Integration

GitHub Actions CI runs automatically on push/PR to main/master branches:

- **Test Job**: Runs pytest on Python 3.11, 3.12, 3.13 with coverage reporting
- **Lint Job**: Checks code formatting (black) and quality (flake8)
- **Docker Job**: Verifies Docker build and container startup

Configuration files:
- `.github/workflows/ci.yml` - GitHub Actions workflow
- `.flake8` - Flake8 configuration (max line length 120, ignores E128, W503, W504)
- `pyproject.toml` - Black, pytest, and coverage configuration

Code quality standards:
- Max line length: 120 characters
- Code formatter: Black (automatic formatting)
- Linter: Flake8 with relaxed rules for test files (allows F401, F841, F541)
- SQLAlchemy filter comparisons: Use `== False` not `is False` (with `# noqa: E712` comment)

Current test coverage: **75%** (87 tests passing)
