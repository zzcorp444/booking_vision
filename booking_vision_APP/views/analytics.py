"""
Analytics views for Booking Vision application with full data responsiveness.
Location: booking_vision_APP/views/analytics.py
"""
from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.db.models import Sum, Count, Avg, Q
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

from ..models.properties import Property
from ..models import Booking, Property, Payment, Guest
from ..models.channels import Channel, ChannelConnection
from ..models.payments import Payment
from ..mixins import AnalyticsDataMixin
import json


class AnalyticsView(AnalyticsDataMixin, LoginRequiredMixin, TemplateView):
    """Main analytics view with comprehensive data responsiveness"""
    template_name = 'analytics/analytics.html'
    login_url = '/accounts/login/'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Date range setup
        today = timezone.now().date()
        date_range = self.request.GET.get('range', '30')  # Default to 30 days

        if date_range == '7':
            start_date = today - timedelta(days=7)
            context['period_label'] = 'Last 7 Days'
        elif date_range == '90':
            start_date = today - timedelta(days=90)
            context['period_label'] = 'Last 3 Months'
        elif date_range == '365':
            start_date = today - timedelta(days=365)
            context['period_label'] = 'Last Year'
        else:
            start_date = today - timedelta(days=30)
            context['period_label'] = 'Last 30 Days'

        context['date_range'] = date_range
        context['start_date'] = start_date
        context['end_date'] = today

        # Get filtered data based on date range
        bookings = Booking.objects.filter(
            rental_property__owner=user,
            created_at__date__gte=start_date,
            created_at__date__lte=today
        )

        properties = Property.objects.filter(owner=user, is_active=True)

        # Revenue Analytics (Data Responsive)
        if context['has_revenue_data']:
            context['revenue_analytics'] = self._get_revenue_analytics(bookings, start_date, today)
        else:
            context['revenue_analytics'] = self._get_empty_revenue_analytics()

        # Occupancy Analytics (Data Responsive)
        if context['has_bookings'] and properties.exists():
            context['occupancy_analytics'] = self._get_occupancy_analytics(bookings, properties, start_date, today)
        else:
            context['occupancy_analytics'] = self._get_empty_occupancy_analytics()

        # Channel Performance (Data Responsive)
        if context['has_connected_channels'] and context['has_bookings']:
            context['channel_analytics'] = self._get_channel_analytics(bookings, user)
        else:
            context['channel_analytics'] = self._get_empty_channel_analytics()

        # Guest Analytics (Data Responsive)
        if context['has_guests']:
            context['guest_analytics'] = self._get_guest_analytics(bookings, user)
        else:
            context['guest_analytics'] = self._get_empty_guest_analytics()

        # Property Performance (Data Responsive)
        if properties.exists() and context['has_bookings']:
            context['property_analytics'] = self._get_property_analytics(properties, bookings)
        else:
            context['property_analytics'] = self._get_empty_property_analytics()

        # Trends and Forecasting (Data Responsive)
        if context['analytics_ready']:
            context['trends'] = self._get_trend_analytics(bookings, start_date, today)
            context['forecasting'] = self._get_forecasting_data(bookings, properties)
        else:
            context['trends'] = self._get_empty_trends()
            context['forecasting'] = self._get_empty_forecasting()

        # Market Insights (Data Responsive)
        if context['bookings_count'] >= 10:
            context['market_insights'] = self._get_market_insights(bookings, properties)
        else:
            context['market_insights'] = self._get_empty_market_insights()

        return context

    def _get_revenue_analytics(self, bookings, start_date, end_date):
        """Get comprehensive revenue analytics"""
        revenue_bookings = bookings.filter(status__in=['confirmed', 'checked_out'])

        return {
            'total_revenue': revenue_bookings.aggregate(Sum('total_price'))['total_price__sum'] or 0,
            'avg_booking_value': revenue_bookings.aggregate(Avg('total_price'))['total_price__avg'] or 0,
            'revenue_per_day': self._calculate_daily_revenue(revenue_bookings, start_date, end_date),
            'revenue_by_channel': self._get_revenue_by_channel(revenue_bookings),
            'revenue_by_property': self._get_revenue_by_property(revenue_bookings),
            'growth_rate': self._calculate_revenue_growth(revenue_bookings, start_date),
            'peak_revenue_day': self._get_peak_revenue_day(revenue_bookings, start_date, end_date)
        }

    def _get_empty_revenue_analytics(self):
        """Return empty revenue analytics structure"""
        return {
            'total_revenue': 0,
            'avg_booking_value': 0,
            'revenue_per_day': [],
            'revenue_by_channel': [],
            'revenue_by_property': [],
            'growth_rate': 0,
            'peak_revenue_day': None,
            'is_empty': True
        }

    def _get_occupancy_analytics(self, bookings, properties, start_date, end_date):
        """Get comprehensive occupancy analytics"""
        confirmed_bookings = bookings.filter(status__in=['confirmed', 'checked_in', 'checked_out'])

        total_days = (end_date - start_date).days + 1
        total_property_days = properties.count() * total_days

        # Calculate booked days
        booked_days = 0
        for booking in confirmed_bookings:
            overlap_start = max(booking.check_in_date, start_date)
            overlap_end = min(booking.check_out_date, end_date)
            if overlap_start <= overlap_end:
                booked_days += (overlap_end - overlap_start).days + 1

        occupancy_rate = (booked_days / total_property_days * 100) if total_property_days > 0 else 0

        return {
            'occupancy_rate': round(occupancy_rate, 1),
            'booked_days': booked_days,
            'available_days': total_property_days - booked_days,
            'occupancy_by_property': self._get_occupancy_by_property(properties, confirmed_bookings, start_date, end_date),
            'occupancy_trends': self._get_occupancy_trends(confirmed_bookings, start_date, end_date),
            'peak_occupancy_period': self._get_peak_occupancy_period(confirmed_bookings, start_date, end_date)
        }

    def _get_empty_occupancy_analytics(self):
        """Return empty occupancy analytics structure"""
        return {
            'occupancy_rate': 0,
            'booked_days': 0,
            'available_days': 0,
            'occupancy_by_property': [],
            'occupancy_trends': [],
            'peak_occupancy_period': None,
            'is_empty': True
        }

    def _get_channel_analytics(self, bookings, user):
        """Get comprehensive channel performance analytics"""
        channels = ChannelConnection.objects.filter(user=user, is_connected=True)

        channel_data = []
        for conn in channels:
            channel_bookings = bookings.filter(channel=conn.channel)
            total_revenue = channel_bookings.filter(
                status__in=['confirmed', 'checked_out']
            ).aggregate(Sum('total_price'))['total_price__sum'] or 0

            channel_data.append({
                'channel': conn.channel,
                'bookings_count': channel_bookings.count(),
                'total_revenue': total_revenue,
                'avg_booking_value': channel_bookings.aggregate(Avg('total_price'))['total_price__avg'] or 0,
                'conversion_rate': self._calculate_conversion_rate(channel_bookings),
                'performance_score': self._calculate_channel_score(channel_bookings.count(), total_revenue)
            })

        return {
            'channel_performance': sorted(channel_data, key=lambda x: x['performance_score'], reverse=True),
            'top_channel': max(channel_data, key=lambda x: x['total_revenue']) if channel_data else None,
            'channel_distribution': self._get_channel_distribution(channel_data),
            'channel_trends': self._get_channel_trends(bookings, channels)
        }

    def _get_empty_channel_analytics(self):
        """Return empty channel analytics structure"""
        return {
            'channel_performance': [],
            'top_channel': None,
            'channel_distribution': [],
            'channel_trends': [],
            'is_empty': True
        }

    def _get_guest_analytics(self, bookings, user):
        """Get comprehensive guest analytics"""
        guests = Guest.objects.filter(booking__rental_property__owner=user).distinct()

        # Guest behavior analysis
        repeat_guests = guests.annotate(
            booking_count=Count('booking')
        ).filter(booking_count__gt=1)

        guest_bookings = bookings.filter(guest__isnull=False)

        return {
            'total_guests': guests.count(),
            'repeat_guests': repeat_guests.count(),
            'repeat_rate': (repeat_guests.count() / guests.count() * 100) if guests.count() > 0 else 0,
            'avg_stay_duration': self._calculate_avg_stay_duration(guest_bookings),
            'guest_origins': self._get_guest_origins(guests),
            'guest_segments': self._get_guest_segments(guests),
            'guest_satisfaction': self._calculate_guest_satisfaction(guest_bookings),
            'top_spending_guests': self._get_top_spending_guests(guests)
        }

    def _get_empty_guest_analytics(self):
        """Return empty guest analytics structure"""
        return {
            'total_guests': 0,
            'repeat_guests': 0,
            'repeat_rate': 0,
            'avg_stay_duration': 0,
            'guest_origins': [],
            'guest_segments': [],
            'guest_satisfaction': 0,
            'top_spending_guests': [],
            'is_empty': True
        }

    def _get_property_analytics(self, properties, bookings):
        """Get comprehensive property performance analytics"""
        property_data = []

        for property in properties:
            property_bookings = bookings.filter(rental_property=property)
            revenue = property_bookings.filter(
                status__in=['confirmed', 'checked_out']
            ).aggregate(Sum('total_price'))['total_price__sum'] or 0

            property_data.append({
                'property': property,
                'bookings_count': property_bookings.count(),
                'total_revenue': revenue,
                'avg_booking_value': property_bookings.aggregate(Avg('total_price'))['total_price__avg'] or 0,
                'occupancy_rate': self._calculate_property_occupancy(property, property_bookings),
                'performance_score': self._calculate_property_score(property_bookings.count(), revenue)
            })

        return {
            'property_performance': sorted(property_data, key=lambda x: x['performance_score'], reverse=True),
            'top_performer': max(property_data, key=lambda x: x['total_revenue']) if property_data else None,
            'underperformers': [p for p in property_data if p['performance_score'] < 50],
            'property_comparison': self._get_property_comparison(property_data)
        }

    def _get_empty_property_analytics(self):
        """Return empty property analytics structure"""
        return {
            'property_performance': [],
            'top_performer': None,
            'underperformers': [],
            'property_comparison': [],
            'is_empty': True
        }

    # Helper methods for calculations
    def _calculate_daily_revenue(self, bookings, start_date, end_date):
        """Calculate daily revenue for the date range"""
        daily_revenue = []
        current_date = start_date

        while current_date <= end_date:
            day_revenue = bookings.filter(
                created_at__date=current_date
            ).aggregate(Sum('total_price'))['total_price__sum'] or 0

            daily_revenue.append({
                'date': current_date.strftime('%Y-%m-%d'),
                'revenue': float(day_revenue)
            })
            current_date += timedelta(days=1)

        return daily_revenue

    def _get_revenue_by_channel(self, bookings):
        """Get revenue breakdown by channel"""
        return list(bookings.values('channel__name').annotate(
            revenue=Sum('total_price'),
            count=Count('id')
        ).order_by('-revenue'))

    def _get_revenue_by_property(self, bookings):
        """Get revenue breakdown by property"""
        return list(bookings.values('rental_property__name').annotate(
            revenue=Sum('total_price'),
            count=Count('id')
        ).order_by('-revenue'))

    def _calculate_conversion_rate(self, bookings):
        """Calculate booking conversion rate"""
        # Placeholder - would need inquiry/lead data
        return 75.0  # Placeholder percentage

    def _calculate_channel_score(self, bookings_count, revenue):
        """Calculate performance score for channel"""
        return (bookings_count * 10) + (revenue * 0.01)

    def _calculate_property_occupancy(self, property, bookings):
        """Calculate occupancy rate for a specific property"""
        # Simplified calculation - would need more sophisticated logic
        return min(bookings.count() * 3, 100)  # Placeholder

    def _calculate_property_score(self, bookings_count, revenue):
        """Calculate performance score for property"""
        return (bookings_count * 15) + (revenue * 0.02)

    # Additional helper methods would be implemented here...
    def _get_trend_analytics(self, bookings, start_date, end_date):
        """Get trend analysis data"""
        return {'trends': 'placeholder'}  # Implement actual trend analysis

    def _get_empty_trends(self):
        """Return empty trends structure"""
        return {'is_empty': True}

    def _get_forecasting_data(self, bookings, properties):
        """Get forecasting data"""
        return {'forecast': 'placeholder'}  # Implement actual forecasting

    def _get_empty_forecasting(self):
        """Return empty forecasting structure"""
        return {'is_empty': True}

    def _get_market_insights(self, bookings, properties):
        """Get market insights"""
        return {'insights': 'placeholder'}  # Implement actual market analysis

    def _get_empty_market_insights(self):
        """Return empty market insights structure"""
        return {'is_empty': True}


@login_required
def analytics_api(request):
    """API endpoint for analytics data"""
    user = request.user
    date_range = request.GET.get('range', '30')

    # Implementation for API response
    return JsonResponse({'status': 'success'})


@method_decorator(login_required, name='dispatch')
class RevenueAnalyticsView(TemplateView):
    template_name = 'analytics/revenue_analytics.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Get user's properties
        properties = Property.objects.filter(owner=user)

        # Get date range from request or default to last 12 months
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=365)

        # Parse date filters from request
        date_filter = self.request.GET.get('date_range', '12_months')
        if date_filter == '30_days':
            start_date = end_date - timedelta(days=30)
        elif date_filter == '90_days':
            start_date = end_date - timedelta(days=90)
        elif date_filter == '6_months':
            start_date = end_date - timedelta(days=180)
        elif date_filter == '12_months':
            start_date = end_date - timedelta(days=365)

        # Get bookings in date range
        bookings = Booking.objects.filter(
            property__owner=user,
            check_in__range=[start_date, end_date]
        )

        # Get payments
        payments = Payment.objects.filter(
            booking__property__owner=user,
            payment_date__range=[start_date, end_date]
        )

        # Calculate basic metrics
        total_revenue = payments.filter(status='completed').aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')

        total_bookings = bookings.count()

        # Calculate average booking value
        avg_booking_value = bookings.aggregate(
            avg=Avg('total_amount')
        )['avg'] or Decimal('0.00')

        # Calculate occupancy rate
        total_possible_nights = 0
        total_booked_nights = 0

        for property in properties:
            days_in_range = (end_date - start_date).days
            total_possible_nights += days_in_range

            property_bookings = bookings.filter(property=property)
            for booking in property_bookings:
                nights = (booking.check_out - booking.check_in).days
                total_booked_nights += nights

        occupancy_rate = (total_booked_nights / total_possible_nights * 100) if total_possible_nights > 0 else 0

        # Monthly revenue breakdown
        monthly_revenue = []
        monthly_bookings = []
        current_date = start_date

        while current_date <= end_date:
            month_start = current_date.replace(day=1)
            if current_date.month == 12:
                month_end = current_date.replace(year=current_date.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                month_end = current_date.replace(month=current_date.month + 1, day=1) - timedelta(days=1)

            month_revenue = payments.filter(
                payment_date__range=[month_start, month_end],
                status='completed'
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

            month_bookings_count = bookings.filter(
                check_in__range=[month_start, month_end]
            ).count()

            monthly_revenue.append({
                'month': current_date.strftime('%Y-%m'),
                'month_name': current_date.strftime('%B %Y'),
                'revenue': float(month_revenue),
                'bookings': month_bookings_count
            })

            if current_date.month == 12:
                current_date = current_date.replace(year=current_date.year + 1, month=1)
            else:
                current_date = current_date.replace(month=current_date.month + 1)

        # Property performance
        property_performance = []
        for property in properties:
            property_bookings = bookings.filter(property=property)
            property_revenue = payments.filter(
                booking__property=property,
                status='completed'
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

            property_nights = sum(
                (booking.check_out - booking.check_in).days
                for booking in property_bookings
            )

            property_performance.append({
                'property': property,
                'revenue': property_revenue,
                'bookings': property_bookings.count(),
                'nights': property_nights,
                'avg_rate': property_revenue / property_nights if property_nights > 0 else Decimal('0.00')
            })

        # Channel performance
        channel_performance = {}
        for booking in bookings:
            channel = booking.channel or 'Direct'
            if channel not in channel_performance:
                channel_performance[channel] = {
                    'bookings': 0,
                    'revenue': Decimal('0.00'),
                    'nights': 0
                }

            channel_performance[channel]['bookings'] += 1
            booking_revenue = payments.filter(
                booking=booking,
                status='completed'
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

            channel_performance[channel]['revenue'] += booking_revenue
            channel_performance[channel]['nights'] += (booking.check_out - booking.check_in).days

        # Revenue by booking source
        revenue_by_source = []
        for channel, data in channel_performance.items():
            revenue_by_source.append({
                'channel': channel,
                'revenue': float(data['revenue']),
                'bookings': data['bookings'],
                'percentage': (float(data['revenue']) / float(total_revenue) * 100) if total_revenue > 0 else 0
            })

        # Seasonal trends
        seasonal_data = {}
        for booking in bookings:
            season = self._get_season(booking.check_in)
            if season not in seasonal_data:
                seasonal_data[season] = {
                    'bookings': 0,
                    'revenue': Decimal('0.00'),
                    'nights': 0
                }

            seasonal_data[season]['bookings'] += 1
            booking_revenue = payments.filter(
                booking=booking,
                status='completed'
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

            seasonal_data[season]['revenue'] += booking_revenue
            seasonal_data[season]['nights'] += (booking.check_out - booking.check_in).days

        # Revenue growth comparison
        previous_period_start = start_date - (end_date - start_date)
        previous_period_end = start_date

        previous_revenue = Payment.objects.filter(
            booking__property__owner=user,
            payment_date__range=[previous_period_start, previous_period_end],
            status='completed'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        revenue_growth = ((total_revenue - previous_revenue) / previous_revenue * 100) if previous_revenue > 0 else 0

        # Top performing months
        top_months = sorted(monthly_revenue, key=lambda x: x['revenue'], reverse=True)[:3]

        # Average daily rate (ADR)
        total_nights = sum(
            (booking.check_out - booking.check_in).days
            for booking in bookings
        )
        adr = total_revenue / total_nights if total_nights > 0 else Decimal('0.00')

        # Revenue per available room (RevPAR)
        revpar = total_revenue / total_possible_nights if total_possible_nights > 0 else Decimal('0.00')

        context.update({
            'properties': properties,
            'has_data': total_bookings > 0,
            'date_range': date_filter,
            'start_date': start_date,
            'end_date': end_date,

            # Key metrics
            'total_revenue': total_revenue,
            'total_bookings': total_bookings,
            'avg_booking_value': avg_booking_value,
            'occupancy_rate': round(occupancy_rate, 2),
            'revenue_growth': round(revenue_growth, 2),
            'adr': adr,
            'revpar': revpar,

            # Chart data
            'monthly_revenue': json.dumps(monthly_revenue),
            'revenue_by_source': json.dumps(revenue_by_source),
            'seasonal_data': json.dumps([
                {'season': season, 'revenue': float(data['revenue'])}
                for season, data in seasonal_data.items()
            ]),

            # Performance data
            'property_performance': property_performance,
            'channel_performance': channel_performance,
            'top_months': top_months,

            # Comparison data
            'previous_revenue': previous_revenue,
            'total_nights': total_nights,
            'total_possible_nights': total_possible_nights,
        })

        return context

    def _get_season(self, date):
        """Determine season based on date"""
        month = date.month
        if month in [12, 1, 2]:
            return 'Winter'
        elif month in [3, 4, 5]:
            return 'Spring'
        elif month in [6, 7, 8]:
            return 'Summer'
        else:
            return 'Fall'
