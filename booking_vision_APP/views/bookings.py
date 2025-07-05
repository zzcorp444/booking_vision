"""
Booking management views for Booking Vision application.
This file contains all booking-related views and calendar functionality.
Location: booking_vision_APP/views/bookings.py
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, TemplateView, CreateView  # Add CreateView here
from django.http import JsonResponse
from django.db.models import Q, Count, Sum, Avg
from datetime import datetime, timedelta
import calendar
import json
from django.urls import reverse_lazy
from django.contrib import messages

from ..models.bookings import Booking, Guest, BookingMessage
from ..models.properties import Property
from ..models.channels import Channel
from ..ai.sentiment_analysis import SentimentAnalyzer


class BookingListView(LoginRequiredMixin, ListView):
    """List all bookings for the current user"""
    model = Booking
    template_name = 'bookings/booking_list.html'
    context_object_name = 'bookings'
    paginate_by = 20

    def get_queryset(self):
        queryset = Booking.objects.filter(
            rental_property__owner=self.request.user
        ).select_related('rental_property', 'guest', 'channel').order_by('-created_at')

        # Filter by status
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)

        # Filter by property
        property_id = self.request.GET.get('property')
        if property_id:
            queryset = queryset.filter(rental_property_id=property_id)

        # Search functionality
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(guest__first_name__icontains=search) |
                Q(guest__last_name__icontains=search) |
                Q(guest__email__icontains=search) |
                Q(rental_property__name__icontains=search)
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Filter options
        context['properties'] = Property.objects.filter(
            owner=self.request.user,
            is_active=True
        )
        context['status_choices'] = Booking.STATUS_CHOICES

        # Current filters
        context['current_status'] = self.request.GET.get('status', '')
        context['current_property'] = self.request.GET.get('property', '')
        context['current_search'] = self.request.GET.get('search', '')

        # Booking statistics
        user_bookings = Booking.objects.filter(rental_property__owner=self.request.user)
        context['booking_stats'] = {
            'total': user_bookings.count(),
            'pending': user_bookings.filter(status='pending').count(),
            'confirmed': user_bookings.filter(status='confirmed').count(),
            'checked_in': user_bookings.filter(status='checked_in').count(),
        }

        return context


class BookingDetailView(LoginRequiredMixin, DetailView):
    """Detailed view of a single booking"""
    model = Booking
    template_name = 'bookings/booking_detail.html'
    context_object_name = 'booking'

    def get_queryset(self):
        return Booking.objects.filter(
            rental_property__owner=self.request.user
        ).select_related('rental_property', 'guest', 'channel')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        booking = context['booking']

        # Messages for this booking
        messages = BookingMessage.objects.filter(
            booking=booking
        ).order_by('created_at')

        # Analyze sentiment for messages
        analyzer = SentimentAnalyzer()
        analyzed_messages = []
        for message in messages:
            sentiment = analyzer.analyze(message.message)
            analyzed_messages.append({
                'message': message,
                'sentiment': sentiment
            })

        context['messages'] = analyzed_messages

        # Guest history
        context['guest_bookings'] = Booking.objects.filter(
            guest=booking.guest,
            rental_property__owner=self.request.user
        ).exclude(id=booking.id).order_by('-created_at')[:5]

        # Timeline events
        timeline = []
        timeline.append({
            'date': booking.created_at,
            'event': 'Booking Created',
            'description': f'Booking received from {booking.channel.name}',
            'type': 'info'
        })

        if booking.status == 'confirmed':
            timeline.append({
                'date': booking.updated_at,
                'event': 'Booking Confirmed',
                'description': 'Booking confirmed and guest notified',
                'type': 'success'
            })

        context['timeline'] = sorted(timeline, key=lambda x: x['date'])

        return context


class CalendarView(LoginRequiredMixin, TemplateView):
    """Calendar view showing all bookings"""
    template_name = 'bookings/calendar.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get current month and year
        today = datetime.now()
        month = int(self.request.GET.get('month', today.month))
        year = int(self.request.GET.get('year', today.year))

        # Generate calendar
        cal = calendar.monthcalendar(year, month)

        # Get bookings for the month
        start_date = datetime(year, month, 1).date()
        if month == 12:
            end_date = datetime(year + 1, 1, 1).date() - timedelta(days=1)
        else:
            end_date = datetime(year, month + 1, 1).date() - timedelta(days=1)

        bookings = Booking.objects.filter(
            rental_property__owner=self.request.user,
            check_in_date__lte=end_date,
            check_out_date__gte=start_date,
            status__in=['confirmed', 'checked_in', 'checked_out']
        ).select_related('rental_property', 'guest')

        # Organize bookings by date
        bookings_by_date = {}
        for booking in bookings:
            current_date = max(booking.check_in_date, start_date)
            end_booking_date = min(booking.check_out_date, end_date)

            while current_date <= end_booking_date:
                if current_date not in bookings_by_date:
                    bookings_by_date[current_date] = []
                bookings_by_date[current_date].append(booking)
                current_date += timedelta(days=1)

        context.update({
            'calendar': cal,
            'month': month,
            'year': year,
            'month_name': calendar.month_name[month],
            'bookings_by_date': bookings_by_date,
            'prev_month': month - 1 if month > 1 else 12,
            'prev_year': year if month > 1 else year - 1,
            'next_month': month + 1 if month < 12 else 1,
            'next_year': year if month < 12 else year + 1,
        })

        return context


def booking_api(request):
    """API endpoint for booking data"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)

    if request.method == 'GET':
        # Get booking data for calendar/charts
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')

        bookings = Booking.objects.filter(
            rental_property__owner=request.user
        )

        if start_date:
            bookings = bookings.filter(check_in_date__gte=start_date)
        if end_date:
            bookings = bookings.filter(check_out_date__lte=end_date)

        booking_data = []
        for booking in bookings:
            booking_data.append({
                'id': booking.id,
                'title': f"{booking.guest.first_name} {booking.guest.last_name}",
                'start': booking.check_in_date.isoformat(),
                'end': booking.check_out_date.isoformat(),
                'property': booking.rental_property.name,
                'status': booking.status,
                'total_price': float(booking.total_price)
            })

        return JsonResponse({'bookings': booking_data})

    return JsonResponse({'error': 'Method not allowed'}, status=405)


class BookingCreateView(LoginRequiredMixin, CreateView):
    """Create a manual booking"""
    model = Booking
    template_name = 'bookings/booking_form.html'
    fields = ['rental_property', 'channel', 'check_in_date',
              'check_out_date', 'num_guests', 'base_price', 'cleaning_fee',
              'service_fee', 'total_price', 'status']

    def get_form(self, form_class=None):
        form = super().get_form(form_class)

        # Filter properties to only show user's properties
        form.fields['rental_property'].queryset = Property.objects.filter(
            owner=self.request.user,
            is_active=True
        )

        # You might want to add help text or customize widgets
        form.fields['check_in_date'].widget.attrs.update({'type': 'date'})
        form.fields['check_out_date'].widget.attrs.update({'type': 'date'})

        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add any additional context if needed
        context['guests'] = Guest.objects.all().order_by('first_name', 'last_name')
        return context

    def form_valid(self, form):
        # You can add additional logic here before saving
        booking = form.save(commit=False)

        # Auto-calculate nights if not set
        if booking.check_in_date and booking.check_out_date:
            # The nights property is already calculated in the model
            pass

        # Create a new guest if needed (you might want to add guest creation to the form)
        if not hasattr(booking, 'guest') or not booking.guest:
            # For now, create a default guest or handle this differently
            guest, created = Guest.objects.get_or_create(
                email='manual@booking.com',
                defaults={
                    'first_name': 'Manual',
                    'last_name': 'Booking'
                }
            )
            booking.guest = guest

        messages.success(self.request, f'Booking created successfully!')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('booking_vision_APP:booking_detail', kwargs={'pk': self.object.pk})