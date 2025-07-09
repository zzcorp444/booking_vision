from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from .bookings import Booking
from .properties import Property


class Review(models.Model):
    RATING_SCALE_CHOICES = [
        ('5_star', '5 Star Scale (0-5)'),
        ('10_point', '10 Point Scale (0-10)'),
    ]

    PLATFORM_CHOICES = [
        ('airbnb', 'Airbnb'),
        ('booking_com', 'Booking.com'),
        ('agoda', 'Agoda'),
        ('vrbo', 'VRBO'),
        ('expedia', 'Expedia'),
        ('direct', 'Direct Booking'),
        ('other', 'Other'),
    ]

    SENTIMENT_CHOICES = [
        ('positive', 'Positive'),
        ('neutral', 'Neutral'),
        ('negative', 'Negative'),
    ]

    # Core fields
    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name='reviews',
        null=True,
        blank=True
    )
    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name='reviews'
    )

    # Guest information
    guest_name = models.CharField(max_length=100)
    guest_email = models.EmailField(blank=True, null=True)

    # Rating and platform
    platform = models.CharField(
        max_length=20,
        choices=PLATFORM_CHOICES,
        default='direct'
    )
    rating_scale = models.CharField(
        max_length=10,
        choices=RATING_SCALE_CHOICES,
        default='5_star'
    )
    raw_rating = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(10)],
        help_text="The original rating as given on the platform"
    )
    normalized_rating = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        help_text="Rating normalized to 5-star scale for comparison"
    )

    # Review content
    title = models.CharField(max_length=200, blank=True)
    content = models.TextField()
    language = models.CharField(max_length=10, default='en')

    # Analysis fields
    sentiment = models.CharField(
        max_length=10,
        choices=SENTIMENT_CHOICES,
        blank=True,
        null=True
    )
    sentiment_score = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(-1), MaxValueValidator(1)],
        help_text="Sentiment score from -1 (negative) to 1 (positive)"
    )

    # Specific ratings (all normalized to 5-star scale)
    cleanliness_rating = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )
    communication_rating = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )
    location_rating = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )
    value_rating = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )
    amenities_rating = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )

    # Response
    response_text = models.TextField(blank=True)
    response_date = models.DateTimeField(null=True, blank=True)
    responded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='review_responses'
    )

    # Metadata
    review_date = models.DateTimeField(default=timezone.now)
    platform_review_id = models.CharField(max_length=100, blank=True)
    is_verified = models.BooleanField(default=False)
    is_public = models.BooleanField(default=True)
    flagged = models.BooleanField(default=False)
    flag_reason = models.TextField(blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-review_date']
        indexes = [
            models.Index(fields=['property', 'review_date']),
            models.Index(fields=['platform', 'review_date']),
            models.Index(fields=['normalized_rating']),
            models.Index(fields=['sentiment']),
        ]

    def __str__(self):
        return f"{self.guest_name} - {self.property.name} ({self.normalized_rating}/5)"

    def save(self, *args, **kwargs):
        # Normalize rating to 5-star scale
        if self.rating_scale == '10_point':
            self.normalized_rating = (self.raw_rating / 10) * 5
        else:  # 5_star
            self.normalized_rating = self.raw_rating

        # Auto-detect sentiment based on rating if not provided
        if not self.sentiment:
            if self.normalized_rating >= 4:
                self.sentiment = 'positive'
            elif self.normalized_rating >= 2.5:
                self.sentiment = 'neutral'
            else:
                self.sentiment = 'negative'

        super().save(*args, **kwargs)

    @property
    def rating_display(self):
        """Display rating in original scale format"""
        if self.rating_scale == '10_point':
            return f"{self.raw_rating}/10"
        else:
            return f"{self.raw_rating}/5"

    @property
    def response_time(self):
        """Calculate response time in hours"""
        if self.response_date:
            diff = self.response_date - self.review_date
            return diff.total_seconds() / 3600  # Convert to hours
        return None

    @property
    def is_recent(self):
        """Check if review is from last 30 days"""
        thirty_days_ago = timezone.now() - timezone.timedelta(days=30)
        return self.review_date >= thirty_days_ago

    @classmethod
    def get_platform_rating_scale(cls, platform):
        """Get the typical rating scale for a platform"""
        scale_mapping = {
            'airbnb': '5_star',
            'booking_com': '5_star',
            'agoda': '10_point',
            'vrbo': '5_star',
            'expedia': '5_star',
            'direct': '5_star',
            'other': '5_star',
        }
        return scale_mapping.get(platform, '5_star')

    @classmethod
    def normalize_rating(cls, rating, from_scale, to_scale='5_star'):
        """Convert rating between different scales"""
        if from_scale == to_scale:
            return rating

        if from_scale == '10_point' and to_scale == '5_star':
            return (rating / 10) * 5
        elif from_scale == '5_star' and to_scale == '10_point':
            return (rating / 5) * 10

        return rating