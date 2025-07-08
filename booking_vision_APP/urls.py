"""
URL configuration for booking_vision_APP.
This file defines all application-specific URLs.
"""
from django.urls import path, include
from .views import (
    dashboard, properties, bookings, analytics, ai_views,
    messages, notifications, payments, profile, activities,
    documentation, channels  # Add channels import
)
from . import api_views

app_name = 'booking_vision_APP'

urlpatterns = [
    # Home redirect
    path('', dashboard.home_redirect, name='home'),

    # Dashboard URLs
    path('dashboard/', dashboard.DashboardView.as_view(), name='dashboard'),

    # Property URLs
    path('properties/', properties.PropertyListView.as_view(), name='property_list'),
    path('properties/create/', properties.PropertyCreateView.as_view(), name='property_create'),
    path('properties/<int:pk>/', properties.PropertyDetailView.as_view(), name='property_detail'),
    path('properties/<int:pk>/edit/', properties.PropertyUpdateView.as_view(), name='property_edit'),

    # Booking URLs
    path('bookings/', bookings.BookingListView.as_view(), name='booking_list'),
    path('bookings/create/', bookings.BookingCreateView.as_view(), name='booking_create'),  # Add this
    path('bookings/<int:pk>/', bookings.BookingDetailView.as_view(), name='booking_detail'),
    path('bookings/calendar/', bookings.CalendarView.as_view(), name='booking_calendar'),

    # Channel Management URLs
    path('channels/', channels.ChannelManagementView.as_view(), name='channel_management'),
    path('channels/connect/', channels.connect_channel, name='connect_channel'),
    path('channels/sync/', channels.sync_bookings, name='sync_bookings'),

    # Messages URLs
    path('messages/', messages.MessagesListView.as_view(), name='messages_list'),
    path('messages/send/', messages.send_message_api, name='send_message'),

    # Notifications URLs
    path('notifications/', notifications.NotificationListView.as_view(), name='notifications_list'),
    path('notifications/create/', notifications.NotificationCreateView.as_view(), name='notification_create'),
    path('notifications/<int:pk>/edit/', notifications.NotificationUpdateView.as_view(), name='notification_edit'),
    path('notifications/<int:pk>/delete/', notifications.NotificationDeleteView.as_view(), name='notification_delete'),

    # Payments URLs
    path('payments/', payments.PaymentsListView.as_view(), name='payments_list'),
    path('payments/history/', payments.PayoutHistoryView.as_view(), name='payout_history'),

    # Analytics URLs
    path('analytics/', analytics.AnalyticsView.as_view(), name='analytics'),
    path('analytics/revenue/', analytics.RevenueAnalyticsView.as_view(), name='revenue_analytics'),

    # AI Features URLs
    path('ai/pricing/', ai_views.SmartPricingView.as_view(), name='smart_pricing'),
    path('ai/maintenance/', ai_views.PredictiveMaintenanceView.as_view(), name='predictive_maintenance'),
    path('ai/guest-experience/', ai_views.GuestExperienceView.as_view(), name='guest_experience'),
    path('ai/business-intelligence/', ai_views.BusinessIntelligenceView.as_view(), name='business_intelligence'),

    # Profile URLs
    path('profile/', profile.ProfileView.as_view(), name='profile'),
    path('settings/', profile.EnhancedSettingsView.as_view(), name='settings'),

    # Activity URLs
    path('activities/', activities.ActivityView.as_view(), name='activity'),
    path('api/activities/', activities.ActivityAPIView.as_view(), name='activity_api'),

    # Documentation URLs
    path('documentation/', documentation.DocumentationView.as_view(), name='documentation'),
    path('documentation/<str:article_id>/', documentation.DocumentationArticleView.as_view(), name='documentation_article'),

    # API URLs
    path('api/dashboard/stats/', api_views.dashboard_stats_api, name='api_dashboard_stats'),
    path('api/analytics/revenue/', api_views.revenue_analytics_api, name='api_revenue_analytics'),
    path('api/ai/toggle/<str:feature>/', api_views.toggle_ai_feature, name='api_toggle_ai_feature'),
]