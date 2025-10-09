# 🎄 Christmas Wishlist

A modern, user-friendly web application for managing Christmas wishlists. Share your holiday wishes with your loved ones, browse others' wishlists, and coordinate gift purchases without spoiling the surprise!

## ✨ Features

### For Users
- **Easy Wishlist Management**: Add items manually or automatically extract product details from URLs (Amazon, eBay, Walmart)
- **Privacy-Focused**: Others can see *what* was purchased but not *who* purchased it
- **Partial Purchases**: Support for multiple people purchasing partial quantities of items
- **Daily Digest Emails**: Get notified when other users update their wishlists
- **Simple Interface**: Clean, Christmas-themed dark UI built with Tailwind CSS
- **Mobile-First**: Fully responsive design with PWA support for mobile installation
- **Secure Authentication**:
  - Email/password login
  - Password reset via email
  - Magic link (passwordless) login
  - Secure token-based sessions

### For Administrators
- **User Management**: View, edit, disable, and delete user accounts
- **Admin Assignment**: Grant or revoke administrative privileges
- **User Impersonation**: Log in as any user to troubleshoot issues
- **Analytics Dashboard**: View system statistics and activity
- **Content Moderation**: Remove inappropriate wishlist items
- **Purchase Tracking**: Monitor all gift purchases across the system

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- Mailgun account (or other SMTP provider) for email functionality

### Docker Deployment (Recommended)

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd ChristmasWishlist
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and configure your settings (see Configuration section below)

3. **Build and run**
   ```bash
   docker compose up -d --build
   ```

4. **Access the application**
   Open your browser to `http://localhost:5000`

### Local Development

1. **Setup environment**
   ```bash
   git clone <repository-url>
   cd ChristmasWishlist
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure and run**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   python run.py
   ```

## ⚙️ Configuration

Edit the `.env` file with your settings:

### Required Settings

```env
# Flask Secret Key (CHANGE THIS!)
SECRET_KEY=your-very-secret-random-key-here

# Email Configuration (Mailgun)
MAIL_SERVER=smtp.mailgun.org
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=postmaster@your-domain.mailgun.org
MAIL_PASSWORD=your-mailgun-password
MAIL_DEFAULT_SENDER=noreply@your-domain.com

# Application URL
APP_URL=http://localhost:5000  # Change to your production domain

# Admin User (Created automatically on first run)
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=change-this-secure-password
```

### Optional Settings

```env
# Database (SQLite by default)
DATABASE_URL=sqlite:///wishlist.db

# Token Expiry (in seconds)
PASSWORD_RESET_TOKEN_EXPIRY=3600
MAGIC_LINK_TOKEN_EXPIRY=1800

# Daily Digest Configuration
DAILY_DIGEST_HOUR=9  # Hour (0-23, UTC) to send daily emails

# Application Name
APP_NAME=Christmas Wishlist
```

## 📖 User Guide

### Getting Started

1. **Create an Account**: Register with your name, email, and password
2. **Add Items to Your Wishlist**:
   - Click "My Wishlist" → "Add Item"
   - Option 1: Paste a product URL and click "Auto-Fill" to extract details
   - Option 2: Manually enter item details
3. **Browse Other Wishlists**:
   - Click "Browse Wishlists" to see all users
   - View any user's wishlist by clicking their name
4. **Mark Items as Purchased**:
   - On someone else's wishlist, click "Mark Purchased"
   - Select quantity (supports partial purchases)
   - The owner will see the item is purchased but not who bought it!

### Adding Items from URLs

The app supports automatic data extraction from:
- **Amazon** ✅
- **eBay** ✅
- **Walmart** ✅
- **Etsy** ❌ (Manual entry required due to bot protection)
- **Other sites** (Generic scraper attempts to extract data)

Simply paste the product URL and click "Auto-Fill from URL". The app will attempt to extract:
- Product name
- Description
- Price
- Image

You can always edit these fields manually before saving.

### Daily Digest Emails

Users receive a daily email (at the time configured in `DAILY_DIGEST_HOUR`) when other users make changes to their wishlists. The email includes:
- Who made changes
- What items were added, updated, or removed
- Direct link to view all wishlists

This keeps everyone informed without constant notifications!

### Password Recovery

**Forgot Password:**
1. Click "Forgot Password?" on the login page
2. Enter your email
3. Check your email for a reset link
4. Click the link and set a new password

**Magic Link Login (Passwordless):**
1. Click "Send me a login link" on the login page
2. Enter your email
3. Check your email for a secure login link
4. Click the link to log in instantly

## 🛡️ Admin Guide

### Accessing Admin Panel

If your account has admin privileges, you'll see an "Admin" link in the navigation bar.

### Admin Features

- **Dashboard**: View system statistics and recent activity
- **User Management**: View, edit, delete users, grant/revoke admin privileges
- **Impersonation**: Log in as any user to troubleshoot issues
- **Content Management**: View and delete inappropriate wishlist items
- **Purchase Tracking**: Monitor all gift purchases

### Manual Commands

Manually trigger the daily digest email (for testing):
```bash
docker exec christmas-wishlist flask send-digest
```

Run tests:
```bash
docker exec christmas-wishlist pytest
```

## 🧪 Testing

```bash
# Run tests inside Docker container
docker exec christmas-wishlist pytest

# Run tests with coverage
docker exec christmas-wishlist pytest --cov=app --cov-report=html
```

## 🚢 CI/CD & Deployment

This project includes automated continuous integration and deployment via GitHub Actions.

### Automated Version Bumping

Versions are automatically bumped when you merge to the `main` branch:

**Workflow:**
```bash
# Work on development branch
git checkout development
git commit -m "feat: add new feature"  # Use conventional commits!
git push

# Merge to main
git checkout main
git merge development
git push

# GitHub Actions automatically:
# 1. Analyzes commit messages
# 2. Bumps version (e.g., 1.0.0 → 1.1.0)
# 3. Updates CHANGELOG.md
# 4. Creates git tag v1.1.0
# 5. Builds and pushes Docker image to Docker Hub
```

**Commit Message Conventions:**
- `feat:` → MINOR version bump (1.0.0 → 1.1.0)
- `fix:` → PATCH version bump (1.0.0 → 1.0.1)
- `BREAKING CHANGE:` or `feat!:` → MAJOR version bump (1.0.0 → 2.0.0)

### Docker Hub Deployment

Docker images are automatically built and pushed to Docker Hub when:
- Code is pushed to `main` branch
- Version tags are created (e.g., `v1.2.3`)

**Setup Required:**
1. Add GitHub secrets:
   - `DOCKERHUB_USERNAME` - Your Docker Hub username
   - `DOCKERHUB_TOKEN` - Docker Hub access token
2. See `DOCKER_HUB_SETUP.md` for detailed instructions

**Pull the latest image:**
```bash
docker pull <your-username>/christmas-wishlist:latest
```

### CI Pipeline

GitHub Actions automatically runs on every push/PR:
- ✅ **Tests** - pytest on Python 3.11, 3.12, 3.13
- ✅ **Code Quality** - Black formatting and Flake8 linting
- ✅ **Docker Build** - Verifies container builds successfully

See `.github/workflows/` for workflow definitions.

**Documentation:**
- `VERSIONING.md` - Complete versioning guide
- `DOCKER_HUB_SETUP.md` - Docker Hub deployment setup
- `.github/workflows/README.md` - CI/CD workflow documentation

## 🏗️ Project Structure

```
ChristmasWishlist/
├── app/
│   ├── __init__.py          # App factory
│   ├── models.py            # Database models (User, WishlistItem, Purchase, WishlistChange)
│   ├── forms.py             # WTForms
│   ├── email.py             # Email utilities (welcome, password reset, daily digest)
│   ├── scheduler.py         # APScheduler for daily digest
│   ├── cli.py               # Flask CLI commands
│   ├── routes/
│   │   ├── main.py          # Main routes
│   │   ├── auth.py          # Authentication
│   │   ├── wishlist.py      # Wishlist CRUD
│   │   ├── admin.py         # Admin panel
│   │   └── scraper.py       # API routes (placeholder)
│   ├── static/
│   │   ├── js/scraper.js    # Client-side URL scraping
│   │   ├── manifest.json    # PWA manifest
│   │   └── sw.js            # Service worker
│   └── templates/           # Jinja2 templates
├── tests/                   # Test suite
├── config.py                # Configuration
├── run.py                   # Application entry point
├── requirements.txt         # Python dependencies
├── Dockerfile              # Docker configuration
├── docker-compose.yml      # Docker Compose
└── README.md               # This file
```

## 🔒 Security Features

- **Password Hashing**: Werkzeug's secure password hashing
- **CSRF Protection**: Flask-WTF CSRF tokens on all forms
- **Secure Sessions**: Flask's signed cookie sessions
- **Reverse Proxy Support**: Built-in ProxyFix middleware for Nginx/Apache
- **HTTPS Support**: Secure cookie configuration for production
- **Email Enumeration Prevention**: Generic success messages for password reset/magic links
- **Token Expiry**: Time-limited tokens for password reset and magic links
- **Admin-Only Routes**: Decorator-based access control
- **Input Validation**: WTForms validation on all user inputs
- **SQL Injection Protection**: SQLAlchemy ORM
- **XSS Protection**: Jinja2 automatic escaping
- **Dependency Security**: Regular updates to patch vulnerabilities

## 🌐 Reverse Proxy Deployment

The application is **fully configured** to run behind a reverse proxy (Nginx, Apache, Caddy).

**Quick Setup for Nginx + HTTPS:**

1. Copy the sample Nginx configuration:
   ```bash
   sudo cp nginx.conf.example /etc/nginx/sites-available/wishlist
   ```

2. Update `.env` for HTTPS:
   ```env
   PREFERRED_URL_SCHEME=https
   SESSION_COOKIE_SECURE=True
   APP_URL=https://yourdomain.com
   ```

3. Enable and test:
   ```bash
   sudo ln -s /etc/nginx/sites-available/wishlist /etc/nginx/sites-enabled/
   sudo nginx -t
   sudo systemctl reload nginx
   ```

**See `REVERSE_PROXY.md` for complete documentation** including SSL/TLS setup with Let's Encrypt.

## 🐛 Troubleshooting

### Email Not Sending

1. Verify Mailgun credentials in `.env`
2. Check that `MAIL_USE_TLS` is set to `True`
3. Verify your Mailgun domain is verified
4. Check application logs: `docker logs christmas-wishlist`

### Database Issues

Reset the database (loses all data):
```bash
docker compose down
docker volume rm christmaswishlist_db  # If using named volumes
docker compose up -d
```

### Port Already in Use

Change the port in `docker-compose.yml`:
```yaml
ports:
  - "8000:5000"  # Use port 8000 instead
```

### Daily Digest Not Sending

1. Check logs: `docker logs christmas-wishlist | grep -i digest`
2. Verify `DAILY_DIGEST_HOUR` is set correctly in `.env` (uses UTC time)
3. Manually test: `docker exec christmas-wishlist flask send-digest`

## 📝 Dependencies

All dependencies are mature, well-maintained packages with security updates.

### Core Dependencies
- **Flask** (3.0.0): Web framework
- **Flask-SQLAlchemy** (3.1.1): Database ORM
- **Flask-Login** (0.6.3): User session management
- **Flask-Mail** (0.9.1): Email sending
- **Flask-WTF** (1.2.1): Form handling and CSRF protection
- **BeautifulSoup4** (4.12.2): HTML parsing for URL scraping
- **Requests** (2.31.0): HTTP library
- **APScheduler** (3.10.4): Task scheduling for daily digest
- **Gunicorn** (21.2.0): Production WSGI server

Check for vulnerabilities:
```bash
pip install pip-audit
pip-audit
```

## 📄 License

This project is provided as-is for personal and educational use.

## 🎅 Credits

Built with ❤️ for making Christmas gift-giving easier and more organized!

---

**Happy Holidays! 🎄**
