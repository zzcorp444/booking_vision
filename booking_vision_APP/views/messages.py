"""
Messages view for unified communication management.
Location: booking_vision_APP/views/messages.py
"""
from django.shortcuts import render, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, TemplateView
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Q, Count
import json

from ..models.bookings import Booking, BookingMessage
from ..models.channels import Channel
from ..ai.sentiment_analysis import SentimentAnalyzer


class MessagesListView(LoginRequiredMixin, ListView):
    """Unified messages view across all channels"""
    model = BookingMessage
    template_name = 'messages/messages_list.html'
    context_object_name = 'messages'
    paginate_by = 20

    def get_queryset(self):
        queryset = BookingMessage.objects.filter(
            booking__rental_property__owner=self.request.user
        ).select_related('booking', 'booking__guest', 'booking__rental_property', 'booking__channel').order_by('-created_at')

        # Filter by channel
        channel_id = self.request.GET.get('channel')
        if channel_id:
            queryset = queryset.filter(booking__channel_id=channel_id)

        # Filter by property
        property_id = self.request.GET.get('property')
        if property_id:
            queryset = queryset.filter(booking__rental_property_id=property_id)

        # Filter by sender
        sender = self.request.GET.get('sender')
        if sender:
            queryset = queryset.filter(sender=sender)

        # Search
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(message__icontains=search) |
                Q(booking__guest__first_name__icontains=search) |
                Q(booking__guest__last_name__icontains=search)
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Analyze sentiment for all messages
        analyzer = SentimentAnalyzer()
        analyzed_messages = []

        for message in context['messages']:
            sentiment = analyzer.analyze(message.message)
            analyzed_messages.append({
                'message': message,
                'sentiment': sentiment
            })

        context['messages'] = analyzed_messages

        # Get filter options
        from ..models.properties import Property
        context['properties'] = Property.objects.filter(owner=self.request.user)
        context['channels'] = Channel.objects.filter(is_active=True)

        # Message statistics
        all_messages = BookingMessage.objects.filter(
            booking__rental_property__owner=self.request.user
        )

        context['message_stats'] = {
            'total': all_messages.count(),
            'unread': all_messages.filter(is_automated=False, sender='guest').count(),
            'guest_messages': all_messages.filter(sender='guest').count(),
            'host_messages': all_messages.filter(sender='host').count(),
            'automated': all_messages.filter(is_automated=True).count(),
        }

        # Current filters
        context['current_channel'] = self.request.GET.get('channel', '')
        context['current_property'] = self.request.GET.get('property', '')
        context['current_sender'] = self.request.GET.get('sender', '')
        context['current_search'] = self.request.GET.get('search', '')

        return context


def send_message_api(request):
    """API endpoint to send messages"""
    if request.method == 'POST':
        data = json.loads(request.body)
        booking_id = data.get('booking_id')
        message_text = data.get('message')
        is_automated = data.get('is_automated', False)

        try:
            booking = Booking.objects.get(
                id=booking_id,
                rental_property__owner=request.user
            )

            # Create message
            message = BookingMessage.objects.create(
                booking=booking,
                sender='host',
                message=message_text,
                is_automated=is_automated
            )

            # TODO: Send via channel API

            return JsonResponse({
                'success': True,
                'message_id': message.id
            })
        except Booking.DoesNotExist:
            return JsonResponse({'error': 'Booking not found'}, status=404)

    return JsonResponse({'error': 'Method not allowed'}, status=405)