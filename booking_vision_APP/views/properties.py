"""
Property management views for Booking Vision application.
This file contains all property-related views and CRUD operations.
Location: booking_vision_APP/views/properties.py
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q, Count, Sum, Avg
import json

from ..models.properties import Property, PropertyImage, Amenity, PropertyAmenity
from ..models.bookings import Booking
from ..models.channels import PropertyChannel

from ..mixins import DataResponsiveMixin


class PropertyListView(DataResponsiveMixin, LoginRequiredMixin, ListView):
    """List all properties for the current user"""
    model = Property
    template_name = 'properties/property_list.html'
    context_object_name = 'properties'
    paginate_by = 12

    def get_queryset(self):
        queryset = Property.objects.filter(
            owner=self.request.user,
            is_active=True
        ).prefetch_related('images', 'bookings')

        # Search functionality
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(city__icontains=search) |
                Q(address__icontains=search)
            )

        # Filter by property type
        property_type = self.request.GET.get('type')
        if property_type:
            queryset = queryset.filter(property_type=property_type)

        return queryset.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Add property statistics
        properties = context['properties']
        context['total_properties'] = properties.count() if hasattr(properties, 'count') else len(properties)

        # Property types for filter
        context['property_types'] = Property.PROPERTY_TYPES

        # Current filters
        context['current_search'] = self.request.GET.get('search', '')
        context['current_type'] = self.request.GET.get('type', '')

        return context


class PropertyDetailView(LoginRequiredMixin, DetailView):
    """Detailed view of a single property"""
    model = Property
    template_name = 'properties/property_detail.html'
    context_object_name = 'property'

    def get_queryset(self):
        return Property.objects.filter(owner=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        property = context['property']

        # Recent bookings
        context['recent_bookings'] = property.bookings.select_related(
            'guest', 'channel'
        ).order_by('-created_at')[:10]

        # Property statistics
        context['total_bookings'] = property.bookings.count()
        context['confirmed_bookings'] = property.bookings.filter(status='confirmed').count()

        # Revenue statistics
        revenue_data = property.bookings.filter(
            status__in=['confirmed', 'checked_out']
        ).aggregate(
            total_revenue=Sum('total_price'),
            avg_booking_value=Avg('total_price')
        )
        context.update(revenue_data)

        # Channel connections
        context['connected_channels'] = PropertyChannel.objects.filter(
            property=property,
            is_active=True
        ).select_related('channel')

        # Amenities
        context['amenities'] = PropertyAmenity.objects.filter(
            property=property
        ).select_related('amenity')

        return context


class PropertyCreateView(LoginRequiredMixin, CreateView):
    """Create a new property"""
    model = Property
    template_name = 'properties/property_form.html'
    fields = [
        'name', 'description', 'property_type', 'address', 'city',
        'country', 'zip_code', 'bedrooms', 'bathrooms', 'max_guests',
        'base_price', 'latitude', 'longitude'
    ]

    def form_valid(self, form):
        form.instance.owner = self.request.user
        messages.success(self.request, 'Property created successfully!')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('booking_vision_APP:property_detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['amenities'] = Amenity.objects.all().order_by('category', 'name')
        return context


class PropertyUpdateView(LoginRequiredMixin, UpdateView):
    """Update an existing property"""
    model = Property
    template_name = 'properties/property_form.html'
    fields = [
        'name', 'description', 'property_type', 'address', 'city',
        'country', 'zip_code', 'bedrooms', 'bathrooms', 'max_guests',
        'base_price', 'latitude', 'longitude', 'ai_pricing_enabled'
    ]

    def get_queryset(self):
        return Property.objects.filter(owner=self.request.user)

    def form_valid(self, form):
        messages.success(self.request, 'Property updated successfully!')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('booking_vision_APP:property_detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['amenities'] = Amenity.objects.all().order_by('category', 'name')
        context['property_amenities'] = PropertyAmenity.objects.filter(
            property=self.object
        ).values_list('amenity_id', flat=True)
        return context


def update_property_amenities(request, pk):
    """AJAX endpoint to update property amenities"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    property = get_object_or_404(Property, pk=pk, owner=request.user)
    data = json.loads(request.body)
    amenity_ids = data.get('amenities', [])

    # Clear existing amenities
    PropertyAmenity.objects.filter(property=property).delete()

    # Add new amenities
    for amenity_id in amenity_ids:
        try:
            amenity = Amenity.objects.get(id=amenity_id)
            PropertyAmenity.objects.create(property=property, amenity=amenity)
        except Amenity.DoesNotExist:
            continue

    return JsonResponse({'success': True, 'message': 'Amenities updated successfully'})