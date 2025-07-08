#!/usr/bin/env bash
# Exit on error
set -o errexit

echo "=== Starting Booking Vision build ==="

# Modify pip.conf to use legacy resolver
# pip config set global.use-deprecated legacy-resolver
echo "1. Installing dependencies..."
pip install -r requirements.txt

# Convert static asset files
echo "2. Collecting static files..."
python manage.py collectstatic --no-input

# Apply any outstanding database migrations
echo "3. Running ALL migrations..."
python manage.py migrate

# Create superuser using environment variables
echo "4. Creating Superuser if doesn't exists..."
python manage.py shell << EOF
import os
from django.contrib.auth import get_user_model
from django.db import IntegrityError

User = get_user_model()

# Get environment variables
username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'ZZ_Corp')
email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'zz.corp.hd@gmail.com')
password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'Elpadrino21!')

# Create superuser if it doesn't exist
if not User.objects.filter(username=username).exists():
    try:
        User.objects.create_superuser(
            username=username,
            email=email,
            password=password
        )
        print(f"Superuser '{username}' created successfully!")
    except IntegrityError as e:
        print(f"Error creating superuser: {e}")
else:
    print(f"Superuser '{username}' already exists.")
EOF

echo "=== Build completed successfully! ==="