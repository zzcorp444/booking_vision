"""
API views for AJAX requests and data endpoints.
Location: booking_vision_APP/api_views.py
"""
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.db.models import Sum, Count, Avg
from django.utils import timezone
from datetime import timedelta
import json

from .models.properties import Property
from .models.bookings import Booking


@login_required
@require_http_methods(["GET"])
def dashboard_stats_api(request):
    """API endpoint for dashboard statistics"""
    user = request.user

    # Get user's properties
    properties = Property.objects.filter(owner=user, is_active=True)

    # Get bookings
    bookings = Booking.objects.filter(rental_property__owner=user)

    # Calculate total revenue
    total_revenue = bookings.filter(
        status__in=['confirmed', 'checked_out']
    ).aggregate(Sum('total_price'))['total_price__sum'] or 0

    # Calculate occupancy rate for last 30 days
    today = timezone.now().date()
    thirty_days_ago = today - timedelta(days=30)

    total_property_days = properties.count() * 30
    booked_days = 0

    for property in properties:
        property_bookings = bookings.filter(
            rental_property=property,
            status__in=['confirmed', 'checked_in', 'checked_out'],
            check_in_date__lte=today,
            check_out_date__gte=thirty_days_ago
        )

        for booking in property_bookings:
            overlap_start = max(booking.check_in_date, thirty_days_ago)
            overlap_end = min(booking.check_out_date, today)
            if overlap_start <= overlap_end:
                booked_days += (overlap_end - overlap_start).days + 1

    occupancy_rate = round((booked_days / total_property_days * 100) if total_property_days > 0 else 0, 1)

    return JsonResponse({
        'total_properties': properties.count(),
        'total_bookings': bookings.count(),
        'total_revenue': float(total_revenue),
        'occupancy_rate': occupancy_rate
    })


@login_required
@require_http_methods(["GET"])
def revenue_analytics_api(request):
    """API endpoint for revenue analytics data"""
    user = request.user
    period = request.GET.get('period', '12months')

    bookings = Booking.objects.filter(
        rental_property__owner=user,
        status__in=['confirmed', 'checked_out']
    )

    if period == '12months':
        # Get monthly revenue for last 12 months
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=365)

        monthly_revenue = {}
        for booking in bookings.filter(created_at__gte=start_date):
            month_key = booking.created_at.strftime('%Y-%m')
            if month_key not in monthly_revenue:
                monthly_revenue[month_key] = 0
            monthly_revenue[month_key] += float(booking.total_price)

        # Sort by date
        sorted_months = sorted(monthly_revenue.keys())

        return JsonResponse({
            'labels': [timezone.datetime.strptime(m, '%Y-%m').strftime('%b %Y') for m in sorted_months],
            'revenue': [monthly_revenue.get(m, 0) for m in sorted_months]
        })

    return JsonResponse({'error': 'Invalid period'}, status=400)


@login_required
@require_http_methods(["POST"])
def toggle_ai_feature(request, feature):
    """Toggle AI features on/off"""
    try:
        data = json.loads(request.body)
        enabled = data.get('enabled', False)

        # Map feature names to property fields
        feature_map = {
            'pricing': 'ai_pricing_enabled',
            'maintenance': 'ai_maintenance_enabled',
            'guest_experience': 'ai_guest_enabled',
            'business_intelligence': 'ai_analytics_enabled'
        }

        if feature not in feature_map:
            return JsonResponse({'error': 'Invalid feature'}, status=400)

        # Update all user properties
        properties = Property.objects.filter(owner=request.user)
        for property in properties:
            setattr(property, feature_map[feature], enabled)
            property.save()

        return JsonResponse({
            'success': True,
            'feature': feature,
            'enabled': enabled
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)