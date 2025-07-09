from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db.models import Q
from booking_vision_APP.models import Guest
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Link existing users to guest records based on matching information'

    def handle(self, *args, **options):
        users_linked = 0

        # Get all users without linked guests
        users_without_guests = User.objects.filter(guest_profile__isnull=True)

        self.stdout.write(f"Found {users_without_guests.count()} users without linked guest profiles")

        for user in users_without_guests:
            # Build search query
            guest_query = Q()

            if user.email:
                guest_query |= Q(email__iexact=user.email)

            if user.first_name and user.last_name:
                guest_query |= Q(
                    first_name__iexact=user.first_name,
                    last_name__iexact=user.last_name
                )

            if hasattr(user, 'userprofile') and user.userprofile.phone:
                guest_query |= Q(phone=user.userprofile.phone)

            # Find unlinked matching guests
            matching_guests = Guest.objects.filter(guest_query).filter(user__isnull=True)

            if matching_guests.exists():
                guest = matching_guests.first()
                guest.link_to_user(user)
                users_linked += 1

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Linked user {user.username} to guest {guest}"
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully linked {users_linked} users to guest profiles"
            )
        )