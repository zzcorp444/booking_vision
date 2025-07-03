#!/usr/bin/env bash
# build.sh - Render build script

set -o errexit  # exit on error

echo "=== Starting Booking Vision build ==="

echo "1. Installing dependencies..."
pip install -r requirements.txt

echo "2. Collecting static files..."
python manage.py collectstatic --no-input

echo "3. Making fresh migrations..."
python manage.py makemigrations booking_vision_APP --noinput

echo "4. Running ALL migrations..."
python manage.py migrate auth
python manage.py migrate contenttypes
python manage.py migrate sessions
python manage.py migrate admin
python manage.py migrate booking_vision_APP

echo "5. Verifying database..."
python manage.py showmigrations

echo "6. Loading initial data..."
python manage.py init_data

echo "=== Build completed successfully! ==="