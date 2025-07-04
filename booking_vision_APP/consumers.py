"""
WebSocket consumers for real-time features
"""
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser


class ActivityConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for activity notifications"""

    async def connect(self):
        """Handle WebSocket connection"""
        self.user = self.scope["user"]

        if self.user.is_anonymous:
            await self.close()
            return

        # Join user's personal channel
        self.user_group = f"user_{self.user.id}"
        await self.channel_layer.group_add(
            self.user_group,
            self.channel_name
        )

        await self.accept()

        # Send initial data
        await self.send_initial_data()

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        if hasattr(self, 'user_group'):
            await self.channel_layer.group_discard(
                self.user_group,
                self.channel_name
            )

    async def receive(self, text_data):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(text_data)
            action = data.get('action')

            if action == 'mark_read':
                await self.mark_activity_read(data.get('activity_id'))
            elif action == 'mark_all_read':
                await self.mark_all_read()
            elif action == 'get_activities':
                await self.send_activities()

        except json.JSONDecodeError:
            await self.send_error("Invalid message format")

    async def activity_notification(self, event):
        """Handle activity notification from channel layer"""
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'activity': event['activity']
        }))

    async def send_initial_data(self):
        """Send initial data when connected"""
        unread_count = await self.get_unread_count()
        recent_activities = await self.get_recent_activities()

        await self.send(text_data=json.dumps({
            'type': 'initial',
            'unread_count': unread_count,
            'recent_activities': recent_activities
        }))

    @database_sync_to_async
    def get_unread_count(self):
        """Get unread activity count"""
        from .models.activities import Activity
        return Activity.objects.filter(user=self.user, is_read=False).count()

    @database_sync_to_async
    def get_recent_activities(self):
        """Get recent activities"""
        from .models.activities import Activity
        activities = Activity.objects.filter(user=self.user)[:20]

        return [{
            'id': a.id,
            'type': a.activity_type,
            'title': a.title,
            'description': a.description,
            'icon': a.icon,
            'color': a.color,
            'timestamp': a.created_at.isoformat(),
            'is_read': a.is_read,
            'is_important': a.is_important
        } for a in activities]

    @database_sync_to_async
    def mark_activity_read(self, activity_id):
        """Mark single activity as read"""
        from .models.activities import Activity
        try:
            activity = Activity.objects.get(id=activity_id, user=self.user)
            activity.mark_as_read()
            return True
        except Activity.DoesNotExist:
            return False

    @database_sync_to_async
    def mark_all_read(self):
        """Mark all activities as read"""
        from .services.activity_service import ActivityService
        ActivityService.mark_all_as_read(self.user)

    async def send_activities(self):
        """Send updated activities list"""
        activities = await self.get_recent_activities()
        unread_count = await self.get_unread_count()

        await self.send(text_data=json.dumps({
            'type': 'activities_update',
            'activities': activities,
            'unread_count': unread_count
        }))

    async def send_error(self, message):
        """Send error message"""
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': message
        }))