"""
Admin configuration for Booking Vision models.
"""
from django.contrib import admin
from .models.properties import Property, Amenity
from .models.bookings import Booking, Guest
from .models.channels import Channel
from .models.ai_models import MaintenanceTask
from .models.users import UserProfile

# Register models with basic admin
admin.site.register(Property)
admin.site.register(Amenity)
admin.site.register(Booking)
admin.site.register(Guest)
admin.site.register(Channel)
admin.site.register(MaintenanceTask)
admin.site.register(UserProfile)

# Customize admin site header
admin.site.site_header = "Booking Vision Admin"
admin.site.site_title = "Booking Vision"
admin.site.index_title = "Welcome to Booking Vision Administration"