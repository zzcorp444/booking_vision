# Add foreign keys to auth.User after auth tables exist
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.core.validators


class Migration(migrations.Migration):
    dependencies = [
        ('booking_vision_APP', '0001_initial_simple'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Now create models with User foreign keys
        migrations.CreateModel(
            name='Property',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('description', models.TextField()),
                ('property_type', models.CharField(
                    choices=[('apartment', 'Apartment'), ('house', 'House'), ('villa', 'Villa'), ('condo', 'Condo'),
                             ('studio', 'Studio')], max_length=20)),
                ('address', models.CharField(max_length=300)),
                ('city', models.CharField(max_length=100)),
                ('country', models.CharField(max_length=100)),
                ('zip_code', models.CharField(max_length=20)),
                ('bedrooms', models.IntegerField(validators=[django.core.validators.MinValueValidator(0)])),
                ('bathrooms', models.IntegerField(validators=[django.core.validators.MinValueValidator(0)])),
                ('max_guests', models.IntegerField(validators=[django.core.validators.MinValueValidator(1)])),
                ('base_price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('latitude', models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ('longitude', models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ('ai_pricing_enabled', models.BooleanField(default=False)),
                ('ai_maintenance_enabled', models.BooleanField(default=False)),
                ('ai_guest_enabled', models.BooleanField(default=False)),
                ('ai_analytics_enabled', models.BooleanField(default=False)),
                ('last_pricing_update', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_active', models.BooleanField(default=True)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='properties',
                                            to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name_plural': 'Properties',
                'ordering': ['-created_at'],
            },
        ),

        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('company_name', models.CharField(blank=True, max_length=200)),
                ('phone', models.CharField(blank=True, max_length=20)),
                ('address', models.CharField(blank=True, max_length=300)),
                ('city', models.CharField(blank=True, max_length=100)),
                ('country', models.CharField(blank=True, max_length=100)),
                ('ai_pricing_enabled', models.BooleanField(default=False)),
                ('ai_maintenance_enabled', models.BooleanField(default=False)),
                ('ai_guest_enabled', models.BooleanField(default=False)),
                ('ai_analytics_enabled', models.BooleanField(default=False)),
                ('subscription_plan', models.CharField(default='free', max_length=50)),
                ('subscription_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='profile',
                                              to=settings.AUTH_USER_MODEL)),
            ],
        ),

        migrations.CreateModel(
            name='ChannelConnection',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('api_key', models.CharField(blank=True, max_length=255)),
                ('api_secret', models.CharField(blank=True, max_length=255)),
                ('access_token', models.TextField(blank=True)),
                ('refresh_token', models.TextField(blank=True)),
                ('is_connected', models.BooleanField(default=False)),
                ('last_sync', models.DateTimeField(blank=True, null=True)),
                ('sync_errors', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('channel',
                 models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='booking_vision_APP.channel')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'unique_together': [('user', 'channel')],
            },
        ),

        # Now create all other models
        migrations.CreateModel(
            name='Booking',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('external_booking_id', models.CharField(blank=True, max_length=100)),
                ('check_in_date', models.DateField()),
                ('check_out_date', models.DateField()),
                ('num_guests', models.IntegerField()),
                ('base_price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('cleaning_fee', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('service_fee', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('total_price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('status', models.CharField(
                    choices=[('pending', 'Pending'), ('confirmed', 'Confirmed'), ('checked_in', 'Checked In'),
                             ('checked_out', 'Checked Out'), ('cancelled', 'Cancelled')], default='pending',
                    max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('ai_generated_instructions', models.TextField(blank=True)),
                ('sentiment_score', models.DecimalField(blank=True, decimal_places=2, max_digits=3, null=True)),
                ('channel', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='bookings',
                                              to='booking_vision_APP.channel')),
                ('guest', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='bookings',
                                            to='booking_vision_APP.guest')),
                ('rental_property',
                 models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='bookings',
                                   to='booking_vision_APP.property')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),

        migrations.CreateModel(
            name='BookingMessage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sender', models.CharField(choices=[('guest', 'Guest'), ('host', 'Host')], max_length=20)),
                ('message', models.TextField()),
                ('is_automated', models.BooleanField(default=False)),
                ('sentiment_score', models.DecimalField(blank=True, decimal_places=2, max_digits=3, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('booking', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='messages',
                                              to='booking_vision_APP.booking')),
            ],
            options={
                'ordering': ['created_at'],
            },
        ),

        migrations.CreateModel(
            name='PropertyImage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image', models.ImageField(upload_to='property_images/')),
                ('caption', models.CharField(blank=True, max_length=200)),
                ('is_primary', models.BooleanField(default=False)),
                ('order', models.IntegerField(default=0)),
                ('property', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='images',
                                               to='booking_vision_APP.property')),
            ],
            options={
                'ordering': ['order'],
            },
        ),

        migrations.CreateModel(
            name='PropertyAmenity',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amenity',
                 models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='booking_vision_APP.amenity')),
                ('property',
                 models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='booking_vision_APP.property')),
            ],
            options={
                'verbose_name_plural': 'Property Amenities',
                'unique_together': [('property', 'amenity')],
            },
        ),

        migrations.CreateModel(
            name='PropertyChannel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('external_property_id', models.CharField(max_length=100)),
                ('channel_url', models.URLField(blank=True)),
                ('sync_availability', models.BooleanField(default=True)),
                ('sync_rates', models.BooleanField(default=True)),
                ('sync_content', models.BooleanField(default=True)),
                ('is_active', models.BooleanField(default=True)),
                ('last_sync', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('channel',
                 models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='booking_vision_APP.channel')),
                ('channel_connection', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                                         to='booking_vision_APP.channelconnection')),
                ('rental_property',
                 models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='booking_vision_APP.property')),
            ],
            options={
                'unique_together': [('rental_property', 'channel')],
            },
        ),

        migrations.CreateModel(
            name='MaintenanceTask',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('description', models.TextField()),
                ('priority', models.CharField(
                    choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('urgent', 'Urgent')],
                    max_length=10)),
                ('status', models.CharField(
                    choices=[('pending', 'Pending'), ('scheduled', 'Scheduled'), ('in_progress', 'In Progress'),
                             ('completed', 'Completed'), ('cancelled', 'Cancelled')], default='pending',
                    max_length=20)),
                ('predicted_by_ai', models.BooleanField(default=False)),
                ('prediction_confidence', models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ('predicted_failure_date', models.DateField(blank=True, null=True)),
                ('scheduled_date', models.DateField(blank=True, null=True)),
                ('estimated_duration', models.IntegerField(blank=True, help_text='Duration in hours', null=True)),
                ('estimated_cost', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('completed_date', models.DateField(blank=True, null=True)),
                ('actual_cost', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('rental_property',
                 models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='maintenance_tasks',
                                   to='booking_vision_APP.property')),
            ],
            options={
                'ordering': ['-priority', '-created_at'],
            },
        ),

        migrations.CreateModel(
            name='PricingRule',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('min_days_ahead', models.IntegerField(default=0)),
                ('max_days_ahead', models.IntegerField(default=365)),
                ('min_stay_length', models.IntegerField(default=1)),
                ('max_stay_length', models.IntegerField(default=30)),
                ('base_multiplier', models.DecimalField(decimal_places=2, default=1.0, max_digits=5)),
                ('weekend_multiplier', models.DecimalField(decimal_places=2, default=1.0, max_digits=5)),
                ('holiday_multiplier', models.DecimalField(decimal_places=2, default=1.0, max_digits=5)),
                ('high_demand_threshold', models.DecimalField(decimal_places=2, default=0.8, max_digits=5)),
                ('high_demand_multiplier', models.DecimalField(decimal_places=2, default=1.2, max_digits=5)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('rental_property',
                 models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='pricing_rules',
                                   to='booking_vision_APP.property')),
            ],
        ),

        migrations.CreateModel(
            name='GuestPreference',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('room_temperature', models.IntegerField(blank=True, null=True)),
                ('preferred_check_in_time', models.TimeField(blank=True, null=True)),
                ('preferred_check_out_time', models.TimeField(blank=True, null=True)),
                ('interests', models.JSONField(blank=True, default=list)),
                ('dietary_restrictions', models.JSONField(blank=True, default=list)),
                ('guest_type', models.CharField(blank=True, max_length=50)),
                ('spending_pattern', models.CharField(blank=True, max_length=50)),
                ('communication_preference', models.CharField(blank=True, max_length=50)),
                ('average_rating', models.DecimalField(blank=True, decimal_places=2, max_digits=3, null=True)),
                ('loyalty_score', models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('guest',
                 models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='ai_preferences',
                                      to='booking_vision_APP.guest')),
            ],
        ),
    ]