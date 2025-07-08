"""
User-related models for the booking vision application.
This file defines user profiles and extended user functionality.
"""
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.validators import MinValueValidator
from decimal import Decimal


class CustomUser(AbstractUser):
    """Custom user model with user types"""
    USER_TYPE_CHOICES = [
        ('admin', 'Admin/Bookmaker'),
        ('host', 'Host'),
        ('guest', 'Guest'),
    ]

    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES, default='guest')
    is_email_verified = models.BooleanField(default=False)
    email_verification_token = models.CharField(max_length=255, blank=True)

    # Payment status for hosts
    is_paid_host = models.BooleanField(default=False)
    subscription_end_date = models.DateTimeField(null=True, blank=True)
    stripe_customer_id = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = 'auth_user'
        swappable = 'AUTH_USER_MODEL'

    def is_admin_or_bookmaker(self):
        return self.user_type == 'admin'

    def is_host(self):
        return self.user_type == 'host'

    def is_guest_user(self):
        return self.user_type == 'guest'

    def has_active_subscription(self):
        """Check if host has active subscription"""
        if not self.is_host():
            return True  # Admins have full access, guests have limited access

        if not self.is_paid_host:
            return False

        from django.utils import timezone
        if self.subscription_end_date:
            return self.subscription_end_date > timezone.now()
        return False


class UserProfile(models.Model):
    """Extended user profile"""
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='profile')

    # Common fields
    phone = models.CharField(max_length=20, blank=True)
    address = models.CharField(max_length=300, blank=True)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True)

    # Host-specific fields
    company_name = models.CharField(max_length=200, blank=True)
    tax_id = models.CharField(max_length=100, blank=True)

    # Guest-specific fields
    date_of_birth = models.DateField(null=True, blank=True)
    id_verification_status = models.CharField(max_length=20, default='unverified')

    # AI preferences (for hosts)
    ai_pricing_enabled = models.BooleanField(default=False)
    ai_maintenance_enabled = models.BooleanField(default=False)
    ai_guest_enabled = models.BooleanField(default=False)
    ai_analytics_enabled = models.BooleanField(default=False)

    # Subscription information (for hosts)
    subscription_plan = models.CharField(max_length=50, default='free')
    subscription_active = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} Profile"


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create user profile when user is created"""
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save user profile when user is saved"""
    if hasattr(instance, 'profile'):
        instance.profile.save()