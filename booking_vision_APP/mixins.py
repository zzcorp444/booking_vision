"""
Data-responsive mixins for Booking Vision application.
This file contains mixins to add data availability context to views.
"""
from django.contrib.auth.mixins import LoginRequiredMixin


class DataResponsiveMixin:
    """Mixin to add data availability context to views"""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Check if user has any connected channels
        context['has_connected_channels'] = self.request.user.channelconnection_set.filter(
            is_connected=True
        ).exists()

        # Check if user has any properties
        context['has_properties'] = self.request.user.property_set.filter(
            is_active=True
        ).exists()

        # Check if user has any bookings
        context['has_bookings'] = self.request.user.property_set.filter(
            booking__isnull=False
        ).exists()

        # Calculate sync status
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
            )
        }

        # Determine empty state
        if not context['has_connected_channels']:
            context['empty_state'] = 'no_channels'
        elif not context['has_properties']:
            context['empty_state'] = 'no_properties'
        elif not context['has_bookings']:
            context['empty_state'] = 'no_bookings'
        else:
            context['empty_state'] = None

        return context