from django.shortcuts import render, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, UpdateView
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django import forms
from django.contrib.auth import get_user_model
from django.db import transaction

from ..models.users import UserProfile
from ..mixins import DataResponsiveMixin

User = get_user_model()


class ProfileForm(forms.ModelForm):
    """Enhanced user profile form"""
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    email = forms.EmailField(required=True)
    
    class Meta:
        model = UserProfile
        fields = ['phone', 'address', 'city', 'country', 'company_name', 
                  'profile_picture']
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
            
            # Hide company name for non-hosts
            if not self.instance.user.is_host():
                self.fields.pop('company_name', None)
    
    def clean_email(self):
        email = self.cleaned_data['email']
        # Check if email is already used by another user
        if User.objects.exclude(pk=self.instance.user.pk).filter(email=email).exists():
            raise forms.ValidationError('This email is already in use.')
        return email
    
    @transaction.atomic
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


class ProfileView(DataResponsiveMixin, LoginRequiredMixin, UpdateView):
    """Enhanced user profile view"""
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
        
        # Get user statistics based on user type
        user = self.request.user
        
        if user.is_host():
            from ..models.properties import Property
            from ..models.bookings import Booking
            from django.db.models import Sum, Count
            
            context['stats'] = {
                'properties': Property.objects.filter(owner=user).count(),
                'bookings': Booking.objects.filter(rental_property__owner=user).count(),
                'revenue': Booking.objects.filter(
                    rental_property__owner=user,
                    status__in=['confirmed', 'checked_out']
                ).aggregate(Sum('total_price'))['total_price__sum'] or 0,
                'member_since': user.date_joined,
                'subscription_status': 'Active' if user.has_active_subscription() else 'Inactive'
            }
        elif user.is_guest_user():
            from ..models.bookings import Booking
            
            context['stats'] = {
                'bookings': Booking.objects.filter(guest__email=user.email).count(),
                'member_since': user.date_joined,
                'verified': user.is_email_verified
            }
        
        return context


class EnhancedSettingsView(DataResponsiveMixin, LoginRequiredMixin, TemplateView):
    """Enhanced settings view with working password reset"""
    template_name = 'profile/settings.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['password_form'] = PasswordChangeForm(self.request.user)
        context['profile'] = self.request.user.profile
        
        # Get connected channels for hosts
        if self.request.user.is_host():
            from ..models.channels import ChannelConnection
            context['connected_channels'] = ChannelConnection.objects.filter(
                user=self.request.user,
                is_connected=True
            ).select_related('channel')
        
        return context
    
    def post(self, request, *args, **kwargs):
        """Handle various settings updates"""
        action = request.POST.get('action')
        
        if action == 'update_profile':
            return self._update_profile(request)
        
        elif action == 'change_password':
            return self._change_password(request)
        
        elif action == 'update_ai_settings':
            return self._update_ai_settings(request)
        
        elif action == 'update_notifications':
            return self._update_notifications(request)
        
        return redirect('booking_vision_APP:settings')
    
    def _update_profile(self, request):
        """Update basic profile information"""
        profile = request.user.profile
        user = request.user
        
        # Update user fields
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        
        # Check email uniqueness
        new_email = request.POST.get('email')
        if new_email and new_email != user.email:
            if User.objects.filter(email=new_email).exclude(pk=user.pk).exists():
                messages.error(request, 'This email is already in use.')
                return redirect('booking_vision_APP:settings')
            user.email = new_email
        
        user.save()
        
        # Update profile fields
        profile.phone = request.POST.get('phone', profile.phone)
        profile.address = request.POST.get('address', profile.address)
        profile.city = request.POST.get('city', profile.city)
        profile.country = request.POST.get('country', profile.country)
        
        if user.is_host():
            profile.company_name = request.POST.get('company_name', profile.company_name)
        
        profile.save()
        
        messages.success(request, 'Profile information updated successfully!')
        return redirect('booking_vision_APP:settings')
    
    def _change_password(self, request):
        """Handle password change with proper validation"""
        form = PasswordChangeForm(request.user, request.POST)
        
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Keep user logged in
            messages.success(request, 'Password changed successfully!')
            
            # Send email notification
            try:
                from django.core.mail import send_mail
                send_mail(
                    'Password Changed - Booking Vision',
                    f'Hello {user.first_name},\n\nYour password was successfully changed. If you did not make this change, please contact us immediately.\n\nBest regards,\nThe Booking Vision Team',
                    'noreply@bookingvision.com',
                    [user.email],
                    fail_silently=False,
                )
            except Exception as e:
                logger.error(f"Failed to send password change email: {str(e)}")
        else:
            # Show specific error messages
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
            
            # Re-render the settings page with the form errors
            context = self.get_context_data()
            context['password_form'] = form
            context['active_tab'] = 'security'  # Show security tab
            return render(request, self.template_name, context)
        
        return redirect('booking_vision_APP:settings')
    
    def _update_ai_settings(self, request):
        """Update AI settings for hosts"""
        if not request.user.is_host():
            messages.error(request, 'Only hosts can update AI settings.')
            return redirect('booking_vision_APP:settings')
        
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
        return redirect('booking_vision_APP:settings')
    
    def _update_notifications(self, request):
        """Update notification preferences"""
        # Add notification preferences to UserProfile model if needed
        messages.success(request, 'Notification settings updated!')
        return redirect('booking_vision_APP:settings')