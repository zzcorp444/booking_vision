"""
Admin configuration for Booking Vision models.
"""
from django.contrib import admin
from .models.properties import Property, PropertyImage, Amenity, PropertyAmenity
from .models.bookings import Booking, Guest, BookingMessage
from .models.channels import Channel, ChannelConnection, PropertyChannel
from .models.ai_models import PricingRule, MaintenanceTask, GuestPreference, MarketData
from .models.users import UserProfile

# Property Admin
@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ['name', 'owner', 'property_type', 'city', 'base_price', 'is_active']
    list_filter = ['property_type', 'city', 'is_active']
    search_fields = ['name', 'city', 'address']

@admin.register(Amenity)
class AmenityAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'icon']
    list_filter = ['category']

# Booking Admin
@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['id', 'property', 'guest', 'check_in_date', 'check_out_date', 'status', 'total_price']
    list_filter = ['status', 'channel']
    search_fields = ['guest__first_name', 'guest__last_name', 'property__name']

@admin.register(Guest)
class GuestAdmin(admin.ModelAdmin):
    list_display = ['first_name', 'last_name', 'email', 'country']
    search_fields = ['first_name', 'last_name', 'email']

# Channel Admin
@admin.register(Channel)
class ChannelAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'requires_api_key']
    list_filter = ['is_active', 'requires_api_key']

# AI Models Admin
@admin.register(MaintenanceTask)
class MaintenanceTaskAdmin(admin.ModelAdmin):
    list_display = ['title', 'property', 'priority', 'status', 'predicted_by_ai']
    list_filter = ['priority', 'status', 'predicted_by_ai']

# User Profile Admin
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'company_name', 'subscription_plan', 'subscription_active']
    list_filter = ['subscription_plan', 'subscription_active']
