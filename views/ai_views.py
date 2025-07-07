"""
AI-powered views for Booking Vision application.
This file contains views for all AI features.
Location: booking_vision_APP/views/ai_views.py
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, View
from django.http import JsonResponse
from django.utils import timezone
from datetime import datetime, timedelta
import json

from ..models.properties import Property
from ..models.bookings import Booking, Guest
from ..models.ai_models import PricingRule, MaintenanceTask, GuestPreference, MarketData
from ..ai.pricing_engine import PricingEngine
from ..ai.sentiment_analysis import SentimentAnalyzer
from ..ai.maintenance_predictor import MaintenancePredictor
from ..ai.guest_experience import GuestExperienceEngine
from ..ai.business_intelligence import BusinessIntelligenceEngine


class SmartPricingView(LoginRequiredMixin, TemplateView):
    """Smart pricing AI view"""
    template_name = 'ai/smart_pricing.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Get user properties
        properties = Property.objects.filter(owner=user, is_active=True)
        context['properties'] = properties

        # Get pricing engine
        pricing_engine = PricingEngine()

        # Get pricing recommendations for each property
        recommendations = []
        for property in properties:
            rec = pricing_engine.get_pricing_recommendation(property)
            if rec:
                recommendations.append({
                    'property': property,
                    'current_price': float(property.base_price),
                    'suggested_price': rec['suggested_price'],
                    'revenue_increase': rec['revenue_increase'],
                    'factors': rec['factors'],
                    'confidence': rec['confidence']
                })

        context['recommendations'] = recommendations

        # Get market data
        if properties.exists():
            market_data = MarketData.objects.filter(
                location=properties.first().city
            ).order_by('-date').first()
            context['market_data'] = market_data

        # Get pricing rules
        context['pricing_rules'] = PricingRule.objects.filter(
            rental_property__owner=user,
            is_active=True
        )

        return context

    def post(self, request, *args, **kwargs):
        """Handle pricing updates"""
        data = json.loads(request.body)
        property_id = data.get('property_id')
        new_price = data.get('price')

        try:
            property = Property.objects.get(id=property_id, owner=request.user)
            property.base_price = new_price
            property.ai_pricing_enabled = True
            property.last_pricing_update = timezone.now()
            property.save()

            return JsonResponse({
                'success': True,
                'message': 'Price updated successfully'
            })
        except Property.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Property not found'
            }, status=404)


class PredictiveMaintenanceView(LoginRequiredMixin, TemplateView):
    """Predictive maintenance AI view"""
    template_name = 'ai/predictive_maintenance.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Get user properties
        properties = Property.objects.filter(owner=user, is_active=True)
        context['properties'] = properties

        # Get maintenance predictor
        predictor = MaintenancePredictor()

        # Get maintenance predictions
        predictions = []
        for property in properties:
            property_predictions = predictor.predict_maintenance_needs(property)
            predictions.extend(property_predictions)

        # Sort by urgency
        predictions.sort(key=lambda x: x['days_until'], reverse=False)
        context['predictions'] = predictions[:10]  # Top 10 predictions

        # Get existing maintenance tasks
        context['maintenance_tasks'] = MaintenanceTask.objects.filter(
            rental_property__owner=user
        ).select_related('rental_property').order_by('-priority', '-created_at')[:20]

        # Get maintenance statistics
        context['maintenance_stats'] = {
            'total_tasks': MaintenanceTask.objects.filter(rental_property__owner=user).count(),
            'pending_tasks': MaintenanceTask.objects.filter(
                rental_property__owner=user,
                status='pending'
            ).count(),
            'ai_predicted': MaintenanceTask.objects.filter(
                rental_property__owner=user,
                predicted_by_ai=True
            ).count(),
            'completed_this_month': MaintenanceTask.objects.filter(
                rental_property__owner=user,
                status='completed',
                completed_date__gte=timezone.now().date().replace(day=1)
            ).count()
        }

        return context

    def post(self, request, *args, **kwargs):
        """Create maintenance task from AI prediction"""
        data = json.loads(request.body)

        property_id = data.get('property_id')
        task_type = data.get('task_type')
        priority = data.get('priority', 'medium')

        try:
            property = Property.objects.get(id=property_id, owner=request.user)

            # Create maintenance task
            task = MaintenanceTask.objects.create(
                rental_property=property,
                title=f"AI Predicted: {task_type}",
                description=data.get('description', ''),
                priority=priority,
                predicted_by_ai=True,
                prediction_confidence=data.get('confidence', 0.8),
                predicted_failure_date=data.get('predicted_date')
            )

            return JsonResponse({
                'success': True,
                'task_id': task.id,
                'message': 'Maintenance task created successfully'
            })
        except Property.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Property not found'
            }, status=404)


class GuestExperienceView(LoginRequiredMixin, TemplateView):
    """Guest experience AI view"""
    template_name = 'ai/guest_experience.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Get guest experience engine
        experience_engine = GuestExperienceEngine()

        # Get recent guests
        recent_bookings = Booking.objects.filter(
            rental_property__owner=user,
            status__in=['confirmed', 'checked_in', 'checked_out']
        ).select_related('guest', 'rental_property').order_by('-created_at')[:20]

        # Analyze guest satisfaction
        guest_insights = []
        for booking in recent_bookings:
            insights = experience_engine.analyze_guest(booking.guest, booking)
            guest_insights.append({
                'booking': booking,
                'guest': booking.guest,
                'insights': insights,
                'satisfaction_score': insights.get('satisfaction_score', 0),
                'preferences': insights.get('preferences', {}),
                'recommendations': insights.get('recommendations', [])
            })

        context['guest_insights'] = guest_insights

        # Get sentiment analysis for recent messages
        sentiment_analyzer = SentimentAnalyzer()
        recent_messages = []

        for booking in recent_bookings[:10]:
            messages = booking.messages.all()
            for message in messages:
                sentiment = sentiment_analyzer.analyze(message.message)
                recent_messages.append({
                    'message': message,
                    'sentiment': sentiment
                })

        context['recent_messages'] = recent_messages

        # Get automated response templates
        context['response_templates'] = experience_engine.get_response_templates()

        # Guest statistics - Fixed query
        total_guests = Guest.objects.filter(bookings__rental_property__owner=user).distinct().count()

        # Count satisfied guests differently to avoid the OneToOneRel issue
        satisfied_guests = 0
        guests_with_bookings = Guest.objects.filter(bookings__rental_property__owner=user).distinct()

        for guest in guests_with_bookings:
            try:
                if hasattr(guest, 'ai_preferences') and guest.ai_preferences.satisfaction_score:
                    if guest.ai_preferences.satisfaction_score >= 4.0:
                        satisfied_guests += 1
            except GuestPreference.DoesNotExist:
                pass

        context['guest_stats'] = {
            'total_guests': total_guests,
            'satisfied_guests': satisfied_guests,
            'satisfaction_rate': round(satisfied_guests / total_guests * 100, 1) if total_guests > 0 else 0,
            'avg_response_time': '< 1 hour',  # This would be calculated from actual data
            'ai_responses_sent': 142  # This would be from actual data
        }

        return context


class BusinessIntelligenceView(LoginRequiredMixin, TemplateView):
    """Business intelligence AI view"""
    template_name = 'ai/business_intelligence.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Get business intelligence engine
        bi_engine = BusinessIntelligenceEngine()

        # Get user properties
        properties = Property.objects.filter(owner=user, is_active=True)

        # Get market analysis
        market_analysis = {}
        for property in properties:
            analysis = bi_engine.analyze_market(property)
            if property.city not in market_analysis:
                market_analysis[property.city] = analysis

        context['market_analysis'] = market_analysis

        # Get competitor analysis
        competitor_data = bi_engine.analyze_competitors(properties.first()) if properties.exists() else None
        context['competitor_data'] = competitor_data

        # Get demand forecasting
        forecast_data = bi_engine.forecast_demand(properties)
        context['forecast_data'] = forecast_data

        # Get ROI analysis
        roi_analysis = []
        for property in properties:
            roi = bi_engine.calculate_roi(property)
            roi_analysis.append({
                'property': property,
                'roi': roi['annual_revenue'],
                'payback_period': roi.get('payback_period', 0),
                'net_income': roi.get('net_income', 0)
            })

        context['roi_analysis'] = sorted(roi_analysis, key=lambda x: x['roi'], reverse=True)

        # Get trend analysis
        trends = bi_engine.analyze_trends(user)
        context['trends'] = trends

        return context


class SentimentAnalysisAPIView(LoginRequiredMixin, View):
    """API endpoint for sentiment analysis"""

    def post(self, request, *args, **kwargs):
        """Analyze sentiment of text"""
        data = json.loads(request.body)
        text = data.get('text', '')

        if not text:
            return JsonResponse({'error': 'No text provided'}, status=400)

        analyzer = SentimentAnalyzer()
        sentiment = analyzer.analyze(text)

        return JsonResponse({
            'sentiment': sentiment['sentiment'],
            'score': sentiment['score'],
            'suggestions': sentiment.get('suggestions', [])
        })


class AIToggleAPIView(LoginRequiredMixin, View):
    """API endpoint for toggling AI features"""

    def post(self, request, feature, *args, **kwargs):
        """Toggle AI feature on/off"""
        data = json.loads(request.body)
        enabled = data.get('enabled', False)

        # Map feature names to property fields
        feature_map = {
            'pricing': 'ai_pricing_enabled',
            'maintenance': 'ai_maintenance_enabled',
            'guest_experience': 'ai_guest_enabled',
            'business_intelligence': 'ai_analytics_enabled'
        }

        if feature not in feature_map:
            return JsonResponse({'error': 'Invalid feature'}, status=400)

        # Update all user properties
        properties = Property.objects.filter(owner=request.user)
        for property in properties:
            setattr(property, feature_map[feature], enabled)
            property.save()

        return JsonResponse({
            'success': True,
            'feature': feature,
            'enabled': enabled
        })