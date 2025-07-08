"""
Notifications view for automated actions and alerts.
Location: booking_vision_APP/views/notifications.py
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from django import forms

from ..models.notifications import NotificationRule, NotificationLog
from ..mixins import DataResponsiveMixin


class NotificationRuleForm(forms.ModelForm):
    """Form for creating/editing notification rules"""
    class Meta:
        model = NotificationRule
        fields = ['name', 'trigger', 'channel', 'days_before', 'time_of_day',
                  'subject', 'message_template', 'properties', 'apply_to_all_properties', 'is_active']
        widgets = {
            'message_template': forms.Textarea(attrs={'rows': 5}),
            'properties': forms.SelectMultiple(attrs={'class': 'form-select', 'size': 5}),
            'time_of_day': forms.TimeInput(attrs={'type': 'time'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            from ..models.properties import Property
            self.fields['properties'].queryset = Property.objects.filter(owner=user)


class NotificationListView(DataResponsiveMixin, LoginRequiredMixin, ListView):
    """List all notification rules"""
    model = NotificationRule
    template_name = 'notifications/notifications_list.html'
    context_object_name = 'rules'

    def get_queryset(self):
        return NotificationRule.objects.filter(user=self.request.user).order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get notification logs
        context['recent_logs'] = NotificationLog.objects.filter(
            rule__user=self.request.user
        ).order_by('-sent_at')[:20]

        # Statistics
        all_logs = NotificationLog.objects.filter(rule__user=self.request.user)
        context['notification_stats'] = {
            'total_sent': all_logs.count(),
            'successful': all_logs.filter(is_successful=True).count(),
            'failed': all_logs.filter(is_successful=False).count(),
            'email_sent': all_logs.filter(channel='email').count(),
            'sms_sent': all_logs.filter(channel='sms').count(),
        }

        return context


class NotificationCreateView(LoginRequiredMixin, CreateView):
    """Create new notification rule"""
    model = NotificationRule
    form_class = NotificationRuleForm
    template_name = 'notifications/notification_form.html'
    success_url = reverse_lazy('booking_vision_APP:notifications_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(self.request, 'Notification rule created successfully!')
        return super().form_valid(form)


class NotificationUpdateView(LoginRequiredMixin, UpdateView):
    """Update notification rule"""
    model = NotificationRule
    form_class = NotificationRuleForm
    template_name = 'notifications/notification_form.html'
    success_url = reverse_lazy('booking_vision_APP:notifications_list')

    def get_queryset(self):
        return NotificationRule.objects.filter(user=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, 'Notification rule updated successfully!')
        return super().form_valid(form)


class NotificationDeleteView(LoginRequiredMixin, DeleteView):
    """Delete notification rule"""
    model = NotificationRule
    template_name = 'notifications/notification_confirm_delete.html'
    success_url = reverse_lazy('booking_vision_APP:notifications_list')

    def get_queryset(self):
        return NotificationRule.objects.filter(user=self.request.user)

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Notification rule deleted successfully!')
        return super().delete(request, *args, **kwargs)