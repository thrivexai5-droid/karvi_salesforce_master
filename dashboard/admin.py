from django.contrib import admin
from .models import UserProfile, Company, Contact, PurchaseOrder, Invoice, InquiryHandler

# Register your models here.

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'get_roles_display', 'can_access_invoice_generation', 'created_at']
    list_filter = ['roles', 'can_access_invoice_generation', 'can_access_inquiry_handler']
    search_fields = ['user__username', 'user__email']

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ['company_name', 'city_1', 'city_2', 'created_at']
    list_filter = ['city_1', 'created_at']
    search_fields = ['company_name', 'city_1', 'city_2']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ['contact_name', 'company', 'location_city', 'email_1', 'phone_1', 'created_at']
    list_filter = ['location_city', 'company', 'created_at']
    search_fields = ['contact_name', 'company__company_name', 'email_1', 'phone_1']
    readonly_fields = ['location_city', 'created_at', 'updated_at']

@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ['po_number', 'company', 'customer_name', 'order_value', 'order_date', 'delivery_date', 'get_status']
    list_filter = ['order_date', 'delivery_date', 'created_at']
    search_fields = ['po_number', 'customer_name', 'company__company']
    readonly_fields = ['customer_name', 'delivery_date', 'due_days']

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ['invoice_number', 'company', 'customer_name', 'order_value', 'invoice_date', 'payment_due_date', 'get_payment_status']
    list_filter = ['invoice_date', 'grn_date', 'payment_due_date', 'created_at']
    search_fields = ['invoice_number', 'customer_name', 'company__company', 'purchase_order__po_number']
    readonly_fields = ['customer_name', 'order_value', 'payment_due_date', 'due_days']

@admin.register(InquiryHandler)
class InquiryHandlerAdmin(admin.ModelAdmin):
    list_display = ['create_id', 'opportunity_id', 'status', 'company', 'customer_name', 'quote_no', 'date_of_quote', 'ba']
    list_filter = ['status', 'date_of_quote', 'created_at']
    search_fields = ['create_id', 'opportunity_id', 'quote_no', 'customer_name', 'company__company', 'ba']
    readonly_fields = ['create_id', 'opportunity_id', 'customer_name', 'quote_no']
    ordering = ['-created_at']
