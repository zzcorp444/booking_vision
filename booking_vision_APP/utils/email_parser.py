"""
Email parsing utilities for booking confirmations
"""
import email
import imaplib
import re
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from email.header import decode_header
from bs4 import BeautifulSoup
import html
from django.utils import timezone

logger = logging.getLogger(__name__)


class BookingEmailParser:
    """Robust email parser for booking confirmations from various channels"""

    def __init__(self):
        self.channel_patterns = {
            'airbnb': {
                'from_patterns': [
                    r'automated@airbnb\.com',
                    r'noreply@airbnb\.com',
                    r'.*@mail\.airbnb\.com'
                ],
                'subject_patterns': [
                    r'reservation confirmed',
                    r'you have a new booking',
                    r'new reservation',
                    r'booking confirmed'
                ],
                'confirmation_patterns': [
                    r'confirmation code[:\s]+([A-Z0-9]{6,12})',
                    r'reservation code[:\s]+([A-Z0-9]{6,12})',
                    r'(HM[A-Z0-9]{8,12})'
                ],
                'guest_patterns': [
                    r'guest[:\s]+([\w\s]+?)(?:\n|\r|<)',
                    r'from[:\s]+([\w\s]+?)(?:\n|\r|<)',
                    r'booked by[:\s]+([\w\s]+?)(?:\n|\r|<)'
                ],
                'date_patterns': [
                    r'check.?in[:\s]+(\w+\s+\d+,?\s+\d{4})',
                    r'check.?out[:\s]+(\w+\s+\d+,?\s+\d{4})',
                    r'(\w+\s+\d+,?\s+\d{4})\s*[-–]\s*(\w+\s+\d+,?\s+\d{4})',
                    r'(\d{1,2}/\d{1,2}/\d{4})\s*[-–]\s*(\d{1,2}/\d{1,2}/\d{4})'
                ],
                'price_patterns': [
                    r'total[:\s]+\$?([\d,]+\.?\d*)',
                    r'amount[:\s]+\$?([\d,]+\.?\d*)',
                    r'payout[:\s]+\$?([\d,]+\.?\d*)'
                ],
                'guests_patterns': [
                    r'(\d+)\s+guests?',
                    r'guests?[:\s]+(\d+)',
                    r'party size[:\s]+(\d+)'
                ]
            },
            'booking_com': {
                'from_patterns': [
                    r'.*@booking\.com',
                    r'.*@mail\.booking\.com',
                    r'noreply@booking\.com'
                ],
                'subject_patterns': [
                    r'new booking',
                    r'reservation confirmed',
                    r'booking confirmation'
                ],
                'confirmation_patterns': [
                    r'booking\.com reservation number[:\s]+(\d{8,12})',
                    r'reservation[:\s]+(\d{8,12})',
                    r'booking[:\s]+(\d{8,12})'
                ],
                'guest_patterns': [
                    r'guest name[:\s]+([\w\s]+?)(?:\n|\r|<)',
                    r'booked by[:\s]+([\w\s]+?)(?:\n|\r|<)'
                ],
                'date_patterns': [
                    r'arrival[:\s]+(\w+,?\s+\d+\s+\w+\s+\d{4})',
                    r'departure[:\s]+(\w+,?\s+\d+\s+\w+\s+\d{4})',
                    r'(\d{1,2}\s+\w+\s+\d{4})\s*[-–]\s*(\d{1,2}\s+\w+\s+\d{4})'
                ],
                'price_patterns': [
                    r'total price[:\s]+[€$£]?([\d,]+\.?\d*)',
                    r'total[:\s]+[€$£]?([\d,]+\.?\d*)'
                ],
                'guests_patterns': [
                    r'(\d+)\s+adults?',
                    r'guests?[:\s]+(\d+)'
                ]
            },
            'vrbo': {
                'from_patterns': [
                    r'.*@vrbo\.com',
                    r'.*@mail\.vrbo\.com',
                    r'noreply@vrbo\.com'
                ],
                'subject_patterns': [
                    r'new booking',
                    r'reservation confirmed',
                    r'you have a reservation'
                ],
                'confirmation_patterns': [
                    r'itinerary[:\s]+(\d{7,12})',
                    r'confirmation[:\s]+(\d{7,12})',
                    r'reservation[:\s]+(\d{7,12})'
                ],
                'guest_patterns': [
                    r'traveler[:\s]+([\w\s]+?)(?:\n|\r|<)',
                    r'guest[:\s]+([\w\s]+?)(?:\n|\r|<)'
                ],
                'date_patterns': [
                    r'check.?in[:\s]+(\w+,?\s+\w+\s+\d+,?\s+\d{4})',
                    r'check.?out[:\s]+(\w+,?\s+\w+\s+\d+,?\s+\d{4})'
                ],
                'price_patterns': [
                    r'total rental amount[:\s]+\$?([\d,]+\.?\d*)',
                    r'total[:\s]+\$?([\d,]+\.?\d*)'
                ],
                'guests_patterns': [
                    r'(\d+)\s+travelers?',
                    r'party size[:\s]+(\d+)'
                ]
            }
        }

    def parse_email(self, email_message) -> Optional[Dict]:
        """Parse a single email message for booking information"""
        try:
            # Get email metadata
            subject = self._decode_header(email_message.get('Subject', ''))
            from_addr = self._decode_header(email_message.get('From', ''))
            date = email_message.get('Date', '')

            # Get email body
            body = self._extract_email_body(email_message)
            if not body:
                return None

            # Identify channel
            channel = self._identify_channel(from_addr, subject)
            if not channel:
                logger.debug(f"Could not identify channel for email from {from_addr}")
                return None

            # Extract booking information
            booking_info = self._extract_booking_info(body, channel, subject)
            if not booking_info:
                logger.debug(f"Could not extract booking info from {channel} email")
                return None

            booking_info.update({
                'channel': channel,
                'email_subject': subject,
                'email_from': from_addr,
                'email_date': date,
                'raw_body': body[:500] if len(body) > 500 else body  # First 500 chars for debugging
            })

            return booking_info

        except Exception as e:
            logger.error(f"Error parsing email: {str(e)}")
            return None

    def _decode_header(self, header_value: str) -> str:
        """Decode email header"""
        if not header_value:
            return ''

        try:
            decoded_parts = decode_header(header_value)
            decoded_string = ''
            for part, encoding in decoded_parts:
                if isinstance(part, bytes):
                    if encoding:
                        decoded_string += part.decode(encoding)
                    else:
                        decoded_string += part.decode('utf-8', errors='ignore')
                else:
                    decoded_string += part
            return decoded_string.strip()
        except Exception as e:
            logger.error(f"Error decoding header: {str(e)}")
            return str(header_value)

    def _extract_email_body(self, email_message) -> str:
        """Extract text content from email"""
        body = ""

        try:
            if email_message.is_multipart():
                for part in email_message.walk():
                    content_type = part.get_content_type()

                    if content_type == "text/plain":
                        charset = part.get_content_charset() or 'utf-8'
                        content = part.get_payload(decode=True)
                        if content:
                            body = content.decode(charset, errors='ignore')
                            break

                    elif content_type == "text/html":
                        charset = part.get_content_charset() or 'utf-8'
                        content = part.get_payload(decode=True)
                        if content:
                            html_content = content.decode(charset, errors='ignore')
                            soup = BeautifulSoup(html_content, 'html.parser')
                            # Remove script and style elements
                            for script in soup(["script", "style"]):
                                script.decompose()
                            body = soup.get_text()
                            break
            else:
                # Single part message
                charset = email_message.get_content_charset() or 'utf-8'
                content = email_message.get_payload(decode=True)
                if content:
                    if email_message.get_content_type() == "text/html":
                        soup = BeautifulSoup(content.decode(charset, errors='ignore'), 'html.parser')
                        body = soup.get_text()
                    else:
                        body = content.decode(charset, errors='ignore')

            # Clean up the body text
            body = html.unescape(body)  # Decode HTML entities
            body = re.sub(r'\s+', ' ', body)  # Normalize whitespace
            return body.strip()

        except Exception as e:
            logger.error(f"Error extracting email body: {str(e)}")
            return ""

    def _identify_channel(self, from_addr: str, subject: str) -> Optional[str]:
        """Identify the booking channel from email metadata"""
        from_addr_lower = from_addr.lower()
        subject_lower = subject.lower()

        for channel, patterns in self.channel_patterns.items():
            # Check from address patterns
            for pattern in patterns['from_patterns']:
                if re.search(pattern, from_addr_lower, re.IGNORECASE):
                    # Verify with subject patterns
                    for subject_pattern in patterns['subject_patterns']:
                        if re.search(subject_pattern, subject_lower, re.IGNORECASE):
                            return channel

        return None

    def _extract_booking_info(self, body: str, channel: str, subject: str) -> Optional[Dict]:
        """Extract booking information from email body"""
        if channel not in self.channel_patterns:
            return None

        patterns = self.channel_patterns[channel]
        booking_info = {}

        # Extract confirmation code
        booking_info['confirmation_code'] = self._extract_with_patterns(
            body, patterns['confirmation_patterns']
        )

        if not booking_info['confirmation_code']:
            logger.debug(f"No confirmation code found for {channel}")
            return None

        # Extract guest name
        booking_info['guest_name'] = self._extract_with_patterns(
            body, patterns['guest_patterns']
        )

        # Extract dates
        dates = self._extract_dates(body, patterns['date_patterns'])
        if dates:
            booking_info.update(dates)

        # Extract price
        booking_info['total_price'] = self._extract_price(
            body, patterns['price_patterns']
        )

        # Extract number of guests
        booking_info['num_guests'] = self._extract_with_patterns(
            body, patterns['guests_patterns']
        )

        # Set default values
        booking_info.setdefault('guest_name', 'Unknown Guest')
        booking_info.setdefault('total_price', 0)
        booking_info.setdefault('num_guests', 1)
        booking_info.setdefault('status', 'confirmed')

        return booking_info

    def _extract_with_patterns(self, text: str, patterns: List[str]) -> Optional[str]:
        """Extract information using regex patterns"""
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                result = match.group(1).strip()
                # Clean up the result
                result = re.sub(r'[^\w\s]', '', result).strip()
                if result:
                    return result
        return None

    def _extract_dates(self, text: str, patterns: List[str]) -> Optional[Dict]:
        """Extract check-in and check-out dates"""
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)

            if matches:
                if isinstance(matches[0], tuple):
                    # Date range pattern
                    check_in_str, check_out_str = matches[0]
                else:
                    # Individual date patterns
                    check_in_matches = re.findall(r'check.?in[:\s]+' + pattern, text, re.IGNORECASE)
                    check_out_matches = re.findall(r'check.?out[:\s]+' + pattern, text, re.IGNORECASE)

                    if check_in_matches and check_out_matches:
                        check_in_str = check_in_matches[0]
                        check_out_str = check_out_matches[0]
                    else:
                        continue

                # Parse dates
                check_in_date = self._parse_date(check_in_str)
                check_out_date = self._parse_date(check_out_str)

                if check_in_date and check_out_date:
                    return {
                        'check_in_date': check_in_date,
                        'check_out_date': check_out_date
                    }

        return None

    def _parse_date(self, date_str: str) -> Optional[datetime.date]:
        """Parse date string into datetime.date object"""
        if not date_str:
            return None

        # Clean up the date string
        date_str = re.sub(r'[,\.]', '', date_str.strip())

        # Common date formats
        date_formats = [
            '%B %d %Y',        # January 15 2024
            '%b %d %Y',        # Jan 15 2024
            '%A %B %d %Y',     # Monday January 15 2024
            '%a %b %d %Y',     # Mon Jan 15 2024
            '%d %B %Y',        # 15 January 2024
            '%d %b %Y',        # 15 Jan 2024
            '%m/%d/%Y',        # 01/15/2024
            '%d/%m/%Y',        # 15/01/2024
            '%Y-%m-%d',        # 2024-01-15
            '%m-%d-%Y',        # 01-15-2024
            '%d-%m-%Y',        # 15-01-2024
        ]

        for fmt in date_formats:
            try:
                parsed_date = datetime.strptime(date_str, fmt)
                return parsed_date.date()
            except ValueError:
                continue

        logger.warning(f"Could not parse date: {date_str}")
        return None

    def _extract_price(self, text: str, patterns: List[str]) -> float:
        """Extract price from text"""
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                price_str = match.group(1)
                # Remove commas and convert to float
                price_str = re.sub(r'[^\d.]', '', price_str)
                try:
                    return float(price_str)
                except ValueError:
                    continue
        return 0.0


class EmailSyncService:
    """Service for syncing emails and extracting bookings"""

    def __init__(self):
        self.parser = BookingEmailParser()

    def sync_user_emails(self, user, email_config: Dict) -> Dict:
        """Sync emails for a specific user"""
        try:
            # Connect to email server
            mail = imaplib.IMAP4_SSL(email_config['imap_server'])
            mail.login(email_config['email'], email_config['password'])
            mail.select('inbox')

            # Search for booking emails from the last 30 days
            since_date = (timezone.now() - timedelta(days=30)).strftime('%d-%b-%Y')

            # Search patterns for different channels
            search_patterns = [
                'FROM "automated@airbnb.com"',
                'FROM "booking.com"',
                'FROM "vrbo.com"',
                f'SINCE {since_date} SUBJECT "booking"',
                f'SINCE {since_date} SUBJECT "reservation"',
                f'SINCE {since_date} SUBJECT "confirmed"'
            ]

            all_bookings = []
            processed_emails = 0

            for pattern in search_patterns:
                try:
                    _, messages = mail.search(None, pattern)
                    message_ids = messages[0].split()

                    for msg_id in message_ids[-50:]:  # Process last 50 emails per pattern
                        try:
                            _, msg_data = mail.fetch(msg_id, '(RFC822)')
                            email_body = msg_data[0][1]
                            email_message = email.message_from_bytes(email_body)

                            booking_info = self.parser.parse_email(email_message)
                            if booking_info:
                                all_bookings.append(booking_info)

                            processed_emails += 1

                        except Exception as e:
                            logger.error(f"Error processing email {msg_id}: {str(e)}")
                            continue

                except Exception as e:
                    logger.error(f"Error with search pattern {pattern}: {str(e)}")
                    continue

            mail.close()
            mail.logout()

            # Save bookings to database
            saved_count = self._save_bookings(user, all_bookings)

            return {
                'success': True,
                'processed_emails': processed_emails,
                'bookings_found': len(all_bookings),
                'bookings_saved': saved_count
            }

        except Exception as e:
            logger.error(f"Error syncing emails for user {user.id}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def _save_bookings(self, user, bookings_data: List[Dict]) -> int:
        """Save extracted bookings to database"""
        from ..models.bookings import Booking, Guest
        from ..models.channels import Channel
        from ..models.properties import Property

        saved_count = 0

        # Get user's first property (you might want to improve this)
        try:
            property = Property.objects.filter(owner=user).first()
            if not property:
                logger.error(f"No property found for user {user.id}")
                return 0
        except Exception as e:
            logger.error(f"Error getting property: {str(e)}")
            return 0

        for booking_data in bookings_data:
            try:
                # Get or create channel
                channel, _ = Channel.objects.get_or_create(
                    name=booking_data['channel'].title(),
                    defaults={'is_active': True}
                )

                # Get or create guest
                guest_name_parts = booking_data.get('guest_name', 'Unknown Guest').split(' ', 1)
                guest_email = f"{booking_data.get('confirmation_code', 'unknown')}@{booking_data['channel'].lower()}.com"

                guest, _ = Guest.objects.get_or_create(
                    email=guest_email,
                    defaults={
                        'first_name': guest_name_parts[0],
                        'last_name': guest_name_parts[1] if len(guest_name_parts) > 1 else '',
                    }
                )

                # Create or update booking
                booking, created = Booking.objects.update_or_create(
                    external_booking_id=booking_data['confirmation_code'],
                    channel=channel,
                    defaults={
                        'rental_property': property,
                        'guest': guest,
                        'check_in_date': booking_data.get('check_in_date'),
                        'check_out_date': booking_data.get('check_out_date'),
                        'num_guests': int(booking_data.get('num_guests', 1)),
                        'total_price': booking_data.get('total_price', 0),
                        'base_price': booking_data.get('total_price', 0),
                        'status': booking_data.get('status', 'confirmed')
                    }
                )

                if created:
                    saved_count += 1
                    logger.info(f"Created booking {booking.id} from email")

            except Exception as e:
                logger.error(f"Error saving booking: {str(e)}")
                continue

        return saved_count