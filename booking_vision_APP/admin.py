from django.contrib import admin
from django.utils import timezone
from .models import (
    UserProfile,  # From users.py
    Guest,  # From bookings.py
    Property, PropertyImage, PropertyAmenity, Amenity,  # From properties.py
    Booking,  # From bookings.py
    Channel, ChannelConnection,  # From channels.py
    Payment, Payout,  # From payments.py
    Notification, NotificationTemplate, NotificationPreference,  # From notifications.py
    Activity,  # From activities.py
    PricingRule, MaintenanceTask, GuestPreference, MarketData,  # From ai_models.py
    AIInsight, PredictiveModel, BusinessMetric, ReviewSentiment, CompetitorAnalysis,  # From ai_models.py
    Review  # From reviews.py
)

# User-related admin
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone', 'created_at']
    search_fields = ['user__username', 'user__email', 'phone']

@admin.register(Guest)
class GuestAdmin(admin.ModelAdmin):
    list_display = ['first_name', 'last_name', 'email', 'total_bookings', 'total_spent']
    search_fields = ['first_name', 'last_name', 'email', 'phone']
    list_filter = ['is_verified', 'is_blacklisted', 'language_preference']

# Property-related admin
@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ['name', 'owner', 'property_type', 'bedrooms', 'bathrooms', 'max_guests', 'base_price']
    list_filter = ['property_type', 'bedrooms', 'bathrooms']
    search_fields = ['name', 'description', 'address', 'city', 'country']
    filter_horizontal = ['amenities']

@admin.register(PropertyImage)
class PropertyImageAdmin(admin.ModelAdmin):
    list_display = ['rental_property', 'caption', 'is_primary', 'order']
    list_filter = ['is_primary']
    search_fields = ['rental_property__name', 'caption']

@admin.register(Amenity)
class AmenityAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'is_premium']
    list_filter = ['category', 'is_premium']
    search_fields = ['name', 'description']

# Booking-related admin
@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['property', 'guest_name', 'check_in', 'check_out', 'status', 'total_amount']
    list_filter = ['status', 'check_in', 'check_out']
    search_fields = ['property__name', 'guest_name', 'guest_email']
    date_hierarchy = 'check_in'

# Channel-related admin
@admin.register(Channel)
class ChannelAdmin(admin.ModelAdmin):
    list_display = ['name', 'channel_type', 'is_active']
    list_filter = ['channel_type', 'is_active']

@admin.register(ChannelConnection)
class ChannelConnectionAdmin(admin.ModelAdmin):
    list_display = ['rental_property', 'channel', 'is_active', 'last_sync']
    list_filter = ['is_active', 'channel']
    search_fields = ['rental_property__name']

# Payment-related admin
@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['booking', 'amount', 'payment_method', 'status', 'payment_date']
    list_filter = ['status', 'payment_method', 'payment_date']
    search_fields = ['booking__property__name', 'booking__guest_name']
    date_hierarchy = 'payment_date'

@admin.register(Payout)
class PayoutAdmin(admin.ModelAdmin):
    list_display = ['user', 'amount', 'status', 'payout_date']
    list_filter = ['status', 'payout_method']
    date_hierarchy = 'payout_date'

# Notification-related admin
@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['guest_name', 'notification_type', 'status', 'scheduled_for']
    list_filter = ['notification_type', 'status', 'delivery_method']
    search_fields = ['guest_name', 'guest_email', 'subject']
    date_hierarchy = 'scheduled_for'

@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'template_type', 'is_active', 'is_default']
    list_filter = ['template_type', 'is_active', 'is_default']
    search_fields = ['name', 'subject_template']

@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ['user', 'auto_notifications_enabled']
    search_fields = ['user__username']

# Activity admin
@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ['user', 'activity_type', 'title', 'priority', 'status', 'created_at']
    list_filter = ['activity_type', 'priority', 'status']
    search_fields = ['user__username', 'title', 'description']
    date_hierarchy = 'created_at'

# AI-related admin
@admin.register(PricingRule)
class PricingRuleAdmin(admin.ModelAdmin):
    list_display = ['name', 'rental_property', 'is_active', 'base_multiplier']
    list_filter = ['is_active']
    search_fields = ['name', 'rental_property__name']

@admin.register(MaintenanceTask)
class MaintenanceTaskAdmin(admin.ModelAdmin):
    list_display = ['title', 'rental_property', 'priority', 'status', 'scheduled_date']
    list_filter = ['priority', 'status', 'predicted_by_ai']
    search_fields = ['title', 'description', 'rental_property__name']
    date_hierarchy = 'scheduled_date'

@admin.register(GuestPreference)
class GuestPreferenceAdmin(admin.ModelAdmin):
    list_display = ['guest', 'guest_type', 'average_rating', 'loyalty_score']
    search_fields = ['guest__first_name', 'guest__last_name', 'guest__email']

@admin.register(MarketData)
class MarketDataAdmin(admin.ModelAdmin):
    list_display = ['location', 'date', 'average_daily_rate', 'occupancy_rate']
    list_filter = ['location']
    search_fields = ['location']
    date_hierarchy = 'date'

@admin.register(AIInsight)
class AIInsightAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'insight_type', 'confidence_score', 'priority', 'is_active']
    list_filter = ['insight_type', 'priority', 'is_active', 'is_implemented']
    search_fields = ['title', 'description']

@admin.register(PredictiveModel)
class PredictiveModelAdmin(admin.ModelAdmin):
    list_display = ['model_name', 'model_type', 'version', 'accuracy_score', 'is_active', 'is_production']
    list_filter = ['model_type', 'is_active', 'is_production']
    search_fields = ['model_name', 'description']

@admin.register(BusinessMetric)
class BusinessMetricAdmin(admin.ModelAdmin):
    list_display = ['user', 'metric_type', 'value', 'date', 'aggregation_period']
    list_filter = ['metric_type', 'aggregation_period']
    date_hierarchy = 'date'

@admin.register(ReviewSentiment)
class ReviewSentimentAdmin(admin.ModelAdmin):
    list_display = ['review', 'sentiment', 'sentiment_score', 'confidence']
    list_filter = ['sentiment']

@admin.register(CompetitorAnalysis)
class CompetitorAnalysisAdmin(admin.ModelAdmin):
    list_display = ['property', 'competitor_name', 'competitor_type', 'average_rate', 'average_rating']
    list_filter = ['competitor_type']
    search_fields = ['property__name', 'competitor_name']

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
