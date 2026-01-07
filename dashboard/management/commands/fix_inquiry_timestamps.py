from django.core.management.base import BaseCommand
from dashboard.models import InquiryHandler
from django.utils import timezone
from datetime import timedelta
import re


class Command(BaseCommand):
    help = 'Fix inquiry timestamps to ensure proper chronological ordering'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without making actual changes',
        )

    def parse_inquiry_date(self, create_id):
        """Extract date information from create_id like KEC013JA2026"""
        try:
            # Pattern: KEC + number + month + year
            match = re.match(r'KEC(\d+)([A-Z]{2})(\d{4})', create_id)
            if match:
                serial_num = int(match.group(1))
                month_code = match.group(2)
                year = int(match.group(3))
                
                # Month code mapping
                month_map = {
                    'JA': 1, 'FE': 2, 'MR': 3, 'AP': 4, 'MY': 5, 'JN': 6,
                    'JL': 7, 'AU': 8, 'SE': 9, 'OC': 10, 'NO': 11, 'DE': 12
                }
                
                month = month_map.get(month_code, 1)
                return year, month, serial_num
            return None, None, None
        except:
            return None, None, None

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No changes will be made')
            )
        
        # Get all inquiries
        inquiries = InquiryHandler.objects.all().order_by('create_id')
        
        self.stdout.write(f'Processing {inquiries.count()} inquiries...')
        
        updated_count = 0
        base_time = timezone.now().replace(hour=9, minute=0, second=0, microsecond=0)
        
        # Group inquiries by year and month, then sort by serial number
        inquiry_groups = {}
        
        for inquiry in inquiries:
            year, month, serial_num = self.parse_inquiry_date(inquiry.create_id)
            if year and month and serial_num:
                key = (year, month)
                if key not in inquiry_groups:
                    inquiry_groups[key] = []
                inquiry_groups[key].append((serial_num, inquiry))
        
        # Sort groups by year/month and process in chronological order
        sorted_groups = sorted(inquiry_groups.keys())
        
        time_offset = 0
        
        for year, month in sorted_groups:
            # Sort inquiries within each month by serial number
            month_inquiries = sorted(inquiry_groups[(year, month)], key=lambda x: x[0])
            
            self.stdout.write(f'\nProcessing {year}-{month:02d} ({len(month_inquiries)} inquiries)')
            
            for serial_num, inquiry in month_inquiries:
                # Calculate new timestamp
                new_timestamp = base_time - timedelta(days=time_offset // 24, hours=time_offset % 24)
                
                if not dry_run:
                    inquiry.created_at = new_timestamp
                    inquiry.save(update_fields=['created_at'])
                
                self.stdout.write(
                    f'  {inquiry.create_id}: {new_timestamp.strftime("%Y-%m-%d %H:%M:%S")}'
                )
                
                updated_count += 1
                time_offset += 1  # Increment by 1 hour for each inquiry
        
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(f'Would update {updated_count} inquiries')
            )
            self.stdout.write(
                self.style.WARNING('Run without --dry-run to apply changes')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'Successfully updated {updated_count} inquiry timestamps')
            )
            self.stdout.write(
                'Inquiries are now ordered chronologically with latest first'
            )