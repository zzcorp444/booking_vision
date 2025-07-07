"""
Channel models for the booking vision application.
This file defines all channel integration models.
"""
from django.db import models
from django.contrib.auth.models import User

class Channel(models.Model):
    """Model representing a booking channel (OTA)"""
    name = models.CharField(max_length=100)
    api_endpoint = models.URLField(blank=True)
    logo = models.ImageField(upload_to='channel_logos/', blank=True)
    is_active = models.BooleanField(default=True)

    # API configuration
    requires_api_key = models.BooleanField(default=True)
    supports_webhooks = models.BooleanField(default=False)
    rate_limit_per_minute = models.IntegerField(default=60)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class ChannelConnection(models.Model):
    """Model for user-specific channel connections"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    channel = models.ForeignKey(Channel, on_delete=models.CASCADE)

    # Authentication details
    api_key = models.CharField(max_length=255, blank=True)
    api_secret = models.CharField(max_length=255, blank=True)
    access_token = models.TextField(blank=True)
    refresh_token = models.TextField(blank=True)

    # No-API sync fields
    ical_url = models.URLField(blank=True, help_text="iCal feed URL")
    email_sync_enabled = models.BooleanField(default=False)
    scraping_enabled = models.BooleanField(default=False)
    extension_token = models.CharField(max_length=255, blank=True)

    # Credentials for scraping (encrypted in production)
    login_email = models.EmailField(blank=True)
    login_password_encrypted = models.CharField(max_length=255, blank=True)

    # Sync preferences
    preferred_sync_method = models.CharField(
        max_length=20,
        choices=[
            ('ical', 'iCal Feed'),
            ('email', 'Email Parsing'),
            ('scraping', 'Web Scraping'),
            ('extension', 'Browser Extension'),
            ('mobile_api', 'Mobile API'),
        ],
        default='ical'
    )

    last_sync_method = models.CharField(max_length=20, blank=True)
    last_sync_error = models.TextField(blank=True)

    # Connection status
    is_connected = models.BooleanField(default=False)
    last_sync = models.DateTimeField(null=True, blank=True)
    sync_errors = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'channel']

    def __str__(self):
        return f"{self.user.username} - {self.channel.name}"

class PropertyChannel(models.Model):
    """Model linking properties to channels"""
    rental_property = models.ForeignKey('booking_vision_APP.Property', on_delete=models.CASCADE)
    channel = models.ForeignKey(Channel, on_delete=models.CASCADE)
    channel_connection = models.ForeignKey(ChannelConnection, on_delete=models.CASCADE)

    # Channel-specific property details
    external_property_id = models.CharField(max_length=100)
    channel_url = models.URLField(blank=True)

    # Sync settings
    sync_availability = models.BooleanField(default=True)
    sync_rates = models.BooleanField(default=True)
    sync_content = models.BooleanField(default=True)

    # Status
    is_active = models.BooleanField(default=True)
    last_sync = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['rental_property', 'channel']

    def __str__(self):
        return f"{self.rental_property.name if self.rental_property else 'Unknown'} - {self.channel.name}"

    @property
    def property(self):
        """Backward compatibility property"""
        return self.rental_property