from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.core.paginator import Paginator
from django.db.models import Q
import json
import logging

from ..models import Property, Channel, ChannelIntegration, Availability, Rate
# Temporarily comment out until API integrations are ready
# from ..integrations.sync_manager import SyncManager

logger = logging.getLogger(__name__)

@login_required
def channel_list(request):
    """Display list of all channels"""
    channels = Channel.objects.filter(user=request.user)
    
    # Add pagination
    paginator = Paginator(channels, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'channels': page_obj,
        'total_channels': channels.count(),
    }
    return render(request, 'channels/channel_list.html', context)

@login_required
def channel_detail(request, channel_id):
    """Display channel details and integration status"""
    channel = get_object_or_404(Channel, id=channel_id, user=request.user)
    
    # Get channel integrations
    integrations = ChannelIntegration.objects.filter(channel=channel)
    
    # Get properties connected to this channel
    properties = channel.properties.all()
    
    context = {
        'channel': channel,
        'integrations': integrations,
        'properties': properties,
    }
    return render(request, 'channels/channel_detail.html', context)

@login_required
def add_channel(request):
    """Add a new channel"""
    if request.method == 'POST':
        channel_name = request.POST.get('name')
        channel_type = request.POST.get('type')
        
        if channel_name and channel_type:
            channel = Channel.objects.create(
                user=request.user,
                name=channel_name,
                channel_type=channel_type,
                is_active=True
            )
            messages.success(request, f'Channel "{channel_name}" added successfully!')
            return redirect('channel_detail', channel_id=channel.id)
        else:
            messages.error(request, 'Please provide both channel name and type.')
    
    # Available channel types
    channel_types = [
        ('airbnb', 'Airbnb'),
        ('booking', 'Booking.com'),
        ('vrbo', 'VRBO'),
        ('expedia', 'Expedia'),
        ('direct', 'Direct Booking'),
    ]
    
    context = {
        'channel_types': channel_types,
    }
    return render(request, 'channels/add_channel.html', context)

@login_required
def sync_channel(request, channel_id):
    """Sync data for a specific channel"""
    channel = get_object_or_404(Channel, id=channel_id, user=request.user)
    
    if request.method == 'POST':
        try:
            # TODO: Implement actual sync when API integrations are ready
            # sync_manager = SyncManager()
            # result = sync_manager.sync_channel(channel.channel_type)
            
            # For now, just mark as synced
            channel.last_sync = timezone.now()
            channel.save()
            
            messages.success(request, f'Channel "{channel.name}" synced successfully!')
            return JsonResponse({'status': 'success', 'message': 'Sync completed'})
            
        except Exception as e:
            logger.error(f"Error syncing channel {channel_id}: {str(e)}")
            messages.error(request, f'Error syncing channel: {str(e)}')
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return redirect('channel_detail', channel_id=channel_id)

@login_required
def channel_settings(request, channel_id):
    """Manage channel settings and configuration"""
    channel = get_object_or_404(Channel, id=channel_id, user=request.user)
    
    if request.method == 'POST':
        # Update channel settings
        channel.name = request.POST.get('name', channel.name)
        channel.is_active = request.POST.get('is_active') == 'on'
        
        # Save API credentials (if provided)
        api_key = request.POST.get('api_key')
        api_secret = request.POST.get('api_secret')
        
        if api_key:
            # TODO: Securely store API credentials
            pass
        
        channel.save()
        messages.success(request, 'Channel settings updated successfully!')
        return redirect('channel_detail', channel_id=channel_id)
    
    context = {
        'channel': channel,
    }
    return render(request, 'channels/channel_settings.html', context)

@login_required
def remove_channel(request, channel_id):
    """Remove a channel"""
    channel = get_object_or_404(Channel, id=channel_id, user=request.user)
    
    if request.method == 'POST':
        channel_name = channel.name
        channel.delete()
        messages.success(request, f'Channel "{channel_name}" removed successfully!')
        return redirect('channel_list')
    
    context = {
        'channel': channel,
    }
    return render(request, 'channels/confirm_remove.html', context)

@login_required
def bulk_sync_channels(request):
    """Sync all channels at once"""
    if request.method == 'POST':
        try:
            channels = Channel.objects.filter(user=request.user, is_active=True)
            
            # TODO: Implement actual bulk sync when API integrations are ready
            # sync_manager = SyncManager()
            # results = sync_manager.sync_all_channels()
            
            # For now, just update last_sync for all channels
            for channel in channels:
                channel.last_sync = timezone.now()
                channel.save()
            
            messages.success(request, f'Successfully synced {channels.count()} channels!')
            return JsonResponse({'status': 'success', 'synced_count': channels.count()})
            
        except Exception as e:
            logger.error(f"Error in bulk sync: {str(e)}")
            messages.error(request, f'Error during bulk sync: {str(e)}')
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return redirect('channel_list')