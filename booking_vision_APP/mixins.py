"""
Data-responsive mixins for Booking Vision application.
This file contains mixins to add data availability context to views.
"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum, Count, Q
from datetime import datetime, timedelta
from django.utils import timezone


class DataResponsiveMixin:
    """Enhanced mixin to add comprehensive data availability context to views"""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Basic data availability checks
        context['has_connected_channels'] = self.request.user.channelconnection_set.filter(
            is_connected=True
        ).exists()

        context['has_properties'] = self.request.user.property_set.filter(
            is_active=True
        ).exists()

        context['has_bookings'] = self.request.user.property_set.filter(
            booking__isnull=False
        ).exists()

        # Enhanced data availability checks
        context['has_recent_bookings'] = self.request.user.property_set.filter(
            booking__created_at__gte=timezone.now() - timedelta(days=30)
        ).exists()

        context['has_confirmed_bookings'] = self.request.user.property_set.filter(
            booking__status='confirmed'
        ).exists()

        context['has_revenue'] = self.request.user.property_set.filter(
            booking__status__in=['confirmed', 'checked_out'],
            booking__total_price__gt=0
        ).exists()

        context['has_messages'] = False
        try:
            from .models.bookings import BookingMessage
            context['has_messages'] = BookingMessage.objects.filter(
                booking__rental_property__owner=self.request.user
            ).exists()
        except:
            pass

        context['has_activities'] = False
        try:
            # Check for any recent activity (bookings, messages, etc.)
            context['has_activities'] = (
                context['has_recent_bookings'] or 
                context['has_messages']
            )
        except:
            pass

        # Enhanced sync status
        context['sync_status'] = {
            'channels_connected': self.request.user.channelconnection_set.filter(
                is_connected=True
            ).count(),
            'properties_added': self.request.user.property_set.filter(
                is_active=True
            ).count(),
            'total_bookings': sum(
                prop.booking_set.count()
                for prop in self.request.user.property_set.all()
            ),
            'confirmed_bookings': sum(
                prop.booking_set.filter(status='confirmed').count()
                for prop in self.request.user.property_set.all()
            ),
            'total_revenue': 0
        }

        # Calculate total revenue safely
        try:
            revenue_sum = self.request.user.property_set.aggregate(
                total=Sum('booking__total_price', filter=Q(booking__status__in=['confirmed', 'checked_out']))
            )['total']
            context['sync_status']['total_revenue'] = revenue_sum or 0
        except:
            context['sync_status']['total_revenue'] = 0

        # Setup progress calculation
        context['setup_progress'] = self._calculate_setup_progress()

        # Determine primary empty state (hierarchical)
        if not context['has_connected_channels']:
            context['empty_state'] = 'no_channels'
        elif not context['has_properties']:
            context['empty_state'] = 'no_properties'
        elif not context['has_bookings']:
            context['empty_state'] = 'no_bookings'
        else:
            context['empty_state'] = None

        # Context-specific empty states for different sections
        context['empty_states'] = {
            'analytics': not context['has_revenue'],
            'activities': not context['has_activities'],
            'messages': not context['has_messages'],
            'recent_bookings': not context['has_recent_bookings']
        }

        # Onboarding flags
        context['show_onboarding'] = not context['has_connected_channels']
        context['show_setup_guide'] = context['sync_status']['channels_connected'] < 2
        context['show_property_guide'] = context['sync_status']['properties_added'] == 0

        return context

    def _calculate_setup_progress(self):
        """Calculate user's setup progress"""
        steps_completed = 0
        total_steps = 4  # Increased from 3 to 4 steps

        # Step 1: Connect at least one channel
        if self.request.user.channelconnection_set.filter(is_connected=True).exists():
            steps_completed += 1

        # Step 2: Add at least one property
        if self.request.user.property_set.filter(is_active=True).exists():
            steps_completed += 1

        # Step 3: Get first booking
        if self.request.user.property_set.filter(booking__isnull=False).exists():
            steps_completed += 1

        # Step 4: Have confirmed bookings with revenue
        if self.request.user.property_set.filter(
            booking__status__in=['confirmed', 'checked_out'],
            booking__total_price__gt=0
        ).exists():
            steps_completed += 1

        return {
            'completed': steps_completed,
            'total': total_steps,
            'percentage': (steps_completed / total_steps) * 100,
            'next_step': self._get_next_setup_step(steps_completed)
        }

    def _get_next_setup_step(self, completed_steps):
        """Get the next recommended setup step"""
        steps = [
            {
                'title': 'Connect Your First Channel',
                'description': 'Connect to Airbnb, Booking.com, or another channel to start receiving bookings.',
                'action_url': 'booking_vision_APP:channel_management',
                'action_text': 'Connect Channel'
            },
            {
                'title': 'Add Your First Property',
                'description': 'Add your rental property details to start managing bookings.',
                'action_url': 'booking_vision_APP:property_create',
                'action_text': 'Add Property'
            },
            {
                'title': 'Get Your First Booking',
                'description': 'Wait for bookings to come in, or add a manual booking to test the system.',
                'action_url': 'booking_vision_APP:booking_create',
                'action_text': 'Add Manual Booking'
            },
            {
                'title': 'Complete Setup',
                'description': 'Your account is fully set up! Explore analytics and AI features.',
                'action_url': 'booking_vision_APP:analytics',
                'action_text': 'View Analytics'
            }
        ]

        if completed_steps < len(steps):
            return steps[completed_steps]
        else:
            return steps[-1]  # Return the last step if all are completed