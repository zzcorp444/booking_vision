"""
Channel management views
"""
from django.shortcuts import render, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
import json

from ..models.channels import Channel, ChannelConnection, PropertyChannel
from ..models.properties import Property
from ..integrations.sync_manager import SyncManager


class ChannelManagementView(LoginRequiredMixin, TemplateView):
    """Channel connection management view"""
    template_name = 'channels/channel_management.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get all channels
        context['channels'] = Channel.objects.filter(is_active=True)

        # Get user's connections
        context['connections'] = ChannelConnection.objects.filter(
            user=self.request.user
        ).select_related('channel')

        # Get connected channels
        connected_channels = {
            conn.channel.id: conn for conn in context['connections']
        }
        context['connected_channels'] = connected_channels

        return context


@login_required
@require_http_methods(["POST"])
def connect_channel(request):
    """Connect to a channel"""
    data = json.loads(request.body)
    channel_id = data.get('channel_id')
    api_key = data.get('api_key')
    api_secret = data.get('api_secret')

    try:
        channel = Channel.objects.get(id=channel_id)

        # Create or update connection
        connection, created = ChannelConnection.objects.update_or_create(
            user=request.user,
            channel=channel,
            defaults={
                'api_key': api_key,
                'api_secret': api_secret,
                'is_connected': True
            }
        )

        # Test connection
        sync_manager = SyncManager(request.user)

        return JsonResponse({
            'success': True,
            'message': f'Successfully connected to {channel.name}'
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@login_required
@require_http_methods(["POST"])
def sync_bookings(request):
    """Manually trigger booking sync"""
    try:
        sync_manager = SyncManager(request.user)
        results = sync_manager.sync_all_bookings()

        return JsonResponse({
            'success': True,
            'results': results
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@login_required
@require_http_methods(["POST"])
def link_property_to_channel(request):
    """Link a property to a channel"""
    data = json.loads(request.body)
    property_id = data.get('property_id')
    channel_id = data.get('channel_id')
    external_property_id = data.get('external_property_id')

    try:
        property = Property.objects.get(id=property_id, owner=request.user)
        connection = ChannelConnection.objects.get(
            user=request.user,
            channel_id=channel_id
        )

        PropertyChannel.objects.update_or_create(
            rental_property=property,
            channel=connection.channel,
            defaults={
                'channel_connection': connection,
                'external_property_id': external_property_id,
                'is_active': True
            }
        )

        return JsonResponse({
            'success': True,
            'message': 'Property linked successfully'
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)

