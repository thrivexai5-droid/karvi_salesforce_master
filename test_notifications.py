#!/usr/bin/env python3
"""
Test script for the automatic notification system.
This script helps you test the notification system locally.
"""

import os
import sys
import django
from datetime import datetime, timedelta

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dashboard_project.settings')
django.setup()

from django.contrib.auth.models import User
from dashboard.models import UserProfile, PurchaseOrder, Invoice, Contact, Company

def create_test_data():
    """Create test data for notification testing"""
    print("Creating test data...")
    
    # Create test admin user
    admin_user, created = User.objects.get_or_create(
        username='admin_test',
        defaults={
            'email': 'admin@test.com',
            'first_name': 'Admin',
            'last_name': 'User'
        }
    )
    if created:
        admin_profile, _ = UserProfile.objects.get_or_create(
            user=admin_user,
            defaults={'roles': 'admin'}
        )
        print(f"✓ Created admin user: {admin_user.email}")
    
    # Create test sales user
    sales_user, created = User.objects.get_or_create(
        username='sales_test',
        defaults={
            'email': 'sales@test.com',
            'first_name': 'Sales',
            'last_name': 'Person'
        }
    )
    if created:
        sales_profile, _ = UserProfile.objects.get_or_create(
            user=sales_user,
            defaults={'roles': 'sales'}
        )
        print(f"✓ Created sales user: {sales_user.email}")
    
    # Create test company first
    from dashboard.models import Company
    company, created = Company.objects.get_or_create(
        company_name='Test Company Ltd',
        city='Test City',
        defaults={
            'address': 'Test Company Address, Test City'
        }
    )
    if created:
        print(f"✓ Created test company: {company.company_name}")
    
    # Create test contact/customer
    contact, created = Contact.objects.get_or_create(
        contact_name='Test Customer',
        defaults={
            'email_1': 'customer@test.com',
            'phone_1': '1234567890',
            'individual_address': 'Test Address',
            'company': company
        }
    )
    if created:
        print(f"✓ Created test contact: {contact.contact_name}")
    
    # Create test purchase order due today
    today = datetime.now().date()
    po_today, created = PurchaseOrder.objects.get_or_create(
        po_number='TEST-PO-TODAY',
        defaults={
            'order_date': today - timedelta(days=30),
            'company': contact,
            'customer_name': 'Test Customer',
            'order_value': 50000.00,
            'days_to_mfg': 30,
            'delivery_date': today,
            'sales_person': sales_user,
        }
    )
    if created:
        print(f"✓ Created PO due today: {po_today.po_number}")
    
    # Create test purchase order overdue
    po_overdue, created = PurchaseOrder.objects.get_or_create(
        po_number='TEST-PO-OVERDUE',
        defaults={
            'order_date': today - timedelta(days=40),
            'company': contact,
            'customer_name': 'Test Customer Overdue',
            'order_value': 75000.00,
            'days_to_mfg': 30,
            'delivery_date': today - timedelta(days=5),  # 5 days overdue
            'sales_person': sales_user,
        }
    )
    if created:
        print(f"✓ Created overdue PO: {po_overdue.po_number}")
    
    print("\nTest data created successfully!")
    print(f"Admin email: {admin_user.email}")
    print(f"Sales email: {sales_user.email}")
    print(f"PO due today: {po_today.po_number}")
    print(f"Overdue PO: {po_overdue.po_number}")

def test_notification_url():
    """Test the notification URL"""
    import requests
    from django.conf import settings
    
    print("\nTesting notification URL...")
    
    # Test with wrong secret (should fail)
    try:
        response = requests.get('http://127.0.0.1:8000/automation/send-emails/?secret=wrong')
        print(f"❌ Wrong secret test: {response.status_code} - {response.json()}")
    except Exception as e:
        print(f"❌ Error testing wrong secret: {e}")
    
    # Test with correct secret (should work)
    try:
        secret_key = getattr(settings, 'CRON_SECRET_KEY', 'MySecureKey2026')
        response = requests.get(f'http://127.0.0.1:8000/automation/send-emails/?secret={secret_key}')
        print(f"✓ Correct secret test: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  Status: {data.get('status')}")
            print(f"  Actions: {len(data.get('actions', []))} notifications sent")
            for action in data.get('actions', []):
                print(f"    - {action}")
        else:
            print(f"  Response: {response.text}")
    except Exception as e:
        print(f"❌ Error testing correct secret: {e}")

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'create':
        create_test_data()
    elif len(sys.argv) > 1 and sys.argv[1] == 'test':
        test_notification_url()
    else:
        print("Usage:")
        print("  python test_notifications.py create  # Create test data")
        print("  python test_notifications.py test    # Test notification URL")
        print("\nMake sure your Django server is running before testing!")