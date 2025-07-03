#!/usr/bin/env bash
# build.sh - Render build script

set -o errexit  # exit on error

echo "Installing dependencies..."
pip install -r requirements.txt

echo "Creating migrations..."
python manage.py makemigrations --noinput

echo "Collecting static files..."
python manage.py collectstatic --no-input

echo "Running migrations..."
python manage.py migrate

echo "Creating migrations for booking_vision_APP if needed..."
python manage.py makemigrations booking_vision_APP --noinput

echo "Applying app migrations..."
python manage.py migrate

echo "Creating superuser if it doesn't exist..."
python manage.py shell << EOF
from django.contrib.auth.models import User
import os

username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'bv_admin')
email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'zz.corp.hd@gmail.com')
password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'Alibaba2021!')

if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username=username, email=email, password=password)
    print(f"Superuser '{username}' created successfully!")
else:
    print(f"Superuser '{username}' already exists.")
EOF

echo "Loading initial data..."
python manage.py shell << EOF
from booking_vision_APP.models.channels import Channel
from booking_vision_APP.models.properties import Amenity

# Create default channels if they don't exist
channels = [
    {'name': 'Airbnb', 'api_endpoint': 'https://api.airbnb.com/'},
    {'name': 'Booking.com', 'api_endpoint': 'https://distribution-xml.booking.com/'},
    {'name': 'VRBO', 'api_endpoint': 'https://api.vrbo.com/'},
    {'name': 'Expedia', 'api_endpoint': 'https://api.expedia.com/'},
    {'name': 'Agoda', 'api_endpoint': 'https://affiliateapi7.agoda.com/'},
]

for channel_data in channels:
    channel, created = Channel.objects.get_or_create(
        name=channel_data['name'],
        defaults=channel_data
    )
    if created:
        print(f"Created channel: {channel.name}")

# Create default amenities
amenities = [
    {'name': 'WiFi', 'category': 'Technology', 'icon': 'fas fa-wifi'},
    {'name': 'Kitchen', 'category': 'Kitchen', 'icon': 'fas fa-utensils'},
    {'name': 'Parking', 'category': 'Transportation', 'icon': 'fas fa-parking'},
    {'name': 'Pool', 'category': 'Recreation', 'icon': 'fas fa-swimming-pool'},
    {'name': 'Air Conditioning', 'category': 'Climate', 'icon': 'fas fa-snowflake'},
    {'name': 'Washer', 'category': 'Laundry', 'icon': 'fas fa-tshirt'},
    {'name': 'TV', 'category': 'Entertainment', 'icon': 'fas fa-tv'},
    {'name': 'Hot Tub', 'category': 'Recreation', 'icon': 'fas fa-hot-tub'},
]

for amenity_data in amenities:
    amenity, created = Amenity.objects.get_or_create(
        name=amenity_data['name'],
        defaults=amenity_data
    )
    if created:
        print(f"Created amenity: {amenity.name}")

print("Initial data loaded successfully!")
EOF

echo "Build completed successfully!"