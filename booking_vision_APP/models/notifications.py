from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.mail import send_mail
from django.template.loader import render_to_string
from .properties import Property
from .bookings import Booking

class Notification(models.Model):
    """
    Automated tasks/messages sent to guests (external notifications)
    """
    NOTIFICATION_TYPES = [
        ('booking_confirmation', 'Booking Confirmation'),
        ('pre_arrival', 'Pre-Arrival Instructions'),
        ('check_in_reminder', 'Check-In Reminder'),
        ('check_in_instructions', 'Check-In Instructions'),
        ('welcome_message', 'Welcome Message'),
        ('mid_stay_check', 'Mid-Stay Check-In'),
        ('check_out_reminder', 'Check-Out Reminder'),
        ('check_out_instructions', 'Check-Out Instructions'),
        ('post_stay_followup', 'Post-Stay Follow-Up'),
        ('review_request', 'Review Request'),
        ('thank_you_message', 'Thank You Message'),
        ('payment_reminder', 'Payment Reminder'),
        ('payment_confirmation', 'Payment Confirmation'),
        ('cancellation_notice', 'Cancellation Notice'),
        ('booking_modification', 'Booking Modification'),
        ('emergency_contact', 'Emergency Contact'),
        ('local_recommendations', 'Local Recommendations'),
        ('weather_alert', 'Weather Alert'),
        ('maintenance_notice', 'Maintenance Notice'),
        ('amenity_instructions', 'Amenity Instructions'),
        ('custom_message', 'Custom Message'),
    ]
    
    DELIVERY_METHODS = [
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('whatsapp', 'WhatsApp'),
        ('push', 'Push Notification'),
        ('in_app', 'In-App Message'),
    ]
    
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    TRIGGER_TYPES = [
        ('manual', 'Manual'),
        ('time_based', 'Time-Based'),
        ('event_based', 'Event-Based'),
        ('condition_based', 'Condition-Based'),
    ]
    
    # Core fields
    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name='guest_notifications'
    )
    
    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name='guest_notifications'
    )
    
    # Recipient information
    guest_name = models.CharField(max_length=200)
    guest_email = models.EmailField()
    guest_phone = models.CharField(max_length=20, blank=True)
    
    # Message content
    notification_type = models.CharField(
        max_length=30,
        choices=NOTIFICATION_TYPES
    )
    
    subject = models.CharField(max_length=300)
    message = models.TextField()
    html_message = models.TextField(blank=True)
    
    # Delivery settings
    delivery_method = models.CharField(
        max_length=20,
        choices=DELIVERY_METHODS,
        default='email'
    )
    
    # Scheduling
    trigger_type = models.CharField(
        max_length=20,
        choices=TRIGGER_TYPES,
        default='manual'
    )
    
    scheduled_for = models.DateTimeField()
    trigger_offset_hours = models.IntegerField(
        default=0,
        help_text="Hours relative to booking event (negative for before, positive for after)"
    )
    
    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='scheduled'
    )
    
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    failure_reason = models.TextField(blank=True)
    
    # Tracking
    opened_at = models.DateTimeField(null=True, blank=True)
    clicked_at = models.DateTimeField(null=True, blank=True)
    replied_at = models.DateTimeField(null=True, blank=True)
    
    # Automation settings
    is_automated = models.BooleanField(default=True)
    auto_retry = models.BooleanField(default=True)
    max_retries = models.IntegerField(default=3)
    retry_count = models.IntegerField(default=0)
    
    # Template and personalization
    template_name = models.CharField(max_length=100, blank=True)
    personalization_data = models.JSONField(default=dict, blank=True)
    
    # Metadata
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_guest_notifications'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-scheduled_for']
        indexes = [
            models.Index(fields=['booking', 'status']),
            models.Index(fields=['property', 'status']),
            models.Index(fields=['scheduled_for', 'status']),
            models.Index(fields=['notification_type']),
        ]
    
    def __str__(self):
        return f"{self.notification_type} - {self.guest_name} - {self.booking.property.name}"
    
    def send_notification(self):
        """Send the notification to the guest"""
        try:
            if self.delivery_method == 'email':
                self._send_email()
            elif self.delivery_method == 'sms':
                self._send_sms()
            elif self.delivery_method == 'whatsapp':
                self._send_whatsapp()
            
            self.status = 'sent'
            self.sent_at = timezone.now()
            self.save()
            return True
            
        except Exception as e:
            self.status = 'failed'
            self.failed_at = timezone.now()
            self.failure_reason = str(e)
            self.save()
            return False
    
    def _send_email(self):
        """Send email notification"""
        send_mail(
            subject=self.subject,
            message=self.message,
            html_message=self.html_message or None,
            from_email=None,  # Use default
            recipient_list=[self.guest_email],
            fail_silently=False,
        )
    
    def _send_sms(self):
        """Send SMS notification"""
        # Implement SMS sending logic
        pass
    
    def _send_whatsapp(self):
        """Send WhatsApp notification"""
        # Implement WhatsApp sending logic
        pass
    
    def mark_as_opened(self):
        """Mark notification as opened by guest"""
        if not self.opened_at:
            self.opened_at = timezone.now()
            self.save(update_fields=['opened_at'])
    
    def mark_as_clicked(self):
        """Mark notification as clicked by guest"""
        if not self.clicked_at:
            self.clicked_at = timezone.now()
            self.save(update_fields=['clicked_at'])
    
    @classmethod
    def create_automated_notifications(cls, booking):
        """Create all automated notifications for a booking"""
        notifications = []
        
        # Define automated notification schedule
        notification_schedule = [
            {
                'type': 'booking_confirmation',
                'offset_hours': 0,
                'subject': 'Booking Confirmation - {property_name}',
                'template': 'booking_confirmation',
            },
            {
                'type': 'pre_arrival',
                'offset_hours': -24,  # 24 hours before check-in
                'subject': 'Pre-Arrival Information - {property_name}',
                'template': 'pre_arrival',
            },
            {
                'type': 'check_in_instructions',
                'offset_hours': -2,  # 2 hours before check-in
                'subject': 'Check-In Instructions - {property_name}',
                'template': 'check_in_instructions',
            },
            {
                'type': 'welcome_message',
                'offset_hours': 2,  # 2 hours after check-in
                'subject': 'Welcome to {property_name}!',
                'template': 'welcome_message',
            },
            {
                'type': 'mid_stay_check',
                'offset_hours': 24,  # 24 hours after check-in
                'subject': 'How is your stay at {property_name}?',
                'template': 'mid_stay_check',
            },
            {
                'type': 'check_out_reminder',
                'offset_hours': -2,  # 2 hours before check-out (relative to check-out)
                'subject': 'Check-Out Reminder - {property_name}',
                'template': 'check_out_reminder',
            },
            {
                'type': 'review_request',
                'offset_hours': 24,  # 24 hours after check-out
                'subject': 'How was your stay at {property_name}?',
                'template': 'review_request',
            },
        ]
        
        for schedule_item in notification_schedule:
            # Calculate scheduled time
            if schedule_item['type'] in ['check_out_reminder']:
                base_time = booking.check_out
            else:
                base_time = booking.check_in
            
            scheduled_time = base_time + timezone.timedelta(hours=schedule_item['offset_hours'])
            
            # Create notification
            notification = cls.objects.create(
                booking=booking,
                property=booking.property,
                guest_name=booking.guest_name,
                guest_email=booking.guest_email,
                guest_phone=booking.guest_phone or '',
                notification_type=schedule_item['type'],
                subject=schedule_item['subject'].format(property_name=booking.property.name),
                message=f"Automated {schedule_item['type']} message",
                scheduled_for=scheduled_time,
                trigger_offset_hours=schedule_item['offset_hours'],
                trigger_type='time_based',
                template_name=schedule_item['template'],
                personalization_data={
                    'guest_name': booking.guest_name,
                    'property_name': booking.property.name,
                    'check_in': booking.check_in.isoformat(),
                    'check_out': booking.check_out.isoformat(),
                }
            )
            notifications.append(notification)
        
        return notifications


class NotificationTemplate(models.Model):
    """Templates for guest notifications"""
    
    TEMPLATE_TYPES = [
        ('booking_confirmation', 'Booking Confirmation'),
        ('pre_arrival', 'Pre-Arrival Instructions'),
        ('check_in_instructions', 'Check-In Instructions'),
        ('welcome_message', 'Welcome Message'),
        ('mid_stay_check', 'Mid-Stay Check-In'),
        ('check_out_reminder', 'Check-Out Reminder'),
        ('review_request', 'Review Request'),
        ('custom', 'Custom Template'),
    ]
    
    name = models.CharField(max_length=200)
    template_type = models.CharField(max_length=30, choices=TEMPLATE_TYPES)
    
    # Content
    subject_template = models.CharField(max_length=300)
    message_template = models.TextField()
    html_template = models.TextField(blank=True)
    
    # Settings
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    
    # Ownership
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notification_templates'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['template_type', 'name']
        unique_together = ['template_type', 'is_default', 'created_by']
    
    def __str__(self):
        return f"{self.name} - {self.template_type}"
    
    def render(self, context):
        """Render template with context data"""
        from django.template import Context, Template
        
        subject = Template(self.subject_template).render(Context(context))
        message = Template(self.message_template).render(Context(context))
        html_message = Template(self.html_template).render(Context(context)) if self.html_template else ''
        
        return {
            'subject': subject,
            'message': message,
            'html_message': html_message,
        }


class NotificationPreference(models.Model):
    """Host preferences for guest notifications"""
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='guest_notification_preferences'
    )
    
    # General settings
    auto_notifications_enabled = models.BooleanField(default=True)
    
    # Notification type preferences
    booking_confirmation_enabled = models.BooleanField(default=True)
    pre_arrival_enabled = models.BooleanField(default=True)
    check_in_instructions_enabled = models.BooleanField(default=True)
    welcome_message_enabled = models.BooleanField(default=True)
    mid_stay_check_enabled = models.BooleanField(default=True)
    check_out_reminder_enabled = models.BooleanField(default=True)
    review_request_enabled = models.BooleanField(default=True)
    
    # Timing preferences
    pre_arrival_hours = models.IntegerField(default=24)
    check_in_reminder_hours = models.IntegerField(default=2)
    welcome_delay_hours = models.IntegerField(default=2)
    mid_stay_delay_hours = models.IntegerField(default=24)
    check_out_reminder_hours = models.IntegerField(default=2)
    review_request_delay_hours = models.IntegerField(default=24)
    
    # Personalization
    sender_name = models.CharField(max_length=100, blank=True)
    sender_email = models.EmailField(blank=True)
    signature = models.TextField(blank=True)
    
    # Branding
    include_property_logo = models.BooleanField(default=True)
    brand_color = models.CharField(max_length=7, default='#667eea')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'guest_notification_preferences'
    
    def __str__(self):
        return f"{self.user.username} - Guest Notification Preferences"
    
    @classmethod
    def get_or_create_for_user(cls, user):
        """Get or create notification preferences for user"""
        preferences, created = cls.objects.get_or_create(user=user)
        return preferences