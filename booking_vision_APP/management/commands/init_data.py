"""
Management command to initialize data for Booking Vision.
This command creates the superuser and loads initial data.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db import transaction
import os


class Command(BaseCommand):
    help = 'Initialize data for Booking Vision'

    def handle(self, *args, **kwargs):
        self.stdout.write('Initializing Booking Vision data...')

        try:
            with transaction.atomic():
                # Create superuser
                self.create_superuser()

                # Load initial data
                self.load_initial_data()

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error during initialization: {str(e)}"))

    def create_superuser(self):
        """Create superuser if it doesn't exist"""
        username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'bv_admin')
        email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'zz.corp.hd@gmail.com')
        password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'Alibaba2021!')

        try:
            if not User.objects.filter(username=username).exists():
                User.objects.create_superuser(username=username, email=email, password=password)
                self.stdout.write(self.style.SUCCESS(f"Superuser '{username}' created successfully!"))
            else:
                self.stdout.write(self.style.WARNING(f"Superuser '{username}' already exists."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error creating superuser: {str(e)}"))

    def load_initial_data(self):
        """Load initial channels and amenities"""
        try:
            # Import models here to ensure they're available
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
                else:
                    self.stdout.write(self.style.WARNING(f"Channel already exists: {channel.name}"))

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
                {'name': 'Gym', 'category': 'Fitness', 'icon': 'fas fa-dumbbell'},
                {'name': 'Heating', 'category': 'Climate', 'icon': 'fas fa-temperature-high'},
            ]

            for amenity_data in amenities:
                amenity, created = Amenity.objects.get_or_create(
                    name=amenity_data['name'],
                    defaults=amenity_data
                )
                if created:
                    self.stdout.write(self.style.SUCCESS(f"Created amenity: {amenity.name}"))
                else:
                    self.stdout.write(self.style.WARNING(f"Amenity already exists: {amenity.name}"))

            self.stdout.write(self.style.SUCCESS("Initial data loaded successfully!"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error loading initial data: {str(e)}"))