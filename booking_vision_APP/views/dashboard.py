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
from django.urls import reverse

from ..models.properties import Property
from ..models.bookings import Booking, Guest, BookingMessage
from ..models.channels import Channel, ChannelConnection
from ..models.payments import Payment
from ..models.notifications import NotificationRule
from ..ai.pricing_engine import PricingEngine
from ..ai.maintenance_predictor import MaintenancePredictor

from ..mixins import DataResponsiveMixin


@login_required
def home_redirect(request):
    """Redirect to dashboard"""
    return redirect('booking_vision_APP:dashboard')


class DashboardView(DataResponsiveMixin, LoginRequiredMixin, TemplateView):
    """Main dashboard view with comprehensive analytics and data responsiveness"""
    template_name = 'dashboard/dashboard.html'
    login_url = '/accounts/login/'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Get date ranges
        today = timezone.now().date()
        month_start = today.replace(day=1)
        year_start = today.replace(month=1, day=1)
        thirty_days_ago = today - timedelta(days=30)
        seven_days_ago = today - timedelta(days=7)

        # Get user's data
        properties = Property.objects.filter(owner=user, is_active=True)
        bookings = Booking.objects.filter(rental_property__owner=user)
        connected_channels = ChannelConnection.objects.filter(user=user, is_connected=True)

        # Enhanced property statistics
        context['total_properties'] = properties.count()
        context['properties'] = properties[:5]  # Recent 5 properties

        # Enhanced booking statistics with data responsiveness
        if bookings.exists():
            context['total_bookings'] = bookings.count()
            context['active_bookings'] = bookings.filter(
                status='confirmed',
                check_in_date__lte=today,
                check_out_date__gte=today
            ).count()

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

            # Today's activities
            context['todays_checkins'] = bookings.filter(
                check_in_date=today,
                status='confirmed'
            ).count()

            context['todays_checkouts'] = bookings.filter(
                check_out_date=today,
                status='checked_in'
            ).count()

            # Recent bookings
            context['recent_bookings'] = bookings.select_related(
                'rental_property', 'guest', 'channel'
            ).order_by('-created_at')[:10]
        else:
            # Set default values when no bookings exist
            context['total_bookings'] = 0
            context['active_bookings'] = 0
            context['upcoming_checkins'] = []
            context['upcoming_checkouts'] = []
            context['todays_checkins'] = 0
            context['todays_checkouts'] = 0
            context['recent_bookings'] = []

        # Enhanced revenue calculations with data responsiveness
        if context['has_revenue_data']:
            revenue_data = bookings.filter(
                status__in=['confirmed', 'checked_out']
            ).aggregate(
                total_revenue=Sum('total_price'),
                monthly_revenue=Sum('total_price', filter=Q(created_at__gte=month_start)),
                yearly_revenue=Sum('total_price', filter=Q(created_at__gte=year_start)),
                avg_booking_value=Avg('total_price')
            )

            context['total_revenue'] = revenue_data.get('total_revenue') or 0
            context['monthly_revenue'] = revenue_data.get('monthly_revenue') or 0
            context['yearly_revenue'] = revenue_data.get('yearly_revenue') or 0
            context['avg_booking_value'] = revenue_data.get('avg_booking_value') or 0

            # Revenue trend calculation
            previous_month_revenue = bookings.filter(
                status__in=['confirmed', 'checked_out'],
                created_at__gte=month_start - timedelta(days=31),
                created_at__lt=month_start
            ).aggregate(total=Sum('total_price'))['total'] or 0

            if previous_month_revenue > 0:
                revenue_change = ((context['monthly_revenue'] - previous_month_revenue) / previous_month_revenue) * 100
                context['revenue_change'] = round(revenue_change, 1)
                context['revenue_trend'] = 'up' if revenue_change > 0 else 'down'
            else:
                context['revenue_change'] = 0
                context['revenue_trend'] = 'neutral'

            # Weekly revenue for sparkline
            context['weekly_revenue'] = self._get_weekly_revenue_data(bookings, today)
        else:
            # Set default values when no revenue data exists
            context['total_revenue'] = 0
            context['monthly_revenue'] = 0
            context['yearly_revenue'] = 0
            context['avg_booking_value'] = 0
            context['revenue_change'] = 0
            context['revenue_trend'] = 'neutral'
            context['weekly_revenue'] = [0] * 7

        # Enhanced occupancy rate calculation with data responsiveness
        if properties.exists() and bookings.exists():
            total_property_days = properties.count() * 30  # Last 30 days
            booked_days = self._calculate_booked_days(properties, thirty_days_ago, today)
            context['occupancy_rate'] = round((booked_days / total_property_days * 100) if total_property_days > 0 else 0, 1)

            # Occupancy trend
            previous_month_days = self._calculate_booked_days(properties, thirty_days_ago - timedelta(days=30), thirty_days_ago)
            previous_occupancy = round((previous_month_days / total_property_days * 100) if total_property_days > 0 else 0, 1)
            context['occupancy_change'] = round(context['occupancy_rate'] - previous_occupancy, 1)
            context['occupancy_trend'] = 'up' if context['occupancy_change'] > 0 else 'down' if context['occupancy_change'] < 0 else 'neutral'
        else:
            context['occupancy_rate'] = 0
            context['occupancy_change'] = 0
            context['occupancy_trend'] = 'neutral'

        # Enhanced channel performance with data responsiveness
        if connected_channels.exists() and bookings.exists():
            context['channel_stats'] = self._get_channel_stats(user)
            context['top_performing_channel'] = max(context['channel_stats'], key=lambda x: x['revenue']) if context['channel_stats'] else None
        else:
            context['channel_stats'] = []
            context['top_performing_channel'] = None

        # Enhanced AI insights with data responsiveness
        if properties.exists():
            context['ai_insights'] = self._get_ai_insights(properties, bookings)
        else:
            context['ai_insights'] = []

        # Enhanced recent activities with data responsiveness
        context['recent_activities'] = self._get_recent_activities(user, bookings)

        # Enhanced upcoming tasks with data responsiveness
        context['upcoming_tasks'] = self._get_upcoming_tasks(user, bookings)

        # Response time metrics (data responsive)
        if context['has_messages']:
            context['avg_response_time'] = self._calculate_avg_response_time(user)
            context['response_time_trend'] = self._get_response_time_trend(user)
        else:
            context['avg_response_time'] = None
            context['response_time_trend'] = 'neutral'

        # Guest satisfaction metrics (data responsive)
        if context['has_guests']:
            context['guest_satisfaction'] = self._calculate_guest_satisfaction(user)
        else:
            context['guest_satisfaction'] = None

        # Performance summary for quick overview
        context['performance_summary'] = {
            'revenue_status': 'good' if context['revenue_trend'] == 'up' else 'warning' if context['revenue_trend'] == 'down' else 'neutral',
            'occupancy_status': 'good' if context['occupancy_rate'] > 70 else 'warning' if context['occupancy_rate'] > 40 else 'poor',
            'booking_status': 'good' if context['todays_checkins'] + context['todays_checkouts'] > 0 else 'neutral',
            'overall_status': self._calculate_overall_status(context)
        }

        # Chart data availability flags
        context['chart_data'] = {
            'revenue_chart_ready': context['has_revenue_data'] and context['recent_bookings_count'] >= 3,
            'occupancy_chart_ready': context['has_bookings'] and properties.exists(),
            'channel_chart_ready': context['has_connected_channels'] and context['has_bookings'],
            'trends_chart_ready': context['recent_bookings_count'] >= 5
        }

        return context

    def _get_weekly_revenue_data(self, bookings, today):
        """Get revenue data for the last 7 days for sparkline chart"""
        daily_revenue = []
        for i in range(7):
            day = today - timedelta(days=6-i)
            revenue = bookings.filter(
                status__in=['confirmed', 'checked_out'],
                created_at__date=day
            ).aggregate(total=Sum('total_price'))['total'] or 0
            daily_revenue.append(float(revenue))
        return daily_revenue

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
        """Get performance statistics for each channel with data responsiveness"""
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

            # Calculate additional metrics
            total_revenue = channel_bookings.aggregate(Sum('total_price'))['total_price__sum'] or 0
            avg_booking_value = channel_bookings.aggregate(Avg('total_price'))['total_price__avg'] or 0

            # Recent performance (last 30 days)
            recent_bookings = channel_bookings.filter(
                created_at__gte=timezone.now() - timedelta(days=30)
            )
            recent_revenue = recent_bookings.aggregate(Sum('total_price'))['total_price__sum'] or 0

            stats.append({
                'channel': channel,
                'bookings': channel_bookings.count(),
                'revenue': total_revenue,
                'avg_booking_value': avg_booking_value,
                'recent_bookings': recent_bookings.count(),
                'recent_revenue': recent_revenue,
                'performance_score': self._calculate_channel_performance_score(
                    channel_bookings.count(), total_revenue, recent_revenue
                )
            })

        return sorted(stats, key=lambda x: x['performance_score'], reverse=True)

    def _calculate_channel_performance_score(self, bookings_count, total_revenue, recent_revenue):
        """Calculate a performance score for channel ranking"""
        # Weighted score based on bookings and revenue
        score = (bookings_count * 10) + (total_revenue * 0.01) + (recent_revenue * 0.02)
        return round(score, 2)

    def _get_ai_insights(self, properties, bookings):
        """Generate AI-powered insights with enhanced data responsiveness"""
        insights = []

        # Only generate insights if we have sufficient data
        if not properties.exists():
            return insights

        # Pricing insights (requires booking history)
        if bookings.exists():
            try:
                pricing_engine = PricingEngine()
                for property in properties[:3]:  # Top 3 properties
                    property_bookings = bookings.filter(rental_property=property)
                    if property_bookings.count() >= 2:  # Need minimum data
                        recommendation = pricing_engine.get_pricing_recommendation(property)
                        if recommendation and recommendation.get('revenue_increase', 0) > 5:
                            insights.append({
                                'type': 'pricing',
                                'property': property,
                                'message': f"Consider adjusting {property.name} price to ${recommendation['suggested_price']:.2f} (potential {recommendation['revenue_increase']:.1f}% revenue increase)",
                                'priority': 'high' if recommendation['revenue_increase'] > 10 else 'medium',
                                'action_url': reverse('booking_vision_APP:smart_pricing') + f"?property_id={property.id}",
                                'confidence': recommendation.get('confidence', 75)
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
                    'priority': alert['priority'],
                    'action_url': reverse('booking_vision_APP:predictive_maintenance') + f"?property_id={alert['property'].id}",
                    'confidence': alert.get('confidence', 80)
                })
        except Exception as e:
            print(f"Error getting maintenance insights: {e}")

        # Booking optimization insights (requires sufficient data)
        if bookings.count() >= 5:
            insights.extend(self._get_booking_optimization_insights(properties, bookings))

        # Guest experience insights
        if bookings.filter(guest__isnull=False).count() >= 3:
            insights.extend(self._get_guest_experience_insights(bookings))

        return insights

    def _get_booking_optimization_insights(self, properties, bookings):
        """Generate booking optimization insights"""
        insights = []

        # Low occupancy properties
        for property in properties:
            property_bookings = bookings.filter(rental_property=property)
            if property_bookings.exists():
                # Calculate occupancy for this property
                thirty_days_ago = timezone.now().date() - timedelta(days=30)
                booked_days = self._calculate_booked_days([property], thirty_days_ago, timezone.now().date())
                occupancy_rate = (booked_days / 30) * 100

                if occupancy_rate < 40:  # Low occupancy threshold
                    insights.append({
                        'type': 'optimization',
                        'property': property,
                        'message': f"{property.name} has low occupancy ({occupancy_rate:.1f}%). Consider adjusting pricing or marketing strategy.",
                        'priority': 'medium',
                        'action_url': reverse('booking_vision_APP:property_detail', args=[property.id]),
                        'confidence': 85
                    })

        return insights

    def _get_guest_experience_insights(self, bookings):
        """Generate guest experience insights"""
        insights = []

        # Check for guests with multiple bookings (repeat customers)
        repeat_guests = Guest.objects.filter(
            booking__rental_property__owner=bookings.first().rental_property.owner
        ).annotate(
            booking_count=Count('booking')
        ).filter(booking_count__gt=1)

        if repeat_guests.exists():
            insights.append({
                'type': 'guest_experience',
                'property': None,
                'message': f"You have {repeat_guests.count()} repeat guests! Consider implementing a loyalty program.",
                'priority': 'low',
                'action_url': reverse('booking_vision_APP:guest_experience'),
                'confidence': 90
            })

        return insights

    def _get_recent_activities(self, user, bookings):
        """Get recent activities for activity feed with data responsiveness"""
        activities = []

        # Recent bookings (if any exist)
        if bookings.exists():
            recent_bookings = bookings.order_by('-created_at')[:5]
            for booking in recent_bookings:
                activities.append({
                    'type': 'booking',
                    'icon': 'calendar-check',
                    'title': f'New booking from {booking.guest.first_name if booking.guest else "Guest"}',
                    'description': f'{booking.rental_property.name} - {booking.check_in_date}',
                    'time_ago': self._time_ago(booking.created_at),
                    'timestamp': booking.created_at,
                    'url': reverse('booking_vision_APP:booking_detail', args=[booking.id])
                })

        # Recent messages (if any exist)
        messages = BookingMessage.objects.filter(
            booking__rental_property__owner=user,
            sender='guest'
        ).order_by('-created_at')[:3]

        for message in messages:
            activities.append({
                'type': 'message',
                'icon': 'comment',
                'title': f'Message from {message.booking.guest.first_name if message.booking.guest else "Guest"}',
                'description': message.message[:50] + '...' if len(message.message) > 50 else message.message,
                'time_ago': self._time_ago(message.created_at),
                'timestamp': message.created_at,
                'url': reverse('booking_vision_APP:messages_list') + f"?booking_id={message.booking.id}"
            })

        # Recent property additions
        recent_properties = Property.objects.filter(
            owner=user,
            created_at__gte=timezone.now() - timedelta(days=7)
        ).order_by('-created_at')[:2]

        for property in recent_properties:
            activities.append({
                'type': 'property',
                'icon': 'home',
                'title': f'Added new property: {property.name}',
                'description': f'{property.property_type} in {property.city}',
                'time_ago': self._time_ago(property.created_at),
                'timestamp': property.created_at,
                'url': reverse('booking_vision_APP:property_detail', args=[property.id])
            })

        # Sort by timestamp and return
        activities.sort(key=lambda x: x['timestamp'], reverse=True)
        return activities[:10]

    def _get_upcoming_tasks(self, user, bookings):
        """Get upcoming tasks with data responsiveness"""
        tasks = []

        # Upcoming check-ins (if bookings exist)
        if bookings.exists():
            upcoming_checkins = bookings.filter(
                status='confirmed',
                check_in_date__gte=timezone.now().date(),
                check_in_date__lte=timezone.now().date() + timedelta(days=7)
            ).order_by('check_in_date')[:3]

            for booking in upcoming_checkins:
                days_until = (booking.check_in_date - timezone.now().date()).days
                priority = 'high' if days_until == 0 else 'medium' if days_until <= 1 else 'low'

                tasks.append({
                    'title': f'Prepare for {booking.guest.first_name if booking.guest else "guest"} check-in',
                    'property': booking.rental_property.name,
                    'due_date': booking.check_in_date,
                    'priority': priority,
                    'type': 'checkin',
                    'url': reverse('booking_vision_APP:booking_detail', args=[booking.id])
                })

        # Maintenance tasks (if any exist)
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
                    'priority': task.priority,
                    'type': 'maintenance',
                    'url': reverse('booking_vision_APP:predictive_maintenance') + f"?task_id={task.id}"
                })
        except ImportError:
            pass

        # Sync reminders (if channels connected but no recent sync)
        connected_channels = ChannelConnection.objects.filter(
            user=user,
            is_connected=True,
            last_sync__lt=timezone.now() - timedelta(hours=24)
        )

        if connected_channels.exists():
            tasks.append({
                'title': 'Sync channel data',
                'property': f'{connected_channels.count()} channel{"s" if connected_channels.count() > 1 else ""}',
                'due_date': 'Overdue',
                'priority': 'medium',
                'type': 'sync',
                'url': reverse('booking_vision_APP:channel_management')
            })

        return tasks

    def _calculate_avg_response_time(self, user):
        """Calculate average response time to guest messages"""
        # This would involve calculating time between guest messages and host responses
        # For now, return a placeholder that could be calculated based on message timestamps
        return "< 1hr"  # Placeholder - implement actual calculation

    def _get_response_time_trend(self, user):
        """Get response time trend"""
        # Placeholder for actual trend calculation
        return 'improving'  # or 'declining', 'stable'

    def _calculate_guest_satisfaction(self, user):
        """Calculate overall guest satisfaction score"""
        # This would be based on reviews, ratings, repeat bookings, etc.
        # Placeholder implementation
        return 4.8  # out of 5

    def _calculate_overall_status(self, context):
        """Calculate overall performance status"""
        scores = []

        if context['revenue_trend'] == 'up':
            scores.append(3)
        elif context['revenue_trend'] == 'down':
            scores.append(1)
        else:
            scores.append(2)

        if context['occupancy_rate'] > 70:
            scores.append(3)
        elif context['occupancy_rate'] > 40:
            scores.append(2)
        else:
            scores.append(1)

        if context['todays_checkins'] + context['todays_checkouts'] > 0:
            scores.append(3)
        else:
            scores.append(2)

        avg_score = sum(scores) / len(scores) if scores else 2

        if avg_score >= 2.5:
            return 'excellent'
        elif avg_score >= 2:
            return 'good'
        else:
            return 'needs_attention'

    def _time_ago(self, timestamp):
        """Convert timestamp to human-readable time ago"""
        from django.utils import timezone
        from django.utils.timesince import timesince
        return timesince(timestamp, timezone.now())


@login_required
def dashboard_metrics_api(request):
    """API endpoint for real-time dashboard metrics"""
    user = request.user

    # Get current metrics
    bookings = Booking.objects.filter(rental_property__owner=user)
    today = timezone.now().date()

    metrics = {
        'active_bookings': bookings.filter(
            status='confirmed',
            check_in_date__lte=today,
            check_out_date__gte=today
        ).count(),
        'todays_checkins': bookings.filter(
            check_in_date=today,
            status='confirmed'
        ).count(),
        'todays_checkouts': bookings.filter(
            check_out_date=today,
            status='checked_in'
        ).count(),
        'total_revenue': bookings.filter(
            status__in=['confirmed', 'checked_out']
        ).aggregate(total=Sum('total_price'))['total'] or 0,
        'timestamp': timezone.now().isoformat()
    }

    return JsonResponse(metrics)