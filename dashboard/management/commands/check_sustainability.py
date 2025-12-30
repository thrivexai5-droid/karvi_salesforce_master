from django.core.management.base import BaseCommand
from dashboard.services import calculate_sustainability_date, get_financial_summary

class Command(BaseCommand):
    help = 'Check current financial sustainability status'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🧮 Financial Sustainability Report'))
        self.stdout.write('=' * 50)
        
        try:
            # Get sustainability data
            data = calculate_sustainability_date()
            
            self.stdout.write(f"📊 Current Status:")
            self.stdout.write(f"   Total Invoice Value: ₹{data['total_invoice_value']:,.0f}")
            self.stdout.write(f"   Available Funds: ₹{data['net_revenue']:,.0f}")
            self.stdout.write(f"   Monthly Expenses: ₹{data['monthly_expenses']:,.0f}")
            self.stdout.write(f"   Daily Burn Rate: ₹{data['daily_burn']:,.0f}")
            self.stdout.write(f"   Runway Days: {data['sustainability_days']} days")
            self.stdout.write(f"   Sustainance Date: {data['sustainability_date']}")
            
            # Status assessment
            if data['sustainability_days'] <= 0:
                status = self.style.ERROR("🔴 CRITICAL - Immediate action required")
            elif data['sustainability_days'] <= 30:
                status = self.style.WARNING("🟡 WARNING - Low sustainability")
            else:
                status = self.style.SUCCESS("🟢 HEALTHY - Good sustainability")
            
            self.stdout.write(f"\n   Status: {status}")
            
            # Get summary
            summary = get_financial_summary()
            self.stdout.write(f"\n📈 Collection Metrics:")
            self.stdout.write(f"   Collection Rate: {summary['invoices']['collection_rate']}%")
            self.stdout.write(f"   Total Collected: ₹{summary['invoices']['total_collected']:,.0f}")
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error: {e}'))