from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from .properties import Property
from .bookings import Booking
from .payments import Payment

class Activity(models.Model):
    """
    Internal activity feed/popups for hosts within the website
    """
    ACTIVITY_TYPES = [
        ('booking_created', 'Booking Created'),
        ('booking_updated', 'Booking Updated'),
        ('booking_cancelled', 'Booking Cancelled'),
        ('payment_received', 'Payment Received'),
        ('payment_failed', 'Payment Failed'),
        ('review_received', 'Review Received'),
        ('review_responded', 'Review Responded'),
        ('property_updated', 'Property Updated'),
        ('property_created', 'Property Created'),
        ('channel_connected', 'Channel Connected'),
        ('channel_disconnected', 'Channel Disconnected'),
        ('calendar_synced', 'Calendar Synced'),
        ('price_updated', 'Price Updated'),
        ('availability_updated', 'Availability Updated'),
        ('maintenance_scheduled', 'Maintenance Scheduled'),
        ('maintenance_completed', 'Maintenance Completed'),
        ('guest_message', 'Guest Message'),
        ('system_update', 'System Update'),
        ('revenue_milestone', 'Revenue Milestone'),
        ('occupancy_alert', 'Occupancy Alert'),
        ('performance_insight', 'Performance Insight'),
        ('recommendation', 'AI Recommendation'),
        ('security_alert', 'Security Alert'),
        ('backup_completed', 'Backup Completed'),
        ('integration_sync', 'Integration Sync'),
        ('user_login', 'User Login'),
        ('user_action', 'User Action'),
        ('other', 'Other'),
    ]
    
    PRIORITY_LEVELS = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    STATUS_CHOICES = [
        ('unread', 'Unread'),
        ('read', 'Read'),
        ('dismissed', 'Dismissed'),
        ('archived', 'Archived'),
    ]
    
    # Core fields
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='activities'
    )
    
    activity_type = models.CharField(
        max_length=30,
        choices=ACTIVITY_TYPES
    )
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_LEVELS,
        default='medium'
    )
    
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='unread'
    )
    
    # Related objects (optional)
    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='activities'
    )
    
    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='activities'
    )
    
    payment = models.ForeignKey(
        Payment,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='activities'
    )
    
    # Action settings
    action_url = models.URLField(blank=True, null=True)
    action_text = models.CharField(max_length=100, blank=True)
    is_actionable = models.BooleanField(default=False)
    
    # Display settings
    show_popup = models.BooleanField(default=False)
    show_in_feed = models.BooleanField(default=True)
    auto_dismiss = models.BooleanField(default=False)
    dismiss_after_hours = models.IntegerField(default=24)
    
    # Metadata
    metadata = models.JSONField(default=dict, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    read_at = models.DateTimeField(null=True, blank=True)
    dismissed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['user', 'activity_type']),
            models.Index(fields=['user', 'priority']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.title}"
    
    def mark_as_read(self):
        """Mark activity as read"""
        if self.status == 'unread':
            self.status = 'read'
            self.read_at = timezone.now()
            self.save(update_fields=['status', 'read_at'])
    
    def dismiss(self):
        """Dismiss activity"""
        self.status = 'dismissed'
        self.dismissed_at = timezone.now()
        self.save(update_fields=['status', 'dismissed_at'])
    
    def archive(self):
        """Archive activity"""
        self.status = 'archived'
        self.save(update_fields=['status'])
    
    @property
    def is_read(self):
        return self.status == 'read'
    
    @property
    def is_unread(self):
        return self.status == 'unread'
    
    @property
    def age_in_hours(self):
        """Get age of activity in hours"""
        return (timezone.now() - self.created_at).total_seconds() / 3600
    
    @property
    def should_auto_dismiss(self):
        """Check if activity should be auto-dismissed"""
        if self.auto_dismiss and self.age_in_hours >= self.dismiss_after_hours:
            return True
        return False
    
    @property
    def icon_class(self):
        """Get icon class for activity type"""
        icons = {
            'booking_created': 'fas fa-calendar-plus text-success',
            'booking_updated': 'fas fa-calendar-edit text-warning',
            'booking_cancelled': 'fas fa-calendar-times text-danger',
            'payment_received': 'fas fa-money-bill-wave text-success',
            'payment_failed': 'fas fa-exclamation-triangle text-danger',
            'review_received': 'fas fa-star text-warning',
            'property_updated': 'fas fa-home text-info',
            'maintenance_scheduled': 'fas fa-wrench text-warning',
            'guest_message': 'fas fa-comments text-primary',
            'revenue_milestone': 'fas fa-trophy text-success',
            'occupancy_alert': 'fas fa-bed text-warning',
            'recommendation': 'fas fa-lightbulb text-info',
            'security_alert': 'fas fa-shield-alt text-danger',
            'system_update': 'fas fa-cog text-secondary',
        }
        return icons.get(self.activity_type, 'fas fa-info-circle text-secondary')
    
    @property
    def priority_color(self):
        """Get color for priority level"""
        colors = {
            'low': 'text-muted',
            'medium': 'text-warning',
            'high': 'text-danger',
            'urgent': 'text-danger',
        }
        return colors.get(self.priority, 'text-secondary')
    
    @classmethod
    def create_activity(cls, user, activity_type, title, description, 
                       priority='medium', property=None, booking=None, 
                       payment=None, action_url=None, action_text=None,
                       show_popup=False, metadata=None):
        """Create a new activity"""
        return cls.objects.create(
            user=user,
            activity_type=activity_type,
            title=title,
            description=description,
            priority=priority,
            property=property,
            booking=booking,
            payment=payment,
            action_url=action_url,
            action_text=action_text,
            show_popup=show_popup,
            is_actionable=bool(action_url),
            metadata=metadata or {}
        )
    
    @classmethod
    def get_unread_count(cls, user):
        """Get count of unread activities for user"""
        return cls.objects.filter(user=user, status='unread').count()
    
    @classmethod
    def get_recent_activities(cls, user, limit=20):
        """Get recent activities for user"""
        return cls.objects.filter(
            user=user,
            status__in=['unread', 'read']
        ).select_related('property', 'booking', 'payment')[:limit]
    
    @classmethod
    def cleanup_old_activities(cls, days=30):
        """Clean up old activities"""
        cutoff_date = timezone.now() - timezone.timedelta(days=days)
        old_activities = cls.objects.filter(
            created_at__lt=cutoff_date,
            status__in=['read', 'dismissed']
        )
        count = old_activities.count()
        old_activities.delete()
        return count