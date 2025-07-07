"""
Base channel integration class
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any
import requests
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class BaseChannelIntegration(ABC):
    """Abstract base class for channel integrations"""

    def __init__(self, api_key: str, api_secret: str = None):
        self.api_key = api_key
        self.api_secret = api_secret
        self.session = requests.Session()
        self.base_url = ""

    @abstractmethod
    def authenticate(self) -> bool:
        """Authenticate with the channel API"""
        pass

    @abstractmethod
    def fetch_bookings(self, property_id: str, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Fetch bookings from the channel"""
        pass

    @abstractmethod
    def update_availability(self, property_id: str, dates: List[datetime], available: bool) -> bool:
        """Update availability on the channel"""
        pass

    @abstractmethod
    def update_rates(self, property_id: str, rates: Dict[datetime, float]) -> bool:
        """Update rates on the channel"""
        pass

    @abstractmethod
    def send_message(self, booking_id: str, message: str) -> bool:
        """Send message to guest through channel"""
        pass

    def make_request(self, method: str, endpoint: str, data: Dict = None) -> Dict:
        """Make API request with error handling"""
        url = f"{self.base_url}/{endpoint}"

        try:
            response = self.session.request(
                method=method,
                url=url,
                json=data,
                headers=self.get_headers()
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {str(e)}")
            raise

    def get_headers(self) -> Dict[str, str]:
        """Get request headers"""
        return {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }