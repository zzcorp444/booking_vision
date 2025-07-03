#!/usr/bin/env python
"""
Script to reset migrations for Booking Vision
"""
import os
import sys
import django

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'booking_vision.settings')
django.setup()

from django.core.management import execute_from_command_line
from django.db import connection


def reset_migrations():
    """Reset all migrations"""
    print("Resetting migrations...")

    # Drop all tables if they exist
    with connection.cursor() as cursor:
        cursor.execute("""
            DROP SCHEMA public CASCADE;
            CREATE SCHEMA public;
            GRANT ALL ON SCHEMA public TO postgres;
            GRANT ALL ON SCHEMA public TO public;
        """)

    # Delete migration files
    try:
        import shutil
        import glob
        migration_files = glob.glob('booking_vision_APP/migrations/0*.py')
        for file in migration_files:
            os.remove(file)
            print(f"Deleted {file}")
    except:
        pass

    # Create fresh migrations
    execute_from_command_line(['manage.py', 'makemigrations'])
    execute_from_command_line(['manage.py', 'migrate'])

    print("Migrations reset complete!")


if __name__ == '__main__':
    reset_migrations()