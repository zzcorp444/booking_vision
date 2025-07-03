"""
AI-powered predictive maintenance system.
This module predicts maintenance needs using machine learning.
Location: booking_vision_APP/ai/maintenance_predictor.py
"""
import numpy as np
from datetime import datetime, timedelta
import random
from collections import defaultdict
import logging

from ..models.properties import Property
from ..models.bookings import Booking
from ..models.ai_models import MaintenanceTask

logger = logging.getLogger(__name__)


class MaintenancePredictor:
    """AI system for predicting maintenance needs"""

    # Maintenance intervals (in days)
    MAINTENANCE_SCHEDULES = {
        'HVAC Filter': {'interval': 90, 'priority': 'medium', 'cost': 50},
        'Deep Cleaning': {'interval': 30, 'priority': 'high', 'cost': 200},
        'Plumbing Inspection': {'interval': 180, 'priority': 'medium', 'cost': 150},
        'Electrical Check': {'interval': 365, 'priority': 'low', 'cost': 100},
        'Appliance Service': {'interval': 180, 'priority': 'medium', 'cost': 300},
        'Smoke Detector Test': {'interval': 90, 'priority': 'high', 'cost': 25},
        'Water Heater Service': {'interval': 365, 'priority': 'medium', 'cost': 200},
        'Gutter Cleaning': {'interval': 180, 'priority': 'low', 'cost': 150},
        'Window Cleaning': {'interval': 60, 'priority': 'low', 'cost': 100},
        'Carpet Cleaning': {'interval': 120, 'priority': 'medium', 'cost': 250}
    }

    def __init__(self):
        self.failure_patterns = self.load_failure_patterns()

    def load_failure_patterns(self):
        """Load historical failure patterns"""
        # In production, this would load from a trained model
        # For now, we'll use predefined patterns
        return {
            'high_usage': {
                'threshold': 20,  # bookings per month
                'impact': 1.5,    # accelerates maintenance needs
                'affected_items': ['Deep Cleaning', 'HVAC Filter', 'Appliance Service']
            },
            'seasonal': {
                'summer': ['HVAC Filter', 'Window Cleaning'],
                'winter': ['Plumbing Inspection', 'Water Heater Service'],
                'spring': ['Gutter Cleaning', 'Deep Cleaning'],
                'fall': ['HVAC Filter', 'Smoke Detector Test']
            },
            'age_factor': {
                'new': 0.8,      # 0-2 years
                'moderate': 1.0,  # 2-5 years
                'old': 1.3       # 5+ years
            }
        }

    def predict_maintenance_needs(self, property):
        """Predict upcoming maintenance needs for a property"""
        predictions = []
        today = datetime.now().date()

        # Get property usage metrics
        usage_metrics = self.calculate_usage_metrics(property)

        # Get last maintenance dates
        last_maintenance = self.get_last_maintenance_dates(property)

        # Predict for each maintenance type
        for maintenance_type, schedule in self.MAINTENANCE_SCHEDULES.items():
            # Calculate days since last maintenance
            last_date = last_maintenance.get(maintenance_type)
            if last_date:
                days_since = (today - last_date).days
            else:
                # Assume needs maintenance if no record
                days_since = schedule['interval']

            # Apply usage factor
            usage_factor = self.calculate_usage_factor(
                property, maintenance_type, usage_metrics
            )

            # Apply seasonal factor
            seasonal_factor = self.calculate_seasonal_factor(maintenance_type)

            # Apply age factor
            age_factor = self.calculate_age_factor(property)

            # Calculate adjusted interval
            adjusted_interval = schedule['interval'] / (usage_factor * seasonal_factor * age_factor)

            # Calculate days until maintenance
            days_until = adjusted_interval - days_since

            # Add prediction if maintenance is due soon
            if days_until <= 30:  # Within 30 days
                confidence = self.calculate_confidence(days_until, usage_metrics)

                predictions.append({
                    'property': property,
                    'maintenance_type': maintenance_type,
                    'days_until': max(0, int(days_until)),
                    'priority': self.adjust_priority(schedule['priority'], days_until),
                    'estimated_cost': schedule['cost'],
                    'confidence': confidence,
                    'factors': {
                        'usage': usage_factor,
                        'seasonal': seasonal_factor,
                        'age': age_factor
                    }
                })

        return sorted(predictions, key=lambda x: x['days_until'])

    def calculate_usage_metrics(self, property):
        """Calculate property usage metrics"""
        today = datetime.now().date()
        thirty_days_ago = today - timedelta(days=30)
        ninety_days_ago = today - timedelta(days=90)

        # Get recent bookings
        recent_bookings = Booking.objects.filter(
            rental_property=property,
            check_in_date__gte=ninety_days_ago,
            status__in=['confirmed', 'checked_in', 'checked_out']
        )

        # Calculate metrics
        bookings_30_days = recent_bookings.filter(
            check_in_date__gte=thirty_days_ago
        ).count()

        total_guests = sum(booking.num_guests for booking in recent_bookings)

        # Calculate occupancy rate
        booked_days = 0
        for booking in recent_bookings:
            if booking.check_out_date >= ninety_days_ago:
                start = max(booking.check_in_date, ninety_days_ago)
                end = min(booking.check_out_date, today)
                booked_days += (end - start).days + 1

        occupancy_rate = booked_days / 90.0

        return {
            'bookings_per_month': bookings_30_days,
            'total_guests': total_guests,
            'occupancy_rate': occupancy_rate,
            'high_usage': bookings_30_days >= self.failure_patterns['high_usage']['threshold']
        }

    def get_last_maintenance_dates(self, property):
        """Get last maintenance date for each type"""
        last_dates = {}

        # Get completed maintenance tasks
        tasks = MaintenanceTask.objects.filter(
            rental_property=property,
            status='completed'
        ).order_by('-completed_date')

        for task in tasks:
            # Extract maintenance type from title
            for mtype in self.MAINTENANCE_SCHEDULES.keys():
                if mtype.lower() in task.title.lower():
                    if mtype not in last_dates:
                        last_dates[mtype] = task.completed_date

        return last_dates

    def calculate_usage_factor(self, property, maintenance_type, usage_metrics):
        """Calculate usage impact factor"""
        base_factor = 1.0

        if usage_metrics['high_usage']:
            high_usage_config = self.failure_patterns['high_usage']
            if maintenance_type in high_usage_config['affected_items']:
                base_factor = high_usage_config['impact']

        # Additional usage-based adjustments
        if maintenance_type == 'Deep Cleaning':
            # More guests = more frequent cleaning needed
            if usage_metrics['total_guests'] > 50:
                base_factor *= 1.2

        return base_factor

    def calculate_seasonal_factor(self, maintenance_type):
        """Calculate seasonal impact factor"""
        current_season = self.get_current_season()
        seasonal_items = self.failure_patterns['seasonal'].get(current_season, [])

        if maintenance_type in seasonal_items:
            return 1.3  # 30% more likely to need maintenance

        return 1.0

    def calculate_age_factor(self, property):
        """Calculate property age impact factor"""
        # This would ideally use actual property age
        # For now, we'll use a random factor
        property_age_years = random.choice([1, 3, 6])

        if property_age_years <= 2:
            return self.failure_patterns['age_factor']['new']
        elif property_age_years <= 5:
            return self.failure_patterns['age_factor']['moderate']
        else:
            return self.failure_patterns['age_factor']['old']

    def get_current_season(self):
        """Get current season"""
        month = datetime.now().month
        if month in [12, 1, 2]:
            return 'winter'
        elif month in [3, 4, 5]:
            return 'spring'
        elif month in [6, 7, 8]:
            return 'summer'
        else:
            return 'fall'

    def adjust_priority(self, base_priority, days_until):
        """Adjust priority based on urgency"""
        if days_until <= 0:
            return 'urgent'
        elif days_until <= 7:
            return 'high'
        elif days_until <= 14 and base_priority == 'high':
            return 'high'
        else:
            return base_priority

    def calculate_confidence(self, days_until, usage_metrics):
        """Calculate prediction confidence"""
        # Base confidence
        confidence = 0.7

        # Adjust based on data availability
        if usage_metrics['bookings_per_month'] > 10:
            confidence += 0.1  # More data = higher confidence

        # Adjust based on urgency
        if days_until <= 0:
            confidence = 0.95  # Very confident if overdue
        elif days_until <= 7:
            confidence += 0.15

        return min(confidence, 0.95)

    def get_upcoming_maintenance(self, properties):
        """Get upcoming maintenance for multiple properties"""
        all_predictions = []

        for property in properties:
            predictions = self.predict_maintenance_needs(property)
            all_predictions.extend(predictions)

        # Sort by urgency
        all_predictions.sort(key=lambda x: (x['days_until'], -x['confidence']))

        # Format for display
        formatted_predictions = []
        for pred in all_predictions[:5]:  # Top 5
            formatted_predictions.append({
                'property': pred['property'],
                'message': f"{pred['maintenance_type']} needed in {pred['days_until']} days",
                'priority': pred['priority'],
                'cost': pred['estimated_cost'],
                'confidence': pred['confidence']
            })

        return formatted_predictions

    def schedule_maintenance(self, property, maintenance_type, scheduled_date):
        """Schedule a maintenance task"""
        schedule = self.MAINTENANCE_SCHEDULES.get(maintenance_type, {})

        task = MaintenanceTask.objects.create(
            rental_property=property,
            title=maintenance_type,
            description=f"Scheduled maintenance for {maintenance_type}",
            priority=schedule.get('priority', 'medium'),
            status='scheduled',
            scheduled_date=scheduled_date,
            estimated_cost=schedule.get('cost', 0),
            predicted_by_ai=True,
            prediction_confidence=0.85
        )

        return task