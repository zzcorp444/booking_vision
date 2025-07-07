"""
Documentation views for Booking Vision
"""
from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView


class DocumentationView(LoginRequiredMixin, TemplateView):
    """Documentation and help center view"""
    template_name = 'documentation/documentation.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Documentation sections
        context['sections'] = [
            {
                'id': 'getting-started',
                'title': 'Getting Started',
                'icon': 'rocket',
                'articles': [
                    {'title': 'Quick Setup Guide', 'url': '#quick-setup'},
                    {'title': 'Adding Your First Property', 'url': '#first-property'},
                    {'title': 'Connecting Channels', 'url': '#connecting-channels'},
                    {'title': 'Understanding the Dashboard', 'url': '#dashboard-guide'},
                ]
            },
            {
                'id': 'properties',
                'title': 'Property Management',
                'icon': 'home',
                'articles': [
                    {'title': 'Creating Properties', 'url': '#creating-properties'},
                    {'title': 'Managing Amenities', 'url': '#managing-amenities'},
                    {'title': 'Property Photos', 'url': '#property-photos'},
                    {'title': 'Pricing Strategies', 'url': '#pricing-strategies'},
                ]
            },
            {
                'id': 'bookings',
                'title': 'Booking Management',
                'icon': 'calendar',
                'articles': [
                    {'title': 'Understanding Booking Status', 'url': '#booking-status'},
                    {'title': 'Calendar Management', 'url': '#calendar-management'},
                    {'title': 'Guest Communication', 'url': '#guest-communication'},
                    {'title': 'Handling Cancellations', 'url': '#cancellations'},
                ]
            },
            {
                'id': 'ai-features',
                'title': 'AI Features',
                'icon': 'robot',
                'articles': [
                    {'title': 'Smart Pricing Setup', 'url': '#smart-pricing'},
                    {'title': 'Predictive Maintenance', 'url': '#predictive-maintenance'},
                    {'title': 'Guest Experience AI', 'url': '#guest-experience'},
                    {'title': 'Business Intelligence', 'url': '#business-intelligence'},
                ]
            },
            {
                'id': 'channels',
                'title': 'Channel Integration',
                'icon': 'link',
                'articles': [
                    {'title': 'Connecting Airbnb', 'url': '#airbnb-connection'},
                    {'title': 'Connecting Booking.com', 'url': '#booking-com-connection'},
                    {'title': 'VRBO Integration', 'url': '#vrbo-integration'},
                    {'title': 'Troubleshooting Sync Issues', 'url': '#sync-troubleshooting'},
                ]
            },
            {
                'id': 'analytics',
                'title': 'Analytics & Reports',
                'icon': 'chart-bar',
                'articles': [
                    {'title': 'Understanding Analytics', 'url': '#understanding-analytics'},
                    {'title': 'Revenue Reports', 'url': '#revenue-reports'},
                    {'title': 'Occupancy Analysis', 'url': '#occupancy-analysis'},
                    {'title': 'Performance Metrics', 'url': '#performance-metrics'},
                ]
            }
        ]

        return context


class DocumentationArticleView(LoginRequiredMixin, TemplateView):
    """Individual documentation article view"""
    template_name = 'documentation/article.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        article_id = kwargs.get('article_id')

        # Sample article content
        articles = {
            'quick-setup': {
                'title': 'Quick Setup Guide',
                'content': '''
                <h3>Welcome to Booking Vision!</h3>
                <p>This guide will help you get started with Booking Vision in just a few simple steps.</p>
                
                <h4>Step 1: Complete Your Profile</h4>
                <p>Start by completing your profile with your business information. This helps us provide better recommendations.</p>
                
                <h4>Step 2: Add Your First Property</h4>
                <p>Navigate to Properties → Add New Property and fill in the details for your rental property.</p>
                
                <h4>Step 3: Connect Your Channels</h4>
                <p>Go to Channel Management and connect your Airbnb, Booking.com, and other platform accounts.</p>
                
                <h4>Step 4: Enable AI Features</h4>
                <p>Turn on AI features like Smart Pricing and Predictive Maintenance in your settings.</p>
                '''
            },
            'smart-pricing': {
                'title': 'Smart Pricing Setup',
                'content': '''
                <h3>AI-Powered Smart Pricing</h3>
                <p>Booking Vision's Smart Pricing uses machine learning to optimize your rates automatically.</p>
                
                <h4>How It Works</h4>
                <ul>
                    <li>Analyzes market demand and competitor pricing</li>
                    <li>Considers seasonal trends and local events</li>
                    <li>Adjusts prices based on booking lead time</li>
                    <li>Factors in your property's performance history</li>
                </ul>
                
                <h4>Setting Up Smart Pricing</h4>
                <ol>
                    <li>Go to AI Features → Smart Pricing</li>
                    <li>Enable Smart Pricing for your properties</li>
                    <li>Set your minimum and maximum price limits</li>
                    <li>Configure pricing rules and preferences</li>
                </ol>
                '''
            }
        }

        context['article'] = articles.get(article_id, {
            'title': 'Article Not Found',
            'content': '<p>The requested article could not be found.</p>'
        })

        return context