"""
Payment models for financial tracking.
"""
from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal


class Payment(models.Model):
    """Payment tracking model"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
        ('cancelled', 'Cancelled'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('credit_card', 'Credit Card'),
        ('debit_card', 'Debit Card'),
        ('bank_transfer', 'Bank Transfer'),
        ('paypal', 'PayPal'),
        ('stripe', 'Stripe'),
        ('cash', 'Cash'),
        ('other', 'Other'),
    ]

    booking = models.ForeignKey('booking_vision_APP.Booking', on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    # Transaction details
    transaction_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    payment_date = models.DateTimeField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)

    # Additional info
    description = models.TextField(blank=True)
    currency = models.CharField(max_length=3, default='USD')
    processing_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Payment {self.id} - {self.booking.rental_property.name if self.booking else 'No Booking'} - {self.amount}"

    @property
    def net_amount(self):
        """Amount after fees"""
        return self.amount - self.processing_fee


class Payout(models.Model):
    """Owner payouts"""
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payouts')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')

    # Payout details
    payout_date = models.DateField()
    payment_method = models.CharField(max_length=50)
    account_details = models.CharField(max_length=200, blank=True)  # Encrypted in production

    # Related payments
    payments = models.ManyToManyField(Payment, related_name='payouts')

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Payout {self.id} - {self.owner.username} - {self.amount}"