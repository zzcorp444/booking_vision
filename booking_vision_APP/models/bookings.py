"""
Booking models for the booking vision application.
This file defines all booking-related database models.
"""
from django.db import models
from django.contrib.auth.models import User

class Guest(models.Model):
    """Model representing a guest"""
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, blank=True)

    # Guest experience AI fields
    preferences = models.JSONField(default=dict, blank=True)
    satisfaction_score = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

class Booking(models.Model):
    """Model representing a booking"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('checked_in', 'Checked In'),
        ('checked_out', 'Checked Out'),
        ('cancelled', 'Cancelled'),
    ]

    # Foreign Keys - use app label booking_vision_APP
    rental_property = models.ForeignKey('booking_vision_APP.Property', on_delete=models.CASCADE, related_name='bookings')
    guest = models.ForeignKey(Guest, on_delete=models.CASCADE, related_name='bookings')
    channel = models.ForeignKey('booking_vision_APP.Channel', on_delete=models.CASCADE, related_name='bookings')

    # Booking details
    external_booking_id = models.CharField(max_length=100, blank=True)
    check_in_date = models.DateField()
    check_out_date = models.DateField()
    num_guests = models.IntegerField()

    # Pricing
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    cleaning_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    service_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)

    # Status and timestamps
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # AI-related fields
    ai_generated_instructions = models.TextField(blank=True)
    sentiment_score = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Booking {self.id} - {self.rental_property.name if self.rental_property else 'Unknown Property'}"

    @property
    def nights(self):
        """Calculate number of nights"""
        if self.check_in_date and self.check_out_date:
            return (self.check_out_date - self.check_in_date).days
        return 0

    @property
    def property(self):
        """Backward compatibility property"""
        return self.rental_property

class BookingMessage(models.Model):
    """Model for booking-related messages"""
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='messages')
    sender = models.CharField(max_length=20, choices=[('guest', 'Guest'), ('host', 'Host')])
    message = models.TextField()
    is_automated = models.BooleanField(default=False)
    sentiment_score = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Message for Booking {self.booking.id}"