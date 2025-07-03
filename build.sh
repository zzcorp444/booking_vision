#!/usr/bin/env bash
# build.sh - Render build script

set -o errexit  # exit on error

echo "=== Starting Booking Vision build ==="

echo "1. Installing dependencies..."
pip install -r requirements.txt

echo "2. Collecting static files..."
python manage.py collectstatic --no-input

echo "3. Creating all migrations..."
python manage.py makemigrations

echo "4. Running core Django migrations first..."
python manage.py migrate contenttypes
python manage.py migrate auth
python manage.py migrate sessions
python manage.py migrate admin

echo "5. Running app migrations..."
python manage.py migrate booking_vision_APP

echo "6. Running any remaining migrations..."
python manage.py migrate

echo "7. Loading initial data..."
python manage.py init_data

echo "=== Build completed successfully! ==="
