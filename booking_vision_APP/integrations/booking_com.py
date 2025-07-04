"""
Booking.com API integration
"""
from .base_channel import BaseChannelIntegration
from typing import Dict, List
from datetime import datetime
import xml.etree.ElementTree as ET
import logging

logger = logging.getLogger(__name__)


class BookingComIntegration(BaseChannelIntegration):
    """Booking.com API integration class"""

    def __init__(self, api_key: str, api_secret: str = None):
        super().__init__(api_key, api_secret)
        self.base_url = "https://secure-supply-xml.booking.com/api"

    def authenticate(self) -> bool:
        """Authenticate with Booking.com API"""
        try:
            # Booking.com uses basic authentication
            self.session.auth = (self.api_key, self.api_secret)

            # Test authentication
            response = self.make_request('GET', 'properties')
            return response is not None

        except Exception as e:
            logger.error(f"Booking.com authentication failed: {str(e)}")
            return False

    def fetch_bookings(self, property_id: str, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Fetch bookings from Booking.com"""
        try:
            # Booking.com uses XML API
            xml_request = f"""
            <request>
                <hotel_id>{property_id}</hotel_id>
                <date_from>{start_date.strftime('%Y-%m-%d')}</date_from>
                <date_to>{end_date.strftime('%Y-%m-%d')}</date_to>
            </request>
            """

            response = self.session.post(
                f"{self.base_url}/reservations",
                data=xml_request,
                headers={'Content-Type': 'application/xml'}
            )

            # Parse XML response
            root = ET.fromstring(response.text)
            bookings = []

            for reservation in root.findall('.//reservation'):
                bookings.append({
                    'external_id': reservation.find('id').text,
                    'guest_name': f"{reservation.find('customer/first_name').text} {reservation.find('customer/last_name').text}",
                    'guest_email': reservation.find('customer/email').text,
                    'check_in': reservation.find('checkin').text,
                    'check_out': reservation.find('checkout').text,
                    'guests': int(reservation.find('numberofguests').text),
                    'total_price': float(reservation.find('totalprice').text),
                    'status': self._map_status(reservation.find('status').text)
                })

            return bookings

        except Exception as e:
            logger.error(f"Failed to fetch Booking.com bookings: {str(e)}")
            return []

    def update_availability(self, property_id: str, dates: List[datetime], available: bool) -> bool:
        """Update availability on Booking.com"""
        try:
            # Build XML request
            availability_xml = '<availability>'
            for date in dates:
                availability_xml += f"""
                <date value="{date.strftime('%Y-%m-%d')}">
                    <available>{1 if available else 0}</available>
                </date>
                """
            availability_xml += '</availability>'

            response = self.session.post(
                f"{self.base_url}/availability",
                data=f"<request><hotel_id>{property_id}</hotel_id>{availability_xml}</request>",
                headers={'Content-Type': 'application/xml'}
            )

            return response.status_code == 200

        except Exception as e:
            logger.error(f"Failed to update Booking.com availability: {str(e)}")
            return False

    def update_rates(self, property_id: str, rates: Dict[datetime, float]) -> bool:
        """Update rates on Booking.com"""
        try:
            # Build XML request
            rates_xml = '<rates>'
            for date, rate in rates.items():
                rates_xml += f"""
                <rate>
                    <date>{date.strftime('%Y-%m-%d')}</date>
                    <price>{rate}</price>
                    <currency>USD</currency>
                </rate>
                """
            rates_xml += '</rates>'

            response = self.session.post(
                f"{self.base_url}/rates",
                data=f"<request><hotel_id>{property_id}</hotel_id>{rates_xml}</request>",
                headers={'Content-Type': 'application/xml'}
            )

            return response.status_code == 200

        except Exception as e:
            logger.error(f"Failed to update Booking.com rates: {str(e)}")
            return False

    def send_message(self, booking_id: str, message: str) -> bool:
        """Send message to guest through Booking.com"""
        try:
            message_xml = f"""
            <request>
                <reservation_id>{booking_id}</reservation_id>
                <message>{message}</message>
            </request>
            """

            response = self.session.post(
                f"{self.base_url}/messages",
                data=message_xml,
                headers={'Content-Type': 'application/xml'}
            )

            return response.status_code == 200

        except Exception as e:
            logger.error(f"Failed to send Booking.com message: {str(e)}")
            return False

    def _map_status(self, booking_status: str) -> str:
        """Map Booking.com status to internal status"""
        status_map = {
            'ok': 'confirmed',
            'cancelled': 'cancelled',
            'pending': 'pending'
        }
        return status_map.get(booking_status, 'pending')