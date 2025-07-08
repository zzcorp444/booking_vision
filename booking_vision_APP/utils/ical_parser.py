"""
iCal parsing and generation utilities
"""
import icalendar
from datetime import datetime, date
from typing import List, Dict, Optional
import requests
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class iCalParser:
    """Parse iCal feeds from booking channels"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'BookingVision/1.0 (Calendar Sync)'
        })

    def fetch_and_parse(self, ical_url: str) -> List[Dict]:
        """Fetch iCal feed and parse events"""
        try:
            response = self.session.get(ical_url, timeout=30)
            response.raise_for_status()

            cal = icalendar.Calendar.from_ical(response.content)
            events = []

            for component in cal.walk():
                if component.name == "VEVENT":
                    event = self._parse_event(component)
                    if event:
                        events.append(event)

            return events

        except Exception as e:
            logger.error(f"Error fetching iCal feed {ical_url}: {str(e)}")
            return []

    def _parse_event(self, component) -> Optional[Dict]:
        """Parse individual iCal event"""
        try:
            summary = str(component.get('SUMMARY', ''))
            description = str(component.get('DESCRIPTION', ''))

            # Extract dates
            dtstart = component.get('DTSTART')
            dtend = component.get('DTEND')

            if not dtstart or not dtend:
                return None

            # Handle date vs datetime
            start_date = dtstart.dt
            end_date = dtend.dt

            if isinstance(start_date, datetime):
                start_date = start_date.date()
            if isinstance(end_date, datetime):
                end_date = end_date.date()

            # Parse channel-specific information
            booking_info = self._extract_booking_info(summary, description)

            return {
                'summary': summary,
                'description': description,
                'start_date': start_date,
                'end_date': end_date,
                'uid': str(component.get('UID', '')),
                'booking_info': booking_info
            }

        except Exception as e:
            logger.error(f"Error parsing iCal event: {str(e)}")
            return None

    def _extract_booking_info(self, summary: str, description: str) -> Dict:
        """Extract booking information from summary and description"""
        import re

        booking_info = {
            'guest_name': None,
            'confirmation_code': None,
            'channel': None,
            'status': 'confirmed'
        }

        # Airbnb patterns
        airbnb_match = re.search(r'Reserved - (.*?) \((HM\w+)\)', summary)
        if airbnb_match:
            booking_info.update({
                'guest_name': airbnb_match.group(1),
                'confirmation_code': airbnb_match.group(2),
                'channel': 'Airbnb'
            })
            return booking_info

        # Booking.com patterns
        booking_com_match = re.search(r'Booking:\s*(\d+)', summary)
        if booking_com_match:
            booking_info.update({
                'confirmation_code': booking_com_match.group(1),
                'channel': 'Booking.com'
            })

        # VRBO patterns
        vrbo_match = re.search(r'VRBO.*?(\d{7,})', summary)
        if vrbo_match:
            booking_info.update({
                'confirmation_code': vrbo_match.group(1),
                'channel': 'VRBO'
            })

        # Generic guest name extraction
        if not booking_info['guest_name']:
            # Try to extract from description
            guest_match = re.search(r'Guest[:\s]+([\w\s]+)', description, re.IGNORECASE)
            if guest_match:
                booking_info['guest_name'] = guest_match.group(1).strip()

        return booking_info


class iCalGenerator:
    """Generate iCal feeds for property availability"""

    def __init__(self):
        self.cal = icalendar.Calendar()
        self.cal.add('prodid', '-//Booking Vision//Property Calendar//EN')
        self.cal.add('version', '2.0')
        self.cal.add('calscale', 'GREGORIAN')
        self.cal.add('method', 'PUBLISH')

    def add_booking(self, booking):
        """Add a booking to the calendar"""
        from ..models.bookings import Booking

        event = icalendar.Event()

        # Basic event info
        event.add('uid', f'booking-{booking.id}@bookingvision.com')
        event.add('dtstart', booking.check_in_date)
        event.add('dtend', booking.check_out_date)
        event.add('dtstamp', timezone.now())

        # Summary and description
        event.add('summary', f'RESERVED - {booking.guest.first_name} {booking.guest.last_name}')
        event.add('description', f'''
Property: {booking.rental_property.name}
Guest: {booking.guest.first_name} {booking.guest.last_name}
Email: {booking.guest.email}
Phone: {booking.guest.phone or 'Not provided'}
Guests: {booking.num_guests}
Status: {booking.get_status_display()}
Total: ${booking.total_price}
Channel: {booking.channel.name}
Confirmation: {booking.external_booking_id or booking.id}
        '''.strip())

        # Status
        if booking.status == 'confirmed':
            event.add('status', 'CONFIRMED')
        elif booking.status == 'cancelled':
            event.add('status', 'CANCELLED')
        else:
            event.add('status', 'TENTATIVE')

        # Categories
        event.add('categories', ['BOOKING', booking.channel.name.upper()])

        self.cal.add_component(event)

    def add_blocked_dates(self, property, start_date, end_date, reason='Blocked'):
        """Add blocked dates to calendar"""
        event = icalendar.Event()

        event.add('uid', f'blocked-{property.id}-{start_date}@bookingvision.com')
        event.add('dtstart', start_date)
        event.add('dtend', end_date)
        event.add('dtstamp', timezone.now())
        event.add('summary', f'BLOCKED - {reason}')
        event.add('description', f'Property: {property.name}\nReason: {reason}')
        event.add('status', 'CONFIRMED')
        event.add('categories', ['BLOCKED'])

        self.cal.add_component(event)

    def generate_property_calendar(self, property):
        """Generate complete calendar for a property"""
        from ..models.bookings import Booking

        # Add property info to calendar
        self.cal.add('x-wr-calname', f'{property.name} - Booking Calendar')
        self.cal.add('x-wr-caldesc', f'Booking calendar for {property.name}')

        # Add all bookings
        bookings = Booking.objects.filter(
            rental_property=property,
            status__in=['confirmed', 'checked_in', 'checked_out']
        )

        for booking in bookings:
            self.add_booking(booking)

        return self.cal.to_ical()

    def export_to_file(self, filename: str):
        """Export calendar to file"""
        with open(filename, 'wb') as f:
            f.write(self.cal.to_ical())


class iCalSyncService:
    """Service for syncing with iCal feeds"""

    def __init__(self):
        self.parser = iCalParser()

    def sync_channel_calendar(self, channel_connection):
        """Sync bookings from channel iCal feed"""
        from ..models.bookings import Booking, Guest
        from ..models.channels import Channel
        from ..models.properties import Property

        if not channel_connection.ical_url:
            logger.warning(f"No iCal URL for {channel_connection.channel.name}")
            return {'success': False, 'error': 'No iCal URL configured'}

        try:
            # Fetch and parse events
            events = self.parser.fetch_and_parse(channel_connection.ical_url)

            synced_count = 0
            errors = []

            # Get user's first property (you might want to improve this mapping)
            property = Property.objects.filter(owner=channel_connection.user).first()
            if not property:
                return {'success': False, 'error': 'No property found for user'}

            for event in events:
                try:
                    booking_info = event['booking_info']

                    if not booking_info.get('confirmation_code'):
                        continue

                    # Create or get guest
                    guest_name = booking_info.get('guest_name', 'Unknown Guest')
                    name_parts = guest_name.split(' ', 1)

                    guest, created = Guest.objects.get_or_create(
                        email=f"{booking_info['confirmation_code']}@{channel_connection.channel.name.lower()}.com",
                        defaults={
                            'first_name': name_parts[0],
                            'last_name': name_parts[1] if len(name_parts) > 1 else ''
                        }
                    )

                    # Create or update booking
                    booking, created = Booking.objects.update_or_create(
                        external_booking_id=booking_info['confirmation_code'],
                        channel=channel_connection.channel,
                        defaults={
                            'rental_property': property,
                            'guest': guest,
                            'check_in_date': event['start_date'],
                            'check_out_date': event['end_date'],
                            'num_guests': 1,  # Default, channels usually don't provide this in iCal
                            'total_price': 0,  # Will need to be updated manually or from other sources
                            'base_price': 0,
                            'status': booking_info.get('status', 'confirmed')
                        }
                    )

                    if created:
                        synced_count += 1

                except Exception as e:
                    logger.error(f"Error processing event: {str(e)}")
                    errors.append(str(e))
                    continue

            # Update last sync time
            channel_connection.last_sync = timezone.now()
            channel_connection.save()

            return {
                'success': True,
                'synced_count': synced_count,
                'total_events': len(events),
                'errors': errors
            }

        except Exception as e:
            logger.error(f"Error syncing iCal for {channel_connection.channel.name}: {str(e)}")
            return {'success': False, 'error': str(e)}