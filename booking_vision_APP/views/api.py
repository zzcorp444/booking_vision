"""
API views for AJAX requests.
Location: booking_vision_APP/views/api.py
"""
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.db.models import Sum, Count, Avg, Q
from django.utils import timezone
from datetime import datetime, timedelta
import json

from ..models.properties import Property
from ..models.bookings import Booking

from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status


@login_required
@require_http_methods(["GET"])
def dashboard_stats_api(request):
    """API endpoint for dashboard statistics"""
    user = request.user
    today = timezone.now().date()

    properties = Property.objects.filter(owner=user, is_active=True)
    bookings = Booking.objects.filter(rental_property__owner=user)

    total_revenue = bookings.filter(
        status__in=['confirmed', 'checked_out']
    ).aggregate(Sum('total_price'))['total_price__sum'] or 0

    # Calculate occupancy rate
    total_property_days = properties.count() * 30
    if total_property_days > 0:
        # Simplified calculation for now
        active_bookings = bookings.filter(
            status__in=['confirmed', 'checked_in'],
            check_in_date__lte=today,
            check_out_date__gte=today - timedelta(days=30)
        ).count()
        occupancy_rate = min(round((active_bookings / total_property_days * 100), 1), 100)
    else:
        occupancy_rate = 0

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
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=365)

    # Group bookings by month
    bookings = Booking.objects.filter(
        rental_property__owner=user,
        status__in=['confirmed', 'checked_out'],
        created_at__gte=start_date
    )

    monthly_revenue = {}
    for booking in bookings:
        month_key = booking.created_at.strftime('%Y-%m')
        if month_key not in monthly_revenue:
            monthly_revenue[month_key] = 0
        monthly_revenue[month_key] += float(booking.total_price)

    # Sort by date
    sorted_months = sorted(monthly_revenue.keys())

    return JsonResponse({
        'labels': [datetime.strptime(m, '%Y-%m').strftime('%b %Y') for m in sorted_months],
        'revenue': [monthly_revenue[m] for m in sorted_months]
    })


@login_required
@require_http_methods(["GET"])
def pricing_data_api(request):
    """API endpoint for pricing data"""
    user = request.user
    properties = Property.objects.filter(owner=user, is_active=True)

    pricing_data = []
    for property in properties:
        pricing_data.append({
            'id': property.id,
            'name': property.name,
            'current_price': float(property.base_price),
            'ai_enabled': property.ai_pricing_enabled,
            'last_update': property.last_pricing_update.isoformat() if property.last_pricing_update else None
        })

    return JsonResponse({
        'properties': pricing_data,
        'total_properties': len(pricing_data)
    })


@login_required
@require_http_methods(["GET"])
def maintenance_predictions_api(request):
    """API endpoint for maintenance predictions"""
    from ..ai.maintenance_predictor import MaintenancePredictor

    user = request.user
    properties = Property.objects.filter(owner=user, is_active=True)

    predictor = MaintenancePredictor()
    predictions = []

    for property in properties[:5]:  # Limit to 5 properties for performance
        property_predictions = predictor.predict_maintenance_needs(property)
        for pred in property_predictions[:3]:  # Top 3 predictions per property
            predictions.append({
                'property_id': property.id,
                'property_name': property.name,
                'maintenance_type': pred['maintenance_type'],
                'days_until': pred['days_until'],
                'priority': pred['priority'],
                'estimated_cost': pred['estimated_cost'],
                'confidence': pred['confidence']
            })

    return JsonResponse({
        'predictions': predictions,
        'total_predictions': len(predictions)
    })


@login_required
@require_http_methods(["GET"])
def maintenance_urgent_api(request):
    """API endpoint for urgent maintenance items"""
    from ..models.ai_models import MaintenanceTask

    user = request.user
    urgent_tasks = MaintenanceTask.objects.filter(
        rental_property__owner=user,
        status__in=['pending', 'scheduled'],
        priority__in=['urgent', 'high']
    ).select_related('rental_property')[:5]

    urgent_items = []
    for task in urgent_tasks:
        urgent_items.append({
            'id': task.id,
            'property_name': task.rental_property.name,
            'title': task.title,
            'priority': task.priority,
            'scheduled_date': task.scheduled_date.isoformat() if task.scheduled_date else None,
            'estimated_cost': float(task.estimated_cost) if task.estimated_cost else 0
        })

    return JsonResponse({
        'urgent_items': urgent_items,
        'total_urgent': len(urgent_items)
    })


@login_required
@require_http_methods(["GET"])
def guests_preferences_api(request):
    """API endpoint for guest preferences"""
    from ..models.bookings import Guest

    user = request.user
    recent_guests = Guest.objects.filter(
        bookings__rental_property__owner=user
    ).distinct().order_by('-created_at')[:10]

    preferences = []
    for guest in recent_guests:
        guest_pref = {
            'id': guest.id,
            'name': f"{guest.first_name} {guest.last_name}",
            'email': guest.email,
            'preferences': guest.preferences,
            'satisfaction_score': float(guest.satisfaction_score) if guest.satisfaction_score else None
        }
        preferences.append(guest_pref)

    return JsonResponse({
        'guests': preferences,
        'total_guests': len(preferences)
    })


@login_required
@require_http_methods(["GET"])
def market_data_api(request):
    """API endpoint for market data"""
    from ..models.ai_models import MarketData

    user = request.user
    properties = Property.objects.filter(owner=user, is_active=True)

    if properties.exists():
        cities = properties.values_list('city', flat=True).distinct()
        market_data = MarketData.objects.filter(
            location__in=cities
        ).order_by('-date')[:10]

        data = []
        for md in market_data:
            data.append({
                'location': md.location,
                'date': md.date.isoformat(),
                'average_daily_rate': float(md.average_daily_rate),
                'occupancy_rate': float(md.occupancy_rate),
                'revenue_per_available_room': float(md.revenue_per_available_room)
            })

        return JsonResponse({
            'market_data': data,
            'locations': list(cities)
        })

    return JsonResponse({
        'market_data': [],
        'locations': []
    })


@login_required
@require_http_methods(["POST"])
def sentiment_analysis_api(request):
    """API endpoint for sentiment analysis"""
    from ..ai.sentiment_analysis import SentimentAnalyzer

    try:
        data = json.loads(request.body)
        text = data.get('text', '')

        if not text:
            return JsonResponse({'error': 'No text provided'}, status=400)

        analyzer = SentimentAnalyzer()
        sentiment = analyzer.analyze(text)

        return JsonResponse({
            'sentiment': sentiment['sentiment'],
            'score': sentiment['score'],
            'confidence': sentiment['confidence'],
            'urgency': sentiment['urgency'],
            'suggestions': sentiment.get('suggestions', [])
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def ai_toggle_api(request, feature):
    """API endpoint for toggling AI features"""
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
        updated = 0
        for property in properties:
            setattr(property, feature_map[feature], enabled)
            property.save()
            updated += 1

        return JsonResponse({
            'success': True,
            'feature': feature,
            'enabled': enabled,
            'properties_updated': updated
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def extension_sync(request):
    """Receive booking data from browser extension"""
    channel_name = request.data.get('channel')
    bookings_data = request.data.get('bookings', [])

    try:
        # Process bookings
        from ..integrations.no_api_sync_manager import AirbnbNoAPISync
        sync = AirbnbNoAPISync()

        # Convert extension data to standard format
        formatted_bookings = []
        for booking in bookings_data:
            formatted_bookings.append({
                'external_booking_id': booking.get('confirmationCode'),
                'guest_name': booking.get('guestName'),
                'check_in': sync._parse_date(booking.get('checkIn')),
                'check_out': sync._parse_date(booking.get('checkOut')),
                'total_price': booking.get('totalPrice', 0),
                'status': 'confirmed',
                'channel': channel_name
            })

        # Save bookings
        saved_count = await sync._save_bookings(request.user, formatted_bookings, channel_name)

        return Response({
            'success': True,
            'bookings_received': len(bookings_data),
            'bookings_saved': saved_count
        })

    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_extension_token(request):
    """Get token for browser extension"""
    from rest_framework.authtoken.models import Token

    token, created = Token.objects.get_or_create(user=request.user)

    return Response({
        'token': token.key,
        'server_url': request.build_absolute_uri('/').rstrip('/')
    })