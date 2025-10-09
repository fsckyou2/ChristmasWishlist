#!/bin/bash
# Quick Start Script for Christmas Wishlist
# This script helps set up the application quickly

set -e

echo "🎄 Christmas Wishlist - Quick Start Setup 🎄"
echo "============================================"
echo ""

# Check Python version
echo "Checking Python version..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.11 or higher."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "✅ Found Python $PYTHON_VERSION"
echo ""

# Create virtual environment
echo "Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "⚠️  Virtual environment already exists"
fi
echo ""

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate
echo "✅ Virtual environment activated"
echo ""

# Install dependencies
echo "Installing dependencies..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
echo "✅ Dependencies installed"
echo ""

# Create .env if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    cp .env.example .env

    # Generate SECRET_KEY
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")

    # Update .env with generated secret key
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' "s/your-secret-key-here-change-in-production/$SECRET_KEY/" .env
    else
        # Linux
        sed -i "s/your-secret-key-here-change-in-production/$SECRET_KEY/" .env
    fi

    echo "✅ .env file created with generated SECRET_KEY"
    echo ""
    echo "⚠️  IMPORTANT: Edit .env and configure:"
    echo "   - Mailgun settings (MAIL_* variables)"
    echo "   - Admin credentials (ADMIN_EMAIL, ADMIN_PASSWORD)"
    echo "   - App URL if deploying (APP_URL)"
    echo ""
else
    echo "⚠️  .env file already exists, skipping"
    echo ""
fi

# Generate templates
echo "Generating HTML templates..."
python3 create_templates.py
python3 create_wishlist_templates.py
python3 create_admin_templates.py
echo "✅ Templates generated"
echo ""

# Create instance directory
mkdir -p instance
echo "✅ Instance directory created"
echo ""

echo "============================================"
echo "✅ Setup Complete!"
echo "============================================"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your configuration:"
echo "   nano .env"
echo ""
echo "2. Run the application:"
echo "   python run.py"
echo ""
echo "3. Open your browser to:"
echo "   http://localhost:5000"
echo ""
echo "For detailed setup instructions, see SETUP.md"
echo ""
echo "🎁 Happy gift-giving!"
