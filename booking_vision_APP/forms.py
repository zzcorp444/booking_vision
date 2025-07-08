# booking_vision_APP/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from .models.users import CustomUser


class HostRegistrationForm(UserCreationForm):
    """Registration form for hosts"""
    email = forms.EmailField(required=True)
    company_name = forms.CharField(max_length=200, required=False)
    phone = forms.CharField(max_length=20, required=False)
    agree_terms = forms.BooleanField(required=True)

    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'first_name', 'last_name',
                  'password1', 'password2', 'company_name', 'phone')

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if CustomUser.objects.filter(email=email).exists():
            raise ValidationError('This email is already registered.')
        return email


class GuestRegistrationForm(UserCreationForm):
    """Registration form for guests"""
    email = forms.EmailField(required=True)
    phone = forms.CharField(max_length=20, required=False)
    date_of_birth = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))

    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'first_name', 'last_name',
                  'password1', 'password2', 'phone', 'date_of_birth')