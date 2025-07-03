#!/usr/bin/env bash
# build.sh - Render build script

set -o errexit  # exit on error

echo "=== Starting Booking Vision build ==="

echo "1. Installing dependencies..."
pip install -r requirements.txt

echo "2. Collecting static files..."
python manage.py collectstatic --no-input

echo "3. Making migrations..."
python manage.py makemigrations

echo "4. Running ALL migrations on fresh database..."
python manage.py migrate

echo "5. Loading initial data..."
python manage.py init_data

echo "=== Build completed successfully! ==="