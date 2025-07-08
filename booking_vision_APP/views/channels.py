"""
Channel management views
"""
import asyncio
from django.shortcuts import render, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
import json

from ..models.channels import Channel, ChannelConnection, PropertyChannel
from ..models.properties import Property
from ..integrations.no_api_sync_manager import NoAPIChannelSync


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
    """Connect to a channel without API"""
    data = json.loads(request.body)
    channel_id = data.get('channel_id')
    sync_method = data.get('sync_method')

    try:
        channel = Channel.objects.get(id=channel_id)

        # Create or update connection
        connection, created = ChannelConnection.objects.update_or_create(
            user=request.user,
            channel=channel,
            defaults={
                'preferred_sync_method': sync_method,
                'is_connected': True
            }
        )

        # Save method-specific configuration
        if sync_method == 'ical':
            connection.ical_url = data.get('ical_url', '')
        elif sync_method == 'email':
            connection.email_sync_enabled = True
            # Save email configuration to user profile
        elif sync_method == 'scraping':
            connection.scraping_enabled = True
            connection.login_email = data.get('login_email', '')
            # Encrypt and save password
            from cryptography.fernet import Fernet
            key = Fernet.generate_key()  # In production, use a persistent key
            f = Fernet(key)
            encrypted_password = f.encrypt(data.get('login_password', '').encode())
            connection.login_password_encrypted = encrypted_password.decode()
        elif sync_method == 'extension':
            # Extension doesn't need additional config
            pass

        connection.save()

        return JsonResponse({
            'success': True,
            'message': f'Successfully configured {channel.name} for {sync_method} sync'
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@login_required
@require_http_methods(["POST"])
async def sync_bookings(request):
    """Manually trigger booking sync without API"""
    try:
        # Convert to async view
        sync_manager = NoAPIChannelSync(request.user)
        results = await sync_manager.sync_all_channels()

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

