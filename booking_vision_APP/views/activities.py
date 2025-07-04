"""
Activity views
"""
from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, View
from django.http import JsonResponse
from django.utils import timezone
import json

from ..models.activities import Activity, ActivityPreference
from ..services.activity_service import ActivityService


class ActivityView(LoginRequiredMixin, ListView):
    """Activity feed view"""
    model = Activity
    template_name = 'activities/activity_feed.html'
    context_object_name = 'activities'
    paginate_by = 50

    def get_queryset(self):
        queryset = Activity.objects.filter(user=self.request.user)

        # Filter by type
        activity_type = self.request.GET.get('type')
        if activity_type:
            queryset = queryset.filter(activity_type=activity_type)

        # Filter by read status
        status = self.request.GET.get('status')
        if status == 'unread':
            queryset = queryset.filter(is_read=False)
        elif status == 'important':
            queryset = queryset.filter(is_important=True)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get user preferences
        preferences, _ = ActivityPreference.objects.get_or_create(user=self.request.user)
        context['preferences'] = preferences

        # Get activity statistics
        all_activities = Activity.objects.filter(user=self.request.user)
        context['stats'] = {
            'total': all_activities.count(),
            'unread': all_activities.filter(is_read=False).count(),
            'important': all_activities.filter(is_important=True).count(),
            'today': all_activities.filter(created_at__date=timezone.now().date()).count()
        }

        # Activity types for filter
        context['activity_types'] = Activity.ACTIVITY_TYPES

        return context


class ActivityAPIView(LoginRequiredMixin, View):
    """API endpoints for activities"""

    def get(self, request, *args, **kwargs):
        """Get activities"""
        activities = Activity.objects.filter(user=request.user)[:20]

        data = {
            'activities': [{
                'id': a.id,
                'type': a.activity_type,
                'title': a.title,
                'description': a.description,
                'icon': a.icon,
                'color': a.color,
                'timestamp': a.created_at.isoformat(),
                'is_read': a.is_read,
                'is_important': a.is_important
            } for a in activities],
            'unread_count': ActivityService.get_unread_count(request.user)
        }

        return JsonResponse(data)

    def post(self, request, *args, **kwargs):
        """Handle activity actions"""
        data = json.loads(request.body)
        action = data.get('action')

        if action == 'mark_read':
            activity_id = data.get('activity_id')
            try:
                activity = Activity.objects.get(id=activity_id, user=request.user)
                activity.mark_as_read()
                return JsonResponse({'success': True})
            except Activity.DoesNotExist:
                return JsonResponse({'error': 'Activity not found'}, status=404)

        elif action == 'mark_all_read':
            ActivityService.mark_all_as_read(request.user)
            return JsonResponse({'success': True})

        elif action == 'update_preferences':
            preferences, _ = ActivityPreference.objects.get_or_create(user=request.user)

            for key, value in data.get('preferences', {}).items():
                if hasattr(preferences, key):
                    setattr(preferences, key, value)

            preferences.save()
            return JsonResponse({'success': True})

        return JsonResponse({'error': 'Invalid action'}, status=400)