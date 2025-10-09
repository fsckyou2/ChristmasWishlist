# Setup Guide for Christmas Wishlist

This guide provides step-by-step instructions for setting up the Christmas Wishlist application.

## Prerequisites

Before starting, ensure you have:

1. **Python 3.11 or higher** installed
   - Check: `python --version` or `python3 --version`
   - Download from: https://www.python.org/downloads/

2. **Git** installed
   - Check: `git --version`
   - Download from: https://git-scm.com/downloads

3. **A Mailgun account** (or other SMTP provider)
   - Sign up at: https://www.mailgun.com/
   - Free tier allows 5,000 emails/month

4. **Docker** (optional, for containerized deployment)
   - Download from: https://www.docker.com/get-started

## Step-by-Step Setup

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd ChristmasWishlist
```

### Step 2: Create Virtual Environment (Local Development Only)

**On macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**On Windows:**
```cmd
python -m venv venv
venv\Scripts\activate
```

You should see `(venv)` in your terminal prompt.

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

For development (includes testing tools):
```bash
pip install -r requirements-dev.txt
```

### Step 4: Configure Environment Variables

1. **Copy the example environment file:**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` file with your text editor and update these values:**

   ```env
   # CRITICAL: Change this to a random string!
   SECRET_KEY=generate-a-random-secret-key-here

   # Your Mailgun settings
   MAIL_SERVER=smtp.mailgun.org
   MAIL_PORT=587
   MAIL_USE_TLS=True
   MAIL_USERNAME=postmaster@your-mailgun-domain.org
   MAIL_PASSWORD=your-mailgun-password
   MAIL_DEFAULT_SENDER=noreply@your-domain.com

   # Your domain (change in production)
   APP_URL=http://localhost:5000

   # Admin account (created on first run)
   ADMIN_EMAIL=admin@example.com
   ADMIN_PASSWORD=ChooseAStrongPassword123!
   ```

   **To generate a secure SECRET_KEY:**
   ```python
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

3. **Mailgun Setup:**
   - Log in to Mailgun
   - Go to "Sending" → "Domain Settings"
   - Copy your SMTP credentials
   - Update MAIL_USERNAME and MAIL_PASSWORD in .env

### Step 5: Generate HTML Templates

The templates are generated via Python scripts to keep the repository clean:

```bash
python create_templates.py
python create_wishlist_templates.py
python create_admin_templates.py
```

You should see output confirming template creation.

### Step 6: Initialize the Database

The database will be created automatically on first run, but you can initialize it manually:

```bash
python -c "from app import create_app, db; app = create_app(); app.app_context().push(); db.create_all()"
```

### Step 7: Run the Application

**Development Mode:**
```bash
python run.py
```

The app will be available at `http://localhost:5000`

**Production Mode (with Gunicorn):**
```bash
gunicorn --bind 0.0.0.0:5000 --workers 4 run:app
```

### Step 8: Create Your First Account

1. Open `http://localhost:5000` in your browser
2. Click "Register"
3. Fill in your details
4. Log in with your credentials

### Step 9: Access Admin Panel (Optional)

The admin account specified in `.env` is created automatically on first run.

1. Log out of your regular account
2. Log in with:
   - Email: (ADMIN_EMAIL from .env)
   - Password: (ADMIN_PASSWORD from .env)
3. You'll see an "Admin" link in the navigation

## Docker Setup (Alternative)

If you prefer Docker:

### Step 1: Setup Environment

```bash
cp .env.example .env
# Edit .env as described in Step 4 above
```

### Step 2: Generate Templates

```bash
python create_templates.py
python create_wishlist_templates.py
python create_admin_templates.py
```

### Step 3: Build and Run

```bash
docker-compose up -d
```

The app will be available at `http://localhost:5000`

### View Logs:
```bash
docker-compose logs -f
```

### Stop:
```bash
docker-compose down
```

## Testing Your Setup

### 1. Test User Registration
- Go to `/auth/register`
- Create a test account
- Verify you can log in

### 2. Test Wishlist Creation
- Add an item manually
- Try the URL auto-fill with an Amazon link
- Edit and delete items

### 3. Test Email (Important!)
- Click "Forgot Password?"
- Enter your email
- Check if you receive the email
- If not, verify Mailgun settings in `.env`

### 4. Test Purchase Flow
- Create a second user account
- View the first user's wishlist
- Mark an item as purchased
- Verify it shows as purchased (but not who purchased it)

### 5. Test Admin Features (if applicable)
- Log in as admin
- Access Admin Dashboard
- Try impersonating a user
- Stop impersonation

## Production Deployment

### Additional Steps for Production:

1. **Use a real database** (PostgreSQL recommended):
   ```env
   DATABASE_URL=postgresql://user:password@localhost/dbname
   ```

2. **Set secure SECRET_KEY:**
   - Generate: `python -c "import secrets; print(secrets.token_hex(32))"`
   - Never commit this to version control!

3. **Update APP_URL** to your domain:
   ```env
   APP_URL=https://your-domain.com
   ```

4. **Use HTTPS:** Set up SSL/TLS (Let's Encrypt recommended)

5. **Set FLASK_ENV to production:**
   ```env
   FLASK_ENV=production
   ```

6. **Use a reverse proxy:** Nginx or Apache recommended

7. **Set up monitoring:** Application logs, error tracking

8. **Regular backups:** Backup your database regularly

9. **Security headers:** Use Flask-Talisman or configure via reverse proxy

## Troubleshooting

### "Module not found" errors
```bash
pip install -r requirements.txt
```

### "Template not found" errors
```bash
python create_templates.py
python create_wishlist_templates.py
python create_admin_templates.py
```

### Email not sending
1. Verify Mailgun credentials
2. Check Mailgun domain is verified
3. Test SMTP connection:
   ```python
   python -c "from app import create_app, mail; app = create_app(); app.app_context().push(); print('SMTP Config OK')"
   ```

### Port 5000 already in use
Change port in `run.py`:
```python
app.run(host='0.0.0.0', port=8000, debug=True)
```

### Database locked (SQLite)
Stop all instances of the app, then:
```bash
rm instance/wishlist.db
python run.py
```

## Next Steps

1. **Invite users:** Share your URL with family
2. **Create wishlists:** Start adding items
3. **Customize:** Edit templates in `app/templates/`
4. **Monitor:** Check logs regularly
5. **Backup:** Set up automated database backups

## Security Checklist

Before going to production:

- [ ] Changed SECRET_KEY from default
- [ ] Changed ADMIN_PASSWORD from default
- [ ] Using HTTPS (SSL/TLS)
- [ ] Set FLASK_ENV=production
- [ ] Updated APP_URL to production domain
- [ ] Email sending works
- [ ] Database backups configured
- [ ] Tested all functionality
- [ ] Reviewed and updated .gitignore

## Getting Help

- Review README.md for detailed documentation
- Check existing issues on GitHub
- Create a new issue with:
  - Your Python version
  - Operating system
  - Error message
  - Steps to reproduce

Happy gift-giving! 🎁
