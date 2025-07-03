"""
AI-related models for the booking vision application.
This file defines models for AI features and machine learning data.
"""
from django.db import models
from django.contrib.auth.models import User
from .properties import Property


class PricingRule(models.Model):
    """Model for dynamic pricing rules"""
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='pricing_rules')
    name = models.CharField(max_length=100)

    # Rule conditions
    min_days_ahead = models.IntegerField(default=0)
    max_days_ahead = models.IntegerField(default=365)
    min_stay_length = models.IntegerField(default=1)
    max_stay_length = models.IntegerField(default=30)

    # Pricing adjustments
    base_multiplier = models.DecimalField(max_digits=5, decimal_places=2, default=1.0)
    weekend_multiplier = models.DecimalField(max_digits=5, decimal_places=2, default=1.0)
    holiday_multiplier = models.DecimalField(max_digits=5, decimal_places=2, default=1.0)

    # Occupancy-based pricing
    high_demand_threshold = models.DecimalField(max_digits=5, decimal_places=2, default=0.8)
    high_demand_multiplier = models.DecimalField(max_digits=5, decimal_places=2, default=1.2)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.property.name} - {self.name}"


class MaintenanceTask(models.Model):
    """Model for maintenance tasks and predictions"""
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='maintenance_tasks')
    title = models.CharField(max_length=200)
    description = models.TextField()
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    # AI prediction fields
    predicted_by_ai = models.BooleanField(default=False)
    prediction_confidence = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    predicted_failure_date = models.DateField(null=True, blank=True)

    # Scheduling
    scheduled_date = models.DateField(null=True, blank=True)
    estimated_duration = models.IntegerField(help_text="Duration in hours", null=True, blank=True)
    estimated_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # Completion
    completed_date = models.DateField(null=True, blank=True)
    actual_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-priority', '-created_at']

    def __str__(self):
        return f"{self.property.name} - {self.title}"


class GuestPreference(models.Model):
    """Model for storing guest preferences and AI insights"""
    guest = models.OneToOneField('bookings.Guest', on_delete=models.CASCADE, related_name='ai_preferences')

    # Preference categories
    room_temperature = models.IntegerField(null=True, blank=True)
    preferred_check_in_time = models.TimeField(null=True, blank=True)
    preferred_check_out_time = models.TimeField(null=True, blank=True)

    # Activity preferences
    interests = models.JSONField(default=list, blank=True)
    dietary_restrictions = models.JSONField(default=list, blank=True)

    # AI-generated insights
    guest_type = models.CharField(max_length=50, blank=True)  # business, leisure, family, etc.
    spending_pattern = models.CharField(max_length=50, blank=True)
    communication_preference = models.CharField(max_length=50, blank=True)

    # Satisfaction tracking
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    loyalty_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Preferences for {self.guest.first_name} {self.guest.last_name}"


class MarketData(models.Model):
    """Model for storing market intelligence data"""
    location = models.CharField(max_length=200)
    date = models.DateField()

    # Market metrics
    average_daily_rate = models.DecimalField(max_digits=10, decimal_places=2)
    occupancy_rate = models.DecimalField(max_digits=5, decimal_places=2)
    revenue_per_available_room = models.DecimalField(max_digits=10, decimal_places=2)

    # Demand indicators
    search_volume = models.IntegerField(default=0)
    booking_lead_time = models.IntegerField(default=0)

    # Events and seasonality
    events = models.JSONField(default=list, blank=True)
    season_factor = models.DecimalField(max_digits=5, decimal_places=2, default=1.0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['location', 'date']
        ordering = ['-date']

    def __str__(self):
        return f"{self.location} - {self.date}"