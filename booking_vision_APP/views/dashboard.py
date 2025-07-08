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
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from ..models.bookings import Guest, BookingMessage
from ..models.channels import ChannelConnection
from ..ai.pricing_engine import PricingEngine
from ..ai.maintenance_predictor import MaintenancePredictor
from ..models import Property, Booking, Channel, Notification, Payment
from ..services.activity_service import ActivityService


@login_required
def home_redirect(request):
    """Redirect to dashboard"""
    return redirect('booking_vision_APP:dashboard')


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

        # Ensure values are not None
        context['total_revenue'] = revenue_data.get('total_revenue') or 0
        context['monthly_revenue'] = revenue_data.get('monthly_revenue') or 0
        context['yearly_revenue'] = revenue_data.get('yearly_revenue') or 0

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

        # Today's check-ins/outs
        context['todays_checkins'] = bookings.filter(
            check_in_date=today,
            status='confirmed'
        ).count()

        context['todays_checkouts'] = bookings.filter(
            check_out_date=today,
            status='checked_in'
        ).count()

        # Recent activities
        context['recent_activities'] = self._get_recent_activities(user)

        # Upcoming tasks
        context['upcoming_tasks'] = self._get_upcoming_tasks(user)

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
        try:
            pricing_engine = PricingEngine()
            for property in properties[:3]:  # Top 3 properties
                recommendation = pricing_engine.get_pricing_recommendation(property)
                if recommendation and recommendation.get('revenue_increase', 0) > 5:
                    insights.append({
                        'type': 'pricing',
                        'property': property,
                        'message': f"Consider adjusting {property.name} price to ${recommendation['suggested_price']:.2f} (potential {recommendation['revenue_increase']:.1f}% revenue increase)",
                        'priority': 'high' if recommendation['revenue_increase'] > 10 else 'medium'
                    })
        except Exception as e:
            print(f"Error getting pricing insights: {e}")

        # Maintenance insights
        try:
            maintenance_predictor = MaintenancePredictor()
            maintenance_alerts = maintenance_predictor.get_upcoming_maintenance(properties)
            for alert in maintenance_alerts[:2]:  # Top 2 alerts
                insights.append({
                    'type': 'maintenance',
                    'property': alert['property'],
                    'message': alert['message'],
                    'priority': alert['priority']
                })
        except Exception as e:
            print(f"Error getting maintenance insights: {e}")

        return insights

    def _get_recent_activities(self, user):
        """Get recent activities for activity feed"""
        activities = []

        # Recent bookings
        recent_bookings = Booking.objects.filter(
            rental_property__owner=user
        ).order_by('-created_at')[:5]

        for booking in recent_bookings:
            activities.append({
                'type': 'booking',
                'icon': 'calendar-check',
                'title': f'New booking from {booking.guest.first_name}',
                'description': f'{booking.rental_property.name} - {booking.check_in_date}',
                'time_ago': self._time_ago(booking.created_at),
                'timestamp': booking.created_at
            })

        # Recent messages
        recent_messages = BookingMessage.objects.filter(
            booking__rental_property__owner=user,
            sender='guest'
        ).order_by('-created_at')[:3]

        for message in recent_messages:
            activities.append({
                'type': 'message',
                'icon': 'comment',
                'title': f'Message from {message.booking.guest.first_name}',
                'description': message.message[:50] + '...' if len(message.message) > 50 else message.message,
                'time_ago': self._time_ago(message.created_at),
                'timestamp': message.created_at
            })

        # Sort by timestamp
        activities.sort(key=lambda x: x['timestamp'], reverse=True)
        return activities[:10]

    def _get_upcoming_tasks(self, user):
        """Get upcoming tasks"""
        tasks = []

        # Upcoming check-ins
        upcoming_checkins = Booking.objects.filter(
            rental_property__owner=user,
            status='confirmed',
            check_in_date__gte=timezone.now().date(),
            check_in_date__lte=timezone.now().date() + timedelta(days=7)
        ).order_by('check_in_date')[:3]

        for booking in upcoming_checkins:
            tasks.append({
                'title': f'Prepare for {booking.guest.first_name} check-in',
                'property': booking.rental_property.name,
                'due_date': booking.check_in_date,
                'priority': 'high' if booking.check_in_date == timezone.now().date() else 'medium'
            })

        # Maintenance tasks
        try:
            from ..models.ai_models import MaintenanceTask
            maintenance_tasks = MaintenanceTask.objects.filter(
                rental_property__owner=user,
                status='pending'
            ).order_by('priority', 'created_at')[:2]

            for task in maintenance_tasks:
                tasks.append({
                    'title': task.title,
                    'property': task.rental_property.name,
                    'due_date': task.scheduled_date or 'ASAP',
                    'priority': task.priority
                })
        except:
            pass

        return tasks

    def _time_ago(self, timestamp):
        """Convert timestamp to human-readable time ago"""
        from django.utils import timezone
        from django.utils.timesince import timesince
        return timesince(timestamp, timezone.now())