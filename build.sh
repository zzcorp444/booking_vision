#!/usr/bin/env bash
# build.sh - Render build script

set -o errexit  # exit on error

echo "Installing dependencies..."
pip install -r requirements.txt

echo "Collecting static files..."
python manage.py collectstatic --no-input

echo "Creating migrations..."
python manage.py makemigrations --noinput

echo "Running migrations..."
python manage.py migrate

echo "Database setup completed. Creating initial data..."

# Create superuser and initial data using a management command instead
cat > booking_vision_APP/management/__init__.py << 'EOF'
# Management commands package
EOF

mkdir -p booking_vision_APP/management/commands

cat > booking_vision_APP/management/commands/__init__.py << 'EOF'
# Management commands
EOF

cat > booking_vision_APP/management/commands/init_data.py << 'EOF'
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
import os

class Command(BaseCommand):
    help = 'Initialize data for Booking Vision'

    def handle(self, *args, **kwargs):
        # Create superuser
        username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin')
        email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@bookingvision.com')
        password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'admin123')
        
        if not User.objects.filter(username=username).exists():
            User.objects.create_superuser(username=username, email=email, password=password)
            self.stdout.write(self.style.SUCCESS(f"Superuser '{username}' created successfully!"))
        else:
            self.stdout.write(self.style.WARNING(f"Superuser '{username}' already exists."))
        
        # Import models here to avoid issues
        from booking_vision_APP.models.channels import Channel
        from booking_vision_APP.models.properties import Amenity
        
        # Create default channels
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
                self.stdout.write(self.style.SUCCESS(f"Created channel: {channel.name}"))
        
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
                self.stdout.write(self.style.SUCCESS(f"Created amenity: {amenity.name}"))
        
        self.stdout.write(self.style.SUCCESS("Initial data loaded successfully!"))
EOF

echo "Running init_data command..."
python manage.py init_data

echo "Build completed successfully!"