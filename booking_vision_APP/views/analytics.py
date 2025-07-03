"""
Analytics views for Booking Vision application.
This file contains analytics and reporting views.
"""
from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.http import JsonResponse
from django.db.models import Sum, Count, Avg, Q
from datetime import datetime, timedelta
import json

from ..models.properties import Property
from ..models.bookings import Booking
from ..models.channels import Channel

class AnalyticsView(LoginRequiredMixin, TemplateView):
    """Main analytics dashboard"""
    template_name = 'analytics/analytics.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Get user properties and bookings
        properties = Property.objects.filter(owner=user, is_active=True)
        bookings = Booking.objects.filter(rental_property__owner=user)

        # Revenue analytics
        context['revenue_stats'] = self.get_revenue_stats(bookings)

        # Occupancy analytics
        context['occupancy_stats'] = self.get_occupancy_stats(properties, bookings)

        # Channel performance
        context['channel_stats'] = self.get_channel_performance(user)

        # Property performance
        context['property_stats'] = self.get_property_performance(properties)

        return context

    def get_revenue_stats(self, bookings):
        """Calculate revenue statistics"""
        today = datetime.now().date()
        this_month = today.replace(day=1)
        last_month = (this_month - timedelta(days=1)).replace(day=1)
        this_year = today.replace(month=1, day=1)

        confirmed_bookings = bookings.filter(status__in=['confirmed', 'checked_out'])

        return {
            'total_revenue': confirmed_bookings.aggregate(Sum('total_price'))['total_price__sum'] or 0,
            'monthly_revenue': confirmed_bookings.filter(
                created_at__gte=this_month
            ).aggregate(Sum('total_price'))['total_price__sum'] or 0,
            'yearly_revenue': confirmed_bookings.filter(
                created_at__gte=this_year
            ).aggregate(Sum('total_price'))['total_price__sum'] or 0,
            'avg_booking_value': confirmed_bookings.aggregate(Avg('total_price'))['total_price__avg'] or 0,
        }

    def get_occupancy_stats(self, properties, bookings):
        """Calculate occupancy statistics"""
        today = datetime.now().date()
        thirty_days_ago = today - timedelta(days=30)

        # Calculate occupancy for last 30 days
        total_property_days = properties.count() * 30

        if total_property_days == 0:
            return {'occupancy_rate': 0, 'booked_nights': 0, 'available_nights': 0}

        booked_days = 0
        for property in properties:
            property_bookings = bookings.filter(
                rental_property=property,
                status__in=['confirmed', 'checked_in', 'checked_out'],
                check_in_date__lte=today,
                check_out_date__gte=thirty_days_ago
            )

            for booking in property_bookings:
                overlap_start = max(booking.check_in_date, thirty_days_ago)
                overlap_end = min(booking.check_out_date, today)
                if overlap_start <= overlap_end:
                    booked_days += (overlap_end - overlap_start).days + 1

        occupancy_rate = (booked_days / total_property_days) * 100 if total_property_days > 0 else 0

        return {
            'occupancy_rate': round(occupancy_rate, 1),
            'booked_nights': booked_days,
            'available_nights': total_property_days - booked_days,
        }

    def get_channel_performance(self, user):
        """Get performance by channel"""
        channels = Channel.objects.all()
        performance = []

        for channel in channels:
            channel_bookings = Booking.objects.filter(
                rental_property__owner=user,
                channel=channel
            )

            revenue = channel_bookings.filter(
                status__in=['confirmed', 'checked_out']
            ).aggregate(Sum('total_price'))['total_price__sum'] or 0

            performance.append({
                'channel': channel,
                'bookings': channel_bookings.count(),
                'revenue': revenue,
                'avg_booking_value': revenue / max(channel_bookings.count(), 1)
            })

        return sorted(performance, key=lambda x: x['revenue'], reverse=True)

    def get_property_performance(self, properties):
        """Get performance by property"""
        performance = []

        for property in properties:
            property_bookings = property.bookings.all()
            confirmed_bookings = property_bookings.filter(status__in=['confirmed', 'checked_out'])

            revenue = confirmed_bookings.aggregate(Sum('total_price'))['total_price__sum'] or 0

            performance.append({
                'property': property,
                'bookings': property_bookings.count(),
                'revenue': revenue,
                'avg_booking_value': revenue / max(confirmed_bookings.count(), 1)
            })

        return sorted(performance, key=lambda x: x['revenue'], reverse=True)

class RevenueAnalyticsView(LoginRequiredMixin, TemplateView):
    """Revenue analytics API endpoint"""

    def get(self, request, *args, **kwargs):
        user = request.user
        period = request.GET.get('period', '12months')

        bookings = Booking.objects.filter(
            rental_property__owner=user,
            status__in=['confirmed', 'checked_out']
        )

        if period == '12months':
            data = self.get_monthly_revenue(bookings, 12)
        elif period == '30days':
            data = self.get_daily_revenue(bookings, 30)
        else:
            data = self.get_monthly_revenue(bookings, 12)

        return JsonResponse(data)

    def get_monthly_revenue(self, bookings, months):
        """Get revenue by month"""
        today = datetime.now().date()
        start_date = today.replace(day=1) - timedelta(days=30 * months)

        monthly_data = {}

        for booking in bookings.filter(created_at__gte=start_date):
            month_key = booking.created_at.strftime('%Y-%m')
            if month_key not in monthly_data:
                monthly_data[month_key] = 0
            monthly_data[month_key] += float(booking.total_price)

        # Sort by date
        sorted_months = sorted(monthly_data.keys())

        return {
            'labels': [datetime.strptime(m, '%Y-%m').strftime('%b %Y') for m in sorted_months],
            'revenue': [monthly_data[m] for m in sorted_months]
        }

    def get_daily_revenue(self, bookings, days):
        """Get revenue by day"""
        today = datetime.now().date()
        start_date = today - timedelta(days=days)

        daily_data = {}

        for booking in bookings.filter(created_at__gte=start_date):
            day_key = booking.created_at.strftime('%Y-%m-%d')
            if day_key not in daily_data:
                daily_data[day_key] = 0
            daily_data[day_key] += float(booking.total_price)

        # Fill in missing days with 0
        current_date = start_date
        while current_date <= today:
            day_key = current_date.strftime('%Y-%m-%d')
            if day_key not in daily_data:
                daily_data[day_key] = 0
            current_date += timedelta(days=1)

        # Sort by date
        sorted_days = sorted(daily_data.keys())

        return {
            'labels': [datetime.strptime(d, '%Y-%m-%d').strftime('%m/%d') for d in sorted_days],
            'revenue': [daily_data[d] for d in sorted_days]
        }