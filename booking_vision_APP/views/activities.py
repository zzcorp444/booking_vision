"""
Activity views for account activity tracking
"""
from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, View
from django.http import JsonResponse
from django.utils import timezone
import json

from ..mixins import DataResponsiveMixin

# For now, return empty view until activity models are created
class ActivityView(DataResponsiveMixin, LoginRequiredMixin, ListView):
    """Activity feed view"""
    template_name = 'activities/activity_feed.html'

    def get_queryset(self):
        # Return empty queryset for now
        return []

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['stats'] = {
            'total': 0,
            'unread': 0,
            'important': 0,
            'today': 0
        }
        context['activity_types'] = []
        context['preferences'] = {
            'show_popup': True,
            'play_sound': True,
            'popup_duration': 5000
        }
        return context


class ActivityAPIView(LoginRequiredMixin, View):
    """API endpoints for activities"""

    def get(self, request, *args, **kwargs):
        """Get activities"""
        data = {
            'activities': [],
            'unread_count': 0
        }
        return JsonResponse(data)

    def post(self, request, *args, **kwargs):
        """Handle activity actions"""
        return JsonResponse({'success': True})