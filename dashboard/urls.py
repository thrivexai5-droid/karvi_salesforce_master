from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard_view, name='index'),
    path('register/', views.register_view, name='register'),
    path('users/', views.user_management_view, name='user_management'),
    path('users/create/', views.user_create_view, name='user_create'),
    path('users/edit/<int:user_id>/', views.user_edit_view, name='user_edit'),
    path('users/delete/<int:user_id>/', views.user_delete_view, name='user_delete'),
    
    # Contact Management URLs
    path('contacts/', views.contact_management_view, name='contact_management'),
    path('contacts/create/', views.contact_create_view, name='contact_create'),
    path('contacts/edit/<int:contact_id>/', views.contact_edit_view, name='contact_edit'),
    path('contacts/delete/<int:contact_id>/', views.contact_delete_view, name='contact_delete'),
    
    # Company Management URLs
    path('companies/create/', views.company_create_view, name='company_create'),
    path('companies/edit/<int:company_id>/', views.company_edit_view, name='company_edit'),
    path('companies/delete/<int:company_id>/', views.company_delete_view, name='company_delete'),
    # Purchase Order Management URLs
    path('purchase-orders/', views.purchase_order_management_view, name='purchase_order_management'),
    path('purchase-orders/create/', views.purchase_order_create_view, name='purchase_order_create'),
    path('purchase-orders/edit/<int:order_id>/', views.purchase_order_edit_view, name='purchase_order_edit'),
    path('purchase-orders/delete/<int:order_id>/', views.purchase_order_delete_view, name='purchase_order_delete'),
    path('purchase-orders/export-excel/', views.export_purchase_orders_excel, name='export_purchase_orders_excel'),
    # Invoice Management URLs
    path('invoices/', views.invoice_management_view, name='invoice_management'),
    path('invoices/create/', views.invoice_create_view, name='invoice_create'),
    path('invoices/edit/<int:invoice_id>/', views.invoice_edit_view, name='invoice_edit'),
    path('invoices/delete/<int:invoice_id>/', views.invoice_delete_view, name='invoice_delete'),
    
    # Inquiry Handler Management URLs
    path('inquiry-handler/', views.inquiry_handler_management_view, name='inquiry_handler_management'),
    path('inquiry-handler/create/', views.inquiry_handler_create_view, name='inquiry_handler_create'),
    path('inquiry-handler/edit/<int:inquiry_id>/', views.inquiry_handler_edit_view, name='inquiry_handler_edit'),
    path('inquiry-handler/delete/<int:inquiry_id>/', views.inquiry_handler_delete_view, name='inquiry_handler_delete'),
    
    # Additional Supply Management URLs
    path('additional-supply/', views.additional_supply_management_view, name='additional_supply_management'),
    path('additional-supply/create/', views.additional_supply_create_view, name='additional_supply_create'),
    path('additional-supply/edit/<int:supply_id>/', views.additional_supply_edit_view, name='additional_supply_edit'),
    path('additional-supply/edit-by-invoice/<int:invoice_id>/', views.additional_supply_edit_by_invoice_view, name='additional_supply_edit_by_invoice'),
    path('additional-supply/delete/<int:supply_id>/', views.additional_supply_delete_view, name='additional_supply_delete'),
    path('additional-supply/delete-by-invoice/<int:invoice_id>/', views.additional_supply_delete_by_invoice_view, name='additional_supply_delete_by_invoice'),
    
    # Quotation Management URLs
    path('quotation/', views.quotation_view, name='quotation_generator'),
    path('quotation/generate/', views.generate_quotation, name='generate_quotation'),
    path('quotation/save-draft/', views.save_quotation_draft, name='save_quotation_draft'),
    path('quotation/management/', views.quotation_management_view, name='quotation_management'),
    path('quotation/edit/<int:quotation_id>/', views.quotation_edit, name='quotation_edit'),
    path('quotation/download/<int:quotation_id>/', views.quotation_download, name='quotation_download'),
    path('quotation/download-file/', views.quotation_download_file, name='quotation_download_file'),
    
    # AJAX endpoints
    path('ajax/get-company-data/', views.get_company_data_ajax, name='get_company_data_ajax'),
    path('ajax/get-contact-data/', views.get_contact_data_ajax, name='get_contact_data_ajax'),
    path('ajax/get-purchase-orders-by-contact/', views.get_purchase_orders_by_contact_ajax, name='get_purchase_orders_by_contact_ajax'),
    path('ajax/get-purchase-order-details/', views.get_purchase_order_details_ajax, name='get_purchase_order_details_ajax'),
    path('ajax/get-invoice-details/', views.get_invoice_details_ajax, name='get_invoice_details_ajax'),
    path('ajax/save-inquiry-items/', views.save_inquiry_items_ajax, name='save_inquiry_items_ajax'),
    path('ajax/get-inquiry-items/', views.get_inquiry_items_ajax, name='get_inquiry_items_ajax'),
    path('ajax/process-po-pdf/', views.process_po_pdf_ajax, name='process_po_pdf_ajax'),
    path('upload-po-ajax/', views.upload_po_ajax, name='upload_po_ajax'),
    path('ajax/save-purchase-order-items/', views.save_purchase_order_items_ajax, name='save_purchase_order_items_ajax'),
    path('ajax/get-purchase-order-items/', views.get_purchase_order_items_ajax, name='get_purchase_order_items_ajax'),
    path('ajax/search-customers/', views.search_customers_ajax, name='search_customers_ajax'),
    path('ajax/fetch-quotation-data/', views.fetch_quotation_data_ajax, name='fetch_quotation_data_ajax'),
]