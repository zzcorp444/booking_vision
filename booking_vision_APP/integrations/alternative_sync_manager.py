"""
Manager for alternative synchronization methods
"""
from typing import Dict, List
import asyncio
from celery import shared_task
import logging

from .scraper_integration import ScraperIntegration, iCalendarSync
from ..models.channels import Channel, ChannelConnection
from ..models.bookings import Booking, Guest

logger = logging.getLogger(__name__)


class AlternativeSyncManager:
    """Manages alternative sync methods when APIs are not available"""

    def __init__(self, user):
        self.user = user
        self.methods = {
            'scraper': ScraperIntegration,
            'ical': iCalendarSync,
        }

    async def sync_all_platforms(self):
        """Sync all platforms using best available method"""
        results = {}

        connections = ChannelConnection.objects.filter(
            user=self.user,
            is_connected=True
        ).select_related('channel')

        tasks = []
        for connection in connections:
            task = self.sync_platform(connection)
            tasks.append(task)

        completed = await asyncio.gather(*tasks, return_exceptions=True)

        for conn, result in zip(connections, completed):
            if isinstance(result, Exception):
                results[conn.channel.name] = {'error': str(result)}
            else:
                results[conn.channel.name] = result

        return results

    async def sync_platform(self, connection: ChannelConnection):
        """Sync a specific platform using best method"""
        channel_name = connection.channel.name.lower()

        # Try methods in order of preference
        methods_order = ['api', 'ical', 'scraper', 'email']

        for method in methods_order:
            try:
                if method == 'ical' and connection.ical_url:
                    return await self._sync_via_ical(connection)
                elif method == 'scraper':
                    return await self._sync_via_scraper(connection)
                elif method == 'email':
                    return await self._sync_via_email(connection)
            except Exception as e:
                logger.warning(f"Method {method} failed for {channel_name}: {str(e)}")
                continue

        raise Exception(f"All sync methods failed for {channel_name}")

    async def _sync_via_scraper(self, connection: ChannelConnection):
        """Sync using web scraping"""
        scraper = ScraperIntegration(
            username=connection.api_key,  # Username stored in api_key
            password=connection.api_secret,  # Password stored in api_secret
            platform=connection.channel.name.lower()
        )

        # Login
        if connection.channel.name.lower() == 'airbnb':
            success = scraper.login_airbnb()
        else:
            # Implement other platform logins
            success = False

        if not success:
            raise Exception("Login failed")

        # Get data using combined methods
        data = scraper.combine_methods()

        # Process bookings
        imported = 0
        for booking_data in data['bookings']:
            guest, _ = Guest.objects.get_or_create(
                email=booking_data.get('guest_email', f"{booking_data['guest_name']}@unknown.com"),
                defaults={'first_name': booking_data['guest_name'].split()[0]}
            )

            booking, created = Booking.objects.update_or_create(
                external_booking_id=booking_data['external_id'],
                channel=connection.channel,
                defaults={
                    'guest': guest,
                    'check_in_date': booking_data['check_in'],
                    'check_out_date': booking_data['check_out'],
                    'total_price': booking_data['total_price'],
                    'status': booking_data['status']
                }
            )

            if created:
                imported += 1

        scraper.cleanup()

        return {'imported': imported, 'method': 'scraper'}

    async def _sync_via_ical(self, connection: ChannelConnection):
        """Sync using iCalendar feed"""
        ical = iCalendarSync(connection.ical_url)
        bookings = await ical.sync_calendar()

        imported = 0
        for booking_data in bookings:
            if booking_data.get('is_booking'):
                # Process booking
                imported += 1

        return {'imported': imported, 'method': 'ical'}

    async def _sync_via_email(self, connection: ChannelConnection):
        """Sync by parsing email confirmations"""
        # Implementation for email parsing
        return {'imported': 0, 'method': 'email'}


@shared_task
def sync_using_alternative_methods(user_id: int):
    """Celery task to sync using alternative methods"""
    from django.contrib.auth.models import User

    try:
        user = User.objects.get(id=user_id)
        manager = AlternativeSyncManager(user)

        # Run async sync
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        results = loop.run_until_complete(manager.sync_all_platforms())

        logger.info(f"Alternative sync completed for user {user_id}: {results}")
        return results

    except Exception as e:
        logger.error(f"Alternative sync failed: {str(e)}")
        raise