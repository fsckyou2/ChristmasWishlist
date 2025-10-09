# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]


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
