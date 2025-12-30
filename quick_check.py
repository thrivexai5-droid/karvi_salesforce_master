#!/usr/bin/env python
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dashboard_project.settings')
django.setup()

from dashboard.models import Quotation

# Check drafts
drafts = Quotation.objects.filter(status='draft')
generated = Quotation.objects.filter(status='generated')

print(f"Drafts: {drafts.count()}")
print(f"Generated: {generated.count()}")

if drafts.exists():
    latest_draft = drafts.first()
    print(f"Latest draft: ID={latest_draft.id}, Quote={latest_draft.quote_number}")
    print(f"Fixtures: {len(latest_draft.fixtures_data) if latest_draft.fixtures_data else 0}")

if generated.exists():
    latest_generated = generated.first()
    print(f"Latest generated: ID={latest_generated.id}, Quote={latest_generated.quote_number}")