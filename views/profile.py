"""
User profile and settings views
"""
from django.shortcuts import render, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, UpdateView
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django import forms
from django.contrib.auth.models import User

from ..models.users import UserProfile


class ProfileForm(forms.ModelForm):
    """User profile form"""
    first_name = forms.CharField(max_length=30, required=False)
    last_name = forms.CharField(max_length=30, required=False)
    email = forms.EmailField()

    class Meta:
        model = UserProfile
        fields = ['company_name', 'phone', 'address', 'city', 'country']
        widgets = {
            'address': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'placeholder': '+1234567890'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user:
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
            self.fields['email'].initial = self.instance.user.email

    def save(self, commit=True):
        profile = super().save(commit=False)
        if commit:
            # Update user fields
            user = profile.user
            user.first_name = self.cleaned_data['first_name']
            user.last_name = self.cleaned_data['last_name']
            user.email = self.cleaned_data['email']
            user.save()
            profile.save()
        return profile


class ProfileView(LoginRequiredMixin, UpdateView):
    """User profile view"""
    model = UserProfile
    form_class = ProfileForm
    template_name = 'profile/profile.html'
    success_url = '/profile/'

    def get_object(self, queryset=None):
        return self.request.user.profile

    def form_valid(self, form):
        messages.success(self.request, 'Profile updated successfully!')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get user statistics
        from ..models.properties import Property
        from ..models.bookings import Booking
        from django.db.models import Sum, Count

        user = self.request.user
        context['stats'] = {
            'properties': Property.objects.filter(owner=user).count(),
            'bookings': Booking.objects.filter(rental_property__owner=user).count(),
            'revenue': Booking.objects.filter(
                rental_property__owner=user,
                status__in=['confirmed', 'checked_out']
            ).aggregate(Sum('total_price'))['total_price__sum'] or 0,
            'member_since': user.date_joined
        }

        return context


class SettingsView(LoginRequiredMixin, TemplateView):
    """Settings view"""
    template_name = 'profile/settings.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['password_form'] = PasswordChangeForm(self.request.user)
        context['profile'] = self.request.user.profile

        # Get connected channels
        from ..models.channels import ChannelConnection
        context['connected_channels'] = ChannelConnection.objects.filter(
            user=self.request.user,
            is_connected=True
        ).select_related('channel')

        return context

    def post(self, request, *args, **kwargs):
        """Handle settings updates"""
        action = request.POST.get('action')

        if action == 'change_password':
            form = PasswordChangeForm(request.user, request.POST)
            if form.is_valid():
                user = form.save()
                update_session_auth_hash(request, user)
                messages.success(request, 'Password changed successfully!')
            else:
                messages.error(request, 'Please correct the errors below.')
                context = self.get_context_data()
                context['password_form'] = form
                return render(request, self.template_name, context)

        elif action == 'update_ai_settings':
            profile = request.user.profile
            profile.ai_pricing_enabled = request.POST.get('ai_pricing_enabled') == 'on'
            profile.ai_maintenance_enabled = request.POST.get('ai_maintenance_enabled') == 'on'
            profile.ai_guest_enabled = request.POST.get('ai_guest_enabled') == 'on'
            profile.ai_analytics_enabled = request.POST.get('ai_analytics_enabled') == 'on'
            profile.save()

            # Update all properties
            from ..models.properties import Property
            Property.objects.filter(owner=request.user).update(
                ai_pricing_enabled=profile.ai_pricing_enabled,
                ai_maintenance_enabled=profile.ai_maintenance_enabled,
                ai_guest_enabled=profile.ai_guest_enabled,
                ai_analytics_enabled=profile.ai_analytics_enabled
            )

            messages.success(request, 'AI settings updated successfully!')

        elif action == 'update_notifications':
            # Handle notification preferences
            profile = request.user.profile
            # Add notification fields to UserProfile model if needed
            messages.success(request, 'Notification settings updated!')

        return redirect('booking_vision_APP:settings')