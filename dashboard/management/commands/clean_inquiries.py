from django.core.management.base import BaseCommand
from dashboard.models import InquiryHandler, InquiryItem


class Command(BaseCommand):
    help = 'Clean all inquiry data from the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirm deletion of all inquiry data',
        )

    def handle(self, *args, **options):
        if not options['confirm']:
            self.stdout.write(
                self.style.WARNING(
                    'This will delete ALL inquiry data. Use --confirm to proceed.'
                )
            )
            return

        try:
            # Count existing data
            inquiry_count = InquiryHandler.objects.count()
            inquiry_item_count = InquiryItem.objects.count()
            
            self.stdout.write(f'Found {inquiry_count} inquiries and {inquiry_item_count} inquiry items')
            
            # Delete all inquiry items first (due to foreign key relationship)
            deleted_items = InquiryItem.objects.all().delete()
            self.stdout.write(
                self.style.SUCCESS(f'Deleted {deleted_items[0]} inquiry items')
            )
            
            # Delete all inquiries
            deleted_inquiries = InquiryHandler.objects.all().delete()
            self.stdout.write(
                self.style.SUCCESS(f'Deleted {deleted_inquiries[0]} inquiries')
            )
            
            self.stdout.write(
                self.style.SUCCESS('✅ All inquiry data has been cleaned successfully!')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error cleaning inquiry data: {str(e)}')
            )