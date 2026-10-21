# CLAUDE.md

Guidance for Claude Code (claude.ai/code) when working in this repository.

## Commands

```bash
pip install -r requirements-dev.txt

pytest                                   # all tests (CSRF and rate limits are off in TestingConfig)
pytest tests/test_security.py            # surprise-protection / authz / XSS / SSRF / CSRF regression tests
black app/ tests/ migrations/ config.py run.py scheduler_worker.py
flake8 app/ tests/ migrations/ config.py run.py scheduler_worker.py
pip-audit -r requirements.txt

# Local run
APP_ENV=development flask --app run:app init-db
APP_ENV=development flask --app run:app bootstrap-admin
scripts/build_css.sh                     # Tailwind -> app/static/css/app.css (the Docker build does this itself)
APP_ENV=development python run.py

# Container
docker compose up -d --build                      # web + scheduler, rootless (uid 568), read-only rootfs
docker build --target dev -t wishlist:dev .       # image with dev deps for running tests
docker compose exec web flask create-invite --note "Name"
docker compose exec web flask send-digest
```

Always run black and flake8 after code changes; CI enforces both strictly.

## Architecture

- **App factory** `app/__init__.py`: Extensions (SQLAlchemy, Migrate, Login, Mail, CSRFProtect, Limiter), ProxyFix (`TRUSTED_PROXY_COUNT`), the security headers and the per-request CSP nonce (`csp_nonce()` in templates). It does **no** database work.
- **Config** `config.py`: `APP_ENV` (falls back to `FLASK_ENV`, default **production**). `ProductionConfig.validate` refuses a missing, placeholder, or short (< 32 chars) `SECRET_KEY`.
- **Policy** `app/policy.py`: Every authorization and surprise-protection rule. Routes and templates must use it rather than ad-hoc checks.
- **Services** `app/services.py`: Item create/update/merge/delete. `record_change()` is the only way to write `WishlistChange` rows.
- **Validation** `app/validation.py`: The single set of rules for item fields (http/https URLs only; images are http/https or `/static/`). Used by forms (`wtf_validator`), JSON endpoints (`clean_item_fields`) and templates (`|safe_href`, `|safe_img`).
- **Net** `app/net.py`: SSRF-guarded `fetch_text()` for the scraper. Never call `requests` directly on a user-supplied URL.
- **Routes** `app/routes/`: auth (invites, magic links, password login), wishlist, admin, passkey, scraper, main (`/healthz`).
- **Email** `app/email.py`: Bodies are rendered from `templates/email/*.{txt,html}` (autoescaped HTML). Sending happens in a background thread that logs failures.
- **Scheduler**: `scheduler_worker.py` runs `app/scheduler.add_jobs` in its own container. `DAILY_DIGEST_HOUR` is local time in `DIGEST_TIMEZONE` (defaults to `TZ`).
- **CLI** `app/cli.py`:
  - `init-db` adopts pre-Alembic DBs at `0001_baseline`, then upgrades.
  - `bootstrap-admin` creates the `ADMIN_EMAIL` user.
  - `create-invite`, `send-digest`.

### Models (`app/models.py`)
- `User`: Email and/or username. `last_login_at` is embedded in magic-link tokens, so each link is single-use (`record_login()` on every login).
- `WishlistItem`: On exactly one list (`user_id` XOR `proxy_wishlist_id`, enforced by a CHECK constraint). `added_by_id` set to someone other than the owner means a **custom gift**.
- `Claim`: Someone's claim on an item. The table is still called `purchases` and the column `purchased_by_id`, mapped to `Claim.claimed_by_id`. `purchased`/`received`/`wrapped` track gift status.
- `ProxyWishlist` / `WishlistDelegate`: Lists for people without accounts, and who may manage them.
- `Invite`: Single-use registration invites (only `sha256(token)` is stored).
- `WishlistChange`: Digest log, always attributed to the list owner. `User.digest_frequency` (daily/weekly/off) and
  `last_digest_at` decide who gets what; every digest links to a signed preferences page (no login needed).
- `WishlistItem.most_wanted` / `size` / `color` / `position`: always order lists with `models.list_order()`.
- `ListVisit` ("new" badges on Browse Wishlists), `Reminder` (empty-list nudges, one per person per 3 days),
  `DeletedItem` (30-minute undo snapshots; `services.delete_item(item, deleted_by=user)` / `services.undo_delete`).

## Rules that must not regress

1. **Surprise protection.** A user never sees claims, claimers or others' custom gifts on their own list. That covers pages, JSON responses, emails, admin pages, and differences in responses. Hidden items return 404 to the owner. Proxy delegates don't see others' custom gifts. Impersonating admins see what the user sees. Add a test in `tests/test_security.py` for any new view of items.
2. **Registration is invite-only.** Don't add registration paths that skip `_invite_from_session()`.
3. **No inline JS or CSS.**
   - Every `<script>` gets `nonce="{{ csp_nonce() }}"`. No `style="..."` attributes or `<style>` blocks (the CSP is
     `style-src 'self'`); use Tailwind classes, or set `element.style` from JS.
   - Tailwind is built from the templates and JS, so write whole class names (never `"bg-" ~ colour ~ "-600"`).
   - Use `data-*` attributes plus listeners (`data-confirm="..."` on forms/buttons is handled by `static/js/app.js`).
   - Build DOM nodes, or wrap values in `escapeHtml()`, before using `innerHTML`.
4. **CSRF.** POST forms need `{{ form.hidden_tag() }}` or `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">`. `fetch()` gets the header automatically from `app.js`. State changes never use GET.
5. **Every item write goes through `services` / `validation`.**
6. **Terminology.** User-facing words come from `docs/GLOSSARY.md` (one word per idea; privacy phrase "hidden from {Name}" / "can't see"). `tests/test_terms.py` renders pages and emails and fails on retired words. Code names (`Claim`, `proxy`, `delegate`) are internal and never shown.

## Migrations

See `docs/MIGRATIONS.md`. Change the models, then `flask db migrate`, then review the file, then test it on a copy of a real database. CI runs `flask db check`.

## Docs

`README.md` (overview, usage), `SECURITY.md` (security model and checklist), `docs/DEPLOYMENT.md` (TrueNAS), `docs/REVERSE_PROXY.md`, `docs/MIGRATIONS.md`, `docs/releasing/` (CI, versioning, Docker Hub).

Releases: merging to `main` runs the tests, bumps the version from conventional commits (`feat:` minor, `fix:` patch, `BREAKING CHANGE`/`!:` major), tags it, and pushes the image to Docker Hub.
