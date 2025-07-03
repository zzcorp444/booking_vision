"""
AI-powered sentiment analysis for guest communications.
This module analyzes guest messages and provides automated responses.
Location: booking_vision_APP/ai/sentiment_analysis.py
"""
from textblob import TextBlob
import re
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


class SentimentAnalyzer:
    """AI system for analyzing sentiment in guest communications"""

    # Positive response templates
    POSITIVE_RESPONSES = [
        "Thank you for your kind words! We're delighted you enjoyed your stay.",
        "We're thrilled to hear you had a great experience!",
        "Your positive feedback means so much to us. Thank you!",
        "We're so happy you loved your stay with us!"
    ]

    # Negative response templates
    NEGATIVE_RESPONSES = [
        "We sincerely apologize for any inconvenience. Let us make this right.",
        "Thank you for bringing this to our attention. We take your feedback seriously.",
        "We're sorry to hear about your experience. How can we improve?",
        "Your feedback is important to us. We'll address this immediately."
    ]

    # Neutral response templates
    NEUTRAL_RESPONSES = [
        "Thank you for your message. We're here to help with anything you need.",
        "We appreciate you reaching out. How can we assist you?",
        "Thanks for getting in touch. We're happy to help.",
        "We've received your message and will respond shortly."
    ]

    def __init__(self):
        self.keywords = {
            'positive': [
                'excellent', 'amazing', 'wonderful', 'perfect', 'love', 'great',
                'fantastic', 'outstanding', 'beautiful', 'clean', 'comfortable',
                'helpful', 'friendly', 'recommend', 'enjoyed', 'relaxing'
            ],
            'negative': [
                'terrible', 'awful', 'horrible', 'disgusting', 'dirty', 'broken',
                'disappointed', 'frustrated', 'angry', 'unacceptable', 'worst',
                'complained', 'refund', 'manager', 'lawsuit', 'review'
            ],
            'urgency': [
                'urgent', 'emergency', 'immediately', 'asap', 'now', 'help',
                'problem', 'issue', 'broken', 'not working', 'stuck', 'locked'
            ]
        }

    def analyze(self, text: str) -> Dict:
        """Analyze sentiment of text message"""
        if not text or not text.strip():
            return {
                'sentiment': 'neutral',
                'score': 0.0,
                'confidence': 0.0,
                'urgency': False,
                'keywords': [],
                'suggestions': []
            }

        # Clean text
        cleaned_text = self.clean_text(text)

        # Use TextBlob for basic sentiment analysis
        blob = TextBlob(cleaned_text)
        polarity = blob.sentiment.polarity

        # Determine sentiment category
        if polarity > 0.1:
            sentiment = 'positive'
        elif polarity < -0.1:
            sentiment = 'negative'
        else:
            sentiment = 'neutral'

        # Enhance with keyword analysis
        keyword_sentiment, found_keywords = self.analyze_keywords(cleaned_text)

        # Adjust sentiment based on keywords
        if keyword_sentiment:
            sentiment = keyword_sentiment

        # Check for urgency
        urgency = self.detect_urgency(cleaned_text)

        # Calculate confidence
        confidence = self.calculate_confidence(polarity, found_keywords, text)

        # Generate response suggestions
        suggestions = self.generate_response_suggestions(sentiment, urgency, found_keywords)

        return {
            'sentiment': sentiment,
            'score': polarity,
            'confidence': confidence,
            'urgency': urgency,
            'keywords': found_keywords,
            'suggestions': suggestions
        }

    def clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        # Convert to lowercase
        text = text.lower()

        # Remove URLs
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)

        # Remove email addresses
        text = re.sub(r'\S+@\S+', '', text)

        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()

        return text

    def analyze_keywords(self, text: str) -> tuple:
        """Analyze text for sentiment keywords"""
        found_keywords = []
        sentiment_scores = {'positive': 0, 'negative': 0}

        words = text.split()

        for category, keywords in self.keywords.items():
            if category in ['positive', 'negative']:
                for keyword in keywords:
                    if keyword in text:
                        found_keywords.append(keyword)
                        sentiment_scores[category] += 1

        # Determine dominant sentiment
        if sentiment_scores['positive'] > sentiment_scores['negative']:
            return 'positive', found_keywords
        elif sentiment_scores['negative'] > sentiment_scores['positive']:
            return 'negative', found_keywords
        else:
            return None, found_keywords

    def detect_urgency(self, text: str) -> bool:
        """Detect if message requires urgent attention"""
        for keyword in self.keywords['urgency']:
            if keyword in text:
                return True

        # Check for multiple exclamation marks
        if text.count('!') >= 2:
            return True

        # Check for ALL CAPS words
        words = text.split()
        caps_count = sum(1 for word in words if word.isupper() and len(word) > 2)
        if caps_count >= 2:
            return True

        return False

    def calculate_confidence(self, polarity: float, keywords: List[str], original_text: str) -> float:
        """Calculate confidence score for sentiment analysis"""
        base_confidence = 0.6

        # Adjust based on polarity strength
        polarity_confidence = min(abs(polarity), 0.3)

        # Adjust based on keywords found
        keyword_confidence = min(len(keywords) * 0.1, 0.2)

        # Adjust based on text length
        text_length_factor = min(len(original_text) / 100, 0.1)

        total_confidence = base_confidence + polarity_confidence + keyword_confidence + text_length_factor

        return min(total_confidence, 0.95)

    def generate_response_suggestions(self, sentiment: str, urgency: bool, keywords: List[str]) -> List[str]:
        """Generate automated response suggestions"""
        suggestions = []

        if urgency:
            suggestions.append("This message appears urgent. Please respond immediately.")

        # Add sentiment-based responses
        if sentiment == 'positive':
            suggestions.extend(self.POSITIVE_RESPONSES[:2])
        elif sentiment == 'negative':
            suggestions.extend(self.NEGATIVE_RESPONSES[:2])
        else:
            suggestions.extend(self.NEUTRAL_RESPONSES[:2])

        # Add keyword-specific suggestions
        if 'broken' in keywords or 'not working' in keywords:
            suggestions.append("We'll send maintenance to check this immediately.")

        if 'dirty' in keywords or 'clean' in keywords:
            suggestions.append("We'll have housekeeping address this right away.")

        if 'refund' in keywords:
            suggestions.append("Let's discuss how we can resolve this situation.")

        return suggestions[:3]  # Return top 3 suggestions

    def generate_automated_response(self, sentiment: str, guest_name: str = "", urgency: bool = False) -> str:
        """Generate a complete automated response"""
        greeting = f"Dear {guest_name}," if guest_name else "Hello,"

        if urgency:
            response_body = "Thank you for reaching out. We understand this is urgent and are addressing it immediately."
        elif sentiment == 'positive':
            response_body = "Thank you for your wonderful feedback! We're delighted you enjoyed your stay."
        elif sentiment == 'negative':
            response_body = "We sincerely apologize for any inconvenience. Your feedback is important to us and we're taking immediate action to address your concerns."
        else:
            response_body = "Thank you for your message. We're here to help with anything you need."

        closing = "\n\nBest regards,\nThe Booking Vision Team"

        return f"{greeting}\n\n{response_body}{closing}"

    def batch_analyze(self, messages: List[str]) -> List[Dict]:
        """Analyze multiple messages at once"""
        results = []
        for message in messages:
            try:
                analysis = self.analyze(message)
                results.append(analysis)
            except Exception as e:
                logger.error(f"Error analyzing message: {str(e)}")
                results.append({
                    'sentiment': 'neutral',
                    'score': 0.0,
                    'confidence': 0.0,
                    'urgency': False,
                    'keywords': [],
                    'suggestions': [],
                    'error': str(e)
                })

        return results