"""
AI-powered guest experience optimization.
This module analyzes guest behavior and preferences to enhance their experience.
Location: booking_vision_APP/ai/guest_experience.py
"""
import json
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List, Any
import logging

from ..models.bookings import Booking, Guest, BookingMessage
from ..models.ai_models import GuestPreference
from .sentiment_analysis import SentimentAnalyzer

logger = logging.getLogger(__name__)


class GuestExperienceEngine:
    """AI system for optimizing guest experience"""

    # Guest type classifications
    GUEST_TYPES = {
        'business': {
            'keywords': ['business', 'work', 'conference', 'meeting', 'corporate'],
            'preferences': ['wifi', 'desk', 'early_checkin', 'quiet']
        },
        'leisure': {
            'keywords': ['vacation', 'holiday', 'relax', 'sightseeing', 'tourist'],
            'preferences': ['pool', 'local_attractions', 'late_checkout', 'concierge']
        },
        'family': {
            'keywords': ['family', 'kids', 'children', 'baby', 'playground'],
            'preferences': ['cribs', 'family_room', 'kitchen', 'safety']
        },
        'couple': {
            'keywords': ['romantic', 'anniversary', 'honeymoon', 'couple', 'date'],
            'preferences': ['privacy', 'romantic_setting', 'room_service', 'spa']
        }
    }

    def __init__(self):
        self.sentiment_analyzer = SentimentAnalyzer()

    def analyze_guest(self, guest: Guest, booking: Booking = None) -> Dict[str, Any]:
        """Comprehensive analysis of guest preferences and behavior"""
        try:
            # Get or create guest preferences
            preferences, created = GuestPreference.objects.get_or_create(guest=guest)

            # Analyze all guest bookings
            guest_bookings = Booking.objects.filter(guest=guest).order_by('-created_at')

            # Analyze guest type
            guest_type = self.classify_guest_type(guest, guest_bookings)

            # Analyze communication patterns
            communication_analysis = self.analyze_communication_patterns(guest)

            # Calculate satisfaction score
            satisfaction_score = self.calculate_satisfaction_score(guest, guest_bookings)

            # Generate personalized recommendations
            recommendations = self.generate_recommendations(guest, guest_type, satisfaction_score)

            # Update guest preferences
            self.update_guest_preferences(preferences, {
                'guest_type': guest_type,
                'satisfaction_score': satisfaction_score,
                'communication_preference': communication_analysis['preference'],
                'last_analyzed': datetime.now().isoformat()
            })

            return {
                'guest_type': guest_type,
                'satisfaction_score': satisfaction_score,
                'communication_pattern': communication_analysis,
                'booking_patterns': self.analyze_booking_patterns(guest_bookings),
                'preferences': self.extract_preferences(guest, guest_bookings),
                'recommendations': recommendations,
                'loyalty_indicators': self.calculate_loyalty_indicators(guest_bookings)
            }

        except Exception as e:
            logger.error(f"Error analyzing guest {guest.id}: {str(e)}")
            return {
                'error': str(e),
                'guest_type': 'unknown',
                'satisfaction_score': 3.0,
                'recommendations': []
            }

    def classify_guest_type(self, guest: Guest, bookings: List[Booking]) -> str:
        """Classify guest type based on booking history and communication"""
        type_scores = defaultdict(int)

        # Analyze booking messages for keywords
        for booking in bookings:
            messages = BookingMessage.objects.filter(booking=booking, sender='guest')
            for message in messages:
                text = message.message.lower()
                for guest_type, config in self.GUEST_TYPES.items():
                    for keyword in config['keywords']:
                        if keyword in text:
                            type_scores[guest_type] += 1

        # Analyze booking patterns
        if bookings:
            # Business travelers often book short stays on weekdays
            weekday_bookings = sum(1 for b in bookings if b.check_in_date.weekday() < 5)
            if weekday_bookings / len(bookings) > 0.7:
                type_scores['business'] += 2

            # Family bookings often longer and include more guests
            family_bookings = sum(1 for b in bookings if b.num_guests > 2 and b.nights > 3)
            if family_bookings > 0:
                type_scores['family'] += family_bookings

            # Leisure travelers often book longer stays
            long_stays = sum(1 for b in bookings if b.nights > 5)
            if long_stays > 0:
                type_scores['leisure'] += long_stays

        # Return the type with highest score
        if type_scores:
            return max(type_scores, key=type_scores.get)
        else:
            return 'leisure'  # Default

    def analyze_communication_patterns(self, guest: Guest) -> Dict[str, Any]:
        """Analyze how the guest prefers to communicate"""
        guest_bookings = Booking.objects.filter(guest=guest)
        all_messages = BookingMessage.objects.filter(
            booking__in=guest_bookings,
            sender='guest'
        ).order_by('created_at')

        if not all_messages:
            return {
                'preference': 'minimal',
                'response_time': 'unknown',
                'message_length': 'unknown',
                'sentiment_trend': 'neutral'
            }

        # Analyze message timing
        response_times = []
        message_lengths = []
        sentiments = []

        for message in all_messages:
            # Message length
            message_lengths.append(len(message.message))

            # Sentiment analysis
            sentiment_result = self.sentiment_analyzer.analyze(message.message)
            sentiments.append(sentiment_result['score'])

        # Determine communication preference
        avg_length = sum(message_lengths) / len(message_lengths) if message_lengths else 0
        message_frequency = len(all_messages) / max(len(guest_bookings), 1)

        if message_frequency > 3 and avg_length > 100:
            preference = 'detailed'
        elif message_frequency > 1:
            preference = 'moderate'
        else:
            preference = 'minimal'

        # Calculate sentiment trend
        if sentiments:
            avg_sentiment = sum(sentiments) / len(sentiments)
            if avg_sentiment > 0.2:
                sentiment_trend = 'positive'
            elif avg_sentiment < -0.2:
                sentiment_trend = 'negative'
            else:
                sentiment_trend = 'neutral'
        else:
            sentiment_trend = 'neutral'

        return {
            'preference': preference,
            'message_frequency': message_frequency,
            'average_message_length': avg_length,
            'sentiment_trend': sentiment_trend,
            'total_messages': len(all_messages)
        }

    def calculate_satisfaction_score(self, guest: Guest, bookings: List[Booking]) -> float:
        """Calculate overall guest satisfaction score"""
        if not bookings:
            return 3.0  # Neutral default

        # Analyze message sentiments
        all_messages = BookingMessage.objects.filter(
            booking__in=bookings,
            sender='guest'
        )

        sentiment_scores = []
        for message in all_messages:
            sentiment = self.sentiment_analyzer.analyze(message.message)
            # Convert polarity (-1 to 1) to satisfaction score (1 to 5)
            satisfaction = 3 + (sentiment['score'] * 2)
            sentiment_scores.append(max(1, min(5, satisfaction)))

        # Consider booking patterns
        pattern_score = 3.0

        # Repeat bookings indicate satisfaction
        if len(bookings) > 1:
            pattern_score += 0.5

        if len(bookings) > 3:
            pattern_score += 0.5

        # Recent bookings weighted more heavily
        recent_bookings = [b for b in bookings if b.created_at.date() > datetime.now().date() - timedelta(days=180)]
        if recent_bookings:
            pattern_score += 0.3

        # Combine sentiment and pattern scores
        if sentiment_scores:
            sentiment_avg = sum(sentiment_scores) / len(sentiment_scores)
            final_score = (sentiment_avg * 0.7) + (pattern_score * 0.3)
        else:
            final_score = pattern_score

        return round(max(1.0, min(5.0, final_score)), 2)

    def analyze_booking_patterns(self, bookings: List[Booking]) -> Dict[str, Any]:
        """Analyze guest booking patterns"""
        if not bookings:
            return {}

        # Timing patterns
        months = [b.check_in_date.month for b in bookings]
        weekdays = [b.check_in_date.weekday() for b in bookings]

        # Stay duration patterns
        durations = [b.nights for b in bookings]

        # Guest count patterns
        guest_counts = [b.num_guests for b in bookings]

        # Spending patterns
        spending = [float(b.total_price) for b in bookings]

        return {
            'preferred_months': self.find_most_common(months),
            'preferred_weekdays': self.find_most_common(weekdays),
            'average_stay_duration': sum(durations) / len(durations),
            'typical_guest_count': self.find_most_common(guest_counts),
            'average_spending': sum(spending) / len(spending),
            'total_bookings': len(bookings),
            'booking_frequency': self.calculate_booking_frequency(bookings)
        }

    def extract_preferences(self, guest: Guest, bookings: List[Booking]) -> Dict[str, Any]:
        """Extract guest preferences from booking history"""
        preferences = {
            'room_preferences': [],
            'service_preferences': [],
            'timing_preferences': {},
            'spending_patterns': {}
        }

        # Analyze property types
        property_types = [b.property.property_type for b in bookings]
        if property_types:
            preferences['preferred_property_type'] = self.find_most_common(property_types)

        # Analyze location preferences
        cities = [b.property.city for b in bookings]
        if cities:
            preferences['preferred_cities'] = list(set(cities))

        return preferences

    def generate_recommendations(self, guest: Guest, guest_type: str, satisfaction_score: float) -> List[
        Dict[str, str]]:
        """Generate personalized recommendations for guest experience"""
        recommendations = []

        # Type-based recommendations
        if guest_type in self.GUEST_TYPES:
            type_config = self.GUEST_TYPES[guest_type]
            for pref in type_config['preferences']:
                recommendations.append({
                    'type': 'amenity',
                    'title': f'Offer {pref.replace("_", " ").title()}',
                    'description': f'Based on {guest_type} traveler preferences',
                    'priority': 'medium'
                })

        # Satisfaction-based recommendations
        if satisfaction_score < 3.0:
            recommendations.append({
                'type': 'service',
                'title': 'Proactive Communication',
                'description': 'Guest may need extra attention - reach out proactively',
                'priority': 'high'
            })
            recommendations.append({
                'type': 'offer',
                'title': 'Special Offer',
                'description': 'Consider offering a discount or upgrade to improve satisfaction',
                'priority': 'medium'
            })
        elif satisfaction_score > 4.0:
            recommendations.append({
                'type': 'loyalty',
                'title': 'VIP Treatment',
                'description': 'Highly satisfied guest - consider VIP perks',
                'priority': 'medium'
            })
            recommendations.append({
                'type': 'referral',
                'title': 'Referral Program',
                'description': 'Happy guest might refer others - mention referral program',
                'priority': 'low'
            })

        return recommendations[:5]  # Return top 5 recommendations

    def calculate_loyalty_indicators(self, bookings: List[Booking]) -> Dict[str, Any]:
        """Calculate guest loyalty indicators"""
        if not bookings:
            return {'loyalty_score': 0, 'likelihood_to_return': 'low'}

        # Factors affecting loyalty
        repeat_bookings = len(bookings) > 1
        recent_booking = any(b.created_at.date() > datetime.now().date() - timedelta(days=90) for b in bookings)
        booking_frequency = len(bookings) / max((datetime.now().date() - bookings[-1].created_at.date()).days / 365,
                                                0.25)

        # Calculate loyalty score
        loyalty_score = 0
        if repeat_bookings:
            loyalty_score += 30
        if recent_booking:
            loyalty_score += 20
        if booking_frequency > 1:
            loyalty_score += 25
        if len(bookings) > 3:
            loyalty_score += 25

        # Determine likelihood to return
        if loyalty_score >= 75:
            likelihood = 'very_high'
        elif loyalty_score >= 50:
            likelihood = 'high'
        elif loyalty_score >= 25:
            likelihood = 'medium'
        else:
            likelihood = 'low'

        return {
            'loyalty_score': loyalty_score,
            'likelihood_to_return': likelihood,
            'repeat_guest': repeat_bookings,
            'recent_activity': recent_booking,
            'booking_frequency': round(booking_frequency, 2)
        }

    def get_response_templates(self) -> Dict[str, List[str]]:
        """Get response templates for different scenarios"""
        return {
            'welcome_business': [
                "Welcome! We've prepared a quiet workspace for you.",
                "Hello! Your room includes complimentary WiFi and a desk area.",
                "Welcome! We know business travelers value efficiency - we're here to help."
            ],
            'welcome_family': [
                "Welcome to our family-friendly property!",
                "Hi! We've made sure your room is safe and comfortable for the whole family.",
                "Welcome! The kids will love our family amenities."
            ],
            'welcome_leisure': [
                "Welcome! We hope you have a wonderful and relaxing stay.",
                "Hello! We're excited to help make your vacation memorable.",
                "Welcome to your home away from home!"
            ],
            'follow_up_positive': [
                "We're so glad you're enjoying your stay!",
                "Thank you for the positive feedback!",
                "We're thrilled everything is going well!"
            ],
            'follow_up_negative': [
                "We sincerely apologize and want to make this right.",
                "Thank you for bringing this to our attention.",
                "We're working immediately to resolve this issue."
            ]
        }

    # Helper methods
    def find_most_common(self, items: List) -> Any:
        """Find the most common item in a list"""
        if not items:
            return None
        return max(set(items), key=items.count)

    def calculate_booking_frequency(self, bookings: List[Booking]) -> float:
        """Calculate how frequently guest books (bookings per year)"""
        if len(bookings) < 2:
            return 0

        first_booking = min(bookings, key=lambda b: b.created_at)
        last_booking = max(bookings, key=lambda b: b.created_at)

        days_span = (last_booking.created_at.date() - first_booking.created_at.date()).days
        years_span = max(days_span / 365, 0.25)  # Minimum 3 months

        return len(bookings) / years_span

    def update_guest_preferences(self, preferences: GuestPreference, data: Dict[str, Any]) -> None:
        """Update guest preferences in database"""
        try:
            for key, value in data.items():
                if hasattr(preferences, key):
                    setattr(preferences, key, value)
            preferences.save()
        except Exception as e:
            logger.error(f"Error updating guest preferences: {str(e)}")