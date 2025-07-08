# booking_vision_APP/integrations/no_api_sync_manager.py
"""
No-API Sync Manager - Combines multiple techniques for channel synchronization
"""
import asyncio
from typing import Dict, List, Any
from datetime import datetime, timedelta
import icalendar
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import imaplib
import email
from email.header import decode_header
import re
import json
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)


class NoAPIChannelSync:
    """Main synchronization manager without API keys"""

    def __init__(self, user):
        self.user = user
        self.sync_methods = {
            'Airbnb': AirbnbNoAPISync(),
            'Booking.com': BookingComNoAPISync(),
            'VRBO': VRBONoAPISync(),
            'Expedia': ExpediaNoAPISync(),
            'Agoda': AgodaNoAPISync()
        }

    async def sync_all_channels(self):
        """Sync all channels using multiple methods"""
        results = {}

        for channel_name, sync_method in self.sync_methods.items():
            try:
                # Try multiple sync methods in order of preference
                result = await self._sync_channel_cascade(channel_name, sync_method)
                results[channel_name] = result
            except Exception as e:
                logger.error(f"Failed to sync {channel_name}: {str(e)}")
                results[channel_name] = {'error': str(e)}

        return results

    async def _sync_channel_cascade(self, channel_name: str, sync_method):
        """Try multiple sync methods in cascade"""
        methods = [
            ('ical', sync_method.sync_via_ical),
            ('email', sync_method.sync_via_email),
            ('scraping', sync_method.sync_via_scraping),
            ('browser_extension', sync_method.sync_via_extension),
            ('mobile_api', sync_method.sync_via_mobile_api)
        ]

        for method_name, method_func in methods:
            try:
                logger.info(f"Trying {method_name} for {channel_name}")
                result = await method_func(self.user)
                if result.get('success'):
                    result['method_used'] = method_name
                    return result
            except Exception as e:
                logger.warning(f"{method_name} failed for {channel_name}: {str(e)}")
                continue

        return {'success': False, 'error': 'All sync methods failed'}


class BaseChannelNoAPISync:
    """Base class for channel-specific sync implementations"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    async def sync_via_ical(self, user) -> Dict:
        """Sync using iCal feeds"""
        raise NotImplementedError

    async def sync_via_email(self, user) -> Dict:
        """Sync by parsing email notifications"""
        raise NotImplementedError

    async def sync_via_scraping(self, user) -> Dict:
        """Sync by web scraping"""
        raise NotImplementedError

    async def sync_via_extension(self, user) -> Dict:
        """Sync using browser extension"""
        raise NotImplementedError

    async def sync_via_mobile_api(self, user) -> Dict:
        """Sync using reverse-engineered mobile API"""
        raise NotImplementedError


class AirbnbNoAPISync(BaseChannelNoAPISync):
    """Airbnb-specific sync without API"""

    async def sync_via_ical(self, user) -> Dict:
        """Sync Airbnb using iCal"""
        try:
            # Get iCal URL from user's channel settings
            channel_conn = await self._get_channel_connection(user, 'Airbnb')
            if not channel_conn.ical_url:
                return {'success': False, 'error': 'No iCal URL configured'}

            # Fetch and parse iCal
            response = self.session.get(channel_conn.ical_url)
            cal = icalendar.Calendar.from_ical(response.content)

            bookings = []
            for event in cal.walk('VEVENT'):
                booking_data = self._parse_airbnb_ical_event(event)
                if booking_data:
                    bookings.append(booking_data)

            # Save bookings
            saved_count = await self._save_bookings(user, bookings, 'Airbnb')

            return {
                'success': True,
                'bookings_found': len(bookings),
                'bookings_saved': saved_count
            }

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _parse_airbnb_ical_event(self, event) -> Dict:
        """Parse Airbnb iCal event"""
        try:
            summary = str(event.get('SUMMARY', ''))
            description = str(event.get('DESCRIPTION', ''))

            # Extract booking details from summary/description
            # Airbnb format: "Reserved - Guest Name (HMXXXXXXX)"
            if 'Reserved' in summary or 'Blocked' in summary:
                match = re.search(r'Reserved - (.*?) \((HM\w+)\)', summary)
                if match:
                    guest_name = match.group(1)
                    confirmation_code = match.group(2)

                    return {
                        'external_booking_id': confirmation_code,
                        'guest_name': guest_name,
                        'check_in': event.get('DTSTART').dt,
                        'check_out': event.get('DTEND').dt,
                        'status': 'confirmed',
                        'channel': 'Airbnb'
                    }

            return None

        except Exception as e:
            logger.error(f"Error parsing Airbnb event: {str(e)}")
            return None

    async def sync_via_email(self, user) -> Dict:
        """Parse Airbnb booking emails"""
        try:
            email_config = await self._get_email_config(user)

            # Connect to email
            mail = imaplib.IMAP4_SSL(email_config['imap_server'])
            mail.login(email_config['email'], email_config['password'])
            mail.select('inbox')

            # Search for Airbnb emails
            _, messages = mail.search(None, 'FROM', '"automated@airbnb.com"')

            bookings = []
            for msg_id in messages[0].split()[-20:]:  # Last 20 emails
                _, msg_data = mail.fetch(msg_id, '(RFC822)')
                email_body = msg_data[0][1]
                email_message = email.message_from_bytes(email_body)

                booking_data = self._parse_airbnb_email(email_message)
                if booking_data:
                    bookings.append(booking_data)

            mail.close()
            mail.logout()

            saved_count = await self._save_bookings(user, bookings, 'Airbnb')

            return {
                'success': True,
                'bookings_found': len(bookings),
                'bookings_saved': saved_count
            }

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _parse_airbnb_email(self, email_message) -> Dict:
        """Parse Airbnb booking confirmation email"""
        try:
            subject = decode_header(email_message['Subject'])[0][0]
            if isinstance(subject, bytes):
                subject = subject.decode()

            # Check if it's a booking confirmation
            if 'Reservation confirmed' not in subject:
                return None

            # Get email body
            body = self._get_email_body(email_message)

            # Extract booking details using regex
            patterns = {
                'confirmation_code': r'Confirmation code[:\s]+([A-Z0-9]+)',
                'guest_name': r'Guest[:\s]+([\w\s]+)',
                'check_in': r'Check-in[:\s]+(\w+\s+\d+,\s+\d{4})',
                'check_out': r'Check-out[:\s]+(\w+\s+\d+,\s+\d{4})',
                'total_price': r'Total[:\s]+\$?([\d,]+\.?\d*)'
            }

            booking_data = {}
            for field, pattern in patterns.items():
                match = re.search(pattern, body, re.IGNORECASE)
                if match:
                    booking_data[field] = match.group(1)

            if booking_data.get('confirmation_code'):
                return {
                    'external_booking_id': booking_data['confirmation_code'],
                    'guest_name': booking_data.get('guest_name', 'Unknown'),
                    'check_in': self._parse_date(booking_data.get('check_in')),
                    'check_out': self._parse_date(booking_data.get('check_out')),
                    'total_price': self._parse_price(booking_data.get('total_price', '0')),
                    'status': 'confirmed',
                    'channel': 'Airbnb'
                }

            return None

        except Exception as e:
            logger.error(f"Error parsing Airbnb email: {str(e)}")
            return None

    async def sync_via_scraping(self, user) -> Dict:
        """Web scraping with Selenium"""
        driver = None
        try:
            # Get saved credentials
            creds = await self._get_channel_credentials(user, 'Airbnb')

            # Setup Chrome driver
            options = webdriver.ChromeOptions()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            driver = webdriver.Chrome(options=options)

            # Login to Airbnb
            driver.get('https://www.airbnb.com/login')

            # Wait for login form
            wait = WebDriverWait(driver, 10)
            email_input = wait.until(EC.presence_of_element_located((By.NAME, 'email')))
            email_input.send_keys(creds['email'])

            # Continue to password
            continue_btn = driver.find_element(By.XPATH, "//button[@type='submit']")
            continue_btn.click()

            # Enter password
            password_input = wait.until(EC.presence_of_element_located((By.NAME, 'password')))
            password_input.send_keys(creds['password'])

            # Submit login
            login_btn = driver.find_element(By.XPATH, "//button[@type='submit']")
            login_btn.click()

            # Wait for dashboard
            wait.until(EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '/hosting')]")))

            # Navigate to reservations
            driver.get('https://www.airbnb.com/hosting/reservations')

            # Wait for reservations to load
            wait.until(EC.presence_of_element_located((By.XPATH, "//div[@data-testid='reservation-list']")))

            # Parse reservations
            bookings = self._parse_airbnb_reservations(driver)

            saved_count = await self._save_bookings(user, bookings, 'Airbnb')

            return {
                'success': True,
                'bookings_found': len(bookings),
                'bookings_saved': saved_count
            }

        except Exception as e:
            return {'success': False, 'error': str(e)}
        finally:
            if driver:
                driver.quit()

    def _parse_airbnb_reservations(self, driver) -> List[Dict]:
        """Parse reservations from Airbnb dashboard"""
        bookings = []

        try:
            # Find all reservation cards
            reservation_cards = driver.find_elements(By.XPATH, "//div[@data-testid='reservation-card']")

            for card in reservation_cards[:20]:  # Limit to 20 most recent
                try:
                    # Extract booking details
                    guest_name = card.find_element(By.XPATH, ".//div[@data-testid='guest-name']").text
                    dates = card.find_element(By.XPATH, ".//div[@data-testid='reservation-dates']").text
                    status = card.find_element(By.XPATH, ".//div[@data-testid='reservation-status']").text
                    confirmation = card.find_element(By.XPATH, ".//div[@data-testid='confirmation-code']").text

                    # Parse dates
                    date_match = re.search(r'(\w+\s+\d+)\s*-\s*(\w+\s+\d+)', dates)
                    if date_match:
                        check_in = self._parse_date(date_match.group(1))
                        check_out = self._parse_date(date_match.group(2))

                        bookings.append({
                            'external_booking_id': confirmation,
                            'guest_name': guest_name,
                            'check_in': check_in,
                            'check_out': check_out,
                            'status': 'confirmed' if 'confirmed' in status.lower() else 'pending',
                            'channel': 'Airbnb'
                        })

                except Exception as e:
                    logger.warning(f"Error parsing reservation card: {str(e)}")
                    continue

        except Exception as e:
            logger.error(f"Error parsing Airbnb reservations: {str(e)}")

        return bookings

    async def sync_via_extension(self, user) -> Dict:
        """Browser extension sync approach"""
        # This would communicate with a browser extension
        # The extension would be installed in the user's browser
        # and would capture booking data as they browse

        try:
            # Check if extension is installed and active
            extension_data = await self._get_extension_data(user, 'Airbnb')

            if not extension_data:
                return {'success': False, 'error': 'Browser extension not installed or inactive'}

            # Get captured bookings from extension storage
            bookings = extension_data.get('bookings', [])

            saved_count = await self._save_bookings(user, bookings, 'Airbnb')

            # Clear extension data after sync
            await self._clear_extension_data(user, 'Airbnb')

            return {
                'success': True,
                'bookings_found': len(bookings),
                'bookings_saved': saved_count
            }

        except Exception as e:
            return {'success': False, 'error': str(e)}

    async def sync_via_mobile_api(self, user) -> Dict:
        """Use reverse-engineered mobile API endpoints"""
        try:
            # Mobile APIs often have less strict authentication
            # This would use endpoints discovered through mobile app analysis

            creds = await self._get_channel_credentials(user, 'Airbnb')

            # Mobile API login
            login_data = {
                'email': creds['email'],
                'password': creds['password'],
                'type': 'email'
            }

            # Use mobile user agent
            mobile_headers = {
                'User-Agent': 'Airbnb/21.44 Android/10',
                'X-Airbnb-API-Key': '915pw2pnf4h1aiguhph5gc5b2',  # Public mobile API key
                'X-Airbnb-Device-ID': self._generate_device_id(),
                'X-Airbnb-Currency': 'USD',
                'X-Airbnb-Locale': 'en-US'
            }

            # Login
            login_response = self.session.post(
                'https://api.airbnb.com/v2/logins',
                json=login_data,
                headers=mobile_headers
            )

            if login_response.status_code != 200:
                return {'success': False, 'error': 'Mobile API login failed'}

            token = login_response.json().get('login', {}).get('id')

            # Get reservations
            mobile_headers['X-Airbnb-OAuth-Token'] = token

            reservations_response = self.session.get(
                'https://api.airbnb.com/v2/reservations',
                params={
                    '_format': 'for_mobile_host',
                    '_limit': 50,
                    'role': 'host'
                },
                headers=mobile_headers
            )

            if reservations_response.status_code == 200:
                bookings = self._parse_mobile_api_response(reservations_response.json())
                saved_count = await self._save_bookings(user, bookings, 'Airbnb')

                return {
                    'success': True,
                    'bookings_found': len(bookings),
                    'bookings_saved': saved_count
                }

            return {'success': False, 'error': 'Failed to fetch reservations'}

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _parse_mobile_api_response(self, data) -> List[Dict]:
        """Parse mobile API response"""
        bookings = []

        for reservation in data.get('reservations', []):
            try:
                bookings.append({
                    'external_booking_id': reservation.get('confirmation_code'),
                    'guest_name': reservation.get('guest', {}).get('full_name', 'Unknown'),
                    'check_in': datetime.fromisoformat(reservation.get('start_date')),
                    'check_out': datetime.fromisoformat(reservation.get('end_date')),
                    'total_price': reservation.get('total_price', {}).get('amount', 0),
                    'status': self._map_airbnb_status(reservation.get('status')),
                    'num_guests': reservation.get('number_of_guests', 1),
                    'channel': 'Airbnb'
                })
            except Exception as e:
                logger.warning(f"Error parsing reservation: {str(e)}")
                continue

        return bookings

    # Helper methods
    async def _get_channel_connection(self, user, channel_name):
        """Get channel connection for user"""
        from ..models.channels import ChannelConnection, Channel

        channel = await Channel.objects.aget(name=channel_name)
        connection, created = await ChannelConnection.objects.aget_or_create(
            user=user,
            channel=channel
        )
        return connection

    async def _get_channel_credentials(self, user, channel_name):
        """Get saved credentials for channel"""
        connection = await self._get_channel_connection(user, channel_name)

        # Decrypt credentials (in production, use proper encryption)
        return {
            'email': connection.api_key,  # Repurpose api_key field
            'password': connection.api_secret  # Repurpose api_secret field
        }

    async def _get_email_config(self, user):
        """Get email configuration"""
        # This would fetch from user settings
        return {
            'imap_server': 'imap.gmail.com',
            'email': user.email,
            'password': 'app_specific_password'  # User needs to set this up
        }

    def _get_email_body(self, email_message):
        """Extract email body"""
        body = ""

        if email_message.is_multipart():
            for part in email_message.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_payload(decode=True).decode()
                    break
                elif part.get_content_type() == "text/html":
                    html_body = part.get_payload(decode=True).decode()
                    soup = BeautifulSoup(html_body, 'html.parser')
                    body = soup.get_text()
        else:
            body = email_message.get_payload(decode=True).decode()

        return body

    def _parse_date(self, date_str):
        """Parse date from various formats"""
        if not date_str:
            return None

        # Try different date formats
        formats = [
            '%B %d, %Y',  # January 1, 2024
            '%b %d, %Y',  # Jan 1, 2024
            '%Y-%m-%d',  # 2024-01-01
            '%d/%m/%Y',  # 01/01/2024
            '%m/%d/%Y',  # 01/01/2024
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt).date()
            except:
                continue

        return None

    def _parse_price(self, price_str):
        """Parse price from string"""
        if not price_str:
            return 0

        # Remove currency symbols and commas
        price_str = re.sub(r'[^\d.]', '', price_str)

        try:
            return float(price_str)
        except:
            return 0

    def _map_airbnb_status(self, status):
        """Map Airbnb status to our status"""
        status_map = {
            'accepted': 'confirmed',
            'pending': 'pending',
            'cancelled': 'cancelled',
            'declined': 'cancelled'
        }
        return status_map.get(status, 'pending')

    def _generate_device_id(self):
        """Generate device ID for mobile API"""
        import uuid
        return str(uuid.uuid4())

    async def _save_bookings(self, user, bookings: List[Dict], channel_name: str) -> int:
        """Save bookings to database"""
        from ..models.bookings import Booking, Guest
        from ..models.channels import Channel
        from ..models.properties import Property

        saved_count = 0
        channel = await Channel.objects.aget(name=channel_name)

        # Get user's first property (in production, match by property details)
        try:
            property = await Property.objects.filter(owner=user).afirst()
            if not property:
                logger.error(f"No property found for user {user.id}")
                return 0
        except Exception as e:
            logger.error(f"Error getting property: {str(e)}")
            return 0

        for booking_data in bookings:
            try:
                # Create or get guest
                guest_name_parts = booking_data.get('guest_name', 'Unknown Guest').split(' ', 1)
                guest, _ = await Guest.objects.aget_or_create(
                    email=f"{booking_data.get('external_booking_id', 'unknown')}@{channel_name.lower()}.com",
                    defaults={
                        'first_name': guest_name_parts[0],
                        'last_name': guest_name_parts[1] if len(guest_name_parts) > 1 else '',
                    }
                )

                # Create or update booking
                booking, created = await Booking.objects.aupdate_or_create(
                    external_booking_id=booking_data['external_booking_id'],
                    channel=channel,
                    defaults={
                        'rental_property': property,
                        'guest': guest,
                        'check_in_date': booking_data['check_in'],
                        'check_out_date': booking_data['check_out'],
                        'num_guests': booking_data.get('num_guests', 1),
                        'total_price': booking_data.get('total_price', 0),
                        'status': booking_data.get('status', 'confirmed')
                    }
                )

                if created:
                    saved_count += 1

            except Exception as e:
                logger.error(f"Error saving booking: {str(e)}")
                continue

        return saved_count

    async def _get_extension_data(self, user, channel_name):
        """Get data from browser extension"""
        # This would communicate with a browser extension via WebSocket or local server
        # For now, return mock data
        return None

    async def _clear_extension_data(self, user, channel_name):
        """Clear extension data after sync"""
        pass


class BookingComNoAPISync(BaseChannelNoAPISync):
    """Booking.com specific sync without API"""

    async def sync_via_ical(self, user) -> Dict:
        """Sync Booking.com using iCal"""
        try:
            channel_conn = await self._get_channel_connection(user, 'Booking.com')
            if not channel_conn.ical_url:
                return {'success': False, 'error': 'No iCal URL configured'}

            response = self.session.get(channel_conn.ical_url)
            cal = icalendar.Calendar.from_ical(response.content)

            bookings = []
            for event in cal.walk('VEVENT'):
                booking_data = self._parse_booking_ical_event(event)
                if booking_data:
                    bookings.append(booking_data)

            saved_count = await self._save_bookings(user, bookings, 'Booking.com')

            return {
                'success': True,
                'bookings_found': len(bookings),
                'bookings_saved': saved_count
            }

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _parse_booking_ical_event(self, event) -> Dict:
        """Parse Booking.com iCal event"""
        try:
            summary = str(event.get('SUMMARY', ''))

            # Booking.com format: "CLOSED - Booking.com (Booking: 1234567890)"
            if 'CLOSED' in summary or 'Booking.com' in summary:
                match = re.search(r'Booking:\s*(\d+)', summary)
                if match:
                    booking_id = match.group(1)

                    return {
                        'external_booking_id': booking_id,
                        'guest_name': 'Booking.com Guest',  # Not available in iCal
                        'check_in': event.get('DTSTART').dt,
                        'check_out': event.get('DTEND').dt,
                        'status': 'confirmed',
                        'channel': 'Booking.com'
                    }

            return None

        except Exception as e:
            logger.error(f"Error parsing Booking.com event: {str(e)}")
            return None

    # Similar implementations for other methods...
    # (email parsing, web scraping, etc.)


class VRBONoAPISync(BaseChannelNoAPISync):
    """VRBO specific sync without API"""

    # Implementation similar to Airbnb but adapted for VRBO
    pass


class ExpediaNoAPISync(BaseChannelNoAPISync):
    """Expedia specific sync without API"""

    # Implementation similar to Airbnb but adapted for Expedia
    pass


class AgodaNoAPISync(BaseChannelNoAPISync):
    """Agoda specific sync without API"""

    # Implementation similar to Airbnb but adapted for Agoda
    pass