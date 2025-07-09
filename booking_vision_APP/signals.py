from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.dispatch import receiver
from django.db.models import Q
from .models import Guest, UserProfile
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def link_guest_to_user(sender, instance, created, **kwargs):
    """
    When a new user is created, check if there's an existing guest record
    that matches their information and link them together.
    """
    if created:  # Only run for newly created users
        try:
            # Get user's email
            user_email = instance.email

            # Get user's profile information if available
            user_profile = None
            if hasattr(instance, 'userprofile'):
                user_profile = instance.userprofile

            # Build the search query
            guest_query = Q()

            # Always search by email (most reliable)
            if user_email:
                guest_query |= Q(email__iexact=user_email)

            # Search by name
            if instance.first_name and instance.last_name:
                guest_query |= Q(
                    first_name__iexact=instance.first_name,
                    last_name__iexact=instance.last_name
                )

            # Search by phone if available
            if user_profile and user_profile.phone:
                guest_query |= Q(phone=user_profile.phone)

            # Search by country if available
            if user_profile and hasattr(user_profile, 'country') and user_profile.country:
                # Refine the search with country if we have name match
                if instance.first_name and instance.last_name:
                    guest_query |= Q(
                        first_name__iexact=instance.first_name,
                        last_name__iexact=instance.last_name,
                        country__iexact=user_profile.country
                    )

            # Find matching guests
            matching_guests = Guest.objects.filter(guest_query).filter(user__isnull=True)

            if matching_guests.exists():
                # Prioritize exact email match
                exact_email_match = matching_guests.filter(email__iexact=user_email).first()

                if exact_email_match:
                    guest_to_link = exact_email_match
                    logger.info(f"Found exact email match for user {instance.username}: Guest {guest_to_link}")
                else:
                    # Use the first match with most matching fields
                    guest_to_link = matching_guests.first()
                    logger.info(f"Found potential match for user {instance.username}: Guest {guest_to_link}")

                # Link the guest to the user
                guest_to_link.link_to_user(instance)

                # Update guest information with user data if missing
                updated_fields = []

                if not guest_to_link.first_name and instance.first_name:
                    guest_to_link.first_name = instance.first_name
                    updated_fields.append('first_name')

                if not guest_to_link.last_name and instance.last_name:
                    guest_to_link.last_name = instance.last_name
                    updated_fields.append('last_name')

                if user_profile:
                    if not guest_to_link.phone and user_profile.phone:
                        guest_to_link.phone = user_profile.phone
                        updated_fields.append('phone')

                    if not guest_to_link.country and hasattr(user_profile, 'country') and user_profile.country:
                        guest_to_link.country = user_profile.country
                        updated_fields.append('country')

                if updated_fields:
                    guest_to_link.save(update_fields=updated_fields)

                # Update booking stats
                guest_to_link.update_booking_stats()

                logger.info(f"Successfully linked guest {guest_to_link} to user {instance.username}")

                # Optional: Send a notification to the user
                # You can create an Activity or Notification here
                from .models import Activity
                Activity.create_activity(
                    user=instance,
                    activity_type='user_action',
                    title='Previous Bookings Found',
                    description=f'We found {guest_to_link.total_bookings} previous bookings associated with your account.',
                    priority='low',
                    show_popup=True
                )

        except Exception as e:
            logger.error(f"Error linking guest to user {instance.username}: {str(e)}")


@receiver(post_save, sender=UserProfile)
def link_guest_on_profile_update(sender, instance, created, **kwargs):
    """
    When a user profile is updated with phone/country info,
    check again for matching guests
    """
    if not created and instance.user:  # Only for updates, not creation
        try:
            # Check if user already has a linked guest
            if hasattr(instance.user, 'guest_profile'):
                return

            # Build search query with updated profile info
            guest_query = Q()

            if instance.user.email:
                guest_query |= Q(email__iexact=instance.user.email)

            if instance.phone:
                guest_query |= Q(phone=instance.phone)

                # Also try phone + name combination
                if instance.user.first_name and instance.user.last_name:
                    guest_query |= Q(
                        first_name__iexact=instance.user.first_name,
                        last_name__iexact=instance.user.last_name,
                        phone=instance.phone
                    )

            # Find unlinked matching guests
            matching_guests = Guest.objects.filter(guest_query).filter(user__isnull=True)

            if matching_guests.exists():
                guest_to_link = matching_guests.first()
                guest_to_link.link_to_user(instance.user)

                logger.info(f"Linked guest {guest_to_link} to user {instance.user.username} after profile update")

        except Exception as e:
            logger.error(f"Error linking guest on profile update: {str(e)}")