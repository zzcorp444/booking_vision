#!/usr/bin/env bash
# build.sh - Render build script

set -o errexit  # exit on error

echo "=== Starting Booking Vision build ==="

echo "1. Installing dependencies..."
pip install -r requirements.txt

echo "2. Collecting static files..."
python manage.py collectstatic --no-input

echo "3. Resetting database and creating fresh migrations..."
# Reset migration tracking
python manage.py migrate --fake booking_vision_APP zero || true
python manage.py migrate --fake-initial || true

# Create fresh migrations
echo "4. Creating new migrations..."
python manage.py makemigrations booking_vision_APP --empty --name reset_migration
python manage.py makemigrations booking_vision_APP

echo "5. Running migrations..."
python manage.py migrate --run-syncdb

echo "6. Creating Django tables..."
python manage.py migrate auth
python manage.py migrate contenttypes
python manage.py migrate sessions
python manage.py migrate admin
python manage.py migrate booking_vision_APP

echo "7. Loading initial data..."
python manage.py init_data

echo "=== Build completed successfully! ==="