"""
AI-powered pricing engine for dynamic pricing optimization.
This module uses machine learning to optimize property pricing.
Location: booking_vision_APP/ai/pricing_engine.py
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from decimal import Decimal
import joblib
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
import logging

from ..models.properties import Property
from ..models.bookings import Booking
from ..models.ai_models import MarketData, PricingRule

logger = logging.getLogger(__name__)


class PricingEngine:
    """AI-powered dynamic pricing engine"""

    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        self.load_or_train_model()

    def load_or_train_model(self):
        """Load existing model or train a new one"""
        try:
            # Try to load existing model
            self.model = joblib.load('pricing_model.pkl')
            self.scaler = joblib.load('pricing_scaler.pkl')
        except:
            # Train new model if none exists
            self.train_model()

    def train_model(self):
        """Train the pricing model with historical data"""
        # In production, this would use actual historical data
        # For now, we'll create a simple model
        self.model = RandomForestRegressor(
            n_estimators=100,
            max_depth=10,
            random_state=42
        )

        # Generate synthetic training data
        X_train, y_train = self.generate_training_data()

        # Fit the model
        X_scaled = self.scaler.fit_transform(X_train)
        self.model.fit(X_scaled, y_train)

        # Save model
        try:
            joblib.dump(self.model, 'pricing_model.pkl')
            joblib.dump(self.scaler, 'pricing_scaler.pkl')
        except:
            logger.warning("Could not save pricing model")

    def generate_training_data(self):
        """Generate synthetic training data"""
        # Features: occupancy_rate, days_ahead, day_of_week, season, local_events, competitor_avg
        features = []
        prices = []

        for _ in range(1000):
            occupancy = np.random.uniform(0.3, 0.95)
            days_ahead = np.random.randint(0, 180)
            day_of_week = np.random.randint(0, 7)
            season = np.random.randint(0, 4)
            local_events = np.random.randint(0, 3)
            competitor_avg = np.random.uniform(80, 300)

            # Base price with variations
            base_price = 150

            # Occupancy factor (higher occupancy = higher price)
            occupancy_factor = 1 + (occupancy - 0.6) * 0.5

            # Days ahead factor (last minute = higher price)
            days_factor = 1.2 if days_ahead < 7 else 1.0

            # Weekend factor
            weekend_factor = 1.2 if day_of_week in [5, 6] else 1.0

            # Season factor
            season_factor = [0.8, 1.0, 1.3, 0.9][season]

            # Event factor
            event_factor = 1 + (local_events * 0.15)

            # Competitor factor
            competitor_factor = competitor_avg / 150

            # Calculate final price
            price = base_price * occupancy_factor * days_factor * weekend_factor * season_factor * event_factor * competitor_factor

            features.append([occupancy, days_ahead, day_of_week, season, local_events, competitor_avg])
            prices.append(price)

        return np.array(features), np.array(prices)

    def get_pricing_recommendation(self, property):
        """Get AI-powered pricing recommendation for a property"""
        try:
            # Collect features
            features = self.extract_features(property)

            # Scale features
            features_scaled = self.scaler.transform([features])

            # Predict optimal price
            predicted_price = self.model.predict(features_scaled)[0]

            # Apply pricing rules
            final_price = self.apply_pricing_rules(property, predicted_price)

            # Calculate potential revenue increase
            current_price = float(property.base_price)
            revenue_increase = ((final_price - current_price) / current_price) * 100

            # Get factors affecting price
            factors = self.get_pricing_factors(property, features)

            return {
                'suggested_price': round(final_price, 2),
                'current_price': current_price,
                'revenue_increase': round(revenue_increase, 1),
                'confidence': 0.85,  # Model confidence
                'factors': factors
            }
        except Exception as e:
            logger.error(f"Error in pricing recommendation: {str(e)}")
            return None

    def extract_features(self, property):
        """Extract features for pricing prediction"""
        # Calculate occupancy rate (last 30 days)
        today = datetime.now().date()
        thirty_days_ago = today - timedelta(days=30)

        bookings = Booking.objects.filter(
            property=property,
            check_in_date__lte=today,
            check_out_date__gte=thirty_days_ago,
            status__in=['confirmed', 'checked_in', 'checked_out']
        )

        booked_days = 0
        for booking in bookings:
            overlap_start = max(booking.check_in_date, thirty_days_ago)
            overlap_end = min(booking.check_out_date, today)
            if overlap_start <= overlap_end:
                booked_days += (overlap_end - overlap_start).days + 1

        occupancy_rate = booked_days / 30.0

        # Days ahead (for next available date)
        next_available = self.get_next_available_date(property)
        days_ahead = (next_available - today).days if next_available else 0

        # Day of week (0 = Monday, 6 = Sunday)
        day_of_week = today.weekday()

        # Season (0 = Winter, 1 = Spring, 2 = Summer, 3 = Fall)
        month = today.month
        season = (month % 12 // 3)

        # Local events (would integrate with events API)
        local_events = 0  # Placeholder

        # Competitor average (would get from market data)
        competitor_avg = self.get_competitor_average(property)

        return [occupancy_rate, days_ahead, day_of_week, season, local_events, competitor_avg]

    def get_next_available_date(self, property):
        """Get the next available date for a property"""
        today = datetime.now().date()

        # Get all future bookings
        future_bookings = Booking.objects.filter(
            property=property,
            check_out_date__gte=today,
            status__in=['confirmed', 'checked_in']
        ).order_by('check_in_date')

        if not future_bookings:
            return today

        # Find first gap
        current_date = today
        for booking in future_bookings:
            if current_date < booking.check_in_date:
                return current_date
            current_date = max(current_date, booking.check_out_date + timedelta(days=1))

        return current_date

    def get_competitor_average(self, property):
        """Get average competitor pricing"""
        # Get market data for the property location
        market_data = MarketData.objects.filter(
            location=property.city
        ).order_by('-date').first()

        if market_data:
            return float(market_data.average_daily_rate)

        # Default to property base price if no market data
        return float(property.base_price)

    def apply_pricing_rules(self, property, base_price):
        """Apply custom pricing rules to the base price"""
        final_price = base_price

        # Get active pricing rules for the property
        rules = PricingRule.objects.filter(
            property=property,
            is_active=True
        )

        for rule in rules:
            # Apply rule multipliers
            final_price *= float(rule.base_multiplier)

            # Apply weekend multiplier if applicable
            if datetime.now().weekday() in [5, 6]:
                final_price *= float(rule.weekend_multiplier)

        # Ensure price is within reasonable bounds
        min_price = float(property.base_price) * 0.5
        max_price = float(property.base_price) * 3.0
        final_price = max(min_price, min(final_price, max_price))

        return final_price

    def get_pricing_factors(self, property, features):
        """Get factors affecting the pricing recommendation"""
        occupancy_rate, days_ahead, day_of_week, season, local_events, competitor_avg = features

        factors = []

        # Occupancy factor
        if occupancy_rate > 0.8:
            factors.append({
                'name': 'High Demand',
                'impact': 'positive',
                'description': f'Property has {occupancy_rate * 100:.0f}% occupancy'
            })
        elif occupancy_rate < 0.5:
            factors.append({
                'name': 'Low Demand',
                'impact': 'negative',
                'description': f'Property has {occupancy_rate * 100:.0f}% occupancy'
            })

        # Timing factor
        if days_ahead < 7:
            factors.append({
                'name': 'Last Minute Booking',
                'impact': 'positive',
                'description': 'Prices typically higher for last-minute bookings'
            })

        # Weekend factor
        if day_of_week in [5, 6]:
            factors.append({
                'name': 'Weekend Premium',
                'impact': 'positive',
                'description': 'Weekend rates are typically higher'
            })

        # Season factor
        season_names = ['Winter', 'Spring', 'Summer', 'Fall']
        if season == 2:  # Summer
            factors.append({
                'name': 'Peak Season',
                'impact': 'positive',
                'description': 'Summer is peak travel season'
            })

        # Competitor factor
        property_price = float(property.base_price)
        if competitor_avg > property_price * 1.1:
            factors.append({
                'name': 'Below Market Rate',
                'impact': 'positive',
                'description': f'Competitors average ${competitor_avg:.0f}, you charge ${property_price:.0f}'
            })

        return factors

    def update_model(self, new_data):
        """Update the model with new booking data"""
        # This would be called periodically to retrain the model
        # with new data to improve predictions
        pass