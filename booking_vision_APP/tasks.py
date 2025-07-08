"""
Celery background tasks for Booking Vision
"""
from celery import shared_task
from asgiref.sync import async_to_sync
from django.utils import timezone
from django.core.mail import send_mail
from django.db.models import Q
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


@shared_task
def sync_all_bookings():
    """Sync bookings from all channels for all users"""
    from django.contrib.auth.models import User
    from .integrations.sync_manager import SyncManager

    logger.info("Starting booking sync for all users")

    results = {}
    for user in User.objects.filter(is_active=True):
        try:
            sync_manager = SyncManager(user)
            user_results = sync_manager.sync_all_bookings()
            results[user.username] = user_results
            logger.info(f"Synced bookings for user {user.username}: {user_results}")
        except Exception as e:
            logger.error(f"Error syncing bookings for user {user.id}: {str(e)}")
            results[user.username] = {'error': str(e)}

    return results


@shared_task
def update_dynamic_pricing():
    """Update pricing for all AI-enabled properties"""
    from .models.properties import Property
    from .ai.pricing_engine import PricingEngine

    logger.info("Starting dynamic pricing update")

    properties = Property.objects.filter(
        ai_pricing_enabled=True,
        is_active=True
    )

    pricing_engine = PricingEngine()
    updated_count = 0

    for property in properties:
        try:
            recommendation = pricing_engine.get_pricing_recommendation(property)
            if recommendation:
                # Update property price
                property.base_price = recommendation['suggested_price']
                property.last_pricing_update = timezone.now()
                property.save()

                # Push to channels
                push_rates_to_channels.delay(property.id)

                updated_count += 1
                logger.info(f"Updated pricing for {property.name}: ${recommendation['suggested_price']}")
        except Exception as e:
            logger.error(f"Error updating pricing for property {property.id}: {str(e)}")

    return f"Updated pricing for {updated_count} properties"


@shared_task
def check_maintenance_predictions():
    """Check for maintenance predictions and create tasks"""
    from .models.properties import Property
    from .ai.maintenance_predictor import MaintenancePredictor
    from .models.ai_models import MaintenanceTask

    logger.info("Checking maintenance predictions")

    properties = Property.objects.filter(
        ai_maintenance_enabled=True,
        is_active=True
    )

    predictor = MaintenancePredictor()
    tasks_created = 0

    for property in properties:
        try:
            predictions = predictor.predict_maintenance_needs(property)

            for prediction in predictions:
                if prediction['days_until'] <= 30 and prediction['confidence'] > 0.7:
                    # Create maintenance task
                    task, created = MaintenanceTask.objects.get_or_create(
                        rental_property=property,
                        title=f"Predicted: {prediction['maintenance_type']}",
                        defaults={
                            'description': f"AI predicted maintenance need with {prediction['confidence'] * 100:.0f}% confidence",
                            'priority': prediction['priority'],
                            'status': 'pending',
                            'predicted_by_ai': True,
                            'prediction_confidence': prediction['confidence'],
                            'estimated_cost': prediction['estimated_cost']
                        }
                    )

                    if created:
                        tasks_created += 1
                        # Notify property owner
                        notify_maintenance_needed.delay(property.id, task.id)

        except Exception as e:
            logger.error(f"Error checking maintenance for property {property.id}: {str(e)}")

    return f"Created {tasks_created} maintenance tasks"


@shared_task
def send_automated_messages():
    """Send automated messages based on rules"""
    from .models.notifications import NotificationRule
    from .models.bookings import Booking, BookingMessage
    from .ai.sentiment_analysis import SentimentAnalyzer

    logger.info("Processing automated messages")

    now = timezone.now()
    messages_sent = 0

    # Get active rules
    rules = NotificationRule.objects.filter(is_active=True)

    for rule in rules:
        try:
            # Find bookings that match the rule criteria
            if rule.trigger == 'check_in_reminder':
                target_date = now.date() + timedelta(days=rule.days_before)
                bookings = Booking.objects.filter(
                    rental_property__owner=rule.user,
                    check_in_date=target_date,
                    status='confirmed'
                )
            elif rule.trigger == 'check_out_reminder':
                target_date = now.date() + timedelta(days=rule.days_before)
                bookings = Booking.objects.filter(
                    rental_property__owner=rule.user,
                    check_out_date=target_date,
                    status='checked_in'
                )
            else:
                continue

            # Apply property filter if needed
            if not rule.apply_to_all_properties:
                bookings = bookings.filter(rental_property__in=rule.properties.all())

            # Send messages
            for booking in bookings:
                # Personalize message
                message_text = rule.message_template.format(
                    guest_name=booking.guest.first_name,
                    property_name=booking.rental_property.name,
                    check_in_date=booking.check_in_date,
                    check_out_date=booking.check_out_date,
                    booking_id=booking.id,
                    total_price=booking.total_price,
                    num_guests=booking.num_guests
                )

                # Create message
                BookingMessage.objects.create(
                    booking=booking,
                    sender='host',
                    message=message_text,
                    is_automated=True
                )

                # Send via channel
                send_channel_message.delay(booking.id, message_text)

                messages_sent += 1

        except Exception as e:
            logger.error(f"Error processing rule {rule.id}: {str(e)}")

    return f"Sent {messages_sent} automated messages"


@shared_task
def generate_analytics_reports():
    """Generate daily analytics reports"""
    from django.contrib.auth.models import User
    from .models.bookings import Booking
    from .models.properties import Property
    from django.db.models import Sum, Count, Avg

    logger.info("Generating analytics reports")

    yesterday = timezone.now().date() - timedelta(days=1)

    for user in User.objects.filter(is_active=True):
        try:
            # Generate daily summary
            properties = Property.objects.filter(owner=user)
            bookings = Booking.objects.filter(
                rental_property__owner=user,
                created_at__date=yesterday
            )

            summary = {
                'date': yesterday,
                'new_bookings': bookings.count(),
                'revenue': bookings.aggregate(Sum('total_price'))['total_price__sum'] or 0,
                'properties': properties.count(),
                'occupancy_rate': calculate_occupancy_rate(user, yesterday)
            }

            # Send email report
            send_analytics_email.delay(user.id, summary)

        except Exception as e:
            logger.error(f"Error generating analytics for user {user.id}: {str(e)}")

    return "Analytics reports generated"


@shared_task
def cleanup_old_data():
    """Clean up old data to maintain performance"""
    from .models.bookings import BookingMessage
    from .models.notifications import NotificationLog

    logger.info("Starting data cleanup")

    # Delete old messages (older than 1 year)
    cutoff_date = timezone.now() - timedelta(days=365)
    deleted_messages = BookingMessage.objects.filter(
        created_at__lt=cutoff_date
    ).delete()

    # Delete old notification logs (older than 90 days)
    cutoff_date = timezone.now() - timedelta(days=90)
    deleted_logs = NotificationLog.objects.filter(
        sent_at__lt=cutoff_date
    ).delete()

    logger.info(f"Deleted {deleted_messages[0]} messages and {deleted_logs[0]} notification logs")

    return "Cleanup completed"


# Helper tasks
@shared_task
def push_rates_to_channels(property_id):
    """Push rate updates to all channels for a property"""
    from .models.properties import Property
    from .integrations.sync_manager import SyncManager

    try:
        property = Property.objects.get(id=property_id)
        sync_manager = SyncManager(property.owner)

        # Create rate dict for next 90 days
        rates = {}
        today = timezone.now().date()
        for i in range(90):
            date = today + timedelta(days=i)
            rates[date] = float(property.base_price)

        results = sync_manager.push_rates(property, rates)
        logger.info(f"Pushed rates for property {property_id}: {results}")

    except Exception as e:
        logger.error(f"Error pushing rates for property {property_id}: {str(e)}")


@shared_task
def send_channel_message(booking_id, message_text):
    """Send message through the booking channel"""
    from .models.bookings import Booking
    from .integrations.sync_manager import SyncManager

    try:
        booking = Booking.objects.get(id=booking_id)
        sync_manager = SyncManager(booking.rental_property.owner)

        # Get the appropriate integration
        channel_name = booking.channel.name
        if channel_name in sync_manager.integrations:
            integration = sync_manager.integrations[channel_name]
            success = integration.send_message(
                booking.external_booking_id,
                message_text
            )
            logger.info(f"Sent message for booking {booking_id}: {success}")

    except Exception as e:
        logger.error(f"Error sending message for booking {booking_id}: {str(e)}")


@shared_task
def notify_maintenance_needed(property_id, task_id):
    """Notify owner about maintenance needs"""
    from .models.properties import Property
    from .models.ai_models import MaintenanceTask

    try:
        property = Property.objects.get(id=property_id)
        task = MaintenanceTask.objects.get(id=task_id)

        subject = f"Maintenance Required: {property.name}"
        message = f"""
        AI has predicted a maintenance need for your property {property.name}:

        Task: {task.title}
        Priority: {task.get_priority_display()}
        Estimated Cost: ${task.estimated_cost}

        Please schedule this maintenance to prevent potential issues.

        Log in to Booking Vision to view details and schedule the maintenance.
        """

        send_mail(
            subject,
            message,
            'noreply@bookingvision.com',
            [property.owner.email],
            fail_silently=False,
        )

    except Exception as e:
        logger.error(f"Error notifying about maintenance: {str(e)}")


@shared_task
def send_analytics_email(user_id, summary):
    """Send daily analytics email"""
    from django.contrib.auth.models import User

    try:
        user = User.objects.get(id=user_id)

        subject = f"Daily Analytics Report - {summary['date']}"
        message = f"""
        Your daily analytics summary for {summary['date']}:

        New Bookings: {summary['new_bookings']}
        Revenue: ${summary['revenue']:.2f}
        Active Properties: {summary['properties']}
        Occupancy Rate: {summary['occupancy_rate']:.1f}%

        Log in to Booking Vision to view detailed analytics.
        """

        send_mail(
            subject,
            message,
            'noreply@bookingvision.com',
            [user.email],
            fail_silently=False,
        )

    except Exception as e:
        logger.error(f"Error sending analytics email: {str(e)}")


def calculate_occupancy_rate(user, date):
    """Calculate occupancy rate for a specific date"""
    from .models.properties import Property
    from .models.bookings import Booking

    properties = Property.objects.filter(owner=user, is_active=True)
    total_properties = properties.count()

    if total_properties == 0:
        return 0

    occupied = Booking.objects.filter(
        rental_property__in=properties,
        status__in=['confirmed', 'checked_in'],
        check_in_date__lte=date,
        check_out_date__gte=date
    ).values('rental_property').distinct().count()

    return (occupied / total_properties) * 100


@shared_task
def sync_all_channels_no_api():
    """Sync all channels without API for all users"""
    from django.contrib.auth.models import User
    from .integrations.no_api_sync_manager import NoAPIChannelSync

    logger.info("Starting no-API sync for all users")

    results = {}
    for user in User.objects.filter(is_active=True):
        try:
            sync_manager = NoAPIChannelSync(user)
            user_results = async_to_sync(sync_manager.sync_all_channels)()
            results[user.username] = user_results
            logger.info(f"Synced channels for user {user.username}: {user_results}")
        except Exception as e:
            logger.error(f"Error syncing for user {user.id}: {str(e)}")
            results[user.username] = {'error': str(e)}

    return results


@shared_task
def process_email_bookings():
    """Process booking emails for all users"""
    from django.contrib.auth.models import User
    from .integrations.no_api_sync_manager import AirbnbNoAPISync

    logger.info("Processing booking emails")

    for user in User.objects.filter(is_active=True):
        try:
            # Get email-enabled channels
            connections = user.channelconnection_set.filter(
                email_sync_enabled=True,
                is_connected=True
            )

            for connection in connections:
                sync_class = {
                    'Airbnb': AirbnbNoAPISync,
                    # Add other channels
                }.get(connection.channel.name)

                if sync_class:
                    sync = sync_class()
                    async_to_sync(sync.sync_via_email)(user)

        except Exception as e:
            logger.error(f"Error processing emails for user {user.id}: {str(e)}")
