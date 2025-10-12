#!/bin/bash
set -e

echo "================================"
echo "Starting Christmas Wishlist App"
echo "================================"

# Ensure instance directory exists
echo ""
echo "Ensuring instance directory exists..."
mkdir -p instance

# Check if database file exists and run migrations (only for web service)
# Scheduler doesn't need to run migrations
if [ "$1" != "scheduler" ]; then
    if [ -f "instance/wishlist.db" ]; then
        # Database exists - run migrations
        echo ""
        echo "Database found - running migrations..."
        python scripts/apply_all_migrations.py

        # Check if migrations succeeded
        if [ $? -eq 0 ]; then
            echo ""
            echo "✅ Migrations completed successfully"
        else
            echo ""
            echo "❌ Migrations failed! Container will not start."
            exit 1
        fi
    else
        # No database - fresh deployment
        echo ""
        echo "No database found - fresh deployment (tables will be created on first request)"
    fi
fi

echo ""

# Start the appropriate service based on arguments
if [ "$1" == "scheduler" ]; then
    echo "Starting scheduler worker..."
    echo "================================"
    exec python scheduler_worker.py
else
    echo "Starting application server..."
    echo "================================"
    exec gunicorn --bind 0.0.0.0:5000 --workers 4 --timeout 120 run:app
fi
