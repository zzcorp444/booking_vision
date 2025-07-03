# Initial migration without foreign keys to auth.User
from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        # Create simple models first (no foreign keys to auth)
        migrations.CreateModel(
            name='Channel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('api_endpoint', models.URLField(blank=True)),
                ('logo', models.ImageField(blank=True, upload_to='channel_logos/')),
                ('is_active', models.BooleanField(default=True)),
                ('requires_api_key', models.BooleanField(default=True)),
                ('supports_webhooks', models.BooleanField(default=False)),
                ('rate_limit_per_minute', models.IntegerField(default=60)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),

        migrations.CreateModel(
            name='Amenity',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('icon', models.CharField(blank=True, max_length=50)),
                ('category', models.CharField(max_length=50)),
            ],
            options={
                'verbose_name_plural': 'Amenities',
            },
        ),

        migrations.CreateModel(
            name='Guest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('first_name', models.CharField(max_length=100)),
                ('last_name', models.CharField(max_length=100)),
                ('email', models.EmailField(max_length=254)),
                ('phone', models.CharField(blank=True, max_length=20)),
                ('country', models.CharField(blank=True, max_length=100)),
                ('preferences', models.JSONField(blank=True, default=dict)),
                ('satisfaction_score', models.DecimalField(blank=True, decimal_places=2, max_digits=3, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),

        migrations.CreateModel(
            name='MarketData',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('location', models.CharField(max_length=200)),
                ('date', models.DateField()),
                ('average_daily_rate', models.DecimalField(decimal_places=2, max_digits=10)),
                ('occupancy_rate', models.DecimalField(decimal_places=2, max_digits=5)),
                ('revenue_per_available_room', models.DecimalField(decimal_places=2, max_digits=10)),
                ('search_volume', models.IntegerField(default=0)),
                ('booking_lead_time', models.IntegerField(default=0)),
                ('events', models.JSONField(blank=True, default=list)),
                ('season_factor', models.DecimalField(decimal_places=2, default=1.0, max_digits=5)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name_plural': 'Market Data',
                'ordering': ['-date'],
                'unique_together': [('location', 'date')],
            },
        ),
    ]