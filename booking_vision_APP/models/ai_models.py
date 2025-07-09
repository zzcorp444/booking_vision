"""
AI-related models for the booking vision application.
This file defines models for AI features and machine learning data.
"""
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal
import json

from .bookings import Guest


class PricingRule(models.Model):
    """Model for dynamic pricing rules"""
    rental_property = models.ForeignKey('Property', on_delete=models.CASCADE, related_name='pricing_rules')
    name = models.CharField(max_length=100)

    # Rule conditions
    min_days_ahead = models.IntegerField(default=0)
    max_days_ahead = models.IntegerField(default=365)
    min_stay_length = models.IntegerField(default=1)
    max_stay_length = models.IntegerField(default=30)

    # Pricing adjustments
    base_multiplier = models.DecimalField(max_digits=5, decimal_places=2, default=1.0)
    weekend_multiplier = models.DecimalField(max_digits=5, decimal_places=2, default=1.0)
    holiday_multiplier = models.DecimalField(max_digits=5, decimal_places=2, default=1.0)

    # Occupancy-based pricing
    high_demand_threshold = models.DecimalField(max_digits=5, decimal_places=2, default=0.8)
    high_demand_multiplier = models.DecimalField(max_digits=5, decimal_places=2, default=1.2)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.rental_property.name if self.rental_property else 'Unknown'} - {self.name}"

    def get_property(self):
        """Backward compatibility property"""
        return self.rental_property


class MaintenanceTask(models.Model):
    """Model for maintenance tasks and predictions"""
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    rental_property = models.ForeignKey('Property', on_delete=models.CASCADE, related_name='maintenance_tasks')
    title = models.CharField(max_length=200)
    description = models.TextField()
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    # AI prediction fields
    predicted_by_ai = models.BooleanField(default=False)
    prediction_confidence = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    predicted_failure_date = models.DateField(null=True, blank=True)

    # Scheduling
    scheduled_date = models.DateField(null=True, blank=True)
    estimated_duration = models.IntegerField(help_text="Duration in hours", null=True, blank=True)
    estimated_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # Completion
    completed_date = models.DateField(null=True, blank=True)
    actual_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-priority', '-created_at']

    def __str__(self):
        return f"{self.rental_property.name if self.rental_property else 'Unknown'} - {self.title}"

    def get_property(self):
        """Backward compatibility property"""
        return self.rental_property

class GuestPreference(models.Model):
    """Model for storing guest preferences and AI insights"""
    guest = models.OneToOneField(Guest, on_delete=models.CASCADE, related_name='ai_preferences')

    # Preference categories
    room_temperature = models.IntegerField(null=True, blank=True)
    preferred_check_in_time = models.TimeField(null=True, blank=True)
    preferred_check_out_time = models.TimeField(null=True, blank=True)

    # Activity preferences
    interests = models.JSONField(default=list, blank=True)
    dietary_restrictions = models.JSONField(default=list, blank=True)

    # AI-generated insights
    guest_type = models.CharField(max_length=50, blank=True)  # business, leisure, family, etc.
    spending_pattern = models.CharField(max_length=50, blank=True)
    communication_preference = models.CharField(max_length=50, blank=True)

    # Satisfaction tracking
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    loyalty_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Preferences for {self.guest.first_name if self.guest else 'Unknown'} {self.guest.last_name if self.guest else ''}"


class MarketData(models.Model):
    """Model for storing market intelligence data"""
    location = models.CharField(max_length=200)
    date = models.DateField()

    # Market metrics
    average_daily_rate = models.DecimalField(max_digits=10, decimal_places=2)
    occupancy_rate = models.DecimalField(max_digits=5, decimal_places=2)
    revenue_per_available_room = models.DecimalField(max_digits=10, decimal_places=2)

    # Demand indicators
    search_volume = models.IntegerField(default=0)
    booking_lead_time = models.IntegerField(default=0)

    # Events and seasonality
    events = models.JSONField(default=list, blank=True)
    season_factor = models.DecimalField(max_digits=5, decimal_places=2, default=1.0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['location', 'date']
        ordering = ['-date']
        verbose_name_plural = "Market Data"

    def __str__(self):
        return f"{self.location} - {self.date}"


# NEW AI MODELS (complementing your existing ones)

class AIInsight(models.Model):
    """Model for storing AI-generated insights and recommendations"""

    INSIGHT_TYPES = [
        ('revenue_optimization', 'Revenue Optimization'),
        ('pricing_suggestion', 'Pricing Suggestion'),
        ('guest_experience', 'Guest Experience'),
        ('operational_efficiency', 'Operational Efficiency'),
        ('market_opportunity', 'Market Opportunity'),
        ('risk_assessment', 'Risk Assessment'),
        ('maintenance_prediction', 'Maintenance Prediction'),
        ('demand_forecast', 'Demand Forecast'),
        ('competitive_analysis', 'Competitive Analysis'),
        ('seasonal_insight', 'Seasonal Insight'),
    ]

    PRIORITY_LEVELS = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]

    IMPACT_LEVELS = [
        ('low', 'Low Impact'),
        ('medium', 'Medium Impact'),
        ('high', 'High Impact'),
        ('very_high', 'Very High Impact'),
    ]

    # Core fields
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ai_insights')
    related_property = models.ForeignKey(
        'booking_vision_APP.Property',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='ai_insights'
    )

    insight_type = models.CharField(max_length=30, choices=INSIGHT_TYPES)
    title = models.CharField(max_length=200)
    description = models.TextField()

    # AI confidence and impact
    confidence_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="AI confidence from 0 to 100"
    )
    priority = models.CharField(max_length=10, choices=PRIORITY_LEVELS)
    impact_level = models.CharField(max_length=15, choices=IMPACT_LEVELS)

    # Potential value
    estimated_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Estimated financial impact"
    )

    # Action and implementation
    recommended_action = models.TextField(blank=True)
    implementation_effort = models.CharField(
        max_length=20,
        choices=[
            ('low', 'Low Effort'),
            ('medium', 'Medium Effort'),
            ('high', 'High Effort'),
        ],
        default='medium'
    )

    # Status tracking
    is_active = models.BooleanField(default=True)
    is_implemented = models.BooleanField(default=False)
    implemented_date = models.DateTimeField(null=True, blank=True)

    # Data source and methodology
    data_sources = models.JSONField(default=list, blank=True)
    ai_model_version = models.CharField(max_length=50, blank=True)
    generation_metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-priority', '-confidence_score', '-created_at']
        indexes = [
            models.Index(fields=['user', 'insight_type']),
            models.Index(fields=['related_property', 'insight_type']),
            models.Index(fields=['confidence_score']),
        ]

    def __str__(self):
        return f"{self.title} - {self.confidence_score}% confidence"

    def mark_as_implemented(self):
        """Mark insight as implemented"""
        self.is_implemented = True
        self.implemented_date = timezone.now()
        self.save(update_fields=['is_implemented', 'implemented_date'])

    def get_property(self):
        """Backward compatibility property"""
        return self.related_property

    @classmethod
    def create_insight(cls, user, insight_type, title, description,
                      confidence_score, priority='medium', related_property=None,
                      estimated_value=None, recommended_action='',
                      implementation_effort='medium', metadata=None):
        """Create a new AI insight"""
        return cls.objects.create(
            user=user,
            related_property=related_property,
            insight_type=insight_type,
            title=title,
            description=description,
            confidence_score=confidence_score,
            priority=priority,
            estimated_value=estimated_value,
            recommended_action=recommended_action,
            implementation_effort=implementation_effort,
            generation_metadata=metadata or {}
        )


class PredictiveModel(models.Model):
    """Model for storing AI prediction models and their performance"""

    MODEL_TYPES = [
        ('demand_forecast', 'Demand Forecasting'),
        ('price_optimization', 'Price Optimization'),
        ('maintenance_prediction', 'Maintenance Prediction'),
        ('guest_satisfaction', 'Guest Satisfaction'),
        ('revenue_forecast', 'Revenue Forecasting'),
        ('occupancy_prediction', 'Occupancy Prediction'),
        ('churn_prediction', 'Guest Churn Prediction'),
        ('market_analysis', 'Market Analysis'),
    ]

    # Model identification
    model_type = models.CharField(max_length=30, choices=MODEL_TYPES)
    model_name = models.CharField(max_length=100)
    version = models.CharField(max_length=20)

    # Model metadata
    description = models.TextField()
    algorithm = models.CharField(max_length=100)
    features = models.JSONField(default=list)
    hyperparameters = models.JSONField(default=dict)

    # Performance metrics
    accuracy_score = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)
    precision_score = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)
    recall_score = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)
    f1_score = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)

    # Training information
    training_data_size = models.IntegerField(default=0)
    training_start_date = models.DateTimeField()
    training_end_date = models.DateTimeField()
    last_retrained = models.DateTimeField(auto_now_add=True)

    # Model status
    is_active = models.BooleanField(default=True)
    is_production = models.BooleanField(default=False)

    # Usage statistics
    prediction_count = models.IntegerField(default=0)
    success_count = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_production', '-accuracy_score', '-created_at']
        unique_together = ['model_type', 'version']

    def __str__(self):
        return f"{self.model_name} v{self.version} - {self.accuracy_score or 'N/A'}% accuracy"

    def get_success_rate(self):
        """Calculate model success rate"""
        if self.prediction_count == 0:
            return 0
        return (self.success_count / self.prediction_count) * 100

    # Use property-like access via method
    @property
    def success_rate(self):
        return self.get_success_rate()

    def record_prediction(self, success=True):
        """Record a prediction and its outcome"""
        self.prediction_count += 1
        if success:
            self.success_count += 1
        self.save(update_fields=['prediction_count', 'success_count'])


class BusinessMetric(models.Model):
    """Model for tracking key business metrics over time"""

    METRIC_TYPES = [
        ('revenue', 'Revenue'),
        ('occupancy_rate', 'Occupancy Rate'),
        ('adr', 'Average Daily Rate'),
        ('revpar', 'Revenue per Available Room'),
        ('guest_satisfaction', 'Guest Satisfaction'),
        ('booking_lead_time', 'Booking Lead Time'),
        ('cancellation_rate', 'Cancellation Rate'),
        ('repeat_guest_rate', 'Repeat Guest Rate'),
        ('market_share', 'Market Share'),
        ('cost_per_acquisition', 'Cost per Acquisition'),
        ('lifetime_value', 'Customer Lifetime Value'),
        ('operational_efficiency', 'Operational Efficiency'),
    ]

    AGGREGATION_PERIODS = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
    ]

    # Core fields
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='business_metrics')
    related_property = models.ForeignKey(
        'booking_vision_APP.Property',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='business_metrics'
    )

    metric_type = models.CharField(max_length=30, choices=METRIC_TYPES)
    value = models.DecimalField(max_digits=15, decimal_places=4)

    # Time dimensions
    date = models.DateField()
    aggregation_period = models.CharField(max_length=20, choices=AGGREGATION_PERIODS)

    # Comparison and trends
    previous_value = models.DecimalField(max_digits=15, decimal_places=4, null=True, blank=True)
    change_percentage = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)

    # Benchmarking
    market_average = models.DecimalField(max_digits=15, decimal_places=4, null=True, blank=True)
    performance_vs_market = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)

    # Data quality
    confidence_level = models.DecimalField(max_digits=5, decimal_places=2, default=100.0)
    data_sources = models.JSONField(default=list)

    # AI predictions
    predicted_next_value = models.DecimalField(max_digits=15, decimal_places=4, null=True, blank=True)
    prediction_confidence = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', 'metric_type']
        unique_together = ['user', 'related_property', 'metric_type', 'date', 'aggregation_period']
        indexes = [
            models.Index(fields=['user', 'metric_type', 'date']),
            models.Index(fields=['related_property', 'metric_type', 'date']),
        ]

    def __str__(self):
        property_name = self.related_property.name if self.related_property else "All Properties"
        return f"{property_name} - {self.metric_type} - {self.date}"

    def get_property(self):
        """Backward compatibility property"""
        return self.related_property

    def calculate_trend(self):
        """Calculate trend compared to previous period"""
        if self.previous_value and self.previous_value != 0:
            self.change_percentage = ((self.value - self.previous_value) / abs(self.previous_value)) * 100
            self.save(update_fields=['change_percentage'])

    @classmethod
    def get_metric_trend(cls, user, metric_type, related_property=None, days=30):
        """Get trend data for a specific metric"""
        queryset = cls.objects.filter(
            user=user,
            metric_type=metric_type,
            date__gte=timezone.now().date() - timezone.timedelta(days=days)
        )

        if related_property:
            queryset = queryset.filter(related_property=related_property)

        return queryset.order_by('date')


class ReviewSentiment(models.Model):
    """Model for storing review sentiment analysis results"""

    SENTIMENT_CHOICES = [
        ('very_negative', 'Very Negative'),
        ('negative', 'Negative'),
        ('neutral', 'Neutral'),
        ('positive', 'Positive'),
        ('very_positive', 'Very Positive'),
    ]

    review = models.OneToOneField(
        'booking_vision_APP.Review',
        on_delete=models.CASCADE,
        related_name='sentiment_analysis'
    )

    # Overall sentiment
    sentiment = models.CharField(max_length=20, choices=SENTIMENT_CHOICES)
    sentiment_score = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        help_text="Sentiment score from -1 (very negative) to 1 (very positive)"
    )
    confidence = models.DecimalField(max_digits=5, decimal_places=4)

    # Aspect-based sentiment
    cleanliness_sentiment = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)
    location_sentiment = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)
    value_sentiment = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)
    communication_sentiment = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)
    amenities_sentiment = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)

    # Keywords and topics
    positive_keywords = models.JSONField(default=list)
    negative_keywords = models.JSONField(default=list)
    topics = models.JSONField(default=list)

    # AI model information
    model_version = models.CharField(max_length=50)
    processing_time = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Sentiment: {self.sentiment} ({self.sentiment_score}) for Review #{self.review.id}"

    def get_sentiment_emoji(self):
        """Get emoji representation of sentiment"""
        emoji_map = {
            'very_negative': '😡',
            'negative': '😞',
            'neutral': '😐',
            'positive': '😊',
            'very_positive': '🤩',
        }
        return emoji_map.get(self.sentiment, '😐')

    # Use property-like access via method
    @property
    def sentiment_emoji(self):
        return self.get_sentiment_emoji()


class CompetitorAnalysis(models.Model):
    """Model for storing competitor analysis data"""

    # Use related_property to avoid conflicts
    related_property = models.ForeignKey(
        'booking_vision_APP.Property',
        on_delete=models.CASCADE,
        related_name='competitor_analyses'
    )

    # Competitor identification
    competitor_name = models.CharField(max_length=200)
    competitor_type = models.CharField(
        max_length=50,
        choices=[
            ('direct', 'Direct Competitor'),
            ('indirect', 'Indirect Competitor'),
            ('aspirational', 'Aspirational Competitor'),
        ]
    )

    # Location and property details
    distance_km = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    competitor_property_type = models.CharField(max_length=100, blank=True)
    room_count = models.IntegerField(null=True, blank=True)

    # Pricing analysis
    average_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    minimum_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    maximum_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # Performance metrics
    occupancy_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    review_count = models.IntegerField(default=0)
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)

    # Amenities and features
    amenities = models.JSONField(default=list)
    unique_features = models.JSONField(default=list)

    # Market positioning
    target_segment = models.CharField(max_length=100, blank=True)
    pricing_strategy = models.CharField(max_length=100, blank=True)

    # Data collection
    data_source = models.CharField(max_length=100, default='manual')
    last_updated = models.DateTimeField(auto_now=True)

    # Analysis results
    competitive_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    strengths = models.JSONField(default=list)
    weaknesses = models.JSONField(default=list)
    opportunities = models.JSONField(default=list)
    threats = models.JSONField(default=list)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-competitive_score', 'distance_km']
        unique_together = ['related_property', 'competitor_name']

    def __str__(self):
        return f"{self.related_property.name} vs {self.competitor_name}"

    def get_property(self):
        """Backward compatibility property"""
        return self.related_property

    def get_price_comparison(self):
        """Compare pricing with the main property"""
        if self.average_rate and hasattr(self.related_property, 'base_price'):
            if self.related_property.base_price > 0:
                return ((self.average_rate - self.related_property.base_price) / self.related_property.base_price) * 100
        return None

    # Use property-like access via method
    @property
    def price_comparison(self):
        return self.get_price_comparison()

    @property
    def property(self):
        """Backward compatibility property"""
        return self.related_property