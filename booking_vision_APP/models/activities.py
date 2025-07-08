"""
Activity tracking models
"""
from django.db import models
from django.conf import settings
from django.utils import timezone


class Activity(models.Model):
    """Track all user activities"""
    ACTIVITY_TYPES = [
        ('booking_created', 'New Booking'),
        ('booking_cancelled', 'Booking Cancelled'),
        ('booking_modified', 'Booking Modified'),
        ('guest_message', 'Guest Message'),
        ('payment_received', 'Payment Received'),
        ('property_added', 'Property Added'),
        ('property_updated', 'Property Updated'),
        ('channel_connected', 'Channel Connected'),
        ('maintenance_alert', 'Maintenance Alert'),
        ('price_changed', 'Price Changed'),
        ('review_received', 'Review Received'),
        ('sync_completed', 'Sync Completed'),
        ('ai_recommendation', 'AI Recommendation'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='activities')  # Fixed
    activity_type = models.CharField(max_length=50, choices=ACTIVITY_TYPES)
    title = models.CharField(max_length=200)
    description = models.TextField()

    # Related objects
    property = models.ForeignKey('booking_vision_APP.Property', on_delete=models.CASCADE, null=True, blank=True)
    booking = models.ForeignKey('booking_vision_APP.Booking', on_delete=models.CASCADE, null=True, blank=True)

    # Metadata
    data = models.JSONField(default=dict, blank=True)
    icon = models.CharField(max_length=50, default='bell')
    color = models.CharField(max_length=20, default='primary')

    # Status
    is_read = models.BooleanField(default=False)
    is_important = models.BooleanField(default=False)

    created_at = models.DateTimeField(default=timezone.now)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['user', 'is_read']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.title}"

    def mark_as_read(self):
        """Mark activity as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save()


class ActivityPreference(models.Model):
    """User preferences for activity notifications"""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='activity_preferences')  # Fixed

    # Notification preferences
    show_popup = models.BooleanField(default=True)
    popup_duration = models.IntegerField(default=5000)  # milliseconds
    play_sound = models.BooleanField(default=True)

    # Filter preferences
    show_bookings = models.BooleanField(default=True)
    show_messages = models.BooleanField(default=True)
    show_payments = models.BooleanField(default=True)
    show_maintenance = models.BooleanField(default=True)
    show_ai = models.BooleanField(default=True)

    # Email preferences
    email_daily_summary = models.BooleanField(default=False)
    email_important_only = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)