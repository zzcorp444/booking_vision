"""
Payments view for financial tracking and management.
Location: booking_vision_APP/views/payments.py
"""
from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, TemplateView
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from ..models.payments import Payment, Payout
from ..models.bookings import Booking
from ..mixins import DataResponsiveMixin


class PaymentsListView(DataResponsiveMixin, LoginRequiredMixin, TemplateView):
    """Financial overview and payments tracking"""
    template_name = 'payments/payments_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Get all payments for user's properties
        payments = Payment.objects.filter(
            booking__rental_property__owner=user
        ).select_related('booking', 'booking__guest', 'booking__rental_property')

        # Financial statistics
        total_revenue = payments.filter(status='completed').aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0')

        pending_payments = payments.filter(status='pending').aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0')

        # This month's revenue
        month_start = timezone.now().date().replace(day=1)
        monthly_revenue = payments.filter(
            status='completed',
            payment_date__gte=month_start
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        # Processing fees
        total_fees = payments.filter(status='completed').aggregate(
            total=Sum('processing_fee')
        )['total'] or Decimal('0')

        context['financial_stats'] = {
            'total_revenue': total_revenue,
            'pending_payments': pending_payments,
            'monthly_revenue': monthly_revenue,
            'total_fees': total_fees,
            'net_revenue': total_revenue - total_fees
        }

        # Recent payments
        context['recent_payments'] = payments.order_by('-created_at')[:20]

        # Upcoming payouts
        context['upcoming_payouts'] = Payout.objects.filter(
            owner=user,
            status__in=['scheduled', 'processing']
        ).order_by('payout_date')[:5]

        # Payment status breakdown
        context['payment_breakdown'] = payments.values('status').annotate(
            count=Count('id'),
            total=Sum('amount')
        ).order_by('status')

        # Revenue by property
        revenue_by_property = {}
        for payment in payments.filter(status='completed'):
            prop_name = payment.booking.rental_property.name
            if prop_name not in revenue_by_property:
                revenue_by_property[prop_name] = Decimal('0')
            revenue_by_property[prop_name] += payment.amount

        context['revenue_by_property'] = sorted(
            revenue_by_property.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]  # Top 5 properties

        # Filter parameters
        context['status_filter'] = self.request.GET.get('status', '')
        context['property_filter'] = self.request.GET.get('property', '')

        # Apply filters
        if context['status_filter']:
            payments = payments.filter(status=context['status_filter'])
        if context['property_filter']:
            payments = payments.filter(booking__rental_property_id=context['property_filter'])

        context['payments'] = payments.order_by('-created_at')[:50]

        # Get properties for filter
        from ..models.properties import Property
        context['properties'] = Property.objects.filter(owner=user)

        return context


class PayoutHistoryView(DataResponsiveMixin, LoginRequiredMixin, ListView):
    """Payout history view"""
    model = Payout
    template_name = 'payments/payout_history.html'
    context_object_name = 'payouts'
    paginate_by = 20

    def get_queryset(self):
        return Payout.objects.filter(
            owner=self.request.user
        ).order_by('-payout_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Payout statistics
        payouts = self.get_queryset()
        context['payout_stats'] = {
            'total_payouts': payouts.filter(status='completed').aggregate(
                total=Sum('amount')
            )['total'] or Decimal('0'),
            'pending_payouts': payouts.filter(
                status__in=['scheduled', 'processing']
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0'),
            'total_count': payouts.count(),
            'completed_count': payouts.filter(status='completed').count()
        }

        return context