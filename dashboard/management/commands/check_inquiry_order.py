from django.core.management.base import BaseCommand
from dashboard.models import InquiryHandler
from django.utils import timezone


class Command(BaseCommand):
    help = 'Check and display inquiry ordering by creation date'

    def handle(self, *args, **options):
        # Get all inquiries ordered by new month-wise ordering (latest month first)
        inquiries = InquiryHandler.objects.all().order_by('-year_month_order', '-serial_number')
        
        self.stdout.write(
            self.style.SUCCESS(f'Found {inquiries.count()} inquiries')
        )
        
        if inquiries.exists():
            self.stdout.write('\nInquiries ordered by month (latest month first):')
            self.stdout.write('-' * 80)
            
            for i, inquiry in enumerate(inquiries[:10], 1):  # Show first 10
                created_date = inquiry.created_at.strftime('%Y-%m-%d %H:%M:%S') if inquiry.created_at else 'No date'
                month_order = inquiry.year_month_order or 'No month'
                serial = inquiry.serial_number or 0
                self.stdout.write(
                    f'{i:2d}. {inquiry.create_id} | {inquiry.quote_no} | {created_date} | {inquiry.status} | Month: {month_order} | Serial: {serial:03d}'
                )
            
            if inquiries.count() > 10:
                self.stdout.write(f'... and {inquiries.count() - 10} more')
                
        else:
            self.stdout.write(
                self.style.WARNING('No inquiries found in the database')
            )