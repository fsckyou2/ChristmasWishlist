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
# Build and start all services (web + scheduler)
docker compose up -d --build

# Stop and remove containers
docker compose down

# Clean volumes (WARNING: deletes database)
docker compose down -v

# View logs
docker logs christmas-wishlist              # Web server logs
docker logs christmas-wishlist-scheduler    # Scheduler logs
docker compose logs -f                      # Follow all logs

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

### Scheduler Architecture

The application uses a **separate scheduler service** to run periodic tasks (like daily digest emails). This architecture prevents duplicate jobs when running multiple gunicorn workers.

**Components**:
- `scheduler_worker.py` - Standalone scheduler process (runs APScheduler in foreground)
- `app/scheduler.py` - Scheduler configuration (legacy, only used if `SCHEDULER_ENABLED=true`)
- `docker-compose.yml` - Defines both `web` and `scheduler` services

**How it works**:
1. Web service runs gunicorn with 4 workers (does NOT run scheduler)
2. Scheduler service runs `scheduler_worker.py` as single process
3. Both services share the same Docker image and database volume
4. Scheduler creates Flask app context to access database and send emails

**Environment Variables**:
- `SCHEDULER_ENABLED=false` - Set on web service to disable in-process scheduler
- `DAILY_DIGEST_HOUR` - Hour (0-23 UTC) for daily emails, default 9

**Manual trigger**:
```bash
docker exec christmas-wishlist flask send-digest
```

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

This project does not use Flask-Migrate/Alembic. Database schema changes are handled via custom migration scripts:

**For Development** (data loss acceptable):
1. Modify models in `app/models.py`
2. Delete database file (SQLite) or drop tables
3. Restart app to recreate tables via `db.create_all()`

**For Production** (preserve data):
1. Modify models in `app/models.py`
2. Create migration script in `scripts/migrate_*.py`
3. Run migration: `docker exec christmas-wishlist python scripts/migrate_*.py`
4. Restart application

**Available Migrations**:
- `scripts/migrate_purchase_fields.py` - Adds purchased/received fields (v1.3.0)
- `scripts/migrate_wishlist_changes_cascade.py` - Adds CASCADE DELETE to wishlist_changes (v1.3.0)

See `MIGRATION_GUIDE.md` for detailed migration instructions and troubleshooting.

## Continuous Integration

GitHub Actions workflows run automatically:

### CI Workflow (`.github/workflows/ci.yml`)
Runs on all pushes and pull requests:
- **Test Job**: Runs pytest on Python 3.11, 3.12, 3.13 with coverage reporting
- **Lint Job**: Checks code formatting (black) and quality (flake8)
- **Docker Job**: Verifies Docker build and container startup

### Release Workflow (`.github/workflows/release.yml`)
Runs on push to main branch only - **single workflow** that:
1. Bumps version based on commit messages
2. Updates VERSION and CHANGELOG.md
3. Commits and pushes changes
4. Creates and pushes git tag
5. Builds Docker image
6. Pushes to Docker Hub

**Setup Required**:
- GitHub Secrets: `PAT_TOKEN`, `DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`
- See `GITHUB_ACTIONS_SETUP.md` for detailed setup instructions

Configuration files:
- `.github/workflows/ci.yml` - CI workflow
- `.github/workflows/release.yml` - Release workflow
- `.flake8` - Flake8 configuration (max line length 120, ignores E128, W503, W504)
- `pyproject.toml` - Black, pytest, and coverage configuration

Code quality standards:
- Max line length: 120 characters
- Code formatter: Black (automatic formatting)
- Linter: Flake8 with relaxed rules for test files (allows F401, F841, F541)
- SQLAlchemy filter comparisons: Use `== False` not `is False` (with `# noqa: E712` comment)

Current test coverage: **76%** (87 tests passing)

## Automated Releases

The release workflow provides **fully automated releases** when merging to main:

**Image Tagging**:
  - `latest` - Most recent version
  - `v1.2.3` - Exact semantic version
  - `v1.2`, `v1` - Major and major.minor versions

**Pull Image**:
```bash
docker pull <your-username>/christmas-wishlist:latest
```

## Semantic Versioning

The project follows semantic versioning (MAJOR.MINOR.PATCH) with **automated version bumping**:

- **Current Version**: Tracked in `VERSION` file (currently 1.0.0)
- **Release Workflow**: `.github/workflows/release.yml` automatically handles version bump + Docker publish
- **Version Endpoint**: `GET /version` returns JSON with current version
- **Template Display**: Version shown in footer of all pages via `app_version` context variable

**Automated Release Workflow**:
```bash
# Work on development branch
git checkout development
git commit -m "feat: add new feature"  # Use conventional commits
git push

# Merge to main - triggers release workflow
git checkout main
git merge development
git push

# GitHub Actions automatically:
# 1. Bumps version based on commit messages
# 2. Updates VERSION and CHANGELOG.md
# 3. Commits and pushes changes [skip ci]
# 4. Creates and pushes git tag (e.g., v1.1.0)
# 5. Builds Docker image with new version
# 6. Pushes to Docker Hub with version tags
```

**Commit Message Convention** (for auto-bumping):
- `feat:` or `feat(scope):` → MINOR version bump (1.0.0 → 1.1.0)
- `fix:` or other messages → PATCH version bump (1.0.0 → 1.0.1)
- `BREAKING CHANGE:` or `feat!:` → MAJOR version bump (1.0.0 → 2.0.0)

**Manual Bump** (if needed):
```bash
python scripts/bump_version.py [major|minor|patch]
```

**Documentation**:
- See `GITHUB_ACTIONS_SETUP.md` for workflow setup guide
- See `WORKFLOW_SEQUENCE.md` for detailed execution flow
- See `VERSIONING.md` for versioning guide
- See `CHANGELOG.md` for version history and changes
- Always check Black and Flake8 formatting
