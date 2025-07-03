"""
URL configuration for booking_vision_APP.
This file defines all application-specific URLs.
"""
from django.urls import path
from .views import dashboard, properties, bookings, analytics, ai_views, api

app_name = 'booking_vision_APP'

urlpatterns = [
    # Dashboard URLs
    path('', dashboard.DashboardView.as_view(), name='dashboard'),
    path('dashboard/', dashboard.DashboardView.as_view(), name='dashboard_home'),

    # Property URLs
    path('properties/', properties.PropertyListView.as_view(), name='property_list'),
    path('properties/create/', properties.PropertyCreateView.as_view(), name='property_create'),
    path('properties/<int:pk>/', properties.PropertyDetailView.as_view(), name='property_detail'),
    path('properties/<int:pk>/edit/', properties.PropertyUpdateView.as_view(), name='property_edit'),

    # Booking URLs
    path('bookings/', bookings.BookingListView.as_view(), name='booking_list'),
    path('bookings/<int:pk>/', bookings.BookingDetailView.as_view(), name='booking_detail'),
    path('bookings/calendar/', bookings.CalendarView.as_view(), name='booking_calendar'),

    # Analytics URLs
    path('analytics/', analytics.AnalyticsView.as_view(), name='analytics'),
    path('analytics/revenue/', analytics.RevenueAnalyticsView.as_view(), name='revenue_analytics'),

    # AI Features URLs
    path('ai/pricing/', ai_views.SmartPricingView.as_view(), name='smart_pricing'),
    path('ai/maintenance/', ai_views.PredictiveMaintenanceView.as_view(), name='predictive_maintenance'),
    path('ai/guest-experience/', ai_views.GuestExperienceView.as_view(), name='guest_experience'),
    path('ai/business-intelligence/', ai_views.BusinessIntelligenceView.as_view(), name='business_intelligence'),

    # API URLs
    path('api/dashboard/stats/', api.dashboard_stats_api, name='api_dashboard_stats'),
    path('api/analytics/revenue/', api.revenue_analytics_api, name='api_revenue_analytics'),
    path('api/pricing/data/', api.pricing_data_api, name='api_pricing_data'),
    path('api/maintenance/predictions/', api.maintenance_predictions_api, name='api_maintenance_predictions'),
    path('api/maintenance/urgent/', api.maintenance_urgent_api, name='api_maintenance_urgent'),
    path('api/guests/preferences/', api.guests_preferences_api, name='api_guests_preferences'),
    path('api/market/data/', api.market_data_api, name='api_market_data'),
    path('api/ai/sentiment-analysis/', api.sentiment_analysis_api, name='api_sentiment_analysis'),
    path('api/ai/toggle/<str:feature>/', api.ai_toggle_api, name='api_ai_toggle'),
]