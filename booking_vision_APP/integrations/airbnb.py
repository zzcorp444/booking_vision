"""
Airbnb API integration
"""
from .base_channel import BaseChannelIntegration
from typing import Dict, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class AirbnbIntegration(BaseChannelIntegration):
    """Airbnb API integration class"""

    def __init__(self, api_key: str, api_secret: str = None):
        super().__init__(api_key, api_secret)
        self.base_url = "https://api.airbnb.com/v2"

    def authenticate(self) -> bool:
        """Authenticate with Airbnb API"""
        try:
            # Airbnb uses OAuth 2.0
            response = self.make_request(
                'POST',
                'oauth/token',
                {
                    'grant_type': 'client_credentials',
                    'client_id': self.api_key,
                    'client_secret': self.api_secret
                }
            )

            if 'access_token' in response:
                self.session.headers.update({
                    'Authorization': f"Bearer {response['access_token']}"
                })
                return True
            return False

        except Exception as e:
            logger.error(f"Airbnb authentication failed: {str(e)}")
            return False

    def fetch_bookings(self, property_id: str, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Fetch bookings from Airbnb"""
        try:
            response = self.make_request(
                'GET',
                f'listings/{property_id}/reservations',
                {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'status': 'accepted,pending'
                }
            )

            bookings = []
            for reservation in response.get('reservations', []):
                bookings.append({
                    'external_id': reservation['confirmation_code'],
                    'guest_name': reservation['guest']['first_name'] + ' ' + reservation['guest']['last_name'],
                    'guest_email': reservation['guest']['email'],
                    'check_in': reservation['start_date'],
                    'check_out': reservation['end_date'],
                    'guests': reservation['number_of_guests'],
                    'total_price': reservation['total_paid_amount'],
                    'status': self._map_status(reservation['status'])
                })

            return bookings

        except Exception as e:
            logger.error(f"Failed to fetch Airbnb bookings: {str(e)}")
            return []

    def update_availability(self, property_id: str, dates: List[datetime], available: bool) -> bool:
        """Update availability on Airbnb"""
        try:
            calendar_updates = []
            for date in dates:
                calendar_updates.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'availability': 'available' if available else 'blocked',
                    'min_nights': 1
                })

            response = self.make_request(
                'PUT',
                f'listings/{property_id}/calendar',
                {'calendar': calendar_updates}
            )

            return response.get('status') == 'success'

        except Exception as e:
            logger.error(f"Failed to update Airbnb availability: {str(e)}")
            return False

    def update_rates(self, property_id: str, rates: Dict[datetime, float]) -> bool:
        """Update rates on Airbnb"""
        try:
            pricing_updates = []
            for date, rate in rates.items():
                pricing_updates.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'price': int(rate),
                    'currency': 'USD'
                })

            response = self.make_request(
                'PUT',
                f'listings/{property_id}/pricing',
                {'pricing': pricing_updates}
            )

            return response.get('status') == 'success'

        except Exception as e:
            logger.error(f"Failed to update Airbnb rates: {str(e)}")
            return False

    def send_message(self, booking_id: str, message: str) -> bool:
        """Send message to guest through Airbnb"""
        try:
            response = self.make_request(
                'POST',
                f'reservations/{booking_id}/messages',
                {
                    'message': message,
                    'type': 'host_to_guest'
                }
            )

            return response.get('status') == 'success'

        except Exception as e:
            logger.error(f"Failed to send Airbnb message: {str(e)}")
            return False

    def _map_status(self, airbnb_status: str) -> str:
        """Map Airbnb status to internal status"""
        status_map = {
            'accepted': 'confirmed',
            'pending': 'pending',
            'cancelled': 'cancelled',
            'declined': 'cancelled'
        }
        return status_map.get(airbnb_status, 'pending')