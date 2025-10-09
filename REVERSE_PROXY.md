# Reverse Proxy Configuration Guide

The Christmas Wishlist application is now fully configured to work behind a reverse proxy (Nginx, Apache, Caddy, etc.).

## What Was Added

### ProxyFix Middleware
The application now includes Werkzeug's `ProxyFix` middleware which properly handles:
- `X-Forwarded-For` - Client IP address
- `X-Forwarded-Proto` - Original protocol (HTTP/HTTPS)
- `X-Forwarded-Host` - Original host header
- `X-Forwarded-Prefix` - URL prefix for subpath deployments

### Security Configuration
Added environment variables for secure cookies when using HTTPS:
- `PREFERRED_URL_SCHEME` - Set to 'https' in production
- `SESSION_COOKIE_SECURE` - Set to 'True' to require HTTPS for cookies

## Configuration

### 1. Update `.env` for Production

When deploying behind a reverse proxy with HTTPS:

```env
# Set these for HTTPS deployment
PREFERRED_URL_SCHEME=https
SESSION_COOKIE_SECURE=True
APP_URL=https://yourdomain.com
```

### 2. Nginx Configuration

A sample Nginx configuration is provided in `nginx.conf.example`.

**Quick Setup:**

1. Copy the example configuration:
   ```bash
   sudo cp nginx.conf.example /etc/nginx/sites-available/wishlist
   ```

2. Edit the file and replace:
   - `yourdomain.com` with your actual domain
   - SSL certificate paths (if using Let's Encrypt, paths are correct)
   - Proxy pass address if needed (default: `http://127.0.0.1:5000`)

3. Enable the site:
   ```bash
   sudo ln -s /etc/nginx/sites-available/wishlist /etc/nginx/sites-enabled/
   ```

4. Test configuration:
   ```bash
   sudo nginx -t
   ```

5. Reload Nginx:
   ```bash
   sudo systemctl reload nginx
   ```

### 3. SSL Certificate Setup (Let's Encrypt)

**Install Certbot:**
```bash
sudo apt install certbot python3-certbot-nginx
```

**Obtain Certificate:**
```bash
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

Certbot will automatically:
- Obtain the certificate
- Update your Nginx configuration
- Set up auto-renewal

**Test Auto-Renewal:**
```bash
sudo certbot renew --dry-run
```

### 4. Apache Configuration

If using Apache instead of Nginx:

**Enable required modules:**
```bash
sudo a2enmod proxy
sudo a2enmod proxy_http
sudo a2enmod headers
sudo a2enmod ssl
```

**Virtual Host Configuration:**
```apache
<VirtualHost *:443>
    ServerName yourdomain.com
    ServerAlias www.yourdomain.com

    SSLEngine on
    SSLCertificateFile /etc/letsencrypt/live/yourdomain.com/fullchain.pem
    SSLCertificateKeyFile /etc/letsencrypt/live/yourdomain.com/privkey.pem

    # Security headers
    Header always set Strict-Transport-Security "max-age=31536000; includeSubDomains"
    Header always set X-Frame-Options "SAMEORIGIN"
    Header always set X-Content-Type-Options "nosniff"
    Header always set X-XSS-Protection "1; mode=block"

    # Proxy settings
    ProxyPreserveHost On
    ProxyPass / http://127.0.0.1:5000/
    ProxyPassReverse / http://127.0.0.1:5000/

    # Proxy headers
    RequestHeader set X-Forwarded-Proto "https"
    RequestHeader set X-Forwarded-Port "443"

    # Logging
    ErrorLog ${APACHE_LOG_DIR}/wishlist-error.log
    CustomLog ${APACHE_LOG_DIR}/wishlist-access.log combined
</VirtualHost>

# HTTP to HTTPS redirect
<VirtualHost *:80>
    ServerName yourdomain.com
    ServerAlias www.yourdomain.com
    Redirect permanent / https://yourdomain.com/
</VirtualHost>
```

### 5. Caddy Configuration

Caddy has automatic HTTPS and is very simple:

**Caddyfile:**
```
yourdomain.com {
    reverse_proxy localhost:5000

    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains"
        X-Frame-Options "SAMEORIGIN"
        X-Content-Type-Options "nosniff"
        X-XSS-Protection "1; mode=block"
    }
}
```

Caddy automatically:
- Obtains SSL certificates
- Redirects HTTP to HTTPS
- Handles certificate renewal

## Running the Application

### With Gunicorn (Recommended for Production)

```bash
gunicorn --bind 127.0.0.1:5000 --workers 4 --timeout 120 run:app
```

### With systemd Service

Create `/etc/systemd/system/wishlist.service`:

```ini
[Unit]
Description=Christmas Wishlist Gunicorn
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/path/to/ChristmasWishlist
Environment="PATH=/path/to/ChristmasWishlist/venv/bin"
ExecStart=/path/to/ChristmasWishlist/venv/bin/gunicorn --bind 127.0.0.1:5000 --workers 4 --timeout 120 run:app

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable wishlist
sudo systemctl start wishlist
```

### With Docker Behind Proxy

Update `docker-compose.yml` to only expose port internally:

```yaml
services:
  web:
    build: .
    ports:
      - "127.0.0.1:5000:5000"  # Only localhost
    # ... rest of config
```

## Testing Reverse Proxy Setup

### 1. Check Headers
```bash
curl -I https://yourdomain.com
```

You should see:
- `Strict-Transport-Security` header
- `X-Frame-Options` header
- Status: 200 OK

### 2. Test HTTPS Redirect
```bash
curl -I http://yourdomain.com
```

Should return `301` or `302` redirect to HTTPS.

### 3. Test SSL
```bash
curl -v https://yourdomain.com
```

Should show valid SSL certificate.

### 4. Check Application Logs

The Flask app should log the correct client IP (from `X-Forwarded-For`), not the proxy IP.

## Troubleshooting

### Issue: Infinite Redirect Loop

**Cause:** Flask doesn't know it's behind HTTPS proxy.

**Solution:** Set in `.env`:
```env
PREFERRED_URL_SCHEME=https
```

### Issue: "Secure cookie on insecure connection" warnings

**Cause:** `SESSION_COOKIE_SECURE=True` but not using HTTPS.

**Solution:**
- Use HTTPS, or
- Set `SESSION_COOKIE_SECURE=False` for development

### Issue: Wrong client IP in logs

**Cause:** ProxyFix not configured correctly.

**Solution:** Adjust `x_for` value in `app/__init__.py` to match number of proxies:
```python
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1)  # 1 proxy
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=2)  # 2 proxies
```

### Issue: 502 Bad Gateway

**Causes:**
- Flask app not running
- Wrong proxy_pass address
- Firewall blocking connection

**Solutions:**
- Check Flask app is running: `curl http://localhost:5000`
- Verify proxy_pass address in Nginx config
- Check firewall rules: `sudo ufw status`

### Issue: Static files not loading

**Cause:** CSP header blocking external resources.

**Solution:** Adjust CSP in Nginx config to allow Tailwind CSS CDN:
```nginx
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com; style-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com;" always;
```

## Performance Optimization

### 1. Enable Gzip Compression (Nginx)

Add to `http` block in `/etc/nginx/nginx.conf`:
```nginx
gzip on;
gzip_vary on;
gzip_min_length 1024;
gzip_types text/plain text/css application/json application/javascript text/xml application/xml;
```

### 2. Cache Static Files (Nginx)

Uncomment in `nginx.conf.example`:
```nginx
location /static/ {
    alias /path/to/ChristmasWishlist/app/static/;
    expires 30d;
    add_header Cache-Control "public, immutable";
}
```

### 3. Rate Limiting (Nginx)

Add to prevent brute force attacks:
```nginx
# In http block
limit_req_zone $binary_remote_addr zone=login:10m rate=5r/m;

# In server block
location /auth/login {
    limit_req zone=login burst=5;
    proxy_pass http://127.0.0.1:5000;
    # ... rest of proxy settings
}
```

## Security Checklist

When running behind reverse proxy:

- [ ] HTTPS enabled with valid SSL certificate
- [ ] HTTP to HTTPS redirect working
- [ ] HSTS header enabled
- [ ] Security headers configured (X-Frame-Options, CSP, etc.)
- [ ] `PREFERRED_URL_SCHEME=https` in `.env`
- [ ] `SESSION_COOKIE_SECURE=True` in `.env`
- [ ] `APP_URL` uses https:// scheme
- [ ] ProxyFix middleware configured correctly
- [ ] Firewall rules allow only necessary ports
- [ ] Flask app bound to localhost only (not 0.0.0.0)
- [ ] Rate limiting configured for auth endpoints
- [ ] Logs show correct client IPs
- [ ] SSL certificate auto-renewal working

## Additional Resources

- [Nginx Official Docs](https://nginx.org/en/docs/)
- [Flask Behind Proxy](https://flask.palletsprojects.com/en/latest/deploying/proxy_fix/)
- [Let's Encrypt](https://letsencrypt.org/)
- [Mozilla SSL Config Generator](https://ssl-config.mozilla.org/)

## Summary

The application is now **fully ready** for reverse proxy deployment with:
- ✅ ProxyFix middleware for correct header handling
- ✅ Configurable HTTPS support
- ✅ Secure cookie configuration
- ✅ Sample Nginx configuration
- ✅ SSL/TLS support
- ✅ Security headers
- ✅ Comprehensive documentation

Just update your `.env` file and configure your reverse proxy!
