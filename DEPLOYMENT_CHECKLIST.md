# Deployment Checklist

Use this checklist to ensure you've completed all necessary steps before deploying to production.

## 🔧 Initial Setup

### Environment Configuration
- [ ] Created `.env` file from `.env.example`
- [ ] Generated secure `SECRET_KEY` (use: `python -c "import secrets; print(secrets.token_hex(32))"`)
- [ ] Changed `ADMIN_PASSWORD` from default
- [ ] Configured Mailgun credentials (MAIL_SERVER, MAIL_USERNAME, MAIL_PASSWORD, etc.)
- [ ] Set `MAIL_DEFAULT_SENDER` to your domain email
- [ ] Updated `APP_URL` to your production domain (e.g., `https://yourdomain.com`)
- [ ] Set `FLASK_ENV=production`
- [ ] `.env` file permissions set to 600 (`chmod 600 .env`)
- [ ] Added `.env` to `.gitignore` (already included)

### Application Setup
- [ ] Generated templates (run all three scripts):
  - [ ] `python create_templates.py`
  - [ ] `python create_wishlist_templates.py`
  - [ ] `python create_admin_templates.py`
- [ ] Installed dependencies: `pip install -r requirements.txt`
- [ ] Tested application locally: `python run.py`
- [ ] Verified database creation (check `instance/wishlist.db` exists)

## 🧪 Testing

- [ ] Ran test suite: `pytest`
- [ ] All tests passing
- [ ] Manually tested:
  - [ ] User registration
  - [ ] Login/logout
  - [ ] Password reset email received
  - [ ] Magic link email received
  - [ ] Adding wishlist items (manual)
  - [ ] Adding wishlist items (URL auto-fill)
  - [ ] Editing items
  - [ ] Deleting items
  - [ ] Viewing other users' wishlists
  - [ ] Purchasing items
  - [ ] Admin dashboard access
  - [ ] User impersonation
  - [ ] Mobile responsive design
  - [ ] PWA installation on mobile

## 🔒 Security

- [ ] Changed default `SECRET_KEY`
- [ ] Changed default `ADMIN_PASSWORD`
- [ ] No secrets committed to Git
- [ ] HTTPS/SSL configured
- [ ] SSL certificate valid and not expired
- [ ] HSTS header configured (if using reverse proxy)
- [ ] Security headers configured (CSP, X-Frame-Options, etc.)
- [ ] Rate limiting considered/implemented
- [ ] Database access restricted (not publicly accessible)
- [ ] File permissions correct (`.env` = 600, database directory writable)

### Dependency Security
- [ ] Ran `pip-audit` for vulnerability scan
- [ ] All dependencies up to date
- [ ] No critical or high vulnerabilities

## 📧 Email Configuration

- [ ] Mailgun domain verified
- [ ] DNS records configured (SPF, DKIM, DMARC)
- [ ] Test email sent successfully
- [ ] Password reset email received and works
- [ ] Magic link email received and works
- [ ] Emails not going to spam folder
- [ ] Email sending rate limits understood (Mailgun free tier: 5,000/month)

## 🗄️ Database

### Development (SQLite)
- [ ] Database file location: `instance/wishlist.db`
- [ ] Database file backed up

### Production (Recommended: PostgreSQL)
- [ ] PostgreSQL installed and configured
- [ ] Database created
- [ ] Database user created with appropriate permissions
- [ ] `DATABASE_URL` updated in `.env`
- [ ] Connection tested
- [ ] Automated backup configured
- [ ] Backup restoration tested

## 🐳 Docker Deployment

If using Docker:

- [ ] Dockerfile reviewed
- [ ] docker-compose.yml reviewed
- [ ] `.env` file present in project root
- [ ] Built image: `docker-compose build`
- [ ] Started container: `docker-compose up -d`
- [ ] Verified container running: `docker-compose ps`
- [ ] Checked logs: `docker-compose logs -f`
- [ ] Health check passing
- [ ] Volumes configured for persistence
- [ ] Port mapping correct (default: 5000:5000)

## 🌐 Web Server / Reverse Proxy

- [ ] Nginx/Apache installed and configured
- [ ] Reverse proxy configured to Flask app
- [ ] SSL/TLS configured (Let's Encrypt recommended)
- [ ] Certificate auto-renewal configured
- [ ] HTTP to HTTPS redirect configured
- [ ] Gzip compression enabled
- [ ] Static file caching configured
- [ ] Security headers configured:
  - [ ] Strict-Transport-Security
  - [ ] X-Content-Type-Options
  - [ ] X-Frame-Options
  - [ ] Content-Security-Policy
  - [ ] Referrer-Policy

## 📊 Monitoring & Logging

- [ ] Application logging configured
- [ ] Log rotation configured
- [ ] Error tracking service configured (Sentry, Rollbar, etc.) - Optional
- [ ] Uptime monitoring configured (UptimeRobot, Pingdom, etc.) - Optional
- [ ] Disk space monitoring
- [ ] Database size monitoring
- [ ] Email quota monitoring

## 🔄 Backup Strategy

- [ ] Database backup automated (daily recommended)
- [ ] Backup storage location configured
- [ ] Backups encrypted
- [ ] Backup retention policy defined (e.g., keep 30 days)
- [ ] Backup restoration procedure documented
- [ ] Backup restoration tested successfully
- [ ] `.env` file backed up securely (separate from code)
- [ ] User-uploaded content backed up (if any)

## 🚀 Performance

- [ ] Gunicorn configured with appropriate number of workers (formula: `(2 x CPU cores) + 1`)
- [ ] Worker timeout configured (default: 120s in Dockerfile)
- [ ] Database connection pooling configured (if using PostgreSQL)
- [ ] Static files served efficiently (CDN or web server, not Flask)
- [ ] Image optimization (if hosting user uploads)
- [ ] Database indexes reviewed and optimized

## 📱 Mobile / PWA

- [ ] PWA manifest.json accessible at `/static/manifest.json`
- [ ] Service worker registered
- [ ] "Add to Home Screen" tested on mobile
- [ ] App icon displays correctly
- [ ] App opens in standalone mode
- [ ] Mobile responsiveness tested on multiple devices
- [ ] Touch targets appropriate size (44x44px minimum)

## 🔐 Admin Account

- [ ] Admin account created (auto-created on first run from `.env`)
- [ ] Admin email accessible
- [ ] Admin password changed from default
- [ ] Admin password strong (12+ characters, mixed case, numbers, symbols)
- [ ] Admin dashboard accessible
- [ ] User management functions tested
- [ ] Impersonation feature tested
- [ ] Admin privileges can be granted/revoked

## 📝 Documentation

- [ ] README.md reviewed and updated if needed
- [ ] SETUP.md instructions tested
- [ ] SECURITY.md reviewed
- [ ] Custom configuration documented
- [ ] API endpoints documented (if any)
- [ ] Deployment process documented for your team

## 🌍 Domain & DNS

- [ ] Domain registered
- [ ] DNS A record pointing to server IP
- [ ] DNS propagation complete (check with `dig yourdomain.com`)
- [ ] WWW subdomain configured (if desired)
- [ ] Domain accessible via HTTPS

## 🧹 Cleanup

- [ ] Development database removed/ignored
- [ ] Debug mode disabled (`FLASK_ENV=production`)
- [ ] Unnecessary files removed
- [ ] .pyc files ignored
- [ ] __pycache__ directories ignored
- [ ] venv directory ignored
- [ ] instance/ directory handled appropriately

## 🎯 Final Checks

- [ ] All environment variables set correctly
- [ ] All configuration verified
- [ ] All tests passing
- [ ] No errors in application logs
- [ ] No errors in web server logs
- [ ] Application accessible at production URL
- [ ] SSL certificate valid and trusted
- [ ] All features working in production
- [ ] Mobile site working correctly
- [ ] Emails sending and receiving correctly
- [ ] Admin panel accessible and functional

## 📊 Post-Deployment

- [ ] Monitor application logs for errors
- [ ] Monitor server resources (CPU, memory, disk)
- [ ] Monitor database performance
- [ ] Check email delivery rates
- [ ] Verify backups running successfully
- [ ] Test disaster recovery procedure
- [ ] Document any issues encountered
- [ ] Set up alerts for critical issues

## 🎉 Launch

- [ ] Soft launch with test users
- [ ] Gather feedback
- [ ] Fix any issues found
- [ ] Full launch
- [ ] Announce to users
- [ ] Monitor closely for first 24-48 hours

## 🔄 Ongoing Maintenance

- [ ] Weekly log review
- [ ] Monthly dependency updates
- [ ] Quarterly security audit
- [ ] Regular backup verification
- [ ] SSL certificate renewal (if not automated)
- [ ] Database optimization (as needed)
- [ ] User feedback review and feature planning

---

## Quick Reference Commands

### Start Application (Docker)
```bash
docker-compose up -d
```

### View Logs (Docker)
```bash
docker-compose logs -f
```

### Stop Application (Docker)
```bash
docker-compose down
```

### Backup Database (SQLite)
```bash
cp instance/wishlist.db backups/wishlist-$(date +%Y%m%d).db
```

### Backup Database (PostgreSQL)
```bash
pg_dump -U username dbname > backups/wishlist-$(date +%Y%m%d).sql
```

### Check Dependencies for Vulnerabilities
```bash
pip install pip-audit
pip-audit
```

### Update Dependencies
```bash
pip list --outdated
pip install --upgrade package-name
```

### View Application Logs
```bash
# Docker
docker-compose logs -f web

# System service
journalctl -u christmas-wishlist -f
```

---

**Remember:** A successful deployment is not just about getting the app running, but ensuring it's secure, monitored, backed up, and maintainable. Take your time with each step!

Good luck! 🎄🎁
