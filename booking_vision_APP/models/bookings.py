"""
Booking models for the booking vision application.
This file defines all booking-related database models.
"""
from django.db import models
from django.contrib.auth.models import User


# In booking_vision_APP/models/bookings.py

class Guest(models.Model):
    """Model representing a guest"""
    # Keep your existing fields
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, blank=True)

    # Guest experience AI fields
    preferences = models.JSONField(default=dict, blank=True)
    satisfaction_score = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Optional: link to user account if guest creates one
    user = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='guest_profile'
    )

    # Add these for better tracking
    total_bookings = models.IntegerField(default=0)
    total_spent = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    last_booking_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['last_name', 'first_name']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['first_name', 'last_name']),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    def get_full_name(self):
        """Get guest's full name"""
        return f"{self.first_name} {self.last_name}"

    def link_to_user(self, user):
        """Link this guest profile to a user account"""
        self.user = user
        self.save(update_fields=['user'])

        # Update user profile with guest info if needed
        if hasattr(user, 'userprofile'):
            profile = user.userprofile
            if not profile.phone and self.phone:
                profile.phone = self.phone
            if not profile.country and self.country:
                profile.country = self.country
            profile.save()

    def update_booking_stats(self):
        """Update booking statistics for the guest"""
        from django.db.models import Sum

        guest_bookings = self.bookings.all()  # Using related_name from Booking model
        self.total_bookings = guest_bookings.count()

        total_amount = guest_bookings.aggregate(
            total=Sum('total_amount')
        )['total'] or 0
        self.total_spent = total_amount

        last_booking = guest_bookings.order_by('-check_out').first()
        if last_booking:
            self.last_booking_date = last_booking.check_out

        self.save(update_fields=['total_bookings', 'total_spent', 'last_booking_date'])


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
    guest = models.ForeignKey(
        Guest,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bookings'
    )
    # Keep these existing fields for backward compatibility
    guest_name = models.CharField(max_length=200)
    guest_email = models.EmailField()
    guest_phone = models.CharField(max_length=20, blank=True)

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

    def save(self, *args, **kwargs):
        # Auto-create or link guest if not provided
        if not self.guest and self.guest_email:
            # Try to find existing guest
            guest_lookup = Guest.objects.filter(email=self.guest_email).first()

            if not guest_lookup:
                # Create new guest
                first_name = self.guest_name.split()[0] if self.guest_name else ''
                last_name = ' '.join(self.guest_name.split()[1:]) if self.guest_name and len(
                    self.guest_name.split()) > 1 else ''

                guest_lookup = Guest.objects.create(
                    first_name=first_name,
                    last_name=last_name,
                    email=self.guest_email,
                    phone=self.guest_phone or ''
                )

            self.guest = guest_lookup

        super().save(*args, **kwargs)

        # Update guest statistics
        if self.guest:
            self.guest.update_booking_stats()


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