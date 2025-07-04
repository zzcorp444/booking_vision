"""
Activity tracking service
"""
from django.contrib.auth.models import User
from django.db import transaction
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.utils import timezone
import json

from ..models.activities import Activity


class ActivityService:
    """Service for creating and managing activities"""

    @staticmethod
    @transaction.atomic
    def create_activity(user: User, activity_type: str, title: str,
                        description: str, **kwargs) -> Activity:
        """Create a new activity and notify user"""

        # Determine icon and color based on type
        type_config = {
            'booking_created': {'icon': 'calendar-check', 'color': 'success'},
            'booking_cancelled': {'icon': 'calendar-times', 'color': 'danger'},
            'guest_message': {'icon': 'comment', 'color': 'info'},
            'payment_received': {'icon': 'dollar-sign', 'color': 'success'},
            'maintenance_alert': {'icon': 'tools', 'color': 'warning'},
            'ai_recommendation': {'icon': 'brain', 'color': 'primary'},
        }

        config = type_config.get(activity_type, {'icon': 'bell', 'color': 'secondary'})

        # Create activity
        activity = Activity.objects.create(
            user=user,
            activity_type=activity_type,
            title=title,
            description=description,
            icon=config['icon'],
            color=config['color'],
            property=kwargs.get('property'),
            booking=kwargs.get('booking'),
            data=kwargs.get('data', {}),
            is_important=kwargs.get('is_important', False)
        )

        # Send real-time notification
        ActivityService._send_notification(activity)

        return activity

    @staticmethod
    def _send_notification(activity: Activity):
        """Send real-time notification via WebSocket"""
        channel_layer = get_channel_layer()

        # Prepare notification data
        notification_data = {
            'type': 'activity_notification',
            'activity': {
                'id': activity.id,
                'type': activity.activity_type,
                'title': activity.title,
                'description': activity.description,
                'icon': activity.icon,
                'color': activity.color,
                'timestamp': activity.created_at.isoformat(),
                'is_important': activity.is_important
            }
        }

        # Send to user's channel
        async_to_sync(channel_layer.group_send)(
            f"user_{activity.user.id}",
            notification_data
        )

    @staticmethod
    def get_unread_count(user: User) -> int:
        """Get count of unread activities"""
        return Activity.objects.filter(user=user, is_read=False).count()

    @staticmethod
    def mark_all_as_read(user: User):
        """Mark all user activities as read"""
        Activity.objects.filter(user=user, is_read=False).update(
            is_read=True,
            read_at=timezone.now()
        )