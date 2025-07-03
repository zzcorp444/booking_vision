"""
Dashboard views for Booking Vision application.
This file contains the main dashboard view with AI-powered insights.
Location: booking_vision_APP/views/dashboard.py
"""
from django.shortcuts import render, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.db.models import Sum, Count, Avg, Q
from django.utils import timezone
from datetime import datetime, timedelta
from django.http import JsonResponse

from ..models.properties import Property
from ..models.bookings import Booking, Guest
from ..models.channels import Channel, ChannelConnection
from ..ai.pricing_engine import PricingEngine
from ..ai.maintenance_predictor import MaintenancePredictor


class DashboardView(LoginRequiredMixin, TemplateView):
    """Main dashboard view with comprehensive analytics"""
    template_name = 'dashboard/dashboard.html'
    login_url = '/accounts/login/'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Get date ranges
        today = timezone.now().date()
        month_start = today.replace(day=1)
        year_start = today.replace(month=1, day=1)

        # Property statistics
        properties = Property.objects.filter(owner=user, is_active=True)
        context['total_properties'] = properties.count()
        context['properties'] = properties[:5]  # Recent 5 properties

        # Booking statistics
        bookings = Booking.objects.filter(rental_property__owner=user)
        context['total_bookings'] = bookings.count()
        context['active_bookings'] = bookings.filter(
            status='confirmed',
            check_in_date__lte=today,
            check_out_date__gte=today
        ).count()

        # Revenue calculations
        revenue_data = bookings.filter(
            status__in=['confirmed', 'checked_out']
        ).aggregate(
            total_revenue=Sum('total_price'),
            monthly_revenue=Sum('total_price', filter=Q(created_at__gte=month_start)),
            yearly_revenue=Sum('total_price', filter=Q(created_at__gte=year_start))
        )
        context.update(revenue_data)

        # Occupancy rate calculation
        total_property_days = properties.count() * 30  # Last 30 days
        booked_days = self._calculate_booked_days(properties, today - timedelta(days=30), today)
        context['occupancy_rate'] = round((booked_days / total_property_days * 100) if total_property_days > 0 else 0, 1)

        # Recent bookings
        context['recent_bookings'] = bookings.select_related('rental_property', 'guest', 'channel').order_by('-created_at')[:10]

        # Channel performance
        context['channel_stats'] = self._get_channel_stats(user)

        # AI insights
        context['ai_insights'] = self._get_ai_insights(properties)

        # Upcoming check-ins/check-outs
        context['upcoming_checkins'] = bookings.filter(
            status='confirmed',
            check_in_date__gte=today,
            check_in_date__lte=today + timedelta(days=7)
        ).order_by('check_in_date')[:5]

        context['upcoming_checkouts'] = bookings.filter(
            status='checked_in',
            check_out_date__gte=today,
            check_out_date__lte=today + timedelta(days=7)
        ).order_by('check_out_date')[:5]

        return context

    def _calculate_booked_days(self, properties, start_date, end_date):
        """Calculate total booked days for properties in date range"""
        booked_days = 0
        for property in properties:
            bookings = Booking.objects.filter(
                rental_property=property,
                status__in=['confirmed', 'checked_in', 'checked_out'],
                check_in_date__lte=end_date,
                check_out_date__gte=start_date
            )
            for booking in bookings:
                overlap_start = max(booking.check_in_date, start_date)
                overlap_end = min(booking.check_out_date, end_date)
                if overlap_start <= overlap_end:
                    booked_days += (overlap_end - overlap_start).days + 1
        return booked_days

    def _get_channel_stats(self, user):
        """Get performance statistics for each channel"""
        channels = Channel.objects.filter(
            channelconnection__user=user,
            channelconnection__is_connected=True
        ).distinct()

        stats = []
        for channel in channels:
            channel_bookings = Booking.objects.filter(
                rental_property__owner=user,
                channel=channel
            )
            stats.append({
                'channel': channel,
                'bookings': channel_bookings.count(),
                'revenue': channel_bookings.aggregate(Sum('total_price'))['total_price__sum'] or 0
            })

        return sorted(stats, key=lambda x: x['revenue'], reverse=True)

    def _get_ai_insights(self, properties):
        """Generate AI-powered insights"""
        insights = []

        # Pricing insights
        pricing_engine = PricingEngine()
        for property in properties[:3]:  # Top 3 properties
            recommendation = pricing_engine.get_pricing_recommendation(property)
            if recommendation:
                insights.append({
                    'type': 'pricing',
                    'property': property,
                    'message': f"Consider adjusting {property.name} price to ${recommendation['suggested_price']:.2f} (potential {recommendation['revenue_increase']:.1f}% revenue increase)",
                    'priority': 'high' if recommendation['revenue_increase'] > 10 else 'medium'
                })

        # Maintenance insights
        maintenance_predictor = MaintenancePredictor()
        maintenance_alerts = maintenance_predictor.get_upcoming_maintenance(properties)
        for alert in maintenance_alerts[:2]:  # Top 2 alerts
            insights.append({
                'type': 'maintenance',
                'property': alert['property'],
                'message': alert['message'],
                'priority': alert['priority']
            })

        return insights


class DashboardAPIView(LoginRequiredMixin, TemplateView):
    """API endpoint for dashboard data"""

    def get(self, request, *args, **kwargs):
        user = request.user
        data_type = request.GET.get('type', 'stats')

        if data_type == 'stats':
            return self.get_stats(user)
        elif data_type == 'revenue':
            return self.get_revenue_data(user)
        elif data_type == 'occupancy':
            return self.get_occupancy_data(user)

        return JsonResponse({'error': 'Invalid data type'}, status=400)

    def get_stats(self, user):
        """Get dashboard statistics"""
        today = timezone.now().date()

        properties = Property.objects.filter(owner=user, is_active=True)
        bookings = Booking.objects.filter(rental_property__owner=user)

        total_revenue = bookings.filter(
            status__in=['confirmed', 'checked_out']
        ).aggregate(Sum('total_price'))['total_price__sum'] or 0

        # Calculate occupancy rate
        total_property_days = properties.count() * 30
        booked_days = self._calculate_booked_days(properties, today - timedelta(days=30), today)
        occupancy_rate = round((booked_days / total_property_days * 100) if total_property_days > 0 else 0, 1)

        return JsonResponse({
            'total_properties': properties.count(),
            'total_bookings': bookings.count(),
            'total_revenue': float(total_revenue),
            'occupancy_rate': occupancy_rate
        })

    def get_revenue_data(self, user):
        """Get revenue chart data"""
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

    def _calculate_booked_days(self, properties, start_date, end_date):
        """Calculate total booked days for properties in date range"""
        booked_days = 0
        for property in properties:
            bookings = Booking.objects.filter(
                rental_property=property,
                status__in=['confirmed', 'checked_in', 'checked_out'],
                check_in_date__lte=end_date,
                check_out_date__gte=start_date
            )
            for booking in bookings:
                overlap_start = max(booking.check_in_date, start_date)
                overlap_end = min(booking.check_out_date, end_date)
                if overlap_start <= overlap_end:
                    booked_days += (overlap_end - overlap_start).days + 1
        return booked_days