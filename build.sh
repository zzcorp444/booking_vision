#!/usr/bin/env bash
# build.sh - Render build script

set -o errexit  # exit on error

echo "=== Starting Booking Vision build ==="

echo "1. Installing dependencies..."
pip install -r requirements.txt

echo "2. Collecting static files..."
python manage.py collectstatic --no-input

echo "3. Ensuring database is ready..."
# Create a Python script to force table creation
cat > create_tables.py << 'EOF'
import os
import sys
import django
from django.db import connection

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'booking_vision.settings')
django.setup()

# Force creation of Django tables
from django.core.management import call_command

print("Creating Django tables...")
try:
    # Migrate without running checks
    call_command('migrate', 'contenttypes', run_syncdb=True)
    call_command('migrate', 'auth', run_syncdb=True)
    call_command('migrate', 'sessions', run_syncdb=True)
    call_command('migrate', 'admin', run_syncdb=True)
    print("Django tables created successfully")
except Exception as e:
    print(f"Error creating Django tables: {e}")

# Now migrate the app
try:
    call_command('migrate', 'booking_vision_APP', run_syncdb=True)
    print("App tables created successfully")
except Exception as e:
    print(f"Error creating app tables: {e}")

# Final migrate to ensure everything is in sync
try:
    call_command('migrate', run_syncdb=True)
    print("All migrations completed")
except Exception as e:
    print(f"Error in final migration: {e}")
EOF

python create_tables.py

echo "4. Loading initial data..."
python manage.py init_data || echo "Initial data loading failed, but continuing..."

echo "=== Build completed successfully! ==="