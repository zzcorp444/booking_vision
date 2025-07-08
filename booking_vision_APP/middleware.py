# booking_vision_APP/middleware.py
"""
Custom middleware for session management
"""
from django.utils import timezone
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
import logging

logger = logging.getLogger(__name__)


class SessionManagementMiddleware:
    """Manage user sessions with timeout and activity tracking"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check if user is authenticated
        if request.user.is_authenticated:
            # Check subscription status for hosts
            if request.user.is_host() and not request.user.is_admin_or_bookmaker():
                if not request.user.has_active_subscription():
                    # Allow access to subscription pages
                    allowed_paths = [
                        reverse('booking_vision_APP:subscription_plans'),
                        reverse('booking_vision_APP:payment'),
                        reverse('logout'),
                        reverse('booking_vision_APP:profile'),
                        reverse('booking_vision_APP:settings'),
                    ]

                    if request.path not in allowed_paths and not request.path.startswith('/admin/'):
                        messages.warning(request, 'Please subscribe to continue using Booking Vision.')
                        return redirect('booking_vision_APP:subscription_plans')

            # Update last activity
            request.session['last_activity'] = timezone.now().isoformat()

            # Check session timeout (30 minutes of inactivity)
            last_activity = request.session.get('last_activity')
            if last_activity:
                last_activity_time = timezone.datetime.fromisoformat(last_activity)
                if (timezone.now() - last_activity_time).seconds > 1800:  # 30 minutes
                    logout(request)
                    messages.info(request, 'Your session has expired. Please log in again.')
                    return redirect('login')

        response = self.get_response(request)
        return response


class RestrictAdminMiddleware:
    """Restrict admin user creation and access"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check admin count on admin user creation
        if request.path.startswith('/admin/') and request.method == 'POST':
            if 'user' in request.path:
                from django.contrib.auth import get_user_model
                User = get_user_model()

                # Check if trying to create admin user
                if request.POST.get('user_type') == 'admin':
                    admin_count = User.objects.filter(user_type='admin').count()
                    if admin_count >= 4:
                        messages.error(request, 'Maximum number of admin users (4) reached.')
                        return redirect(request.path)

        response = self.get_response(request)
        return response