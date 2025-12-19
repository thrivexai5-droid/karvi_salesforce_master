from django.db import models
from django.contrib.auth.models import User
from datetime import datetime, timedelta
import json

class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('sales', 'Sales'),
        ('project_manager', 'Project Manager'),
        ('admin', 'Administrator'),
        ('manager', 'Manager'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    roles = models.TextField(default='sales', help_text="Comma-separated list of roles")
    
    # Form Permissions
    can_access_invoice_generation = models.BooleanField(default=False, verbose_name="Invoice Generation")
    can_access_inquiry_handler = models.BooleanField(default=False, verbose_name="Inquiry Handler")
    can_access_quotation_generation = models.BooleanField(default=False, verbose_name="Quotation Generation")
    can_access_additional_supply = models.BooleanField(default=False, verbose_name="Additional Supply")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"
    
    def get_roles_list(self):
        """Return the first role from roles field"""
        if self.roles:
            return self.roles.split(',')[0].strip()
        return 'sales'  # Default role
    
    def get_roles_display(self):
        """Return display name for the role"""
        role = self.get_roles_list()
        role_dict = dict(self.ROLE_CHOICES)
        return role_dict.get(role, role.title())
    
    def get_role_display(self):
        """Alias for get_roles_display for backward compatibility"""
        return self.get_roles_display()
    
    def get_display_password(self):
        """Generate a realistic password based on user info"""
        # Create a more realistic password pattern
        username = self.user.username
        if len(username) >= 4:
            # Use first 4 chars of username + year + special char
            return f"{username[:4].title()}2024@"
        else:
            # Short username, use full + numbers
            return f"{username.title()}123@"
    
    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"


class Company(models.Model):
    """Company model with structured locations and addresses"""
    
    # Company Name - Required and unique per city combination
    company_name = models.CharField(max_length=200, verbose_name="Company Name")
    
    # Company Locations (Cities) - Exactly two cities
    city_1 = models.CharField(max_length=100, verbose_name="Primary City")
    city_2 = models.CharField(max_length=100, verbose_name="Secondary City", blank=True, null=True)
    
    # Company Addresses - Exactly three addresses
    address_1 = models.TextField(verbose_name="Primary Address")
    address_2 = models.TextField(verbose_name="Secondary Address", blank=True, null=True)
    address_3 = models.TextField(verbose_name="Tertiary Address", blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def get_cities_display(self):
        """Return formatted cities display"""
        cities = [self.city_1]
        if self.city_2:
            cities.append(self.city_2)
        return ", ".join(cities)
    
    def get_primary_city(self):
        """Return primary city for dropdown display"""
        return self.city_1
    
    def get_addresses_list(self):
        """Return list of non-empty addresses"""
        addresses = [self.address_1]
        if self.address_2:
            addresses.append(self.address_2)
        if self.address_3:
            addresses.append(self.address_3)
        return addresses
    
    def __str__(self):
        return f"{self.company_name} – {self.city_1}"
    
    class Meta:
        verbose_name = "Company"
        verbose_name_plural = "Companies"
        ordering = ['company_name', 'city_1']
        # Ensure company name is unique per primary city
        unique_together = ['company_name', 'city_1']


class Contact(models.Model):
    """Contact model with enhanced fields and Company relationship"""
    
    # Client/Contact Name - Required
    contact_name = models.CharField(max_length=200, verbose_name="Client/Contact Name")
    
    # Email Addresses - Allow two emails
    email_1 = models.EmailField(verbose_name="Primary Email Address")
    email_2 = models.EmailField(verbose_name="Secondary Email Address", blank=True, null=True)
    
    # Phone Numbers - Allow three phone numbers
    phone_1 = models.CharField(max_length=20, verbose_name="Primary Phone Number")
    phone_2 = models.CharField(max_length=20, verbose_name="Secondary Phone Number", blank=True, null=True)
    phone_3 = models.CharField(max_length=20, verbose_name="Tertiary Phone Number", blank=True, null=True)
    
    # Company - Foreign Key relationship (dropdown only)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, verbose_name="Company")
    
    # Location (City) - Auto-fetched from selected company (read-only)
    location_city = models.CharField(max_length=100, verbose_name="Location (City)", blank=True)
    
    # Individual Address - Manual text input (separate from company address)
    individual_address = models.TextField(verbose_name="Individual Address")
    
    # Legacy fields for backward compatibility (will be migrated)
    customer_name = models.CharField(max_length=200, verbose_name="Customer Name", blank=True, null=True)
    email = models.EmailField(verbose_name="Email Address", blank=True, null=True)  # Legacy field
    plant = models.CharField(max_length=100, verbose_name="Plant Location", blank=True, null=True)
    address = models.TextField(verbose_name="Address", blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        # Auto-fetch location city from selected company
        if self.company:
            self.location_city = self.company.get_primary_city()
        
        # Maintain backward compatibility
        if not self.customer_name:
            self.customer_name = self.contact_name
        
        # Populate legacy email field for backward compatibility
        if not self.email and self.email_1:
            self.email = self.email_1
        
        super().save(*args, **kwargs)
    
    def get_emails_list(self):
        """Return list of non-empty emails"""
        emails = [self.email_1]
        if self.email_2:
            emails.append(self.email_2)
        return emails
    
    def get_phones_list(self):
        """Return list of non-empty phone numbers"""
        phones = [self.phone_1]
        if self.phone_2:
            phones.append(self.phone_2)
        if self.phone_3:
            phones.append(self.phone_3)
        return phones
    
    def get_primary_email(self):
        """Return primary email for backward compatibility"""
        return self.email_1
    
    def __str__(self):
        return f"{self.contact_name} - {self.company.company_name}"
    
    class Meta:
        verbose_name = "Contact"
        verbose_name_plural = "Contacts"
        ordering = ['-created_at']


class PurchaseOrder(models.Model):
    
    po_number = models.CharField(max_length=50, unique=True, verbose_name="PO Number")
    
 
    order_date = models.DateField(verbose_name="Order Date")
    
 
    company = models.ForeignKey(Contact, on_delete=models.CASCADE, verbose_name="Company", related_name='purchase_orders')
    
    # 4. Customer (auto-fetch based on company selection)
    customer_name = models.CharField(max_length=200, verbose_name="Customer Name")
    
     
    order_value = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Order Value")
    
     
    days_to_mfg = models.PositiveIntegerField(verbose_name="Days to Manufacturing")
    
 
    delivery_date = models.DateField(verbose_name="Delivery Date", blank=True, null=True)
    
    
    due_days = models.IntegerField(verbose_name="Due Days", blank=True, null=True, help_text="Positive: days remaining, Negative: days overdue")
    
     
    remarks = models.TextField(blank=True, null=True, verbose_name="Remarks")
    
    
    sales_person = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='sales_orders',
        limit_choices_to={'userprofile__roles__contains': 'sales'},
        verbose_name="Sales Person"
    )
    
    # Sales Person Percentage
    sales_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        null=True, 
        blank=True,
        verbose_name="Sales Percentage (%)",
        help_text="Enter percentage (e.g., 5.50 for 5.5%)"
    )
    
     
    project_manager = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='managed_orders',
        limit_choices_to={'userprofile__roles__contains': 'project_manager'},
        verbose_name="Project Manager"
    )
    
    # Project Manager Percentage
    project_manager_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        null=True, 
        blank=True,
        verbose_name="Project Manager Percentage (%)",
        help_text="Enter percentage (e.g., 3.25 for 3.25%)"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        # Auto-calculate delivery date
        if self.order_date and self.days_to_mfg:
            self.delivery_date = self.order_date + timedelta(days=self.days_to_mfg)
        
        # Auto-calculate due days
        if self.delivery_date:
            self.due_days = self.calculate_due_days()
        
        # Auto-fetch customer name from selected company
        if self.company:
            self.customer_name = self.company.customer_name
            
        super().save(*args, **kwargs)
    
    def calculate_due_days(self):
        """
        Calculate the number of days remaining (or past due) for an order.
        Returns: Integer representing days remaining (positive) or past due (negative)
        """
        if not self.delivery_date:
            return None
            
        # Standardize today's date to midnight for accurate day counting
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).date()
        
        # Calculate the difference
        time_difference = self.delivery_date - today
        return time_difference.days
    
    def get_status(self):
        """Get order status based on due days"""
        if self.due_days is None:
            return "Unknown"
        elif self.due_days > 7:
            return "On Track"
        elif self.due_days > 0:
            return "Due Soon"
        elif self.due_days == 0:
            return "Due Today"
        else:
            return "Overdue"
    
    def get_status_class(self):
        """Get CSS class for status display"""
        status = self.get_status()
        if status == "On Track":
            return "success"
        elif status == "Due Soon":
            return "warning"
        elif status == "Due Today":
            return "info"
        elif status == "Overdue":
            return "danger"
        else:
            return "secondary"
    
    def get_due_days_display(self):
        """Get formatted due days display text"""
        if self.due_days is None:
            return "Unknown"
        elif self.due_days > 0:
            return f"{self.due_days} days left"
        elif self.due_days == 0:
            return "Due today"
        else:
            return f"{abs(self.due_days)} days overdue"
    
    def __str__(self):
        return f"PO-{self.po_number} - {self.company.company} - {self.customer_name}"
    
    class Meta:
        verbose_name = "Purchase Order"
        verbose_name_plural = "Purchase Orders"
        ordering = ['-created_at']


class Invoice(models.Model):
    # Invoice Number - Manual Entry
    invoice_number = models.CharField(
        max_length=50, 
        unique=True, 
        verbose_name="Invoice Number",
        help_text="Enter invoice number manually"
    )
    
    # Invoice Date - Manual Entry
    invoice_date = models.DateField(
        verbose_name="Invoice Date",
        help_text="Enter invoice date manually"
    )
    
    # Company - Dropdown select from database
    company = models.ForeignKey(
        Contact, 
        on_delete=models.CASCADE, 
        verbose_name="Company",
        related_name='invoices',
        help_text="Select company from database"
    )
    
    # Customer - Auto-fetch based on company selection
    customer_name = models.CharField(
        max_length=200, 
        verbose_name="Customer Name",
        help_text="Auto-fetched based on client selection",
        blank=True  # Allow blank since it's auto-filled
    )
    
    # Value - Auto-fetch from PurchaseOrder based on client and customer
    purchase_order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.CASCADE,
        verbose_name="Purchase Order",
        help_text="Select purchase order to auto-fetch value"
    )
    
    # Order Value - Auto-fetched from selected PurchaseOrder
    order_value = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        verbose_name="Order Value",
        help_text="Auto-fetched from selected purchase order",
        null=True,  # Allow null since it's auto-filled
        blank=True  # Allow blank since it's auto-filled
    )
    
    # GRN Date - Manual Entry
    grn_date = models.DateField(
        verbose_name="GRN Date",
        help_text="Enter GRN date manually"
    )
    
    # Payment Due Date - Auto-calculated (GRN Date + 15 days)
    payment_due_date = models.DateField(
        verbose_name="Payment Due Date",
        help_text="Auto-calculated: GRN Date + 15 days",
        null=True,  # Allow null since it's auto-calculated
        blank=True  # Allow blank since it's auto-calculated
    )
    
    # Due Days - Auto-calculated (number of days from today to payment due date)
    due_days = models.IntegerField(
        verbose_name="Due Days",
        help_text="Auto-calculated: days remaining (positive) or overdue (negative)",
        null=True,  # Allow null since it's auto-calculated
        blank=True  # Allow blank since it's auto-calculated
    )
    
    # Remarks - Manual Entry
    remarks = models.TextField(
        blank=True, 
        null=True, 
        verbose_name="Remarks",
        help_text="Enter remarks manually (optional)"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        # Auto-fetch customer name from selected company
        if self.company:
            self.customer_name = self.company.customer_name
        
        # Auto-fetch order value from selected purchase order
        if self.purchase_order:
            self.order_value = self.purchase_order.order_value
        
        # Auto-calculate payment due date (GRN Date + 15 days)
        if self.grn_date:
            self.payment_due_date = self.grn_date + timedelta(days=15)
        
        # Auto-calculate due days
        if self.payment_due_date:
            self.due_days = self.calculate_due_days()
        
        super().save(*args, **kwargs)
    
    def calculate_due_days(self):
        """
        Calculate the number of days remaining (or past due) for payment.
        Returns: Integer representing days remaining (positive) or past due (negative)
        """
        if not self.payment_due_date:
            return None
            
        # Standardize today's date to midnight for accurate day counting
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).date()
        
        # Calculate the difference
        time_difference = self.payment_due_date - today
        return time_difference.days
    
    def get_payment_status(self):
        """Get payment status based on due days"""
        if self.due_days is None:
            return "Unknown"
        elif self.due_days > 7:
            return "Not Due"
        elif self.due_days > 0:
            return "Due Soon"
        elif self.due_days == 0:
            return "Due Today"
        else:
            return "Overdue"
    
    def get_status_class(self):
        """Get CSS class for status display"""
        status = self.get_payment_status()
        if status == "Not Due":
            return "success"
        elif status == "Due Soon":
            return "warning"
        elif status == "Due Today":
            return "info"
        elif status == "Overdue":
            return "danger"
        else:
            return "secondary"
    
    def get_due_days_display(self):
        """Get formatted due days display text"""
        if self.due_days is None:
            return "Unknown"
        elif self.due_days > 0:
            return f"{self.due_days} days left"
        elif self.due_days == 0:
            return "Due today"
        else:
            return f"{abs(self.due_days)} days overdue"
    
    def __str__(self):
        return f"INV-{self.invoice_number} - {self.company.company} - {self.customer_name}"
    
    class Meta:
        verbose_name = "Invoice"
        verbose_name_plural = "Invoices"
        ordering = ['-created_at']


class InquiryHandler(models.Model):
    """Inquiry Handler model with auto-generated IDs and status-based Opportunity IDs"""
    
    # Status choices as per your requirements
    STATUS_CHOICES = [
        # Early Stage (prefix: e) - Reordered sequence
        ('Enquiry', 'Enquiry'),
        ('Inputs', 'Inputs'),
        ('Inspection', 'Inspection'),
        ('Enquiry Hold', 'Enquiry Hold'),
        ('Pending', 'Pending'),
        ('Quotation', 'Quotation'),
        ('Negotiation', 'Negotiation'),
        ('PO-Confirm', 'PO-Confirm'),
        ('PO Hold', 'PO Hold'),
        ('Design', 'Design'),
        ('Design Review', 'Design Review'), 
        ('Material Receive', 'Material Receive'),
        ('Manufacturing', 'Manufacturing'),
        ('Stage-Inspection', 'Stage-Inspection'),
        ('Approval', 'Approval'),
        ('Dispatch', 'Dispatch'),
        ('GRN', 'GRN'),
        ('Project Closed', 'Project Closed'),
        ('Lost', 'Lost'),
    ]
    
    # 1. Create ID - Auto-generated with function
    create_id = models.CharField(
        max_length=15,
        unique=True,
        verbose_name="Create ID",
        help_text="Auto-generated ID (e.g., KEC020JY2025)",
        blank=True
    )
    
    # 2. Status - Dropdown selection
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='Inputs',
        verbose_name="Status",
        help_text="Select current status"
    )
    
    # 3. Opportunity ID - Auto-generated based on status and create_id
    opportunity_id = models.CharField(
        max_length=20,
        verbose_name="Opportunity ID",
        help_text="Auto-generated based on status (e.g., eKEC020JY2025)",
        blank=True
    )
    
    # 4. Lead Description - Manual entry
    lead_description = models.TextField(
        verbose_name="Lead Description",
        help_text="Enter lead description manually"
    )
    
    # 5. Company - Dropdown select from database
    company = models.ForeignKey(
        Contact,
        on_delete=models.CASCADE,
        verbose_name="Company",
        related_name='inquiries',
        help_text="Select company from database"
    )
    
    # 6. Customer - Auto-fetch based on company selection
    customer_name = models.CharField(
        max_length=200,
        verbose_name="Customer Name",
        help_text="Auto-fetched based on company selection",
        blank=True
    )
    
    # 7. Quote No - Same as Create ID
    quote_no = models.CharField(
        max_length=15,
        verbose_name="Quote Number",
        help_text="Same as Create ID (e.g., KEC020JY2025)",
        blank=True
    )
    
    # 8. Date of Quote - Manual entry
    date_of_quote = models.DateField(
        verbose_name="Date of Quote",
        help_text="Enter quote date manually"
    )
    
    # 9. Remarks - Manual entry
    remarks = models.TextField(
        blank=True,
        null=True,
        verbose_name="Remarks",
        help_text="Enter remarks manually (optional)"
    )
    
    # 10. BA - Manual entry (kept for backward compatibility)
    ba = models.CharField(
        max_length=100,
        verbose_name="BA (Business Analyst)",
        help_text="Enter BA name manually",
        blank=True,
        null=True
    )
    
    # 10a. Sales - Dropdown selection (replaces BA in form)
    sales = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={'userprofile__roles__contains': 'sales'},
        verbose_name="Sales Person",
        help_text="Select sales person from database"
    )
    
    # 10b. Next Date - Manual entry (new field)
    next_date = models.DateField(
        blank=True,
        null=True,
        verbose_name="Next Date",
        help_text="Enter next date manually (optional)"
    )
    
    # 11. Additional Supply Remarks - Manual entry (for Additional Supply page)
    remarks_add = models.TextField(
        blank=True,
        null=True,
        verbose_name="Additional Supply Remarks",
        help_text="Enter additional supply remarks manually (optional)"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        # Auto-generate Create ID if not exists
        if not self.create_id:
            self.create_id = self.generate_create_id()
        
        # Auto-fetch customer name from selected company
        if self.company:
            self.customer_name = self.company.customer_name
        
        # Auto-generate Opportunity ID based on status
        self.opportunity_id = self.generate_opportunity_id()
        
        # Set Quote Number to be the same as Create ID
        self.quote_no = self.create_id
        
        super().save(*args, **kwargs)
    
    def generate_create_id(self):
        """Generate Create ID: KEC + serial + month + year (e.g., KEC020JY2025)"""
        from datetime import datetime
        
        # Get current date
        now = datetime.now()
        month_abbr = now.strftime('%b').upper()[:2]  # JA, FE, MR, AP, MY, JN, JY, AU, SE, OC, NO, DE
        year = now.year
        
        # Get next serial number for this month/year
        prefix = f"KEC"
        month_year = f"{month_abbr}{year}"
        
        # Find highest serial number for current month/year
        existing_ids = InquiryHandler.objects.filter(
            create_id__startswith=prefix,
            create_id__endswith=month_year
        ).values_list('create_id', flat=True)
        
        # Extract serial numbers
        serial_numbers = []
        for create_id in existing_ids:
            try:
                # Extract serial from KEC020JY2025 -> 020
                serial_part = create_id[3:-6]  # Remove KEC and JY2025
                serial_numbers.append(int(serial_part))
            except (ValueError, IndexError):
                continue
        
        # Get next serial number
        next_serial = max(serial_numbers, default=0) + 1
        serial_str = f"{next_serial:03d}"  # 001, 002, 003, etc.
        
        return f"{prefix}{serial_str}{month_year}"
    
    def generate_opportunity_id(self):
        """Generate Opportunity ID based on status and create_id"""
        if not self.create_id:
            return ""
        
        # Status mapping to prefixes
        status_prefix_map = {
            
            
            # Order Stage (prefix: o)
            'Enquiry Hold': 'o',
            'PO-Confirm': 'o',
            'Design Review': 'o',
            'Manufacturing': 'o',
            # Early Stage (prefix: e)
            'Inputs': 'e',
            'Pending': 'e',
            'Inspection': 'e',
            'Enquiry': 'e',
            'Quotation': 'e',
            'Negotiation': 'e',
            
            # Invoice Stage (prefix: i)
            'Stage-Inspection': 'i',
            'Dispatch': 'i',
            'GRN': 'i',
            'Project Closed': 'i',
            
            # Special cases
            'Lost': 'LOST',
            'PO Hold': 'HOLD',
            'Design': 'DESIGN',
            'Material Receive': 'MATERIAL',
            'Approval': 'APPROVAL',
        }
        
        prefix = status_prefix_map.get(self.status, 'UNKNOWN')
        
        if prefix in ['LOST', 'HOLD', 'DESIGN', 'MATERIAL', 'APPROVAL', 'UNKNOWN']:
            return prefix
        else:
            return f"{prefix}{self.create_id}"
    

    
    def get_status_class(self):
        """Get CSS class for status display"""
        status_classes = {
            'Enquiry': 'primary',
            'Pending': 'warning',
            'Inspection': 'info',
            'Inputs': 'secondary',
            'Quotation': 'success',
            'Negotiation': 'warning',
            'Enquiry Hold': 'warning',
            'PO-Confirm': 'success',
            'Design Review': 'info',
            'Manufacturing': 'primary',
            'Stage-Inspection': 'info',
            'Dispatch': 'success',
            'GRN': 'success',
            'Project Closed': 'success',
            'Lost': 'danger',
            'PO Hold': 'warning',
            'Design': 'info',
            'Material Receive': 'primary',
            'Approval': 'warning',
        }
        return status_classes.get(self.status, 'secondary')
    
    def __str__(self):
        return f"{self.create_id} - {self.opportunity_id} - {self.company.company}"
    
    class Meta:
        verbose_name = "Inquiry Handler"
        verbose_name_plural = "Inquiry Handlers"
        ordering = ['-created_at']


class InquiryItem(models.Model):
    """Inquiry Item model for storing individual items in an inquiry"""
    
    inquiry = models.ForeignKey(
        InquiryHandler,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name="Inquiry"
    )
    
    item_name = models.CharField(
        max_length=200,
        verbose_name="Item Name",
        help_text="Enter item name manually"
    )
    
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Quantity",
        help_text="Enter quantity"
    )
    
    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Price",
        help_text="Enter price per unit"
    )
    
    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name="Amount",
        help_text="Auto-calculated: Quantity × Price",
        editable=False
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        # Auto-calculate amount
        self.amount = self.quantity * self.price
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.item_name} - Qty: {self.quantity} - ₹{self.amount}"
    
    class Meta:
        verbose_name = "Inquiry Item"
        verbose_name_plural = "Inquiry Items"
        ordering = ['id']