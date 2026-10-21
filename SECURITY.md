# Security

## Model

This is a family app on a home server. The things it protects, in order:

1. **The surprise.** Nobody learns what others are giving them. On your own list you never see claims, claimers, or custom gifts others added, whether in pages, JSON responses, the daily digest, or admin pages (admins are protected on their own list too). The rules live in [`app/policy.py`](app/policy.py), and `tests/test_security.py::TestSurpriseProtection` covers each path.
2. **Membership.** Registration requires a single-use invite (only a SHA-256 of the token is stored). Open the app to the internet only behind TLS.
3. **The home network.** The product scraper fetches user-supplied URLs, so [`app/net.py`](app/net.py) only allows http/https on ports 80/443. It refuses non-public addresses, and re-checks the address actually connected to, on every connection and redirect. It also ignores proxy environment variables and caps response size.

## Controls

- **Authentication**: Single-use, 30-minute magic links (the GET shows a confirm button so mail scanners can't use them up), passkeys (origin pinned to `APP_URL`), and Werkzeug password hashes. Sessions are cleared on login.
- **Rate limits** (Flask-Limiter): Login, magic-link requests (also per email address), registration, passkey login, and scraping.
- **CSRF**: `CSRFProtect` is on app-wide. Forms carry tokens, and `fetch()` calls send `X-CSRFToken` (see `static/js/app.js`). State changes never use GET.
- **XSS**:
  - Jinja autoescaping, with no `|safe` on user data.
  - Every item write goes through [`app/validation.py`](app/validation.py) (http/https URLs only; images are http/https or `/static/`).
  - Templates re-check URLs at render time (`safe_href` / `safe_img`).
  - Client code builds DOM nodes rather than HTML strings.
  - A nonce-based CSP with no inline handlers. `style-src` allows inline styles for the Tailwind CDN.
- **Headers**: CSP, `X-Frame-Options: DENY`, `nosniff`, `Referrer-Policy: same-origin`, and HSTS on HTTPS.
- **Email**: Bodies are rendered from autoescaped templates.
- **Errors**: Clients get generic messages; details go to the logs.
- **Production config**: `APP_ENV` defaults to production. The app refuses to start with a missing, placeholder, or short `SECRET_KEY`. Cookies are `Secure`, `HttpOnly`, and `SameSite=Lax`.
- **Container**:
  - Runs as uid/gid 568, never root.
  - Has no compilers or dev dependencies.
  - Designed for a read-only root filesystem with all capabilities dropped and `no-new-privileges`.
- **Supply chain**:
  - Pinned dependencies, with Dependabot and `pip-audit` in CI.
  - A pinned Tailwind CDN version.
  - No third-party CORS proxies; product pages are fetched only by the server.

## Deployment checklist

- [ ] `SECRET_KEY` is random and at least 32 characters (`python -c "import secrets; print(secrets.token_urlsafe(48))"`)
- [ ] `APP_URL` is the public `https://` URL; `WEBAUTHN_RP_ID` is its domain
- [ ] The app port is reachable only by the reverse proxy (`TRUSTED_PROXY_COUNT` matches the number of proxies)
- [ ] The image is pinned to a release tag, not `:latest`
- [ ] The database directory is writable by uid/gid 568 and backed up
- [ ] The reverse proxy terminates TLS

## Known limitations

- Rate limits use per-worker memory by default (limits are effectively multiplied by the number of gunicorn workers). Set `RATELIMIT_STORAGE_URI` to a shared store for strict limits.
- Changing your email in Account Settings does not re-verify the new address.
- Proxy wishlists are merged into a new account by matching name or email at registration. With invite-only registration, only invited people can trigger this.
- Helpers of a list kept for someone see *that* items are claimed (so they don't buy something twice) but not *who* claimed them, and never see surprise gifts others add.

## Reporting

Open a private security advisory on GitHub, or email the maintainer. Please don't open public issues for vulnerabilities.
