from django.contrib import admin
from .models import UserProfile, Company, Contact, PurchaseOrder, PurchaseOrderItem, Invoice, InquiryHandler

# Register your models here.

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'get_roles_display', 'can_access_invoice_generation', 'created_at']
    list_filter = ['roles', 'can_access_invoice_generation', 'can_access_inquiry_handler']
    search_fields = ['user__username', 'user__email']

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ['company_name', 'city', 'created_at']
    list_filter = ['city', 'created_at']
    search_fields = ['company_name', 'city']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ['customer_name', 'company', 'location_city', 'email', 'phone', 'created_at']
    list_filter = ['location_city', 'company', 'created_at']
    search_fields = ['customer_name', 'company__company_name', 'email', 'phone']
    readonly_fields = ['location_city', 'created_at', 'updated_at']

class PurchaseOrderItemInline(admin.TabularInline):
    model = PurchaseOrderItem
    extra = 1
    readonly_fields = ['amount']

@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'po_number', 'company', 'customer_name', 'order_value', 'order_date', 'delivery_date', 'payment_terms_display', 'get_status']
    list_filter = ['order_date', 'delivery_date', 'payment_terms', 'created_at']
    search_fields = ['po_number', 'customer_name', 'company__customer_name']
    readonly_fields = ['customer_name', 'delivery_date', 'due_days']
    inlines = [PurchaseOrderItemInline]
    
    def payment_terms_display(self, obj):
        return f"{obj.payment_terms} days" if obj.payment_terms else "-"
    payment_terms_display.short_description = "Payment Terms"
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('po_number', 'order_date', 'company', 'customer_name')
        }),
        ('Order Details', {
            'fields': ('order_value', 'days_to_mfg', 'delivery_date', 'due_days')
        }),
        ('Additional Information', {
            'fields': ('remarks', 'payment_terms')
        }),
        ('Team Assignment', {
            'fields': ('sales_person', 'sales_percentage', 'project_manager', 'project_manager_percentage')
        }),
    )

@admin.register(PurchaseOrderItem)
class PurchaseOrderItemAdmin(admin.ModelAdmin):
    list_display = ['purchase_order', 'material_code', 'item_name', 'quantity', 'price', 'amount', 'created_at']
    list_filter = ['created_at', 'purchase_order__order_date']
    search_fields = ['item_name', 'material_code', 'purchase_order__po_number']
    readonly_fields = ['amount']

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ['invoice_number', 'company', 'customer_name', 'order_value', 'invoice_date', 'payment_due_date', 'get_payment_status']
    list_filter = ['invoice_date', 'grn_date', 'payment_due_date', 'created_at']
    search_fields = ['invoice_number', 'customer_name', 'company__customer_name', 'purchase_order__po_number']
    readonly_fields = ['customer_name', 'order_value', 'payment_due_date', 'due_days']

@admin.register(InquiryHandler)
class InquiryHandlerAdmin(admin.ModelAdmin):
    list_display = ['create_id', 'opportunity_id', 'status', 'company', 'customer_name', 'quote_no', 'date_of_quote', 'sales']
    list_filter = ['status', 'date_of_quote', 'created_at']
    search_fields = ['create_id', 'opportunity_id', 'quote_no', 'customer_name', 'company__company_name', 'sales__username']
    readonly_fields = ['create_id', 'opportunity_id', 'customer_name', 'quote_no']
    ordering = ['-year_month_order', '-serial_number']
