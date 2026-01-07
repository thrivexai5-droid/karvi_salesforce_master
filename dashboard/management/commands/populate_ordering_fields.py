from django.core.management.base import BaseCommand
from dashboard.models import InquiryHandler
import re


class Command(BaseCommand):
    help = 'Populate year_month_order and serial_number fields for existing inquiries'

    def handle(self, *args, **options):
        inquiries = InquiryHandler.objects.all()
        updated_count = 0
        
        self.stdout.write(f'Processing {inquiries.count()} inquiries...')
        
        for inquiry in inquiries:
            if inquiry.create_id:
                # Extract year, month, and serial number from create_id
                match = re.match(r'KEC(\d+)([A-Z]{2})(\d{4})', inquiry.create_id)
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
                    
                    # Update the fields
                    inquiry.year_month_order = f"{year}-{month:02d}"
                    inquiry.serial_number = serial_num
                    inquiry.save(update_fields=['year_month_order', 'serial_number'])
                    
                    updated_count += 1
                    
                    if updated_count % 50 == 0:
                        self.stdout.write(f'Updated {updated_count} inquiries...')
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully updated {updated_count} inquiries with ordering fields')
        )
        
        # Show sample of the new ordering
        self.stdout.write('\nSample of new ordering (latest month first):')
        sample_inquiries = InquiryHandler.objects.all().order_by('-year_month_order', '-serial_number')[:10]
        
        for i, inquiry in enumerate(sample_inquiries, 1):
            self.stdout.write(
                f'{i:2d}. {inquiry.create_id} | {inquiry.year_month_order} | Serial: {inquiry.serial_number:03d}'
            )