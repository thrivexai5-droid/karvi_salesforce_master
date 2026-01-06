from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.conf import settings
import os

class Command(BaseCommand):
    help = 'Setup production environment for PythonAnywhere deployment'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Setting up production environment...'))
        
        # Check if we're in production
        if not settings.DEBUG:
            self.stdout.write('Running in production mode')
        else:
            self.stdout.write('Running in development mode')
        
        # Run migrations
        self.stdout.write('Running database migrations...')
        call_command('migrate', verbosity=1)
        
        # Collect static files
        self.stdout.write('Collecting static files...')
        call_command('collectstatic', '--noinput', verbosity=1)
        
        # Check database connection
        from django.db import connection
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            self.stdout.write(self.style.SUCCESS('Database connection: OK'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Database connection failed: {e}'))
        
        # Check required environment variables
        required_vars = ['SECRET_KEY', 'DB_NAME', 'DB_USER', 'DB_PASSWORD', 'DB_HOST']
        missing_vars = []
        
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            self.stdout.write(
                self.style.WARNING(
                    f'Missing environment variables: {", ".join(missing_vars)}'
                )
            )
        else:
            self.stdout.write(self.style.SUCCESS('All required environment variables are set'))
        
        self.stdout.write(self.style.SUCCESS('Production setup completed!'))
        self.stdout.write('Next steps:')
        self.stdout.write('1. Create superuser: python manage.py createsuperuser')
        self.stdout.write('2. Test the application')
        self.stdout.write('3. Configure web server (if not done already)')