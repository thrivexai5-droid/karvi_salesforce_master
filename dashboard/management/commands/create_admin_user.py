from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from dashboard.models import UserProfile


class Command(BaseCommand):
    help = 'Create admin superuser with specified details'

    def handle(self, *args, **options):
        # User details
        username = 'kush'
        email = 'kush@karvienc.com'
        first_name = 'kush'
        last_name = 'Patel'
        phone = '7600953567'
        password = 'Darshan@1234'
        
        try:
            # Check if user already exists
            if User.objects.filter(username=username).exists():
                self.stdout.write(
                    self.style.WARNING(f'User "{username}" already exists!')
                )
                return
            
            # Create superuser
            user = User.objects.create_superuser(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name
            )
            
            # Create or update user profile with admin permissions
            user_profile, created = UserProfile.objects.get_or_create(
                user=user,
                defaults={
                    'roles': 'admin',
                    'phone_number': phone,
                    'can_access_invoice_generation': True,
                    'can_access_inquiry_handler': True,
                    'can_access_quotation_generation': True,
                    'can_access_additional_supply': True,
                }
            )
            
            if not created:
                # Update existing profile
                user_profile.roles = 'admin'
                user_profile.phone_number = phone
                user_profile.can_access_invoice_generation = True
                user_profile.can_access_inquiry_handler = True
                user_profile.can_access_quotation_generation = True
                user_profile.can_access_additional_supply = True
                user_profile.save()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully created admin user "{username}" with full access permissions!'
                )
            )
            self.stdout.write(f'Name: {first_name} {last_name}')
            self.stdout.write(f'Email: {email}')
            self.stdout.write(f'Phone: {phone}')
            self.stdout.write(f'Username: {username}')
            self.stdout.write(f'Password: {password}')
            self.stdout.write(f'Role: Administrator')
            self.stdout.write(f'Superuser: Yes')
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating user: {str(e)}')
            )