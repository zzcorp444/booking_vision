#!/usr/bin/env bash
# build.sh - Render build script

set -o errexit  # exit on error

echo "=== Starting Booking Vision build ==="

echo "1. Installing dependencies..."
pip install -r requirements.txt

echo "2. Collecting static files..."
python manage.py collectstatic --no-input

echo "3. Making migrations..."
python manage.py makemigrations --noinput

echo "4. Running migrations..."
python manage.py migrate --noinput

echo "5. Loading initial data..."
python manage.py init_data

echo "=== Build completed successfully! ==="