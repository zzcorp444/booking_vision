from django.apps import AppConfig


class BookingVisionAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'booking_vision_APP'

    def ready(self):
        import booking_vision_APP.signals
