"""
Admin configuration for Booking Vision models.
"""
from django.contrib import admin
from .models import (
    UserProfile, Property, PropertyImage, PropertyAmenity,
    Booking, Channel, ChannelConnection, Payment, Payout,
    Notification, NotificationPreference, Activity,
    AIInsight, PredictiveModel, BusinessMetric, Review
)

from django.utils import timezone

# Register models with basic admin
admin.site.register(Property)
admin.site.register(Amenity)
admin.site.register(Booking)
admin.site.register(Guest)
admin.site.register(Channel)
admin.site.register(MaintenanceTask)
admin.site.register(UserProfile)

# Customize admin site header
admin.site.site_header = "Booking Vision Admin"
admin.site.site_title = "Booking Vision"
admin.site.index_title = "Welcome to Booking Vision Administration"


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = [
        'guest_name',
        'property',
        'platform',
        'rating_display',
        'normalized_rating',
        'sentiment',
        'review_date',
        'is_verified'
    ]
    list_filter = [
        'platform',
        'rating_scale',
        'sentiment',
        'is_verified',
        'is_public',
        'review_date'
    ]
    search_fields = [
        'guest_name',
        'guest_email',
        'title',
        'content',
        'property__name'
    ]
    readonly_fields = ['normalized_rating', 'sentiment_score']

    fieldsets = (
        ('Basic Information', {
            'fields': ('booking', 'property', 'guest_name', 'guest_email')
        }),
        ('Rating & Platform', {
            'fields': ('platform', 'rating_scale', 'raw_rating', 'normalized_rating')
        }),
        ('Review Content', {
            'fields': ('title', 'content', 'language', 'review_date')
        }),
        ('Analysis', {
            'fields': ('sentiment', 'sentiment_score'),
            'classes': ('collapse',)
        }),
        ('Detailed Ratings', {
            'fields': (
                'cleanliness_rating',
                'communication_rating',
                'location_rating',
                'value_rating',
                'amenities_rating'
            ),
            'classes': ('collapse',)
        }),
        ('Response', {
            'fields': ('response_text', 'response_date', 'responded_by'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': (
                'platform_review_id',
                'is_verified',
                'is_public',
                'flagged',
                'flag_reason'
            ),
            'classes': ('collapse',)
        }),
    )

    def rating_display(self, obj):
        return obj.rating_display

    rating_display.short_description = 'Rating'

    def save_model(self, request, obj, form, change):
        if obj.response_text and not obj.responded_by:
            obj.responded_by = request.user
            if not obj.response_date:
                obj.response_date = timezone.now()
        super().save_model(request, obj, form, change)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = [
        'user',
        'title',
        'notification_type',
        'priority',
        'status',
        'created_at',
        'read_at'
    ]
    list_filter = [
        'notification_type',
        'priority',
        'status',
        'created_at',
        'property'
    ]
    search_fields = [
        'user__username',
        'title',
        'message',
        'property__name'
    ]
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'title', 'message', 'notification_type', 'priority', 'status')
        }),
        ('Related Objects', {
            'fields': ('property', 'booking'),
            'classes': ('collapse',)
        }),
        ('Actions', {
            'fields': ('action_url', 'action_text'),
            'classes': ('collapse',)
        }),
        ('Delivery', {
            'fields': ('email_sent', 'email_sent_at', 'push_sent', 'push_sent_at'),
            'classes': ('collapse',)
        }),
        ('Scheduling', {
            'fields': ('scheduled_for', 'expires_at'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'read_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = [
        'user',
        'enabled',
        'booking_notifications',
        'payment_notifications',
        'review_notifications',
        'quiet_hours_enabled'
    ]
    list_filter = [
        'enabled',
        'booking_notifications',
        'payment_notifications',
        'review_notifications',
        'digest_enabled'
    ]
    search_fields = ['user__username']