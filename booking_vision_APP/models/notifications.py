"""
Notification models for automated actions and alerts.
"""
from django.db import models
from django.conf import settings


class NotificationRule(models.Model):
    """Automated notification rules"""
    TRIGGER_CHOICES = [
        ('booking_created', 'New Booking'),
        ('check_in_reminder', 'Check-in Reminder'),
        ('check_out_reminder', 'Check-out Reminder'),
        ('review_request', 'Review Request'),
        ('payment_reminder', 'Payment Reminder'),
        ('maintenance_due', 'Maintenance Due'),
        ('low_occupancy', 'Low Occupancy Alert'),
        ('high_demand', 'High Demand Alert'),
    ]

    CHANNEL_CHOICES = [
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('platform', 'Platform Message'),
        ('push', 'Push Notification'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notification_rules')  # Fixed
    name = models.CharField(max_length=200)
    trigger = models.CharField(max_length=50, choices=TRIGGER_CHOICES)
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES)

    # Timing
    days_before = models.IntegerField(default=0, help_text="Days before event (negative for after)")
    time_of_day = models.TimeField(null=True, blank=True)

    # Content
    subject = models.CharField(max_length=200)
    message_template = models.TextField(help_text="Use {guest_name}, {property_name}, {check_in_date}, etc.")

    # Conditions
    properties = models.ManyToManyField('booking_vision_APP.Property', blank=True)
    apply_to_all_properties = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.get_trigger_display()}"


class NotificationLog(models.Model):
    """Log of sent notifications"""
    rule = models.ForeignKey(NotificationRule, on_delete=models.CASCADE, related_name='logs')
    booking = models.ForeignKey('booking_vision_APP.Booking', on_delete=models.CASCADE, null=True, blank=True)
    recipient = models.EmailField()
    channel = models.CharField(max_length=20)
    subject = models.CharField(max_length=200)
    message = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)
    is_successful = models.BooleanField(default=True)
    error_message = models.TextField(blank=True)

    def __str__(self):
        return f"Notification to {self.recipient} at {self.sent_at}"