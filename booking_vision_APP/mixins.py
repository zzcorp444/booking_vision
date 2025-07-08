"""
Data-responsive mixins for Booking Vision application.
This file contains mixins to add data availability context to views.
"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Sum, Q, Avg
from django.utils import timezone
from datetime import datetime, timedelta


class DataResponsiveMixin:
    """Enhanced mixin to add comprehensive data availability context to views"""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Import models to avoid circular imports
        from .models.channels import ChannelConnection, Channel
        from .models.properties import Property
        from .models.bookings import Booking, Guest, BookingMessage
        from .models.ai_models import PricingRule, MaintenanceTask
        from .models.payments import Payment
        from .models.notifications import NotificationRule

        # Check if user has any connected channels
        connected_channels = ChannelConnection.objects.filter(
            user=user,
            is_connected=True
        )
        context['has_connected_channels'] = connected_channels.exists()
        context['connected_channels_count'] = connected_channels.count()
        context['connected_channels'] = connected_channels

        # Check if user has any properties
        active_properties = Property.objects.filter(
            owner=user,
            is_active=True
        )
        context['has_properties'] = active_properties.exists()
        context['properties_count'] = active_properties.count()
        context['active_properties'] = active_properties

        # Check if user has any bookings
        user_bookings = Booking.objects.filter(
            rental_property__owner=user
        )
        context['has_bookings'] = user_bookings.exists()
        context['bookings_count'] = user_bookings.count()

        # Recent bookings check (last 30 days)
        thirty_days_ago = timezone.now() - timedelta(days=30)
        recent_bookings = user_bookings.filter(created_at__gte=thirty_days_ago)
        context['has_recent_bookings'] = recent_bookings.exists()
        context['recent_bookings_count'] = recent_bookings.count()

        # Confirmed bookings
        confirmed_bookings = user_bookings.filter(status='confirmed')
        context['has_confirmed_bookings'] = confirmed_bookings.exists()
        context['confirmed_bookings_count'] = confirmed_bookings.count()

        # Check for guest messages
        guest_messages = BookingMessage.objects.filter(
            booking__rental_property__owner=user
        )
        context['has_messages'] = guest_messages.exists()
        context['messages_count'] = guest_messages.count()
        context['unread_messages_count'] = guest_messages.filter(is_read=False).count()

        # Check for payments
        user_payments = Payment.objects.filter(
            booking__rental_property__owner=user
        )
        context['has_payments'] = user_payments.exists()
        context['payments_count'] = user_payments.count()

        # Check for guests
        user_guests = Guest.objects.filter(
            booking__rental_property__owner=user
        ).distinct()
        context['has_guests'] = user_guests.exists()
        context['guests_count'] = user_guests.count()

        # AI features status
        context['ai_features'] = {
            'pricing_rules': PricingRule.objects.filter(
                rental_property__owner=user,
                is_active=True
            ).count(),
            'maintenance_tasks': MaintenanceTask.objects.filter(
                rental_property__owner=user
            ).count(),
            'ai_enabled_properties': active_properties.filter(
                Q(ai_pricing_enabled=True) |
                Q(ai_maintenance_enabled=True) |
                Q(ai_guest_enabled=True) |
                Q(ai_analytics_enabled=True)
            ).count(),
            'notification_rules': NotificationRule.objects.filter(
                user=user,
                is_active=True
            ).count()
        }

        # Revenue data availability
        revenue_bookings = user_bookings.filter(
            status__in=['confirmed', 'checked_out'],
            total_price__gt=0
        )
        context['has_revenue_data'] = revenue_bookings.exists()
        context['total_revenue'] = revenue_bookings.aggregate(
            total=Sum('total_price')
        )['total'] or 0

        # Monthly revenue
        current_month = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        monthly_revenue = revenue_bookings.filter(
            created_at__gte=current_month
        ).aggregate(total=Sum('total_price'))['total'] or 0
        context['monthly_revenue'] = monthly_revenue
        context['has_monthly_revenue'] = monthly_revenue > 0

        # Analytics data availability
        context['analytics_data'] = {
            'has_occupancy_data': confirmed_bookings.exists(),
            'has_booking_trends': user_bookings.filter(
                created_at__gte=thirty_days_ago
            ).exists(),
            'has_channel_performance': connected_channels.exists() and user_bookings.exists(),
            'has_guest_analytics': user_guests.exists(),
            'avg_booking_value': revenue_bookings.aggregate(
                avg=Avg('total_price')
            )['avg'] or 0
        }

        # Calculate comprehensive sync status
        context['sync_status'] = {
            'channels_connected': connected_channels.count(),
            'properties_added': active_properties.count(),
            'total_bookings': user_bookings.count(),
            'recent_sync': connected_channels.filter(
                last_sync__gte=thirty_days_ago
            ).count(),
            'setup_progress': self._calculate_setup_progress(
                connected_channels.exists(),
                active_properties.exists(),
                user_bookings.exists()
            ),
            'is_fully_synced': self._is_fully_synced(
                connected_channels, active_properties, user_bookings
            )
        }

        # Determine the current empty state
        context['empty_state'] = self._determine_empty_state(
            connected_channels.exists(),
            active_properties.exists(),
            user_bookings.exists()
        )

        # Setup guidance
        context['setup_guidance'] = self._get_setup_guidance(context['empty_state'])

        # Data insights
        context['data_insights'] = self._get_data_insights(
            user, active_properties, user_bookings, connected_channels
        )

        # Performance metrics availability
        context['performance_metrics'] = {
            'has_response_time_data': guest_messages.exists(),
            'has_occupancy_rate': confirmed_bookings.exists(),
            'has_revenue_trends': revenue_bookings.filter(
                created_at__gte=thirty_days_ago
            ).exists(),
            'has_booking_patterns': user_bookings.filter(
                created_at__gte=timezone.now() - timedelta(days=90)
            ).count() >= 5
        }

        # Data completeness score
        context['data_completeness'] = self._calculate_data_completeness(
            connected_channels.exists(),
            active_properties.exists(),
            user_bookings.exists(),
            user_payments.exists(),
            guest_messages.exists()
        )

        return context

    def _calculate_setup_progress(self, has_channels, has_properties, has_bookings):
        """Calculate setup completion percentage"""
        progress = 0
        if has_channels:
            progress += 33
        if has_properties:
            progress += 33
        if has_bookings:
            progress += 34
        return progress

    def _is_fully_synced(self, channels, properties, bookings):
        """Determine if the account is fully synced and operational"""
        return (channels.exists() and
                properties.exists() and
                bookings.exists() and
                channels.filter(last_sync__gte=timezone.now() - timedelta(hours=24)).exists())

    def _determine_empty_state(self, has_channels, has_properties, has_bookings):
        """Determine which empty state to show"""
        if not has_channels:
            return 'no_channels'
        elif not has_properties:
            return 'no_properties'
        elif not has_bookings:
            return 'no_bookings'
        else:
            return None

    def _get_setup_guidance(self, empty_state):
        """Get contextual setup guidance based on current state"""
        guidance = {
            'no_channels': {
                'title': 'Connect Your First Channel',
                'description': 'Start by connecting your booking channels (Airbnb, Booking.com, etc.) to begin importing your reservations automatically.',
                'action_text': 'Connect Channels',
                'action_url': 'booking_vision_APP:channel_management',
                'icon': 'fas fa-link',
                'color': 'primary',
                'priority': 'high'
            },
            'no_properties': {
                'title': 'Add Your First Property',
                'description': 'You\'ve connected channels! Now add your properties to start managing bookings.',
                'action_text': 'Add Property',
                'action_url': 'booking_vision_APP:property_create',
                'icon': 'fas fa-home',
                'color': 'success',
                'priority': 'high'
            },
            'no_bookings': {
                'title': 'Sync Your Bookings',
                'description': 'Your channels are connected and properties are set up. Sync your existing bookings or wait for new ones to arrive.',
                'action_text': 'Sync Now',
                'action_url': 'booking_vision_APP:sync_bookings',
                'icon': 'fas fa-sync',
                'color': 'info',
                'priority': 'medium'
            }
        }
        return guidance.get(empty_state, {})

    def _get_data_insights(self, user, properties, bookings, channels):
        """Generate data insights and recommendations"""
        insights = []

        if properties.exists() and not bookings.exists():
            insights.append({
                'type': 'info',
                'icon': 'fas fa-lightbulb',
                'title': 'Setup Complete!',
                'message': 'Your properties are ready. Bookings will appear automatically as they come in.',
                'action': None,
                'priority': 'low'
            })

        if bookings.exists():
            confirmed_bookings = bookings.filter(status='confirmed').count()
            if confirmed_bookings > 0:
                insights.append({
                    'type': 'success',
                    'icon': 'fas fa-chart-line',
                    'title': f'{confirmed_bookings} Confirmed Booking{"s" if confirmed_bookings != 1 else ""}',
                    'message': 'Your business is active! Check analytics for insights.',
                    'action': {
                        'text': 'View Analytics',
                        'url': 'booking_vision_APP:analytics'
                    },
                    'priority': 'medium'
                })

        # AI recommendations
        ai_enabled_properties = properties.filter(
            Q(ai_pricing_enabled=True) |
            Q(ai_maintenance_enabled=True) |
            Q(ai_guest_enabled=True) |
            Q(ai_analytics_enabled=True)
        ).count()

        if properties.count() > 0 and ai_enabled_properties == 0:
            insights.append({
                'type': 'warning',
                'icon': 'fas fa-robot',
                'title': 'Enable AI Features',
                'message': 'Boost your revenue with AI-powered pricing and maintenance predictions.',
                'action': {
                    'text': 'Explore AI Features',
                    'url': 'booking_vision_APP:smart_pricing'
                },
                'priority': 'medium'
            })

        # Performance insights
        if bookings.count() >= 5:
            # Check for revenue optimization opportunities
            from .models.ai_models import PricingRule
            if not PricingRule.objects.filter(rental_property__owner=user, is_active=True).exists():
                insights.append({
                    'type': 'info',
                    'icon': 'fas fa-dollar-sign',
                    'title': 'Optimize Your Pricing',
                    'message': 'You have enough booking data to enable smart pricing recommendations.',
                    'action': {
                        'text': 'Enable Smart Pricing',
                        'url': 'booking_vision_APP:smart_pricing'
                    },
                    'priority': 'high'
                })

        return insights

    def _calculate_data_completeness(self, has_channels, has_properties, has_bookings, has_payments, has_messages):
        """Calculate overall data completeness percentage"""
        factors = [has_channels, has_properties, has_bookings, has_payments, has_messages]
        completed = sum(1 for factor in factors if factor)
        return int((completed / len(factors)) * 100)


class AnalyticsDataMixin(DataResponsiveMixin):
    """Specialized mixin for analytics views with enhanced data context"""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Analytics-specific data checks
        context['analytics_ready'] = (
            context['has_bookings'] and
            context['has_properties'] and
            context['bookings_count'] >= 3
        )

        context['chart_data_available'] = {
            'revenue': context['has_revenue_data'],
            'occupancy': context['has_confirmed_bookings'],
            'sources': context['has_connected_channels'] and context['has_bookings'],
            'trends': context['recent_bookings_count'] >= 5
        }

        return context


class PropertyDataMixin(DataResponsiveMixin):
    """Specialized mixin for property-related views"""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Property-specific insights
        if hasattr(self, 'object') and self.object:
            property_obj = self.object
            property_bookings = property_obj.booking_set.all()

            context['property_data'] = {
                'has_bookings': property_bookings.exists(),
                'bookings_count': property_bookings.count(),
                'revenue': property_bookings.filter(
                    status__in=['confirmed', 'checked_out']
                ).aggregate(total=Sum('total_price'))['total'] or 0,
                'ai_enabled': any([
                    property_obj.ai_pricing_enabled,
                    property_obj.ai_maintenance_enabled,
                    property_obj.ai_guest_enabled,
                    property_obj.ai_analytics_enabled
                ])
            }

        return context


class BookingDataMixin(DataResponsiveMixin):
    """Specialized mixin for booking-related views"""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Booking-specific data context
        today = timezone.now().date()

        context['booking_insights'] = {
            'todays_checkins': context.get('total_bookings', 0) and Booking.objects.filter(
                rental_property__owner=self.request.user,
                check_in_date=today,
                status='confirmed'
            ).count() or 0,
            'todays_checkouts': context.get('total_bookings', 0) and Booking.objects.filter(
                rental_property__owner=self.request.user,
                check_out_date=today,
                status='checked_in'
            ).count() or 0,
            'upcoming_checkins': context.get('total_bookings', 0) and Booking.objects.filter(
                rental_property__owner=self.request.user,
                check_in_date__gte=today,
                check_in_date__lte=today + timedelta(days=7),
                status='confirmed'
            ).count() or 0
        }

        return context