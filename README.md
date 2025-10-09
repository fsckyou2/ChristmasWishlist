# 🎄 Christmas Wishlist

A modern, user-friendly web application for managing Christmas wishlists. Share your holiday wishes with family and friends, browse others' wishlists, and coordinate gift purchases without spoiling the surprise!

## ✨ Features

### For Users
- **Easy Wishlist Management**: Add items manually or automatically extract product details from URLs (Amazon, eBay, Walmart, etc.)
- **Privacy-Focused**: Others can see *what* was purchased but not *who* purchased it
- **Partial Purchases**: Support for multiple people purchasing partial quantities of items
- **Simple Interface**: Clean, Christmas-themed UI built with Tailwind CSS
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
- Python 3.11+
- Docker and Docker Compose (for containerized deployment)
- Mailgun account (or other SMTP provider) for email functionality

### Method 1: Docker (Recommended)

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd ChristmasWishlist
   ```

2. **Create environment file**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and fill in your configuration values (see Configuration section below)

3. **Generate templates**
   ```bash
   python create_templates.py
   python create_wishlist_templates.py
   python create_admin_templates.py
   ```

4. **Build and run with Docker**
   ```bash
   docker-compose up -d
   ```

5. **Access the application**
   Open your browser to `http://localhost:5000`

### Method 2: Local Development

1. **Clone and setup**
   ```bash
   git clone <repository-url>
   cd ChristmasWishlist
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Create environment file**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` with your configuration

4. **Generate templates**
   ```bash
   python create_templates.py
   python create_wishlist_templates.py
   python create_admin_templates.py
   ```

5. **Run the application**
   ```bash
   python run.py
   ```

6. **Access the application**
   Open your browser to `http://localhost:5000`

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
- Amazon
- eBay
- Walmart
- Many other sites (generic scraper)

Simply paste the product URL and click "Auto-Fill from URL". The app will attempt to extract:
- Product name
- Description
- Price
- Image

You can always edit these fields manually before saving.

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

**Dashboard:**
- View system statistics
- See recent user activity
- Quick access to management features

**User Management:**
- View all registered users
- Grant/revoke admin privileges
- Delete user accounts
- Reset user passwords
- **Impersonate users** to troubleshoot issues

**Impersonation:**
1. Go to Admin → Manage Users
2. Click "Impersonate" next to any user
3. You'll be logged in as that user
4. Click "Stop Impersonating" to return to your admin account

**Content Management:**
- View all wishlist items
- Delete inappropriate content
- Monitor purchase activity

## 🧪 Testing

Run the test suite:

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run tests
pytest

# Run tests with coverage
pytest --cov=app --cov-report=html
```

View coverage report by opening `htmlcov/index.html` in your browser.

## 🏗️ Project Structure

```
ChristmasWishlist/
├── app/
│   ├── __init__.py          # App factory
│   ├── models.py            # Database models
│   ├── forms.py             # WTForms
│   ├── email.py             # Email utilities
│   ├── scraper.py           # URL scraping
│   ├── routes/
│   │   ├── main.py          # Main routes
│   │   ├── auth.py          # Authentication
│   │   ├── wishlist.py      # Wishlist CRUD
│   │   └── admin.py         # Admin panel
│   ├── static/
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

**See `REVERSE_PROXY.md` for complete documentation** including:
- Nginx, Apache, and Caddy configurations
- SSL/TLS setup with Let's Encrypt
- Security headers configuration
- Troubleshooting guide
- Performance optimization

## 🐛 Troubleshooting

### Templates Not Found

Run the template generation scripts:
```bash
python create_templates.py
python create_wishlist_templates.py
python create_admin_templates.py
```

### Email Not Sending

1. Verify Mailgun credentials in `.env`
2. Check that `MAIL_USE_TLS` is set to `True`
3. Verify your Mailgun domain is verified
4. Check application logs for SMTP errors

### Database Issues

Delete the database and restart (loses all data):
```bash
rm instance/wishlist.db
python run.py
```

### Port Already in Use

Change the port in `docker-compose.yml` or `run.py`:
```yaml
ports:
  - "8000:5000"  # Use port 8000 instead
```

## 📝 Dependencies

All dependencies are mature, well-maintained packages. See `requirements.txt` for versions.

### Core Dependencies
- **Flask** (3.0.0): Web framework
- **Flask-SQLAlchemy** (3.1.1): Database ORM
- **Flask-Login** (0.6.3): User session management
- **Flask-Mail** (0.9.1): Email sending
- **Flask-WTF** (1.2.1): Form handling and CSRF protection
- **BeautifulSoup4** (4.12.2): HTML parsing for URL scraping
- **Requests** (2.31.0): HTTP library
- **Gunicorn** (21.2.0): Production WSGI server

All dependencies have been checked for known vulnerabilities. Use `pip-audit` to verify:
```bash
pip install pip-audit
pip-audit
```

## 📄 License

This project is provided as-is for personal and educational use.

## 🎅 Credits

Built with ❤️ for making Christmas gift-giving easier and more organized!

## 🤝 Contributing

This is a personal project, but suggestions and bug reports are welcome via issues.

## 📞 Support

For issues or questions:
1. Check the Troubleshooting section above
2. Review existing GitHub issues
3. Create a new issue with detailed information
