"""
Channel synchronization manager
"""
import logging
from typing import Dict, List
from datetime import datetime, timedelta
from django.utils import timezone
from celery import shared_task

from ..models.channels import Channel, ChannelConnection, PropertyChannel
from ..models.bookings import Booking, Guest
from ..models.properties import Property
from .airbnb import AirbnbIntegration
from .booking_com import BookingComIntegration

logger = logging.getLogger(__name__)


class SyncManager:
    """Manages synchronization across all channels"""

    CHANNEL_INTEGRATIONS = {
        'Airbnb': AirbnbIntegration,
        'Booking.com': BookingComIntegration,
        # Add more channels here
    }

    def __init__(self, user):
        self.user = user
        self.integrations = {}
        self._initialize_integrations()

    def _initialize_integrations(self):
        """Initialize channel integrations"""
        connections = ChannelConnection.objects.filter(
            user=self.user,
            is_connected=True
        ).select_related('channel')

        for connection in connections:
            channel_name = connection.channel.name
            if channel_name in self.CHANNEL_INTEGRATIONS:
                integration_class = self.CHANNEL_INTEGRATIONS[channel_name]
                integration = integration_class(
                    connection.api_key,
                    connection.api_secret
                )

                if integration.authenticate():
                    self.integrations[channel_name] = integration
                else:
                    logger.error(f"Failed to authenticate {channel_name}")

    def sync_all_bookings(self):
        """Sync bookings from all channels"""
        results = {}

        for channel_name, integration in self.integrations.items():
            try:
                results[channel_name] = self._sync_channel_bookings(channel_name, integration)
            except Exception as e:
                logger.error(f"Error syncing {channel_name}: {str(e)}")
                results[channel_name] = {'error': str(e)}

        return results

    def _sync_channel_bookings(self, channel_name: str, integration):
        """Sync bookings from a specific channel"""
        channel = Channel.objects.get(name=channel_name)
        property_channels = PropertyChannel.objects.filter(
            channel_connection__user=self.user,
            channel=channel,
            is_active=True
        ).select_related('rental_property')

        total_synced = 0

        for pc in property_channels:
            # Fetch bookings for last 90 days
            start_date = timezone.now() - timedelta(days=90)
            end_date = timezone.now() + timedelta(days=365)

            bookings = integration.fetch_bookings(
                pc.external_property_id,
                start_date,
                end_date
            )

            for booking_data in bookings:
                # Create or update booking
                guest, _ = Guest.objects.get_or_create(
                    email=booking_data['guest_email'],
                    defaults={
                        'first_name': booking_data['guest_name'].split()[0],
                        'last_name': ' '.join(booking_data['guest_name'].split()[1:]),
                    }
                )

                booking, created = Booking.objects.update_or_create(
                    external_booking_id=booking_data['external_id'],
                    channel=channel,
                    defaults={
                        'rental_property': pc.rental_property,
                        'guest': guest,
                        'check_in_date': booking_data['check_in'],
                        'check_out_date': booking_data['check_out'],
                        'num_guests': booking_data['guests'],
                        'total_price': booking_data['total_price'],
                        'status': booking_data['status']
                    }
                )

                if created:
                    total_synced += 1

            # Update last sync time
            pc.last_sync = timezone.now()
            pc.save()

        return {'synced': total_synced}

    def push_availability(self, property: Property, dates: List[datetime], available: bool):
        """Push availability updates to all channels"""
        results = {}

        property_channels = PropertyChannel.objects.filter(
            rental_property=property,
            is_active=True,
            sync_availability=True
        ).select_related('channel')

        for pc in property_channels:
            channel_name = pc.channel.name
            if channel_name in self.integrations:
                try:
                    success = self.integrations[channel_name].update_availability(
                        pc.external_property_id,
                        dates,
                        available
                    )
                    results[channel_name] = success
                except Exception as e:
                    logger.error(f"Error updating availability on {channel_name}: {str(e)}")
                    results[channel_name] = False

        return results

    def push_rates(self, property: Property, rates: Dict[datetime, float]):
        """Push rate updates to all channels"""
        results = {}

        property_channels = PropertyChannel.objects.filter(
            rental_property=property,
            is_active=True,
            sync_rates=True
        ).select_related('channel')

        for pc in property_channels:
            channel_name = pc.channel.name
            if channel_name in self.integrations:
                try:
                    success = self.integrations[channel_name].update_rates(
                        pc.external_property_id,
                        rates
                    )
                    results[channel_name] = success
                except Exception as e:
                    logger.error(f"Error updating rates on {channel_name}: {str(e)}")
                    results[channel_name] = False

        return results


@shared_task
def sync_all_users_bookings():
    """Celery task to sync bookings for all users"""
    from django.contrib.auth.models import User

    for user in User.objects.filter(is_active=True):
        try:
            sync_manager = SyncManager(user)
            sync_manager.sync_all_bookings()
        except Exception as e:
            logger.error(f"Error syncing bookings for user {user.id}: {str(e)}")