"""
Business Intelligence AI Engine for market analysis and insights.
This module provides advanced analytics and market intelligence.
Location: booking_vision_APP/ai/business_intelligence.py
"""
import json
from datetime import datetime, timedelta
from decimal import Decimal
import logging
from typing import Dict, List, Any
import random
from django.utils import timezone

from ..models.properties import Property
from ..models.bookings import Booking
from ..models.ai_models import MarketData

logger = logging.getLogger(__name__)


class BusinessIntelligenceEngine:
    """AI system for business intelligence and market analytics"""

    def __init__(self):
        self.market_trends = {}
        self.competitor_data = {}

    def analyze_market(self, property: Property) -> Dict[str, Any]:
        """Analyze market conditions for a property location"""
        try:
            # Get market data for the property location
            market_data = MarketData.objects.filter(
                location=property.city
            ).order_by('-date').first()

            if not market_data:
                # Generate synthetic market data for demo
                return self.generate_synthetic_market_data(property.city)

            # Calculate market metrics
            market_metrics = {
                'location': property.city,
                'average_daily_rate': float(market_data.average_daily_rate),
                'occupancy_rate': float(market_data.occupancy_rate),
                'revenue_per_room': float(market_data.revenue_per_available_room),
                'market_demand': self.calculate_market_demand(market_data),
                'seasonality_factor': float(market_data.season_factor),
                'price_trend': self.calculate_price_trend(property.city),
                'demand_forecast': self.forecast_demand_trend(property.city),
                'recommendations': self.generate_market_recommendations(market_data)
            }

            return market_metrics

        except Exception as e:
            logger.error(f"Error analyzing market: {str(e)}")
            return self.generate_synthetic_market_data(property.city)

    def analyze_competitors(self, property: Property) -> Dict[str, Any]:
        """Analyze competitor properties in the area"""
        try:
            # In production, this would pull from external APIs
            # For now, generate synthetic competitor data

            competitors = []
            for i in range(5):
                competitors.append({
                    'name': f'Competitor Property {i+1}',
                    'distance': round(random.uniform(0.1, 5.0), 1),
                    'price': round(random.uniform(80, 300), 2),
                    'rating': round(random.uniform(3.5, 5.0), 1),
                    'occupancy': round(random.uniform(60, 95), 1),
                    'amenities_score': round(random.uniform(60, 100), 1)
                })

            # Sort by distance
            competitors.sort(key=lambda x: x['distance'])

            # Calculate competitive position
            avg_price = sum(c['price'] for c in competitors) / len(competitors)
            property_price = float(property.base_price)

            competitive_analysis = {
                'total_competitors': len(competitors),
                'competitors': competitors[:3],  # Top 3 closest
                'average_competitor_price': avg_price,
                'price_position': 'above' if property_price > avg_price else 'below',
                'price_difference': ((property_price - avg_price) / avg_price) * 100,
                'market_share_estimate': self.estimate_market_share(property, competitors),
                'competitive_advantages': self.identify_competitive_advantages(property),
                'threats': self.identify_competitive_threats(property, competitors)
            }

            return competitive_analysis

        except Exception as e:
            logger.error(f"Error analyzing competitors: {str(e)}")
            return {
                'total_competitors': 0,
                'competitors': [],
                'error': str(e)
            }

    def forecast_demand(self, properties: List[Property]) -> Dict[str, Any]:
        """Forecast demand for properties"""
        try:
            forecasts = []

            for property in properties[:5]:  # Limit to 5 properties for performance
                # Generate forecast for next 90 days
                daily_forecasts = []
                base_occupancy = random.uniform(0.6, 0.85)

                for days_ahead in range(90):
                    date = timezone.now().date() + timedelta(days=days_ahead)

                    # Apply seasonality
                    seasonality = self.get_seasonality_factor(date)

                    # Apply day of week factor
                    dow_factor = 1.2 if date.weekday() in [4, 5] else 1.0

                    # Random variation
                    variation = random.uniform(0.9, 1.1)

                    occupancy = min(0.95, base_occupancy * seasonality * dow_factor * variation)

                    daily_forecasts.append({
                        'date': date.isoformat(),
                        'occupancy_forecast': round(occupancy * 100, 1),
                        'demand_level': self.classify_demand_level(occupancy)
                    })

                forecasts.append({
                    'property': property.name,
                    'forecast': daily_forecasts[:30],  # Return 30 days
                    'average_occupancy': round(sum(f['occupancy_forecast'] for f in daily_forecasts[:30]) / 30, 1),
                    'peak_periods': self.identify_peak_periods(daily_forecasts[:30])
                })

            return {
                'forecasts': forecasts,
                'market_outlook': self.generate_market_outlook(forecasts),
                'recommendations': self.generate_demand_recommendations(forecasts)
            }

        except Exception as e:
            logger.error(f"Error forecasting demand: {str(e)}")
            return {
                'forecasts': [],
                'error': str(e)
            }

    def calculate_roi(self, property: Property) -> Dict[str, Any]:
        """Calculate return on investment for a property"""
        try:
            # Get booking data
            bookings = Booking.objects.filter(
                rental_property=property,
                status__in=['confirmed', 'checked_out']
            )

            # Calculate revenue
            total_revenue = sum(float(b.total_price) for b in bookings)
            months_active = max(1, (timezone.now().date() - property.created_at.date()).days / 30)
            monthly_revenue = total_revenue / months_active
            annual_revenue = monthly_revenue * 12

            # Estimate costs (simplified)
            estimated_costs = {
                'mortgage': annual_revenue * 0.3,
                'maintenance': annual_revenue * 0.1,
                'utilities': annual_revenue * 0.05,
                'management': annual_revenue * 0.15,
                'other': annual_revenue * 0.05
            }

            total_costs = sum(estimated_costs.values())
            net_income = annual_revenue - total_costs

            # Assume property value for ROI calculation
            property_value = float(property.base_price) * 365 * 0.6  # Rough estimate

            roi_metrics = {
                'annual_revenue': annual_revenue,
                'annual_costs': total_costs,
                'net_income': net_income,
                'roi_percentage': (net_income / property_value) * 100 if property_value > 0 else 0,
                'payback_period': property_value / net_income if net_income > 0 else float('inf'),
                'cap_rate': (net_income / property_value) * 100 if property_value > 0 else 0,
                'cost_breakdown': estimated_costs,
                'revenue_per_booking': total_revenue / max(bookings.count(), 1),
                'break_even_occupancy': self.calculate_break_even_occupancy(property, estimated_costs)
            }

            return roi_metrics

        except Exception as e:
            logger.error(f"Error calculating ROI: {str(e)}")
            return {
                'annual_revenue': 0,
                'net_income': 0,
                'roi_percentage': 0,
                'error': str(e)
            }

    def analyze_trends(self, user) -> Dict[str, Any]:
        """Analyze booking and revenue trends"""
        try:
            # Get user's bookings
            bookings = Booking.objects.filter(
                rental_property__owner=user
            ).order_by('created_at')

            if not bookings:
                return {
                    'booking_trend': 'no_data',
                    'revenue_trend': 'no_data',
                    'insights': []
                }

            # Analyze monthly trends
            monthly_data = {}
            for booking in bookings:
                month_key = booking.created_at.strftime('%Y-%m')
                if month_key not in monthly_data:
                    monthly_data[month_key] = {
                        'bookings': 0,
                        'revenue': 0
                    }
                monthly_data[month_key]['bookings'] += 1
                monthly_data[month_key]['revenue'] += float(booking.total_price)

            # Calculate trends
            months = sorted(monthly_data.keys())
            if len(months) >= 2:
                # Compare last month to previous
                last_month = monthly_data[months[-1]]
                prev_month = monthly_data[months[-2]]

                booking_change = ((last_month['bookings'] - prev_month['bookings']) / max(prev_month['bookings'], 1)) * 100
                revenue_change = ((last_month['revenue'] - prev_month['revenue']) / max(prev_month['revenue'], 1)) * 100

                trends = {
                    'booking_trend': 'up' if booking_change > 0 else 'down',
                    'booking_change': round(booking_change, 1),
                    'revenue_trend': 'up' if revenue_change > 0 else 'down',
                    'revenue_change': round(revenue_change, 1),
                    'monthly_data': [
                        {
                            'month': datetime.strptime(m, '%Y-%m').strftime('%b %Y'),
                            'bookings': monthly_data[m]['bookings'],
                            'revenue': monthly_data[m]['revenue']
                        }
                        for m in months[-6:]  # Last 6 months
                    ],
                    'insights': self.generate_trend_insights(booking_change, revenue_change),
                    'predictions': self.generate_trend_predictions(monthly_data, months)
                }
            else:
                trends = {
                    'booking_trend': 'insufficient_data',
                    'revenue_trend': 'insufficient_data',
                    'insights': ['Need more data to analyze trends']
                }

            return trends

        except Exception as e:
            logger.error(f"Error analyzing trends: {str(e)}")
            return {
                'booking_trend': 'error',
                'revenue_trend': 'error',
                'error': str(e)
            }

    # Helper methods
    def generate_synthetic_market_data(self, location: str) -> Dict[str, Any]:
        """Generate synthetic market data for demo purposes"""
        return {
            'location': location,
            'average_daily_rate': round(random.uniform(100, 250), 2),
            'occupancy_rate': round(random.uniform(65, 85), 1),
            'revenue_per_room': round(random.uniform(80, 200), 2),
            'market_demand': 'high' if random.random() > 0.5 else 'moderate',
            'seasonality_factor': round(random.uniform(0.8, 1.2), 2),
            'price_trend': 'increasing' if random.random() > 0.5 else 'stable',
            'demand_forecast': 'positive',
            'recommendations': [
                'Consider dynamic pricing during peak seasons',
                'Monitor competitor pricing weekly',
                'Focus on guest experience to maintain high ratings'
            ]
        }

    def calculate_market_demand(self, market_data: MarketData) -> str:
        """Calculate market demand level"""
        if market_data.occupancy_rate > 80:
            return 'very_high'
        elif market_data.occupancy_rate > 65:
            return 'high'
        elif market_data.occupancy_rate > 50:
            return 'moderate'
        else:
            return 'low'

    def calculate_price_trend(self, location: str) -> str:
        """Calculate price trend for location"""
        # In production, this would analyze historical data
        trends = ['increasing', 'stable', 'decreasing']
        return random.choice(trends)

    def forecast_demand_trend(self, location: str) -> str:
        """Forecast demand trend"""
        # In production, this would use ML models
        trends = ['positive', 'neutral', 'negative']
        return random.choice(trends)

    def generate_market_recommendations(self, market_data: MarketData) -> List[str]:
        """Generate market-based recommendations"""
        recommendations = []

        if market_data.occupancy_rate > 80:
            recommendations.append("High demand detected - consider increasing prices by 10-15%")
        elif market_data.occupancy_rate < 50:
            recommendations.append("Low occupancy - consider promotional pricing or special offers")

        if market_data.season_factor > 1.1:
            recommendations.append("Peak season approaching - optimize pricing and minimum stay requirements")

        return recommendations

    def estimate_market_share(self, property: Property, competitors: List[Dict]) -> float:
        """Estimate market share based on competitive position"""
        # Simplified calculation based on price and rating
        total_properties = len(competitors) + 1
        return round(100 / total_properties, 1)

    def identify_competitive_advantages(self, property: Property) -> List[str]:
        """Identify property's competitive advantages"""
        advantages = []

        if property.ai_pricing_enabled:
            advantages.append("AI-powered dynamic pricing")

        if property.ai_guest_enabled:
            advantages.append("AI-enhanced guest experience")

        # Check amenities
        amenity_count = property.propertyamenity_set.count()
        if amenity_count > 10:
            advantages.append(f"Extensive amenities ({amenity_count} features)")

        return advantages

    def identify_competitive_threats(self, property: Property, competitors: List[Dict]) -> List[str]:
        """Identify competitive threats"""
        threats = []

        # Check if priced too high
        avg_price = sum(c['price'] for c in competitors) / len(competitors) if competitors else 0
        if float(property.base_price) > avg_price * 1.2:
            threats.append("Priced significantly above market average")

        # Check ratings
        high_rated_competitors = sum(1 for c in competitors if c.get('rating', 0) > 4.5)
        if high_rated_competitors > len(competitors) / 2:
            threats.append("Many highly-rated competitors in area")

        return threats

    def get_seasonality_factor(self, date: datetime.date) -> float:
        """Get seasonality factor for a date"""
        month = date.month

        # Summer peak
        if month in [6, 7, 8]:
            return 1.3
        # Winter low
        elif month in [1, 2, 11, 12]:
            return 0.8
        # Spring/Fall moderate
        else:
            return 1.0

    def classify_demand_level(self, occupancy: float) -> str:
        """Classify demand level based on occupancy"""
        if occupancy > 0.85:
            return 'very_high'
        elif occupancy > 0.7:
            return 'high'
        elif occupancy > 0.5:
            return 'moderate'
        else:
            return 'low'

    def identify_peak_periods(self, forecasts: List[Dict]) -> List[Dict]:
        """Identify peak demand periods"""
        peak_periods = []

        for i, forecast in enumerate(forecasts):
            if forecast['occupancy_forecast'] > 85:
                peak_periods.append({
                    'date': forecast['date'],
                    'occupancy': forecast['occupancy_forecast']
                })

        return peak_periods[:5]  # Top 5 peak days

    def generate_market_outlook(self, forecasts: List[Dict]) -> str:
        """Generate overall market outlook"""
        if not forecasts:
            return 'uncertain'

        avg_occupancy = sum(f['average_occupancy'] for f in forecasts) / len(forecasts)

        if avg_occupancy > 80:
            return 'very_positive'
        elif avg_occupancy > 65:
            return 'positive'
        elif avg_occupancy > 50:
            return 'neutral'
        else:
            return 'challenging'

    def generate_demand_recommendations(self, forecasts: List[Dict]) -> List[str]:
        """Generate recommendations based on demand forecast"""
        recommendations = []

        if forecasts:
            avg_occupancy = sum(f['average_occupancy'] for f in forecasts) / len(forecasts)

            if avg_occupancy > 80:
                recommendations.append("High demand expected - increase prices by 10-20%")
                recommendations.append("Implement minimum stay requirements during peak periods")
            elif avg_occupancy < 60:
                recommendations.append("Lower demand expected - consider promotional campaigns")
                recommendations.append("Offer discounts for longer stays")

            # Check for peak periods
            for forecast in forecasts:
                if forecast.get('peak_periods'):
                    recommendations.append(f"Prepare for peak demand on {len(forecast['peak_periods'])} days")
                    break

        return recommendations[:3]

    def calculate_break_even_occupancy(self, property: Property, costs: Dict[str, float]) -> float:
        """Calculate break-even occupancy rate"""
        total_costs = sum(costs.values())
        daily_rate = float(property.base_price)
        annual_revenue_at_full = daily_rate * 365

        if annual_revenue_at_full > 0:
            break_even_occupancy = (total_costs / annual_revenue_at_full) * 100
            return round(min(break_even_occupancy, 100), 1)

        return 0

    def generate_trend_insights(self, booking_change: float, revenue_change: float) -> List[str]:
        """Generate insights based on trends"""
        insights = []

        if booking_change > 20:
            insights.append("Excellent booking growth - maintain momentum")
        elif booking_change < -20:
            insights.append("Significant booking decline - review pricing and marketing")

        if revenue_change > booking_change + 10:
            insights.append("Revenue growing faster than bookings - pricing strategy working well")
        elif revenue_change < booking_change - 10:
            insights.append("Revenue lagging bookings - consider optimizing pricing")

        return insights

    def generate_trend_predictions(self, monthly_data: Dict, months: List[str]) -> Dict[str, Any]:
        """Generate predictions based on trends"""
        if len(months) < 3:
            return {'status': 'insufficient_data'}

        # Simple linear projection
        recent_months = months[-3:]
        recent_bookings = [monthly_data[m]['bookings'] for m in recent_months]

        # Calculate average growth
        growth_rate = 0
        if len(recent_bookings) > 1:
            growth_rate = (recent_bookings[-1] - recent_bookings[0]) / max(recent_bookings[0], 1)

        # Project next month
        next_month_bookings = int(recent_bookings[-1] * (1 + growth_rate))

        return {
            'next_month_bookings': max(0, next_month_bookings),
            'growth_rate': round(growth_rate * 100, 1),
            'confidence': 'medium'  # Would be calculated based on data consistency
        }