# booking_vision_APP/views/auth.py
"""
Authentication views for user registration and management
"""
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.urls import reverse
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.views.generic import CreateView, TemplateView
from django.db import transaction
import logging

from ..models.users import CustomUser, UserProfile
from ..forms import HostRegistrationForm, GuestRegistrationForm

logger = logging.getLogger(__name__)


class HostRegistrationView(CreateView):
    """Registration view for hosts"""
    model = CustomUser
    form_class = HostRegistrationForm
    template_name = 'registration/register_host.html'
    
    def form_valid(self, form):
        with transaction.atomic():
            # Create user
            user = form.save(commit=False)
            user.user_type = 'host'
            user.is_active = False  # Require email verification
            user.email_verification_token = get_random_string(64)
            user.save()
            
            # Create profile
            profile = UserProfile.objects.create(
                user=user,
                company_name=form.cleaned_data.get('company_name'),
                phone=form.cleaned_data.get('phone'),
                subscription_plan='trial'  # Start with trial
            )
            
            # Send verification email
            self.send_verification_email(user)
            
            messages.success(self.request, 'Registration successful! Please check your email to verify your account.')
            return redirect('booking_vision_APP:registration_success')
    
    def send_verification_email(self, user):
        """Send email verification"""
        verification_url = self.request.build_absolute_uri(
            reverse('booking_vision_APP:verify_email', kwargs={'token': user.email_verification_token})
        )
        
        subject = 'Verify your Booking Vision account'
        message = f"""
        Welcome to Booking Vision!
        
        Please click the link below to verify your email address:
        {verification_url}
        
        This link will expire in 24 hours.
        
        Best regards,
        The Booking Vision Team
        """
        
        send_mail(subject, message, 'noreply@bookingvision.com', [user.email])


class GuestRegistrationView(CreateView):
    """Registration view for guests"""
    model = CustomUser
    form_class = GuestRegistrationForm
    template_name = 'registration/register_guest.html'
    
    def form_valid(self, form):
        with transaction.atomic():
            # Create user
            user = form.save(commit=False)
            user.user_type = 'guest'
            user.is_active = True  # Guests can use immediately
            user.save()
            
            # Create profile
            profile = UserProfile.objects.create(
                user=user,
                phone=form.cleaned_data.get('phone'),
                date_of_birth=form.cleaned_data.get('date_of_birth')
            )
            
            # Auto-login
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password1')
            user = authenticate(username=username, password=password)
            login(self.request, user)
            
            messages.success(self.request, 'Welcome to Booking Vision!')
            return redirect('booking_vision_APP:guest_dashboard')


def verify_email(request, token):
    """Verify email address"""
    try:
        user = CustomUser.objects.get(email_verification_token=token)
        user.is_active = True
        user.is_email_verified = True
        user.email_verification_token = ''
        user.save()
        
        messages.success(request, 'Email verified successfully! You can now log in.')
        return redirect('login')
    except CustomUser.DoesNotExist:
        messages.error(request, 'Invalid verification link.')
        return redirect('booking_vision_APP:register')


@login_required
def check_subscription(request):
    """Check if host has active subscription"""
    if request.user.is_guest_user():
        return redirect('booking_vision_APP:guest_dashboard')
    
    if request.user.is_admin_or_bookmaker():
        return redirect('booking_vision_APP:dashboard')
    
    if not request.user.has_active_subscription():
        return redirect('booking_vision_APP:subscription_plans')
    
    return redirect('booking_vision_APP:dashboard')