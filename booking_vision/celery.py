"""
Celery configuration for Booking Vision
"""
import os
from celery import Celery
from django.conf import settings

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'booking_vision.settings')

# Create Celery app
app = Celery('booking_vision')

# Configure Celery using settings from Django settings.py
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps
app.autodiscover_tasks()

# Celery beat schedule for periodic tasks
from celery.schedules import crontab

app.conf.beat_schedule = {
    # No-API sync every hour
    'sync-channels-no-api': {
        'task': 'booking_vision_APP.tasks.sync_all_channels_no_api',
        'schedule': crontab(minute=0),
    },

    # Process emails every 15 minutes
    'process-booking-emails': {
        'task': 'booking_vision_APP.tasks.process_email_bookings',
        'schedule': crontab(minute='*/15'),
    },
    # Sync bookings every 30 minutes
    'sync-all-bookings': {
        'task': 'booking_vision_APP.tasks.sync_all_bookings',
        'schedule': crontab(minute='*/30'),
    },

    # Update dynamic pricing every hour
    'update-dynamic-pricing': {
        'task': 'booking_vision_APP.tasks.update_dynamic_pricing',
        'schedule': crontab(minute=0),
    },

    # Check for maintenance predictions daily at 9 AM
    'check-maintenance': {
        'task': 'booking_vision_APP.tasks.check_maintenance_predictions',
        'schedule': crontab(hour=9, minute=0),
    },

    # Send automated messages every 15 minutes
    'send-automated-messages': {
        'task': 'booking_vision_APP.tasks.send_automated_messages',
        'schedule': crontab(minute='*/15'),
    },

    # Generate analytics reports daily at midnight
    'generate-analytics': {
        'task': 'booking_vision_APP.tasks.generate_analytics_reports',
        'schedule': crontab(hour=0, minute=0),
    },

    # Clean up old data monthly
    'cleanup-old-data': {
        'task': 'booking_vision_APP.tasks.cleanup_old_data',
        'schedule': crontab(day_of_month=1, hour=2, minute=0),
    },
}


@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')

