from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from django import forms
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.db import models
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime
import json
import base64
from .models import UserProfile, Company, Contact, PurchaseOrder, PurchaseOrderItem, Invoice, InquiryHandler, InquiryItem, Quotation
from .password_storage import password_storage

# Import Mistral AI for PDF processing
try:
    from mistralai import Mistral
    MISTRAL_AVAILABLE = True
except ImportError:
    MISTRAL_AVAILABLE = False

@login_required
@csrf_exempt
def upload_po_ajax(request):
    """AJAX endpoint that receives the PDF, calls the AI service, and returns JSON data to the frontend."""
    if request.method == 'POST' and request.FILES.get('po_file'):
        try:
            # Import the service function
            from .services import extract_po_data_from_pdf
            
            # Call the service
            extracted_data = extract_po_data_from_pdf(request.FILES['po_file'])
            
            # Log extracted data for debugging (optional)
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Extracted PO data: {extracted_data}")
            
            return JsonResponse({'success': True, 'data': extracted_data})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'No file provided.'})

@login_required
@csrf_exempt
def save_purchase_order_items_ajax(request):
    """AJAX endpoint to save purchase order items"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            purchase_order_id = data.get('purchase_order_id')
            items_data = data.get('items', [])
            
            if not purchase_order_id:
                return JsonResponse({'success': False, 'error': 'Purchase order ID is required'})
            
            # Get the purchase order
            try:
                purchase_order = PurchaseOrder.objects.get(id=purchase_order_id)
            except PurchaseOrder.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Purchase order not found'})
            
            # Clear existing items
            purchase_order.items.all().delete()
            
            # Add new items
            total_amount = 0
            for item_data in items_data:
                if item_data.get('item_name') and item_data.get('quantity') and item_data.get('price'):
                    # Extract material code from item name if it's in [CODE] format
                    item_name = item_data['item_name']
                    material_code = ''
                    
                    if item_name.startswith('[') and ']' in item_name:
                        parts = item_name.split(']', 1)
                        material_code = parts[0][1:]  # Remove the opening bracket
                        item_name = parts[1].strip() if len(parts) > 1 else item_name
                    
                    item = PurchaseOrderItem.objects.create(
                        purchase_order=purchase_order,
                        material_code=material_code,
                        item_name=item_name,
                        quantity=float(item_data['quantity']),
                        price=float(item_data['price'])
                    )
                    total_amount += float(item.amount)
            
            # Update purchase order total value
            purchase_order.order_value = total_amount
            purchase_order.save()
            
            return JsonResponse({
                'success': True,
                'total_amount': total_amount,
                'message': f'Saved {len(items_data)} items successfully'
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@login_required
def get_purchase_order_items_ajax(request):
    """AJAX endpoint to get purchase order items"""
    purchase_order_id = request.GET.get('purchase_order_id')
    
    print(f"DEBUG: get_purchase_order_items_ajax called with PO ID: {purchase_order_id}")
    
    if not purchase_order_id:
        return JsonResponse({'success': False, 'error': 'Purchase order ID is required'})
    
    try:
        purchase_order = PurchaseOrder.objects.get(id=purchase_order_id)
        items = purchase_order.items.all()
        
        print(f"DEBUG: Found {items.count()} items for PO {purchase_order.po_number}")
        
        items_data = []
        total_amount = 0
        
        for item in items:
            # Combine material code and item name for display
            display_name = item.item_name
            if hasattr(item, 'material_code') and item.material_code:
                display_name = f"[{item.material_code}] {item.item_name}"
            
            item_data = {
                'id': item.id,
                'item_name': display_name,
                'quantity': str(item.quantity),
                'price': str(item.price),
                'amount': str(item.amount)
            }
            items_data.append(item_data)
            total_amount += float(item.amount)
            print(f"DEBUG: Item data: {item_data}")
        
        response_data = {
            'success': True,
            'items': items_data,
            'total_amount': total_amount
        }
        print(f"DEBUG: Returning response: {response_data}")
        return JsonResponse(response_data)
        
    except PurchaseOrder.DoesNotExist:
        print(f"DEBUG: Purchase order {purchase_order_id} not found")
        return JsonResponse({'success': False, 'error': 'Purchase order not found'})
    except Exception as e:
        print(f"DEBUG: Error in get_purchase_order_items_ajax: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def search_customers_ajax(request):
    """AJAX endpoint to search customers for autocomplete"""
    query = request.GET.get('q', '').strip()
    
    if len(query) < 2:  # Require at least 2 characters
        return JsonResponse({'success': True, 'customers': []})
    
    try:
        # Search in customer_name and contact_name fields
        customers = Contact.objects.filter(
            models.Q(customer_name__icontains=query) |
            models.Q(contact_name__icontains=query)
        ).select_related('company').order_by('customer_name')[:10]  # Limit to 10 results
        
        customers_data = []
        for customer in customers:
            customers_data.append({
                'id': customer.id,
                'customer_name': customer.customer_name,
                'contact_name': customer.contact_name,
                'company_name': customer.company.company_name if customer.company else '',
                'display_text': f"{customer.customer_name} - {customer.company.company_name if customer.company else 'No Company'}"
            })
        
        return JsonResponse({
            'success': True,
            'customers': customers_data
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    
    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user

class UserManagementForm(forms.Form):
    # Basic Information
    name = forms.CharField(
        max_length=100, 
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter full name'})
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter email address'})
    )
    password = forms.CharField(
        min_length=8,
        required=True,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter password'})
    )
    
    # Role Selection
    ROLE_CHOICES = [
        ('sales', 'Sales'),
        ('project_manager', 'Project Manager'),
    ]
    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    # Form Permissions - Multiple Select
    FORM_CHOICES = [
        ('invoice_generation', 'Invoice Generation'),
        ('inquiry_handler', 'Inquiry Handler'),
        ('quotation_generation', 'Quotation Generation'),
        ('additional_supply', 'Additional Supply'),
    ]
    
    form_permissions = forms.MultipleChoiceField(
        choices=FORM_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        help_text="Select multiple forms this user can access"
    )
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("A user with this email already exists.")
        return email
    
    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get('role')
        form_permissions = cleaned_data.get('form_permissions', [])
        
        # Role-based permission validation
        if role == 'project_manager' and form_permissions:
            invalid_perms = [perm for perm in form_permissions if perm != 'additional_supply']
            if invalid_perms:
                raise forms.ValidationError("Project Managers can only access Additional Supply.")
        
        if role == 'sales' and form_permissions:
            allowed_perms = ['invoice_generation', 'inquiry_handler', 'quotation_generation']
            invalid_perms = [perm for perm in form_permissions if perm not in allowed_perms]
            if invalid_perms:
                raise forms.ValidationError("Sales users can only access Invoice Generation, Inquiry Handler, or Quotation Generation.")
        
        return cleaned_data

class UserEditForm(forms.Form):
    # Basic Information
    name = forms.CharField(
        max_length=100, 
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter full name'})
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter email address'})
    )
    password = forms.CharField(
        min_length=8,
        required=False,  # Optional for edit
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Leave blank to keep current password'})
    )
    
    # Role Selection
    ROLE_CHOICES = [
        ('sales', 'Sales'),
        ('project_manager', 'Project Manager'),
    ]
    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    # Form Permissions - Multiple Select
    FORM_CHOICES = [
        ('invoice_generation', 'Invoice Generation'),
        ('inquiry_handler', 'Inquiry Handler'),
        ('quotation_generation', 'Quotation Generation'),
        ('additional_supply', 'Additional Supply'),
    ]
    
    form_permissions = forms.MultipleChoiceField(
        choices=FORM_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        help_text="Select multiple forms this user can access"
    )
    
    def __init__(self, *args, **kwargs):
        self.user_instance = kwargs.pop('user_instance', None)
        super().__init__(*args, **kwargs)
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if self.user_instance and User.objects.filter(email=email).exclude(id=self.user_instance.id).exists():
            raise forms.ValidationError("A user with this email already exists.")
        elif not self.user_instance and User.objects.filter(email=email).exists():
            raise forms.ValidationError("A user with this email already exists.")
        return email
    
    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get('role')
        form_permissions = cleaned_data.get('form_permissions', [])
        
        # Role-based permission validation
        if role == 'project_manager' and form_permissions:
            invalid_perms = [perm for perm in form_permissions if perm != 'additional_supply']
            if invalid_perms:
                raise forms.ValidationError("Project Managers can only access Additional Supply.")
        
        if role == 'sales' and form_permissions:
            allowed_perms = ['invoice_generation', 'inquiry_handler', 'quotation_generation']
            invalid_perms = [perm for perm in form_permissions if perm not in allowed_perms]
            if invalid_perms:
                raise forms.ValidationError("Sales users can only access Invoice Generation, Inquiry Handler, or Quotation Generation.")
        
        return cleaned_data

@login_required
def dashboard_view(request):
    """Main dashboard view - requires authentication"""
    from decimal import Decimal
    from django.db.models import Count, Case, When, IntegerField, Max
    from datetime import datetime
    
    # Calculate dynamic values from Invoice model
    total_value_result = Invoice.objects.aggregate(total=Sum('order_value'))
    total_value = total_value_result['total'] or Decimal('0')
    
    # Calculate GST as 18% of Total Value (using Decimal for precision)
    gst_rate = Decimal('0.18')
    gst_value = total_value * gst_rate
    
    # Calculate Max Date - Latest date from invoices and inquiries
    max_invoice_date = Invoice.objects.aggregate(max_date=Max('invoice_date'))['max_date']
    max_inquiry_date = InquiryHandler.objects.aggregate(max_date=Max('date_of_quote'))['max_date']
    max_po_date = PurchaseOrder.objects.aggregate(max_date=Max('order_date'))['max_date']
    
    # Find the latest date among all sources
    dates_list = [d for d in [max_invoice_date, max_inquiry_date, max_po_date] if d is not None]
    max_date = max(dates_list) if dates_list else None
    
    # Format max date for display (DD-MM-YYYY)
    max_date_formatted = max_date.strftime('%d-%m-%Y') if max_date else '—'
    
    # Calculate Sustainance Date - Using the latest created_at date as system-defined date
    from django.utils import timezone
    
    # Get timezone-aware datetime.min for comparison
    timezone_aware_min = timezone.make_aware(datetime.min) if timezone.is_naive(datetime.min) else datetime.min
    
    max_created_date = max(
        Invoice.objects.aggregate(max_created=Max('created_at'))['max_created'] or timezone_aware_min,
        InquiryHandler.objects.aggregate(max_created=Max('created_at'))['max_created'] or timezone_aware_min,
        PurchaseOrder.objects.aggregate(max_created=Max('created_at'))['max_created'] or timezone_aware_min
    )
    
    # Format sustainance date for display (DD-MM-YYYY)
    sustainance_date_formatted = max_created_date.strftime('%d-%m-%Y') if max_created_date != timezone_aware_min else '—'
    
    # Format values for display (Indian number format)
    def format_indian_currency(amount):
        """Format number in Indian currency style (e.g., 4,21,50,000)"""
        if amount == 0:
            return "0"
        
        # Convert to float for formatting, then back to string
        amount_float = float(amount)
        amount_str = f"{amount_float:,.0f}"  # No decimal places for currency display
        
        return amount_str
    
    # Get dynamic inquiry status data for Leads chart
    def get_inquiry_status_data():
        """Fetch inquiry counts by status for Leads chart"""
        import json
        
        # Define the exact statuses to include in the chart (as per requirements)
        chart_statuses = [
            'Inputs', 'Pending', 'Inspection', 'Enquiry', 'Quotation', 'Negotiation',
            'Enquiry Hold', 'PO-Confirm', 'Design Review', 'Manufacturing',
            'Stage-Inspection', 'Dispatch', 'GRN', 'Project Closed', 'Lost', 'PO Hold'
        ]
        
        # Get counts for each status using a single optimized query
        status_counts = InquiryHandler.objects.aggregate(
            **{
                status.lower().replace('-', '_').replace(' ', '_'): Count(
                    Case(When(status=status, then=1), output_field=IntegerField())
                )
                for status in chart_statuses
            }
        )
        
        # Format data for chart consumption
        data_values = [status_counts.get(status.lower().replace('-', '_').replace(' ', '_'), 0) for status in chart_statuses]
        
        chart_data = {
            'categories': json.dumps(chart_statuses),
            'data': json.dumps(data_values)
        }
        
        return chart_data
    
    # Get inquiry status data
    inquiry_chart_data = get_inquiry_status_data()
    
    context = {
        'max_date': max_date_formatted,
        'sustainance_date': sustainance_date_formatted,
        'total_value': format_indian_currency(total_value),
        'gst_value': format_indian_currency(gst_value),
        'total_value_raw': total_value,
        'gst_value_raw': gst_value,
        'inquiry_chart_data': inquiry_chart_data,
    }
    
    return render(request, 'dashboard/index.html', context)

@login_required
def user_management_view(request):
    """User management page with list of users"""
    search_query = request.GET.get('search', '')
    users = User.objects.select_related('userprofile').all()
    
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )
    
    users = users.order_by('-date_joined')
    
    # Pagination
    paginator = Paginator(users, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'total_users': User.objects.count(),
        'active_users': User.objects.filter(is_active=True).count(),
        'sales_users': UserProfile.objects.filter(roles__contains='sales').count(),
        'pm_users': UserProfile.objects.filter(roles__contains='project_manager').count(),
    }
    
    return render(request, 'dashboard/user_management.html', context)

@login_required
def user_create_view(request):
    """Create new user with profile"""
    if request.method == 'POST':
        form = UserManagementForm(request.POST)
        if form.is_valid():
            try:
                # Create User
                name_parts = form.cleaned_data['name'].split(' ', 1)
                first_name = name_parts[0]
                last_name = name_parts[1] if len(name_parts) > 1 else ''
                
                # Generate username from email
                username = form.cleaned_data['email'].split('@')[0]
                counter = 1
                original_username = username
                while User.objects.filter(username=username).exists():
                    username = f"{original_username}{counter}"
                    counter += 1
                
                # Store the plain password for later display
                plain_password = form.cleaned_data['password']
                
                user = User.objects.create_user(
                    username=username,
                    email=form.cleaned_data['email'],
                    password=plain_password,
                    first_name=first_name,
                    last_name=last_name
                )
                
                # Store the password for display purposes
                password_storage.store_password(username, plain_password)
                
                # Create UserProfile with multiple form permissions
                selected_permissions = form.cleaned_data.get('form_permissions', [])
                selected_role = form.cleaned_data['role']
                
                profile, created = UserProfile.objects.get_or_create(
                    user=user,
                    defaults={
                        'roles': selected_role,
                        'can_access_invoice_generation': 'invoice_generation' in selected_permissions,
                        'can_access_inquiry_handler': 'inquiry_handler' in selected_permissions,
                        'can_access_quotation_generation': 'quotation_generation' in selected_permissions,
                        'can_access_additional_supply': 'additional_supply' in selected_permissions
                    }
                )
                
                messages.success(request, f'User {form.cleaned_data["name"]} created successfully!')
                return redirect('dashboard:user_management')
                
            except Exception as e:
                messages.error(request, f'Error creating user: {str(e)}')
                # If user was created but profile failed, clean up
                if 'user' in locals():
                    user.delete()
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = UserManagementForm()
    
    return render(request, 'dashboard/user_form.html', {
        'form': form,
        'title': 'Add User',
        'action': 'Create'
    })

@login_required
def user_edit_view(request, user_id):
    """Edit existing user"""
    user = get_object_or_404(User, id=user_id)
    profile, created = UserProfile.objects.get_or_create(user=user)
    
    if request.method == 'POST':
        form = UserEditForm(request.POST, user_instance=user)
        if form.is_valid():
            # Update User
            name_parts = form.cleaned_data['name'].split(' ', 1)
            user.first_name = name_parts[0]
            user.last_name = name_parts[1] if len(name_parts) > 1 else ''
            user.email = form.cleaned_data['email']
            if form.cleaned_data['password']:
                new_password = form.cleaned_data['password']
                user.set_password(new_password)
                # Update stored password
                password_storage.store_password(user.username, new_password)
            user.save()
            
            # Update UserProfile with single role and multiple form permissions
            selected_role = form.cleaned_data['role']
            selected_permissions = form.cleaned_data['form_permissions']
            profile.roles = selected_role
            profile.can_access_invoice_generation = 'invoice_generation' in selected_permissions
            profile.can_access_inquiry_handler = 'inquiry_handler' in selected_permissions
            profile.can_access_quotation_generation = 'quotation_generation' in selected_permissions
            profile.can_access_additional_supply = 'additional_supply' in selected_permissions
            profile.save()
            
            messages.success(request, f'User {user.get_full_name()} updated successfully!')
            return redirect('dashboard:user_management')
    else:
        # Pre-populate form with selected permissions (multiple)
        selected_permissions = []
        if profile.can_access_invoice_generation:
            selected_permissions.append('invoice_generation')
        if profile.can_access_inquiry_handler:
            selected_permissions.append('inquiry_handler')
        if profile.can_access_quotation_generation:
            selected_permissions.append('quotation_generation')
        if profile.can_access_additional_supply:
            selected_permissions.append('additional_supply')
            
        initial_data = {
            'name': f"{user.first_name} {user.last_name}".strip(),
            'email': user.email,
            'role': profile.get_roles_list(),
            'form_permissions': selected_permissions,
        }
        form = UserEditForm(initial=initial_data, user_instance=user)
    
    return render(request, 'dashboard/user_form.html', {
        'form': form,
        'title': f'Edit User: {user.get_full_name() or user.username}',
        'action': 'Update',
        'user_obj': user,
        'is_edit': True,
        'current_password': password_storage.get_password(user.username)  # Get stored password
    })

@login_required
def user_delete_view(request, user_id):
    """Delete user"""
    user = get_object_or_404(User, id=user_id)
    
    if request.user.id == user.id:
        messages.error(request, 'You cannot delete your own account!')
        return redirect('dashboard:user_management')
    
    if request.method == 'POST':
        username = user.username
        user.delete()
        messages.success(request, f'User {username} deleted successfully!')
        return redirect('dashboard:user_management')
    
    return render(request, 'dashboard/user_delete.html', {'user_obj': user})

def register_view(request):
    """User registration view"""
    if request.user.is_authenticated:
        return redirect('dashboard:index')
    
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}! You can now log in.')
            return redirect('login')
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'registration/register.html', {'form': form})

def login_view(request):
    """Custom login view to handle redirects"""
    if request.user.is_authenticated:
        return redirect('dashboard:index')
    
    # Django's built-in LoginView will handle the actual login
    # This is just for redirect logic
    return redirect('login')

def custom_logout_view(request):
    """Custom logout view that redirects to dashboard URL as requested"""
    logout(request)
    messages.success(request, 'You have been successfully logged out.')
    return redirect('/')  # Redirect to dashboard URL (/) as requested


# Company Management Forms and Views
class CompanyForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = ['company_name', 'city_1', 'address_1']
        widgets = {
            'company_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter company name'}),
            'city_1': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter city'}),
            'address_1': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Enter company address'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        company_name = cleaned_data.get('company_name')
        city_1 = cleaned_data.get('city_1')
        
        # Check for unique (company_name, city) combination
        # Same company cannot have the same city twice, but different companies can share cities
        if company_name and city_1:
            existing = Company.objects.filter(company_name=company_name, city_1=city_1)
            if self.instance and self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            if existing.exists():
                raise forms.ValidationError(f"This company already exists for the selected city. Company '{company_name}' is already registered in '{city_1}'.")
        
        return cleaned_data

@login_required
def company_management_view(request):
    """Company management page with list of companies"""
    search_query = request.GET.get('search', '')
    companies = Company.objects.all()
    
    if search_query:
        companies = companies.filter(
            Q(company_name__icontains=search_query) |
            Q(city_1__icontains=search_query) |
            Q(city_2__icontains=search_query)
        )
    
    companies = companies.order_by('company_name', 'city_1')
    
    # Pagination
    paginator = Paginator(companies, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'total_companies': Company.objects.count(),
    }
    
    return render(request, 'dashboard/company_management.html', context)

@login_required
def company_create_view(request):
    """Create new company"""
    if request.method == 'POST':
        form = CompanyForm(request.POST)
        if form.is_valid():
            company = form.save()
            messages.success(request, f'Company {company.company_name} created successfully!')
            return redirect('dashboard:contact_management')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CompanyForm()
    
    return render(request, 'dashboard/company_form.html', {
        'form': form,
        'title': 'Add New Company',
        'action': 'Create'
    })

@login_required
def company_edit_view(request, company_id):
    """Edit existing company"""
    company = get_object_or_404(Company, id=company_id)
    
    if request.method == 'POST':
        form = CompanyForm(request.POST, instance=company)
        if form.is_valid():
            company = form.save()
            messages.success(request, f'Company {company.company_name} updated successfully!')
            return redirect('dashboard:contact_management')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CompanyForm(instance=company)
    
    return render(request, 'dashboard/company_form.html', {
        'form': form,
        'title': f'Edit Company: {company.company_name}',
        'action': 'Update',
        'company_obj': company,
        'is_edit': True
    })

@login_required
def company_delete_view(request, company_id):
    """Delete company"""
    company = get_object_or_404(Company, id=company_id)
    
    # Check if company is being used by contacts
    contacts_count = Contact.objects.filter(company=company).count()
    
    if request.method == 'POST':
        # Handle AJAX request
        if request.headers.get('Content-Type') == 'application/json':
            if contacts_count > 0:
                return JsonResponse({
                    'success': False,
                    'message': f'Cannot delete company {company.company_name}. It is being used by {contacts_count} contact(s).'
                })
            
            company_name = company.company_name
            company.delete()
            return JsonResponse({
                'success': True,
                'message': f'Company {company_name} deleted successfully!'
            })
        
        # Handle regular form submission (fallback)
        if contacts_count > 0:
            messages.error(request, f'Cannot delete company {company.company_name}. It is being used by {contacts_count} contact(s).')
            return redirect('dashboard:contact_management')
        
        company_name = company.company_name
        company.delete()
        messages.success(request, f'Company {company_name} deleted successfully!')
        return redirect('dashboard:contact_management')
    
    # GET request - show delete confirmation page (fallback)
    return render(request, 'dashboard/company_delete.html', {'company_obj': company})

# Contact Management Forms and Views
class ContactForm(forms.ModelForm):
    # Company selection dropdown
    company = forms.ModelChoiceField(
        queryset=Company.objects.all(),
        empty_label="Select Company",
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'company-select'}),
        label="Company Name *",
        help_text="Select company from master list"
    )
    
    class Meta:
        model = Contact
        fields = ['contact_name', 'email_1', 'phone_1', 'phone_2', 'company', 'individual_address']
        widgets = {
            'contact_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter client name'}),
            'email_1': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter email address'}),
            'phone_1': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter phone number'}),
            'phone_2': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter secondary phone number (optional)'}),
            'individual_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Enter personal address'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Order companies by name and city
        self.fields['company'].queryset = Company.objects.all().order_by('company_name', 'city_1')
        
        # If editing existing contact, set the company field
        if self.instance and self.instance.pk and self.instance.company:
            self.fields['company'].initial = self.instance.company
    
    def clean_phone_1(self):
        phone = self.cleaned_data.get('phone_1')
        if phone and not phone.replace('+', '').replace('-', '').replace(' ', '').replace('(', '').replace(')', '').isdigit():
            raise forms.ValidationError("Please enter a valid phone number.")
        return phone
    
    def clean_phone_2(self):
        phone = self.cleaned_data.get('phone_2')
        if phone and not phone.replace('+', '').replace('-', '').replace(' ', '').replace('(', '').replace(')', '').isdigit():
            raise forms.ValidationError("Please enter a valid phone number.")
        return phone

@login_required
def contact_management_view(request):
    """Contact management page with list of contacts and companies"""
    search_query = request.GET.get('search', '')
    view_type = request.GET.get('view', 'contacts')  # 'contacts' or 'companies'
    
    if view_type == 'companies':
        # Show companies
        companies = Company.objects.all()
        
        if search_query:
            companies = companies.filter(
                Q(company_name__icontains=search_query) |
                Q(city_1__icontains=search_query) |
                Q(city_2__icontains=search_query)
            )
        
        companies = companies.order_by('company_name', 'city_1')
        
        # Pagination
        paginator = Paginator(companies, 10)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context = {
            'page_obj': page_obj,
            'search_query': search_query,
            'view_type': view_type,
            'total_companies': Company.objects.count(),
            'total_contacts': Contact.objects.count(),
        }
    else:
        # Show contacts (default)
        contacts = Contact.objects.select_related('company').all()
        
        if search_query:
            contacts = contacts.filter(
                Q(contact_name__icontains=search_query) |
                Q(customer_name__icontains=search_query) |
                Q(email_1__icontains=search_query) |
                Q(email_2__icontains=search_query) |
                Q(phone_1__icontains=search_query) |
                Q(company__company_name__icontains=search_query) |
                Q(location_city__icontains=search_query)
            )
        
        contacts = contacts.order_by('-created_at')
        
        # Pagination
        paginator = Paginator(contacts, 10)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context = {
            'page_obj': page_obj,
            'search_query': search_query,
            'view_type': view_type,
            'total_contacts': Contact.objects.count(),
            'total_companies': Company.objects.count(),
        }
    
    return render(request, 'dashboard/contact_management.html', context)

@login_required
def contact_create_view(request):
    """Create new contact"""
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            contact = form.save()
            messages.success(request, f'Contact {contact.customer_name} created successfully!')
            return redirect('dashboard:contact_management')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ContactForm()
    
    return render(request, 'dashboard/contact_form.html', {
        'form': form,
        'title': 'Add New Contact',
        'action': 'Create'
    })

@login_required
def contact_edit_view(request, contact_id):
    """Edit existing contact"""
    contact = get_object_or_404(Contact, id=contact_id)
    
    if request.method == 'POST':
        form = ContactForm(request.POST, instance=contact)
        if form.is_valid():
            contact = form.save()
            messages.success(request, f'Contact {contact.customer_name} updated successfully!')
            return redirect('dashboard:contact_management')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ContactForm(instance=contact)
    
    return render(request, 'dashboard/contact_form.html', {
        'form': form,
        'title': f'Edit Contact: {contact.customer_name}',
        'action': 'Update',
        'contact_obj': contact,
        'is_edit': True
    })

@login_required
def contact_delete_view(request, contact_id):
    """Delete contact"""
    contact = get_object_or_404(Contact, id=contact_id)
    
    if request.method == 'POST':
        customer_name = contact.customer_name
        contact.delete()
        messages.success(request, f'Contact {customer_name} deleted successfully!')
        return redirect('dashboard:contact_management')
    
    return render(request, 'dashboard/contact_delete.html', {'contact_obj': contact})


# Purchase Order Management Forms and Views
class PurchaseOrderForm(forms.ModelForm):
    # Add customer_name as a text input for autocomplete
    customer_name_select = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'id': 'customer-select',
            'placeholder': 'Type to search customer name...',
            'autocomplete': 'off'
        }),
        label="Customer Name *",
        help_text="Start typing to search for customers"
    )
    
    # Hidden field to store the selected customer ID
    selected_customer_id = forms.CharField(
        widget=forms.HiddenInput(),
        required=False
    )
    
    class Meta:
        model = PurchaseOrder
        fields = ['po_number', 'order_date', 'customer_name_select', 'selected_customer_id', 'order_value', 'days_to_mfg', 'remarks', 'payment_terms', 'sales_person', 'sales_percentage', 'project_manager', 'project_manager_percentage']
        widgets = {
            'po_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter PO Number'}),
            'order_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'order_value': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter order value', 'step': '0.01'}),
            'days_to_mfg': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter manufacturing days'}),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Enter remarks (optional)'}),
            'payment_terms': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter days (e.g., 45)', 'min': '1'}),
            'sales_person': forms.Select(attrs={'class': 'form-select'}),
            'sales_percentage': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter percentage (e.g., 5.50)', 'step': '0.01', 'min': '0', 'max': '100'}),
            'project_manager': forms.Select(attrs={'class': 'form-select'}),
            'project_manager_percentage': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter percentage (e.g., 3.25)', 'step': '0.01', 'min': '0', 'max': '100'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filter sales persons (users with sales role)
        sales_users = User.objects.filter(userprofile__roles__contains='sales').distinct()
        self.fields['sales_person'].queryset = sales_users
        self.fields['sales_person'].empty_label = "Select Sales Person"
        
        # Filter project managers (users with project_manager role)
        pm_users = User.objects.filter(userprofile__roles__contains='project_manager').distinct()
        self.fields['project_manager'].queryset = pm_users
        self.fields['project_manager'].empty_label = "Select Project Manager"
        
        # If editing existing order, set the customer fields
        if self.instance and self.instance.pk and self.instance.company:
            self.fields['customer_name_select'].initial = self.instance.company.customer_name
            self.fields['selected_customer_id'].initial = self.instance.company.id
            
        # Debug: Print payment terms value when editing
        if self.instance and self.instance.pk:
            print(f"DEBUG: Editing PO {self.instance.po_number}, Payment Terms: {self.instance.payment_terms}")
            
            # Ensure payment_terms field gets the correct initial value
            if self.instance.payment_terms is not None:
                self.fields['payment_terms'].initial = self.instance.payment_terms
    
    def clean(self):
        cleaned_data = super().clean()
        selected_customer_id = cleaned_data.get('selected_customer_id')
        customer_name_select = cleaned_data.get('customer_name_select')
        
        # Validate that a customer was selected
        if not selected_customer_id and customer_name_select:
            raise forms.ValidationError("Please select a valid customer from the dropdown.")
        
        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Set company and customer_name based on selected customer ID
        selected_customer_id = self.cleaned_data.get('selected_customer_id')
        if selected_customer_id:
            try:
                selected_contact = Contact.objects.get(id=selected_customer_id)
                instance.company = selected_contact
                instance.customer_name = selected_contact.customer_name
            except Contact.DoesNotExist:
                pass
        
        if commit:
            instance.save()
        return instance

@login_required
def purchase_order_management_view(request):
    """Purchase Order management page with list of orders"""
    search_query = request.GET.get('search', '')
    orders = PurchaseOrder.objects.select_related('company', 'sales_person', 'project_manager').all()
    
    if search_query:
        orders = orders.filter(
            Q(po_number__icontains=search_query) |
            Q(company__company__icontains=search_query) |
            Q(customer_name__icontains=search_query) |
            Q(sales_person__username__icontains=search_query) |
            Q(project_manager__username__icontains=search_query)
        )
    
    orders = orders.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(orders, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Statistics
    total_orders = PurchaseOrder.objects.count()
    total_value = PurchaseOrder.objects.aggregate(total=models.Sum('order_value'))['total'] or 0
    overdue_orders = PurchaseOrder.objects.filter(due_days__lt=0).count()
    due_today = PurchaseOrder.objects.filter(due_days=0).count()
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'total_orders': total_orders,
        'total_value': total_value,
        'overdue_orders': overdue_orders,
        'due_today': due_today,
    }
    
    return render(request, 'dashboard/purchase_order_management.html', context)

@login_required
def purchase_order_create_view(request):
    """Create new purchase order"""
    if request.method == 'POST':
        form = PurchaseOrderForm(request.POST)
        if form.is_valid():
            order = form.save()
            
            # Handle items data
            items_data_json = request.POST.get('items_data')
            print(f"DEBUG: Received items_data: {items_data_json}")
            
            if items_data_json:
                try:
                    items_data = json.loads(items_data_json)
                    print(f"DEBUG: Parsed items_data: {items_data}")
                    
                    total_amount = 0
                    
                    for item_data in items_data:
                        if item_data.get('item_name') and item_data.get('quantity') and item_data.get('price'):
                            # Extract material code from item name if it's in [CODE] format
                            item_name = item_data['item_name']
                            material_code = ''
                            
                            if item_name.startswith('[') and ']' in item_name:
                                parts = item_name.split(']', 1)
                                material_code = parts[0][1:]  # Remove the opening bracket
                                item_name = parts[1].strip() if len(parts) > 1 else item_name
                            
                            item = PurchaseOrderItem.objects.create(
                                purchase_order=order,
                                material_code=material_code,
                                item_name=item_name,
                                quantity=float(item_data['quantity']),
                                price=float(item_data['price'])
                            )
                            total_amount += float(item.amount)
                            print(f"DEBUG: Created item: {item}")
                    
                    # Update order value with calculated total
                    if total_amount > 0:
                        order.order_value = total_amount
                        order.save()
                        print(f"DEBUG: Updated order value to: {total_amount}")
                        
                except (json.JSONDecodeError, ValueError) as e:
                    print(f"DEBUG: Error processing items: {str(e)}")
                    messages.warning(request, f'Items data could not be processed: {str(e)}')
            else:
                print("DEBUG: No items_data received in POST")
            
            messages.success(request, f'Purchase Order {order.po_number} created successfully!')
            return redirect('dashboard:purchase_order_management')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = PurchaseOrderForm()
    
    return render(request, 'dashboard/purchase_order_form.html', {
        'form': form,
        'title': 'Create Order',
        'action': 'Create'
    })

@login_required
def purchase_order_edit_view(request, order_id):
    """Edit existing purchase order"""
    order = get_object_or_404(PurchaseOrder, id=order_id)
    
    if request.method == 'POST':
        form = PurchaseOrderForm(request.POST, instance=order)
        if form.is_valid():
            order = form.save()
            
            # Handle items data
            items_data_json = request.POST.get('items_data')
            print(f"DEBUG EDIT: Received items_data: {items_data_json}")
            
            if items_data_json:
                try:
                    items_data = json.loads(items_data_json)
                    print(f"DEBUG EDIT: Parsed items_data: {items_data}")
                    
                    # Clear existing items
                    order.items.all().delete()
                    print(f"DEBUG EDIT: Cleared existing items")
                    
                    total_amount = 0
                    for item_data in items_data:
                        if item_data.get('item_name') and item_data.get('quantity') and item_data.get('price'):
                            # Extract material code from item name if it's in [CODE] format
                            item_name = item_data['item_name']
                            material_code = ''
                            
                            if item_name.startswith('[') and ']' in item_name:
                                parts = item_name.split(']', 1)
                                material_code = parts[0][1:]  # Remove the opening bracket
                                item_name = parts[1].strip() if len(parts) > 1 else item_name
                            
                            item = PurchaseOrderItem.objects.create(
                                purchase_order=order,
                                material_code=material_code,
                                item_name=item_name,
                                quantity=float(item_data['quantity']),
                                price=float(item_data['price'])
                            )
                            total_amount += float(item.amount)
                            print(f"DEBUG EDIT: Created item: {item}")
                    
                    # Update order value with calculated total
                    if total_amount > 0:
                        order.order_value = total_amount
                        order.save()
                        print(f"DEBUG EDIT: Updated order value to: {total_amount}")
                        
                except (json.JSONDecodeError, ValueError) as e:
                    print(f"DEBUG EDIT: Error processing items: {str(e)}")
                    messages.warning(request, f'Items data could not be processed: {str(e)}')
            else:
                print("DEBUG EDIT: No items_data received in POST")
            
            messages.success(request, f'Purchase Order {order.po_number} updated successfully!')
            return redirect('dashboard:purchase_order_management')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = PurchaseOrderForm(instance=order)
    
    return render(request, 'dashboard/purchase_order_form.html', {
        'form': form,
        'title': f'Edit Purchase Order: {order.po_number}',
        'action': 'Update',
        'order_obj': order,
        'is_edit': True
    })

@login_required
def purchase_order_delete_view(request, order_id):
    """Delete purchase order"""
    order = get_object_or_404(PurchaseOrder, id=order_id)
    
    if request.method == 'POST':
        po_number = order.po_number
        order.delete()
        messages.success(request, f'Purchase Order {po_number} deleted successfully!')
        return redirect('dashboard:purchase_order_management')
    
    return render(request, 'dashboard/purchase_order_delete.html', {'order_obj': order})

@login_required
def get_company_data_ajax(request):
    """Centralized AJAX endpoint to get company data by company ID"""
    company_id = request.GET.get('company_id')
    if not company_id:
        return JsonResponse({'success': False, 'error': 'No company ID provided'})
    
    try:
        company = Company.objects.get(id=company_id)
        return JsonResponse({
            'success': True,
            'company_id': company.id,
            'company_name': company.company_name,
            'primary_city': company.city_1,
            'secondary_city': company.city_2 or '',
            'cities_display': company.get_cities_display(),
            'location_city': company.get_primary_city(),
            'addresses': company.get_addresses_list()
        })
    except Company.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Company not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Error fetching company data: {str(e)}'})

@login_required
def get_contact_data_ajax(request):
    """Centralized AJAX endpoint to get contact data by contact ID"""
    contact_id = request.GET.get('contact_id')
    if not contact_id:
        return JsonResponse({'success': False, 'error': 'No contact ID provided'})
    
    try:
        contact = Contact.objects.select_related('company').get(id=contact_id)
        return JsonResponse({
            'success': True,
            'contact_id': contact.id,
            'contact_name': contact.contact_name,
            'customer_name': contact.customer_name,
            'email_1': contact.email_1,
            'email_2': contact.email_2 or '',
            'phone_1': contact.phone_1,
            'phone_2': contact.phone_2 or '',
            'company_id': contact.company.id if contact.company else None,
            'company_name': contact.company.company_name if contact.company else '',
            'location_city': contact.location_city,
            'individual_address': contact.individual_address
        })
    except Contact.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Contact not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Error fetching contact data: {str(e)}'})

@login_required
def export_purchase_orders_excel(request):
    """Export purchase orders to Excel file"""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    from django.http import HttpResponse
    from datetime import datetime
    
    # Get the same filtered queryset as the management view
    search_query = request.GET.get('search', '')
    orders = PurchaseOrder.objects.select_related('company', 'sales_person', 'project_manager').all()
    
    if search_query:
        orders = orders.filter(
            Q(po_number__icontains=search_query) |
            Q(company__company__icontains=search_query) |
            Q(customer_name__icontains=search_query) |
            Q(sales_person__username__icontains=search_query) |
            Q(project_manager__username__icontains=search_query)
        )
    
    orders = orders.order_by('-created_at')
    
    # Create workbook and worksheet
    wb = Workbook()
    ws = wb.active
    ws.title = "Purchase Orders"
    
    # Define headers
    headers = [
        'PO Number',
        'Company', 
        'Customer',
        'Order Date',
        'Order Value',
        'Delivery Date',
        'Status',
        'Payment Terms',
        'Sales Person',
        'Sales %',
        'Project Manager',
        'PM %'
    ]
    
    # Style for headers
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center")
    
    # Add headers
    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_num)
        cell.value = header
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
    
    # Add data rows
    for row_num, order in enumerate(orders, 2):
        
        # Company
        ws.cell(row=row_num, column=2, value=order.company.company if order.company else "")
        
        # PO Number
        ws.cell(row=row_num, column=1, value=order.po_number)
        
        # Customer
        ws.cell(row=row_num, column=3, value=order.customer_name)
        
        # Order Date (formatted as DD-MM-YYYY)
        order_date_formatted = order.order_date.strftime('%d-%m-%Y') if order.order_date else ""
        ws.cell(row=row_num, column=4, value=order_date_formatted)
        
        # Order Value (numeric)
        ws.cell(row=row_num, column=5, value=float(order.order_value) if order.order_value else 0)
        
        # Delivery Date (formatted as DD-MM-YYYY)
        delivery_date_formatted = order.delivery_date.strftime('%d-%m-%Y') if order.delivery_date else ""
        ws.cell(row=row_num, column=6, value=delivery_date_formatted)
        
        # Status
        status = order.get_status()
        if order.due_days is not None:
            if order.due_days > 0:
                status = f"{order.due_days} days left"
            elif order.due_days == 0:
                status = "Due today"
            else:
                status = f"{abs(order.due_days)} days overdue"
        ws.cell(row=row_num, column=7, value=status)
        
        # Payment Terms
        payment_terms = f"{order.payment_terms} days" if order.payment_terms else ""
        ws.cell(row=row_num, column=8, value=payment_terms)
        
        # Sales Person
        sales_person_name = ""
        if order.sales_person:
            sales_person_name = order.sales_person.get_full_name() or order.sales_person.username
        ws.cell(row=row_num, column=9, value=sales_person_name)
        
        # Sales Percentage
        sales_percentage = float(order.sales_percentage) if order.sales_percentage else ""
        ws.cell(row=row_num, column=10, value=sales_percentage)
        
        # Project Manager
        pm_name = ""
        if order.project_manager:
            pm_name = order.project_manager.get_full_name() or order.project_manager.username
        ws.cell(row=row_num, column=11, value=pm_name)
        
        # PM Percentage
        pm_percentage = float(order.project_manager_percentage) if order.project_manager_percentage else ""
        ws.cell(row=row_num, column=12, value=pm_percentage)
    
    # Auto-adjust column widths
    for column in ws.columns:
        max_length = 0
        column_letter = column[0].column_letter
        for cell in column:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = min(max_length + 2, 50)  # Cap at 50 characters
        ws.column_dimensions[column_letter].width = adjusted_width
    
    # Create HTTP response
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="purchase_orders.xlsx"'
    
    # Save workbook to response
    wb.save(response)
    
    return response


# Invoice Management Forms and Views
class InvoiceForm(forms.ModelForm):
    # Customer selection autocomplete - primary field for selection
    customer_select = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'id': 'customer-select',
            'placeholder': 'Type to search customer name...',
            'autocomplete': 'off'
        }),
        label="Customer *",
        help_text="Start typing to search for customers"
    )
    
    # Hidden field to store the selected customer ID
    selected_customer_id = forms.CharField(
        widget=forms.HiddenInput(),
        required=False
    )
    
    # Purchase Order selection - will be filtered based on customer selection
    purchase_order = forms.ModelChoiceField(
        queryset=PurchaseOrder.objects.all(),  # Show all initially, will be filtered by JavaScript
        empty_label="Select Purchase Order",
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'purchase-order-select'}),
        label="Purchase Order *"
    )
    
    class Meta:
        model = Invoice
        fields = ['invoice_date', 'customer_select', 'selected_customer_id', 'purchase_order', 'grn_date', 'remarks']
        # Exclude auto-generated/calculated fields: invoice_number, customer_name, order_value, payment_due_date, due_days, client (auto-fetched)
        widgets = {
            'invoice_date': forms.DateInput(attrs={
                'class': 'form-control', 
                'type': 'date'
            }),
            'grn_date': forms.DateInput(attrs={
                'class': 'form-control', 
                'type': 'date'
            }),
            'remarks': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3, 
                'placeholder': 'Enter remarks (optional)'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # If editing existing invoice, set the customer fields
        if self.instance and self.instance.pk and self.instance.company:
            self.fields['customer_select'].initial = self.instance.company.customer_name
            self.fields['selected_customer_id'].initial = self.instance.company.id
            
            # For editing: include current PO even if it has invoice, but exclude others with invoices
            if self.instance.purchase_order:
                self.fields['purchase_order'].queryset = PurchaseOrder.objects.filter(
                    company=self.instance.company
                ).filter(
                    Q(id=self.instance.purchase_order.id) |  # Include current PO
                    ~Q(invoice__isnull=False)  # Exclude POs that have invoices
                ).order_by('-created_at')
                self.fields['purchase_order'].initial = self.instance.purchase_order
            else:
                # If editing but no PO selected, exclude all POs with invoices
                self.fields['purchase_order'].queryset = PurchaseOrder.objects.filter(
                    company=self.instance.company,
                    invoice__isnull=True  # Only POs without invoices
                ).order_by('-created_at')
        else:
            # For new forms, show only purchase orders that don't have invoices yet
            self.fields['purchase_order'].queryset = PurchaseOrder.objects.filter(
                invoice__isnull=True  # Only POs without invoices
            ).order_by('-created_at')
            
            # Set current date as default for new invoices
            from datetime import date
            self.fields['invoice_date'].initial = date.today()
    
    def clean(self):
        cleaned_data = super().clean()
        selected_customer_id = cleaned_data.get('selected_customer_id')
        customer_name_select = cleaned_data.get('customer_select')
        purchase_order = cleaned_data.get('purchase_order')
        
        # Validate that a customer was selected
        if not selected_customer_id and customer_name_select:
            raise forms.ValidationError("Please select a valid customer from the dropdown.")
        
        # Validate that the selected purchase order belongs to the selected customer
        if selected_customer_id and purchase_order:
            try:
                selected_contact = Contact.objects.get(id=selected_customer_id)
                if purchase_order.company != selected_contact:
                    raise forms.ValidationError("The selected purchase order does not belong to the selected customer.")
            except Contact.DoesNotExist:
                raise forms.ValidationError("Selected customer not found.")
        
        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Set company and customer_name based on selected customer ID
        selected_customer_id = self.cleaned_data.get('selected_customer_id')
        if selected_customer_id:
            try:
                selected_contact = Contact.objects.get(id=selected_customer_id)
                instance.company = selected_contact
                instance.customer_name = selected_contact.customer_name
            except Contact.DoesNotExist:
                pass
        
        if commit:
            instance.save()
        return instance

@login_required
def invoice_management_view(request):
    """Invoice management page with list of invoices"""
    search_query = request.GET.get('search', '')
    invoices = Invoice.objects.select_related('company', 'purchase_order').all()
    
    if search_query:
        invoices = invoices.filter(
            Q(invoice_number__icontains=search_query) |
            Q(company__company__icontains=search_query) |
            Q(customer_name__icontains=search_query) |
            Q(purchase_order__po_number__icontains=search_query)
        )
    
    invoices = invoices.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(invoices, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Statistics
    total_invoices = Invoice.objects.count()
    total_value = Invoice.objects.aggregate(total=models.Sum('order_value'))['total'] or 0
    overdue_invoices = Invoice.objects.filter(due_days__lt=0).count()
    due_today = Invoice.objects.filter(due_days=0).count()
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'total_invoices': total_invoices,
        'total_value': total_value,
        'overdue_invoices': overdue_invoices,
        'due_today': due_today,
    }
    
    return render(request, 'dashboard/invoice_management.html', context)

@login_required
def invoice_create_view(request):
    """Create new invoice"""
    if request.method == 'POST':
        form = InvoiceForm(request.POST)
        
        # Update purchase order queryset based on selected company
        if 'company' in request.POST and request.POST['company']:
            try:
                company_id = int(request.POST['company'])
                company = Contact.objects.get(id=company_id)
                form.fields['purchase_order'].queryset = PurchaseOrder.objects.filter(
                    company=company
                ).order_by('-created_at')
            except (ValueError, Contact.DoesNotExist):
                pass
        
        if form.is_valid():
            invoice = form.save()
            messages.success(request, f'Invoice {invoice.invoice_number} created successfully!')
            return redirect('dashboard:invoice_management')
        else:
            # Add detailed error messages for debugging
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = InvoiceForm()
    
    return render(request, 'dashboard/invoice_form.html', {
        'form': form,
        'title': 'Create New Invoice',
        'action': 'Create'
    })

@login_required
def invoice_edit_view(request, invoice_id):
    """Edit existing invoice"""
    invoice = get_object_or_404(Invoice, id=invoice_id)
    
    if request.method == 'POST':
        form = InvoiceForm(request.POST, instance=invoice)
        
        # Update purchase order queryset based on selected company
        if 'company' in request.POST and request.POST['company']:
            try:
                company_id = int(request.POST['company'])
                company = Contact.objects.get(id=company_id)
                form.fields['purchase_order'].queryset = PurchaseOrder.objects.filter(
                    company=company
                ).order_by('-created_at')
            except (ValueError, Contact.DoesNotExist):
                pass
        
        if form.is_valid():
            invoice = form.save()
            messages.success(request, f'Invoice {invoice.invoice_number} updated successfully!')
            return redirect('dashboard:invoice_management')
        else:
            # Add detailed error messages for debugging
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = InvoiceForm(instance=invoice)
    
    return render(request, 'dashboard/invoice_form.html', {
        'form': form,
        'title': f'Edit Invoice: {invoice.invoice_number}',
        'action': 'Update',
        'invoice_obj': invoice,
        'is_edit': True
    })

@login_required
def invoice_delete_view(request, invoice_id):
    """Delete invoice"""
    invoice = get_object_or_404(Invoice, id=invoice_id)
    
    if request.method == 'POST':
        invoice_number = invoice.invoice_number
        invoice.delete()
        messages.success(request, f'Invoice {invoice_number} deleted successfully!')
        return redirect('dashboard:invoice_management')
    
    return render(request, 'dashboard/invoice_delete.html', {'invoice_obj': invoice})

@login_required
def get_purchase_orders_by_contact_ajax(request):
    """AJAX endpoint to get purchase orders based on selected contact"""
    contact_id = request.GET.get('contact_id')
    if not contact_id:
        return JsonResponse({'success': False, 'error': 'No contact ID provided'})
    
    try:
        contact = Contact.objects.select_related('company').get(id=contact_id)
        
        # Only get purchase orders that don't have invoices yet
        purchase_orders = PurchaseOrder.objects.filter(
            company=contact,
            invoice__isnull=True  # Only POs without invoices
        ).order_by('-created_at')
        
        po_data = []
        for po in purchase_orders:
            po_data.append({
                'id': po.id,
                'po_number': po.po_number,
                'order_value': str(po.order_value),
                'order_date': po.order_date.strftime('%Y-%m-%d') if po.order_date else '',
                'customer_name': po.customer_name
            })
        
        return JsonResponse({
            'success': True,
            'purchase_orders': po_data,
            'contact_id': contact.id,
            'customer_name': contact.customer_name,
            'company_name': contact.company.company_name if contact.company else ''
        })
    except Contact.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Contact not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Error fetching purchase orders: {str(e)}'})

@login_required
def get_purchase_order_details_ajax(request):
    """AJAX endpoint to get purchase order details"""
    po_id = request.GET.get('po_id')
    if po_id:
        try:
            po = PurchaseOrder.objects.get(id=po_id)
            return JsonResponse({
                'success': True,
                'order_value': str(po.order_value),
                'customer_name': po.customer_name,
                'po_number': po.po_number,
                'payment_terms': po.payment_terms or 15  # Default to 15 days if not set
            })
        except PurchaseOrder.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Purchase Order not found'})
    return JsonResponse({'success': False, 'error': 'No Purchase Order ID provided'})


# Inquiry Handler Management Forms and Views
class InquiryHandlerForm(forms.ModelForm):
    # Customer selection dropdown - primary field for selection
    customer_select = forms.ModelChoiceField(
        queryset=Contact.objects.all(),
        empty_label="Select Customer",
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'customer-select'}),
        label="Customer *",
        help_text="Select customer from database"
    )
    
    # Sales dropdown - replaces BA field
    sales = forms.ModelChoiceField(
        queryset=User.objects.filter(userprofile__roles__contains='sales'),
        empty_label="Select Sales Person",
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'sales-select'}),
        label="Sales *",
        help_text="Select sales person from database"
    )
    
    # Next Date field - new optional field
    next_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label="Next Date",
        help_text="Enter next date manually (optional)"
    )
    
    class Meta:
        model = InquiryHandler
        fields = ['status', 'customer_select', 'date_of_quote', 'sales', 'next_date', 'remarks']
        # Removed fields: create_id (auto-generated), lead_description (removed), ba (replaced with sales)
        # Auto-generated fields: create_id, opportunity_id, customer_name, quote_no
        widgets = {
            'status': forms.Select(attrs={
                'class': 'form-select',
                'id': 'status-select'
            }),
            'date_of_quote': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'required': 'required'  # Enforce HTML5 required attribute
            }),
            'remarks': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter remarks (optional)'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set customer queryset ordered by customer name
        self.fields['customer_select'].queryset = Contact.objects.all().order_by('customer_name')
        
        # Set sales queryset ordered by username
        self.fields['sales'].queryset = User.objects.filter(userprofile__roles__contains='sales').order_by('username')
        
        # Explicitly mark date_of_quote as required
        self.fields['date_of_quote'].required = True
        
        # Set default date to today for new forms
        if not self.instance.pk:
            from datetime import date
            self.fields['date_of_quote'].initial = date.today()
        
        # If editing existing inquiry, set the customer_select field
        if self.instance and self.instance.pk and self.instance.company:
            self.fields['customer_select'].initial = self.instance.company
    
    def clean_date_of_quote(self):
        """Validate that date_of_quote is provided"""
        date_of_quote = self.cleaned_data.get('date_of_quote')
        if not date_of_quote:
            raise forms.ValidationError("Date of Quote is required and cannot be empty.")
        return date_of_quote
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Set both company and customer_name based on selected customer
        if self.cleaned_data.get('customer_select'):
            selected_contact = self.cleaned_data['customer_select']
            instance.company = selected_contact  # Set the company relationship
            
            # Ensure customer_name is properly set (fallback to contact_name if customer_name is empty)
            customer_name = selected_contact.customer_name or selected_contact.contact_name
            instance.customer_name = customer_name
        
        if commit:
            instance.save()
        return instance


@login_required
def save_inquiry_items_ajax(request):
    """AJAX endpoint to save inquiry items"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'})
    
    try:
        import json
        data = json.loads(request.body)
        inquiry_id = data.get('inquiry_id')
        items = data.get('items', [])
        
        if not inquiry_id:
            return JsonResponse({'success': False, 'error': 'No inquiry ID provided'})
        
        inquiry = InquiryHandler.objects.get(id=inquiry_id)
        
        # Clear existing items
        inquiry.items.all().delete()
        
        # Add new items
        total_amount = 0
        for item_data in items:
            if item_data.get('item_name') and item_data.get('quantity') and item_data.get('price'):
                item = InquiryItem.objects.create(
                    inquiry=inquiry,
                    item_name=item_data['item_name'],
                    quantity=float(item_data['quantity']),
                    price=float(item_data['price'])
                )
                total_amount += item.amount
        
        return JsonResponse({
            'success': True,
            'total_amount': str(total_amount),
            'items_count': len(items)
        })
        
    except InquiryHandler.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Inquiry not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Error saving items: {str(e)}'})


@login_required
def get_inquiry_items_ajax(request):
    """AJAX endpoint to get inquiry items"""
    inquiry_id = request.GET.get('inquiry_id')
    if not inquiry_id:
        return JsonResponse({'success': False, 'error': 'No inquiry ID provided'})
    
    try:
        inquiry = InquiryHandler.objects.get(id=inquiry_id)
        items_data = []
        
        for item in inquiry.items.all():
            items_data.append({
                'item_name': item.item_name,
                'quantity': str(item.quantity),
                'price': str(item.price),
                'amount': str(item.amount)
            })
        
        return JsonResponse({
            'success': True,
            'items': items_data
        })
        
    except InquiryHandler.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Inquiry not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Error fetching items: {str(e)}'})

@login_required
def inquiry_handler_management_view(request):
    """Inquiry Handler management page with list of inquiries"""
    search_query = request.GET.get('search', '')
    inquiries = InquiryHandler.objects.select_related('company').all()
    
    if search_query:
        inquiries = inquiries.filter(
            Q(create_id__icontains=search_query) |
            Q(opportunity_id__icontains=search_query) |
            Q(quote_no__icontains=search_query) |
            Q(company__company__icontains=search_query) |
            Q(customer_name__icontains=search_query) |
            Q(ba__icontains=search_query)
        )
    
    inquiries = inquiries.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(inquiries, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Statistics
    total_inquiries = InquiryHandler.objects.count()
    active_inquiries = InquiryHandler.objects.exclude(status__in=['Lost', 'Project Closed']).count()
    quotation_stage = InquiryHandler.objects.filter(status='Quotation').count()
    closed_inquiries = InquiryHandler.objects.filter(status='Project Closed').count()
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'total_inquiries': total_inquiries,
        'active_inquiries': active_inquiries,
        'quotation_stage': quotation_stage,
        'closed_inquiries': closed_inquiries,
    }
    
    return render(request, 'dashboard/inquiry_handler_management.html', context)

@login_required
def inquiry_handler_create_view(request):
    """Create new inquiry"""
    if request.method == 'POST':
        form = InquiryHandlerForm(request.POST)
        
        if form.is_valid():
            inquiry = form.save()
            
            # Handle items data if provided
            items_data = request.POST.get('items_data')
            if items_data:
                try:
                    import json
                    items = json.loads(items_data)
                    
                    # Save each item
                    for item_data in items:
                        if item_data.get('item_name') and item_data.get('quantity') and item_data.get('price'):
                            InquiryItem.objects.create(
                                inquiry=inquiry,
                                item_name=item_data['item_name'],
                                quantity=float(item_data['quantity']),
                                price=float(item_data['price'])
                            )
                except (json.JSONDecodeError, ValueError, KeyError) as e:
                    messages.warning(request, f'Some items could not be saved: {str(e)}')
            
            messages.success(request, f'Inquiry {inquiry.create_id} created successfully!')
            return redirect('dashboard:inquiry_handler_management')
        else:
            # Add detailed error messages for debugging
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = InquiryHandlerForm()
    
    return render(request, 'dashboard/inquiry_handler_form.html', {
        'form': form,
        'title': 'Create New Inquiry',
        'action': 'Create'
    })

@login_required
def inquiry_handler_edit_view(request, inquiry_id):
    """Edit existing inquiry"""
    inquiry = get_object_or_404(InquiryHandler, id=inquiry_id)
    
    if request.method == 'POST':
        form = InquiryHandlerForm(request.POST, instance=inquiry)
        
        if form.is_valid():
            inquiry = form.save()
            messages.success(request, f'Inquiry {inquiry.create_id} updated successfully!')
            return redirect('dashboard:inquiry_handler_management')
        else:
            # Add detailed error messages for debugging
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = InquiryHandlerForm(instance=inquiry)
    
    return render(request, 'dashboard/inquiry_handler_form.html', {
        'form': form,
        'title': f'Edit Inquiry: {inquiry.create_id}',
        'action': 'Update',
        'inquiry_obj': inquiry,
        'is_edit': True
    })

@login_required
def inquiry_handler_delete_view(request, inquiry_id):
    """Delete inquiry"""
    inquiry = get_object_or_404(InquiryHandler, id=inquiry_id)
    
    if request.method == 'POST':
        create_id = inquiry.create_id
        inquiry.delete()
        messages.success(request, f'Inquiry {create_id} deleted successfully!')
        return redirect('dashboard:inquiry_handler_management')
    
    return render(request, 'dashboard/inquiry_handler_delete.html', {'inquiry_obj': inquiry})




# Additional Supply Management Forms and Views
class AdditionalSupplyForm(forms.ModelForm):
    class Meta:
        model = InquiryHandler
        fields = ['remarks_add']
        widgets = {
            'remarks_add': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Enter additional supply remarks manually'
            }),
        }

@login_required
def additional_supply_management_view(request):
    """Additional Supply management page - shows all invoices that have invoice numbers"""
    search_query = request.GET.get('search', '')
    
    # Filter only invoices that have invoice numbers (meaning they exist/are created)
    invoices = Invoice.objects.select_related('company', 'purchase_order').filter(
        invoice_number__isnull=False
    ).exclude(invoice_number='')
    
    if search_query:
        invoices = invoices.filter(
            Q(invoice_number__icontains=search_query) |
            Q(company__company__icontains=search_query) |
            Q(customer_name__icontains=search_query) |
            Q(purchase_order__po_number__icontains=search_query) |
            Q(remarks__icontains=search_query)
        )
    
    invoices = invoices.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(invoices, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Statistics
    total_invoices = Invoice.objects.filter(
        invoice_number__isnull=False
    ).exclude(invoice_number='').count()
    with_remarks = Invoice.objects.filter(
        invoice_number__isnull=False,
        remarks__isnull=False
    ).exclude(invoice_number='').exclude(remarks='').count()
    without_remarks = total_invoices - with_remarks
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'total_invoices': total_invoices,
        'with_remarks': with_remarks,
        'without_remarks': without_remarks,
    }
    
    return render(request, 'dashboard/additional_supply_management.html', context)

@login_required
def additional_supply_edit_view(request, inquiry_id):
    """Edit additional supply remarks for GRN status inquiry"""
    inquiry = get_object_or_404(InquiryHandler, id=inquiry_id, status='GRN')
    
    if request.method == 'POST':
        form = AdditionalSupplyForm(request.POST, instance=inquiry)
        
        if form.is_valid():
            inquiry = form.save()
            messages.success(request, f'Additional Supply remarks for {inquiry.create_id} updated successfully!')
            return redirect('dashboard:additional_supply_management')
        else:
            # Add detailed error messages for debugging
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = AdditionalSupplyForm(instance=inquiry)
    
    return render(request, 'dashboard/additional_supply_form.html', {
        'form': form,
        'title': f'Edit Additional Supply: {inquiry.create_id}',
        'action': 'Update',
        'inquiry_obj': inquiry,
        'is_edit': True
    })

# Quotation Generation Views
from django.shortcuts import render
from django.http import HttpResponse
from django.conf import settings
from docx import Document
from docx.enum.text import WD_COLOR_INDEX
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from io import BytesIO
import os
from docx.shared import Inches, Mm
from docx.enum.dml import MSO_THEME_COLOR_INDEX
from docx.enum.text import WD_COLOR_INDEX
from copy import deepcopy

# Fixed image width to insert into table cells (in millimetres). Adjust to 60/70/80 as needed.
IMAGE_WIDTH_MM = 38.1

def seek_and_replace(doc, replacements):
    """Replace text in DOCX while preserving formatting, especially for highlighted text"""
    
    def replace_in_paragraph(paragraph, replacements):
        # Get full text from all runs
        full_text = "".join(run.text for run in paragraph.runs)
        replaced_text = full_text
        
        # Try replacements on full text
        for old, new in replacements.items():
            if new and old in replaced_text:
                replaced_text = replaced_text.replace(old, new)
        
        # If text changed, rebuild the paragraph
        if replaced_text != full_text:
            # Check if any run has highlighting
            has_highlighted = any(run.font.highlight_color == WD_COLOR_INDEX.YELLOW for run in paragraph.runs)
            
            if has_highlighted:
                # Keep first run's formatting and clear others
                first_run = paragraph.runs[0] if paragraph.runs else None
                if first_run:
                    # Clear all runs
                    for run in paragraph.runs[1:]:
                        run.text = ""
                    # Set new text in first run
                    first_run.text = replaced_text
            else:
                # Non-highlighted text - simple replacement
                for run in paragraph.runs:
                    run.text = ""
                if paragraph.runs:
                    paragraph.runs[0].text = replaced_text
    
    def replace_in_table(table, replacements, is_pricing_table=False):
        for row_idx, row in enumerate(table.rows):
            for cell_idx, cell in enumerate(row.cells):
                # Skip Sr column (column 0) in pricing table to preserve sequential numbers
                if is_pricing_table and cell_idx == 0:
                    continue  # Skip Sr column replacement
                
                # Skip image cells (column 3 in pricing table)
                if is_pricing_table and cell_idx == 3:  # Pricing table image column
                    # Check if this is a fixture row (has serial number)
                    if len(row.cells) > 0 and row.cells[0].text.strip().isdigit():
                        continue  # Skip image cell replacement for fixture rows
                
                for para in cell.paragraphs:
                    replace_in_paragraph(para, replacements)
                for inner_table in cell.tables:
                    replace_in_table(inner_table, replacements)
    
    # Replace in paragraphs
    for para in doc.paragraphs:
        replace_in_paragraph(para, replacements)
    
    # Replace in tables
    for table_idx, table in enumerate(doc.tables):
        is_pricing_table = (table_idx == 1)  # Second table is the pricing table
        replace_in_table(table, replacements, is_pricing_table)
    
    # Replace in headers and footers
    for section in doc.sections:
        for para in section.header.paragraphs:
            replace_in_paragraph(para, replacements)
        for para in section.footer.paragraphs:
            replace_in_paragraph(para, replacements)
    
    print(f"Text replacements completed for {len(replacements)} items")
    return doc

def _insert_image_in_cell(cell, image_bytes):
    """Insert image into cell, clearing existing content first"""
    if not image_bytes:
        print("No image bytes provided")
        return False
    
    try:
        # Check if Pillow is available for image processing
        try:
            from PIL import Image
            print("Pillow is available for image processing")
        except ImportError:
            print("Warning: Pillow not installed. Image upload feature disabled.")
            return False
        
        print(f"Processing image of size: {len(image_bytes)} bytes")
        
        # Create image stream and validate
        img_stream = BytesIO(image_bytes)
        img_stream.seek(0)
        
        # Validate and process image
        try:
            with Image.open(img_stream) as img:
                print(f"Original image: {img.format}, {img.mode}, {img.size}")
                
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'LA', 'P'):
                    print(f"Converting image from {img.mode} to RGB")
                    img = img.convert('RGB')
                
                # Resize image if too large (max 800px width)
                if img.width > 800:
                    ratio = 800 / img.width
                    new_height = int(img.height * ratio)
                    img = img.resize((800, new_height), Image.Resampling.LANCZOS)
                    print(f"Resized image to: {img.size}")
                
                # Save as JPEG to ensure compatibility
                processed_stream = BytesIO()
                img.save(processed_stream, format='JPEG', quality=85, optimize=True)
                processed_stream.seek(0)
                print(f"Processed image size: {len(processed_stream.getvalue())} bytes")
                
        except Exception as img_error:
            print(f"Error processing image: {img_error}")
            return False
        
        # Clear cell content
        print("Clearing cell content")
        cell.text = ""
        
        # Remove all existing paragraphs
        for paragraph in cell.paragraphs:
            p = paragraph._element
            p.getparent().remove(p)
        
        # Add new paragraph
        paragraph = cell.add_paragraph()
        run = paragraph.add_run()
        
        # Set paragraph alignment to center
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # Add image to document with proper sizing
        try:
            processed_stream.seek(0)
            run.add_picture(processed_stream, width=Mm(IMAGE_WIDTH_MM))
            print(f"Successfully added image to cell with width {IMAGE_WIDTH_MM}mm")
        except Exception as docx_error:
            print(f"Error adding image to DOCX: {docx_error}")
            return False
        
        # Mark the cell as having an image
        cell._element.set('image_inserted', 'true')
        print("Image insertion completed successfully")
        return True
        
    except Exception as e:
        print(f"Error inserting image: {e}")
        import traceback
        traceback.print_exc()
        return False

def add_fixture_rows_to_table(table, fixtures_data):
    """Add additional fixture rows dynamically for fixtures beyond the first 2"""
    if len(fixtures_data) <= 2:
        return  # No additional rows needed
    
    print(f"=== ADDING ROWS FOR {len(fixtures_data) - 2} ADDITIONAL FIXTURES ===")
    
    # Find column positions from header
    column_positions = {}
    if len(table.rows) > 0:
        header_row = table.rows[0]
        for col_idx, cell in enumerate(header_row.cells):
            header_text = cell.text.strip().lower()
            if 'sr' in header_text or 'serial' in header_text:
                column_positions['sr'] = col_idx
            elif 'description' in header_text:
                column_positions['description'] = col_idx
            elif 'image' in header_text:
                column_positions['image'] = col_idx
            elif 'qty' in header_text or 'quantity' in header_text:
                column_positions['qty'] = col_idx
            elif 'rate' in header_text:
                column_positions['rate'] = col_idx
            elif 'per' in header_text or 'unit' in header_text:
                column_positions['per'] = col_idx
            elif 'amount' in header_text:
                column_positions['amount'] = col_idx
    
    # Template rows to clone (fixture row and its corresponding words row)
    template_fixture_row = table.rows[1] if len(table.rows) > 1 else None  # First fixture row
    template_words_row = table.rows[2] if len(table.rows) > 2 else None    # First words row
    
    if not template_fixture_row:
        print("No template fixture row found")
        return
    
    # Insert position should be at the end of existing rows
    insert_position = len(table.rows)
    
    for idx in range(2, len(fixtures_data)):  # Start from 3rd fixture
        fixture = fixtures_data[idx]
        
        print(f"Adding fixture {idx + 1}")
        
        # Clone fixture row and insert it at the correct position
        new_fixture_row = _clone_row_at_position(table, template_fixture_row, insert_position)
        insert_position += 1
        
        # Fill in the fixture data using column positions
        cells = new_fixture_row.cells
        
        try:
            # Clear all cells first
            for cell in cells:
                cell.text = ""
            
            # Place Sr number in Sr column
            if 'sr' in column_positions and column_positions['sr'] < len(cells):
                cells[column_positions['sr']].text = str(idx + 1)
                print(f"Set Sr to '{idx + 1}' in column {column_positions['sr']}")
            
            # Place description in Description column
            if 'description' in column_positions and column_positions['description'] < len(cells):
                desc_lines = []
                if fixture.get('name') or fixture.get('desc'):
                    desc_lines.append(f"{fixture.get('name', '')} {fixture.get('desc', '')}".strip())
                desc_lines.append("(as per annexure)")
                if fixture.get('hsn'):
                    desc_lines.append(f"HSN Code: {fixture.get('hsn')}")
                if fixture.get('specifications', '').strip():
                    desc_lines.append(f"Specifications: {fixture.get('specifications')}")
                
                description_text = "\n".join(desc_lines)
                cells[column_positions['description']].text = description_text
                print(f"Set description in column {column_positions['description']}")
            
            # Place image in Image column
            if 'image' in column_positions and column_positions['image'] < len(cells):
                if fixture.get('image'):
                    success = _insert_image_in_cell(cells[column_positions['image']], fixture.get('image'))
                    if not success:
                        cells[column_positions['image']].text = f"[Image: {fixture.get('name', 'Product')}]"
                else:
                    cells[column_positions['image']].text = ""
            
            # Place other data in correct columns
            if 'qty' in column_positions and column_positions['qty'] < len(cells):
                cells[column_positions['qty']].text = fixture.get('qty', '1')
            
            if 'rate' in column_positions and column_positions['rate'] < len(cells):
                cells[column_positions['rate']].text = fixture.get('price', '')
            
            if 'per' in column_positions and column_positions['per'] < len(cells):
                cells[column_positions['per']].text = fixture.get('unit', 'Set')
            
            if 'amount' in column_positions and column_positions['amount'] < len(cells):
                cells[column_positions['amount']].text = fixture.get('total', '')
            
            print(f"Successfully added fixture {idx + 1}")
            
        except Exception as e:
            print(f"Error filling fixture data for fixture {idx + 1}: {e}")
            continue
        
        # Clone words row immediately after the fixture row
        if template_words_row:
            new_words_row = _clone_row_at_position(table, template_words_row, insert_position)
            insert_position += 1
            
            # Set the "In Words" text
            try:
                words_cells = new_words_row.cells
                
                # Clear all cells first
                for cell in words_cells:
                    cell.text = ""
                
                # Clear Sr column
                if 'sr' in column_positions and column_positions['sr'] < len(words_cells):
                    words_cells[column_positions['sr']].text = ""
                
                # Set words text starting from Description column
                words_text = f"In Words: {fixture.get('words', '')}"
                start_col = column_positions.get('description', 1)
                for col_idx in range(start_col, len(words_cells)):
                    words_cells[col_idx].text = words_text
                
                print(f"Set words text for fixture {idx + 1}")
                
            except Exception as e:
                print(f"Error setting words text for fixture {idx + 1}: {e}")
    
    print(f"=== COMPLETED ADDING {len(fixtures_data) - 2} ADDITIONAL FIXTURES ===")

def _clone_row_at_position(table, source_row, insert_position):
    """Clone a complete row with all cell properties and merged cells at specific position"""
    from copy import deepcopy
    
    # Clone the row element completely
    new_row_element = deepcopy(source_row._element)
    
    # Get the table element
    tbl_element = table._element
    
    # Insert the new row at the specified position
    if insert_position >= len(table.rows):
        # Append to end
        tbl_element.append(new_row_element)
    else:
        # Insert at specific position
        existing_row = table.rows[insert_position]._element
        tbl_element.insert(tbl_element.index(existing_row), new_row_element)
    
    # Return the newly created row
    # We need to refresh the table rows to get the correct row object
    return table.rows[insert_position]

def populate_pricing_table_with_fixtures(table, fixtures_data):
    """DYNAMIC column-wise data placement - works for ANY number of fixtures"""
    if not fixtures_data:
        return
    
    print(f"=== DYNAMIC TABLE POPULATION FOR {len(fixtures_data)} FIXTURES ===")
    print(f"Table has {len(table.rows)} rows, {len(table.columns)} columns")
    
    # STEP 1: Find column positions by reading headers
    column_positions = {}
    if len(table.rows) > 0:
        header_row = table.rows[0]
        for col_idx, cell in enumerate(header_row.cells):
            header_text = cell.text.strip().lower()
            print(f"Column {col_idx}: '{header_text}'")
            
            if 'sr' in header_text or 'serial' in header_text:
                column_positions['sr'] = col_idx
            elif 'description' in header_text:
                column_positions['description'] = col_idx
            elif 'image' in header_text:
                column_positions['image'] = col_idx
            elif 'qty' in header_text or 'quantity' in header_text:
                column_positions['qty'] = col_idx
            elif 'rate' in header_text:
                column_positions['rate'] = col_idx
            elif 'per' in header_text or 'unit' in header_text:
                column_positions['per'] = col_idx
            elif 'amount' in header_text:
                column_positions['amount'] = col_idx
    
    print(f"Column positions found: {column_positions}")
    
    # STEP 2: Find ALL fixture rows dynamically (not just first 2)
    fixture_rows = []
    for r_idx in range(1, len(table.rows)):  # Skip header row
        row = table.rows[r_idx]
        row_text = " ".join([cell.text.strip() for cell in row.cells]).lower()
        
        # Check for any fixture pattern
        if "fixture" in row_text and ("holding" in row_text or "pulling" in row_text or "connector" in row_text or "pcba" in row_text):
            # Try to determine fixture number from the row
            fixture_num = None
            if "fixture 1" in row_text or "holding" in row_text:
                fixture_num = 0
            elif "fixture 2" in row_text or "pulling" in row_text:
                fixture_num = 1
            else:
                # For fixtures beyond 2, try to extract number or assign sequentially
                for i in range(len(fixtures_data)):
                    if f"fixture {i+1}" in row_text:
                        fixture_num = i
                        break
                
                # If still not found, assign based on order
                if fixture_num is None:
                    fixture_num = len(fixture_rows)
            
            if fixture_num is not None and fixture_num < len(fixtures_data):
                fixture_rows.append((r_idx, fixture_num))
                print(f"Found Fixture {fixture_num + 1} at row {r_idx}")
    
    print(f"Found {len(fixture_rows)} fixture rows for {len(fixtures_data)} fixtures")
    
    # STEP 3: Process ALL fixtures dynamically
    for row_idx, fixture_idx in fixture_rows:
        if fixture_idx >= len(fixtures_data):
            continue
            
        fixture = fixtures_data[fixture_idx]
        row = table.rows[row_idx]
        cells = row.cells
        
        print(f"=== PLACING DATA FOR FIXTURE {fixture_idx + 1} IN ROW {row_idx} ===")
        
        # CLEAR only the data cells (not image cells) to prevent mixing
        for col_name, col_idx in column_positions.items():
            if col_name != 'image' and col_idx < len(cells):
                cells[col_idx].text = ""
        
        # Place Sr number in Sr column
        if 'sr' in column_positions and column_positions['sr'] < len(cells):
            sr_col = column_positions['sr']
            cells[sr_col].text = str(fixture_idx + 1)
            print(f"Placed Sr '{fixture_idx + 1}' in column {sr_col}")
        
        # Place description in Description column
        if 'description' in column_positions and column_positions['description'] < len(cells):
            desc_col = column_positions['description']
            desc_lines = []
            if fixture.get('name') or fixture.get('desc'):
                desc_lines.append(f"{fixture.get('name', '')} {fixture.get('desc', '')}".strip())
            desc_lines.append("(as per annexure)")
            if fixture.get('hsn'):
                desc_lines.append(f"HSN Code: {fixture.get('hsn')}")
            if fixture.get('specifications', '').strip():
                desc_lines.append(f"Specifications: {fixture.get('specifications')}")
            
            description_text = "\n".join(desc_lines)
            cells[desc_col].text = description_text
            print(f"Placed description in column {desc_col}")
        
        # Place image in Image column
        if 'image' in column_positions and column_positions['image'] < len(cells):
            img_col = column_positions['image']
            if fixture.get('image'):
                success = _insert_image_in_cell(cells[img_col], fixture.get('image'))
                if not success:
                    cells[img_col].text = f"[Image: {fixture.get('name', 'Product')}]"
                print(f"Placed image in column {img_col}")
            else:
                cells[img_col].text = ""
        
        # Place quantity in Qty column
        if 'qty' in column_positions and column_positions['qty'] < len(cells):
            qty_col = column_positions['qty']
            cells[qty_col].text = fixture.get('qty', '1')
            print(f"Placed qty '{fixture.get('qty', '1')}' in column {qty_col}")
        
        # Place rate in Rate column
        if 'rate' in column_positions and column_positions['rate'] < len(cells):
            rate_col = column_positions['rate']
            cells[rate_col].text = fixture.get('price', '')
            print(f"Placed rate '{fixture.get('price', '')}' in column {rate_col}")
        
        # Place unit in Per column
        if 'per' in column_positions and column_positions['per'] < len(cells):
            per_col = column_positions['per']
            cells[per_col].text = fixture.get('unit', 'Set')
            print(f"Placed per '{fixture.get('unit', 'Set')}' in column {per_col}")
        
        # Place amount in Amount column
        if 'amount' in column_positions and column_positions['amount'] < len(cells):
            amount_col = column_positions['amount']
            cells[amount_col].text = fixture.get('total', '')
            print(f"Placed amount '{fixture.get('total', '')}' in column {amount_col}")
    
    # STEP 4: Handle "In Words" rows dynamically
    words_rows = []
    for r_idx in range(1, len(table.rows)):
        row = table.rows[r_idx]
        row_text = " ".join([cell.text.strip() for cell in row.cells]).lower()
        if "in words:" in row_text:
            words_rows.append(r_idx)
    
    print(f"Found {len(words_rows)} words rows")
    
    # Process words rows for ALL fixtures
    for i, row_idx in enumerate(words_rows):
        if i < len(fixtures_data):
            fixture = fixtures_data[i]
            row = table.rows[row_idx]
            cells = row.cells
            
            # Clear Sr column
            if 'sr' in column_positions and column_positions['sr'] < len(cells):
                cells[column_positions['sr']].text = ""
            
            # Place words text starting from Description column
            words_text = f"In Words: {fixture.get('words', '')}"
            start_col = column_positions.get('description', 1)
            for col_idx in range(start_col, len(cells)):
                cells[col_idx].text = words_text
            
            print(f"Placed words for fixture {i + 1} in row {row_idx}")
    
    print("=== DYNAMIC TABLE POPULATION COMPLETE ===")
    
    # VERIFICATION: Show what's in each column for all fixtures
    print("=== VERIFICATION FOR ALL FIXTURES ===")
    fixture_count = 0
    for r_idx in range(min(20, len(table.rows))):  # Check more rows for multiple fixtures
        row = table.rows[r_idx]
        cells = row.cells
        
        # Check if this is a fixture row
        if 'sr' in column_positions and column_positions['sr'] < len(cells):
            sr_text = cells[column_positions['sr']].text.strip()
            if sr_text.isdigit():
                fixture_count += 1
                print(f"Fixture {sr_text} (Row {r_idx}):")
                for col_name, col_idx in column_positions.items():
                    if col_idx < len(cells):
                        cell_text = cells[col_idx].text.strip()[:30]
                        if cell_text:
                            print(f"  {col_name} (col {col_idx}): '{cell_text}'")
    
    print(f"Verified {fixture_count} fixtures in table")

def insert_images_in_inclusion_section(doc, fixtures_data):
    """IMPROVED APPROACH: Keep original Inclusions section, just add images properly with correct font size"""
    try:
        print("=== IMPROVED APPROACH: ADDING IMAGES TO EXISTING INCLUSION SECTION ===")
        print(f"Processing {len(fixtures_data)} fixtures")
        
        # Find the inclusion section paragraph that contains the actual fixture content
        inclusion_content_paragraph = None
        inclusion_para_index = -1
        
        for para_idx, paragraph in enumerate(doc.paragraphs):
            para_text = paragraph.text.strip()
            # Look for paragraph that contains fixture content (not just the header)
            if ("1. Product Name:" in para_text or 
                "Product Name:" in para_text and len(para_text) > 50):
                inclusion_content_paragraph = paragraph
                inclusion_para_index = para_idx
                print(f"Found inclusion content at paragraph {para_idx}")
                print(f"Original content: '{para_text[:100]}...'")
                break
        
        if not inclusion_content_paragraph:
            print("Could not find inclusion content paragraph")
            return
        
        # Clear the existing content paragraph and rebuild it with images
        inclusion_content_paragraph.clear()
        
        # Build new inclusion content with images in the SAME paragraph location
        from docx.shared import Mm, Pt
        from io import BytesIO
        
        for idx, fixture in enumerate(fixtures_data, 1):
            if not (fixture.get('name') or fixture.get('desc')):
                continue
                
            print(f"Adding fixture {idx}: {fixture.get('name', 'Unknown')}")
            
            # Add the fixture number and product name with 16pt font
            run = inclusion_content_paragraph.add_run(f"{idx}. Product Name: {fixture.get('name', f'Fixture {idx}')}")
            run.font.size = Pt(16)  # Set font size to 16pt
            inclusion_content_paragraph.add_run().add_break()
            
            # Add image if available - RIGHT AFTER Product Name (smaller size)
            if fixture.get('image'):
                try:
                    img_stream = BytesIO(fixture['image'])
                    img_stream.seek(0)
                    img_run = inclusion_content_paragraph.add_run()
                    img_run.add_picture(img_stream, width=Mm(35))  # Reduced from 50mm to 35mm
                    inclusion_content_paragraph.add_run().add_break()
                    print(f"✅ Added image for fixture {idx} (35mm width)")
                except Exception as img_error:
                    print(f"❌ Failed to add image for fixture {idx}: {img_error}")
                    error_run = inclusion_content_paragraph.add_run("   [Image could not be loaded]")
                    error_run.font.size = Pt(16)
                    inclusion_content_paragraph.add_run().add_break()
            
            # Add description with 16pt font
            if fixture.get('desc'):
                desc_run = inclusion_content_paragraph.add_run(f"   Description: {fixture['desc']}")
                desc_run.font.size = Pt(16)
                inclusion_content_paragraph.add_run().add_break()
            
            # Add standard text with 16pt font
            annexure_run = inclusion_content_paragraph.add_run("   (as per annexure)")
            annexure_run.font.size = Pt(16)
            inclusion_content_paragraph.add_run().add_break()
            
            # Add HSN Code with 16pt font
            if fixture.get('hsn'):
                hsn_run = inclusion_content_paragraph.add_run(f"   HSN Code: {fixture['hsn']}")
                hsn_run.font.size = Pt(16)
                inclusion_content_paragraph.add_run().add_break()
            
            # Add specifications with 16pt font
            if fixture.get('specifications', '').strip():
                spec_run = inclusion_content_paragraph.add_run(f"   Specifications: {fixture['specifications']}")
                spec_run.font.size = Pt(16)
                inclusion_content_paragraph.add_run().add_break()
            
            # Add spacing between fixtures (except for the last one)
            if idx < len([f for f in fixtures_data if f.get('name') or f.get('desc')]):
                inclusion_content_paragraph.add_run().add_break()
        
        print("=== INCLUSION SECTION UPDATED WITH 16PT FONT AND 35MM IMAGES ===")
        
    except Exception as e:
        print(f"❌ Error updating inclusion section: {e}")
        import traceback
        traceback.print_exc()

@login_required
def quotation_view(request):
    """Quotation generator page"""
    return render(request, 'dashboard/quotation_generator.html')

@login_required
def generate_quotation(request):
    """Generate quotation document with proper image handling and specifications"""
    if request.method == 'POST':
        try:
            # Collect form data
            quote_data = {
                'quote_no': request.POST.get('quote_no', 'KEC005JN2025'),
                'revision': request.POST.get('revision', 'Rev A'),
                'date': request.POST.get('date', 'Wednesday, September 24, 2025'),
                'to_person': request.POST.get('to_person', 'Mr. Mohak Dholakia'),
                'firm': request.POST.get('firm', 'Schneider Electric India Private Limited'),
                'address': request.POST.get('address', ''),
                'payment_terms': request.POST.get('payment_terms', 'Payment: 45 Days from delivery (Being an MSME)'),
                'delivery_terms': request.POST.get('delivery_terms', 'Delivery: 2-3 weeks per fixture from Purchase Order'),
            }
            
            # Process fixtures with image handling
            fixtures = []
            fixture_index = 0
            
            while True:
                name_key = f'fixtures[{fixture_index}][name]'
                if name_key not in request.POST:
                    break
                    
                fixture = {
                    'name': request.POST.get(name_key, ''),
                    'desc': request.POST.get(f'fixtures[{fixture_index}][desc]', ''),
                    'hsn': request.POST.get(f'fixtures[{fixture_index}][hsn]', '84790000'),
                    'qty': request.POST.get(f'fixtures[{fixture_index}][qty]', '1'),
                    'unit': request.POST.get(f'fixtures[{fixture_index}][unit]', 'Set'),
                    'price': request.POST.get(f'fixtures[{fixture_index}][price]', ''),
                    'total': request.POST.get(f'fixtures[{fixture_index}][total]', ''),
                    'words': request.POST.get(f'fixtures[{fixture_index}][words]', ''),
                    'specifications': request.POST.get(f'fixtures[{fixture_index}][specifications]', ''),
                    'has_image': False,
                    'image': None,
                }
                
                # Handle image upload for this fixture
                image_key = f'fixtures[{fixture_index}][image]'
                if image_key in request.FILES:
                    uploaded_file = request.FILES[image_key]
                    if uploaded_file and uploaded_file.size > 0:
                        try:
                            image_bytes = uploaded_file.read()
                            fixture['image'] = image_bytes
                            fixture['has_image'] = True
                            print(f"Processed image for fixture {fixture_index + 1}: {len(image_bytes)} bytes")
                        except Exception as img_error:
                            print(f"Error processing image for fixture {fixture_index + 1}: {img_error}")
                            fixture['has_image'] = False
                            fixture['image'] = None
                
                fixtures.append(fixture)
                fixture_index += 1
            
            # Ensure we have at least 2 fixtures for template compatibility
            while len(fixtures) < 2:
                fixtures.append({
                    'name': f'Fixture {len(fixtures) + 1}',
                    'desc': '',
                    'hsn': '84790000',
                    'qty': '1',
                    'unit': 'Set',
                    'price': '',
                    'total': '',
                    'words': '',
                    'specifications': '',
                    'has_image': False,
                    'image': None,
                })
            
            # Build content for tag-based replacements with enhanced inclusion section
            inclusion_items = []
            scope_items = []
            specification_items = []
            
            for idx, fixture in enumerate(fixtures, 1):
                if fixture['name'] or fixture['desc']:
                    # Enhanced inclusion with Product Name, Image, Description, and Specifications
                    inclusion_parts = []
                    
                    # Product Name (this will be the line we search for)
                    if fixture.get('name'):
                        inclusion_parts.append(f"Product Name: {fixture['name']}")
                    
                    # Product Image will be inserted after Product Name (handled separately)
                    
                    # Description
                    if fixture.get('desc'):
                        inclusion_parts.append(f"Description: {fixture['desc']}")
                    
                    # Additional details
                    inclusion_parts.append("(as per annexure)")
                    
                    if fixture.get('hsn'):
                        inclusion_parts.append(f"HSN Code: {fixture['hsn']}")
                    
                    # Specifications
                    if fixture.get('specifications', '').strip():
                        inclusion_parts.append(f"Specifications: {fixture['specifications']}")
                    
                    # Combine all parts for this fixture - EACH FIXTURE GETS ITS OWN BLOCK
                    inclusion_text = f"{idx}. " + "\n   ".join(inclusion_parts)
                    inclusion_items.append({
                        'text': inclusion_text,
                        'image': fixture.get('image') if fixture.get('has_image') or fixture.get('image') else None,
                        'fixture_name': fixture.get('name', f'Fixture {idx}')
                    })
                    
                    # Scope items (simpler format)
                    scope_items.append(f"{idx}. {fixture['name']} - {fixture['desc']}")
                
                # Specifications for separate section
                if fixture.get('specifications', '').strip():
                    spec_item = f"{idx}. {fixture['name']}:\n{fixture['specifications']}"
                    specification_items.append(spec_item)
            
            # Build final content strings - SEPARATE EACH FIXTURE WITH DOUBLE LINE BREAKS
            inclusion_content = "\n\n".join([item['text'] for item in inclusion_items]) if inclusion_items else "Fixtures as per discussion"
            scope_content = "\n".join(scope_items) if scope_items else "Design & manufacturing of fixtures as per discussion"
            specification_content = "\n\n".join(specification_items) if specification_items else "Specifications as per discussion and drawings."
            
            # Prepare fixtures data for database (without image bytes)
            # Note: Image bytes cannot be stored in JSONField, so we only store metadata
            # Images are processed during document generation but not persisted
            fixtures_for_db = []
            for fixture in fixtures:
                db_fixture = dict(fixture)
                # Remove image bytes before saving to database
                if 'image' in db_fixture:
                    del db_fixture['image']
                fixtures_for_db.append(db_fixture)
            
            # Save to database
            quotation = Quotation.objects.create(
                quote_number=quote_data['quote_no'],
                revision=quote_data['revision'],
                quotation_date=quote_data['date'],
                to_person=quote_data['to_person'],
                firm=quote_data['firm'],
                address=quote_data['address'],
                payment_terms=quote_data['payment_terms'],
                delivery_terms=quote_data['delivery_terms'],
                scope_description=scope_content,
                fixtures_data=fixtures_for_db,
                fixtures_count=len(fixtures),
                status='generated',
                created_by=request.user
            )
            
            # Load template
            from pathlib import Path
            BASE_DIR = Path(__file__).resolve().parent.parent
            template_path = os.path.join(BASE_DIR, 'Quote KEC005JN2025 RevA - new format full_1.docx')
            doc = Document(template_path)
            
            # Prepare replacements for tag-based system
            replacements = {
                # Basic document info
                "KEC005JN2025": quote_data['quote_no'],
                "Rev A": quote_data['revision'],
                "Wednesday, September 24, 2025": quote_data['date'],
                "Mr. Mohak Dholakia": quote_data['to_person'],
                "Schneider Electric India Private Limited": quote_data['firm'],
                "Electrical & Automation (E&A), Village Ankhol, Behind L&T Knowledge City, N. H. 8, Between Ajwa-Waghodia Junction, Vadodara –390019. India": quote_data['address'],
                
                # Terms
                "Payment: 45 Days from delivery (Being an MSME)": quote_data['payment_terms'],
                "Delivery: 2-3 weeks per fixture from Purchase Order (Gov. force majeure conditions apply at time of delivery)": quote_data['delivery_terms'],
                
                # Tag-based content sections
                "<inclusion>": inclusion_content,
                "<scope>": scope_content,
                "<specification>": specification_content,
                "< specification>": specification_content,  # Handle the space variant
                
                # Price replacements only (avoid fixture name replacements that interfere with Sr column)
                "26,879/-": fixtures[0]['price'] if fixtures[0]['price'] else "26,879/-",
                "Twenty-Six Thousand Eight Hundred Seventy-Nine INR Only PER EACH": fixtures[0]['words'] if fixtures[0]['words'] else "Twenty-Six Thousand Eight Hundred Seventy-Nine INR Only PER EACH",
                
                "29,546/-": fixtures[1]['price'] if fixtures[1]['price'] else "29,546/-",
                "Twenty-Nine Thousand Five Hundred Forty-Six INR Only PER EACH": fixtures[1]['words'] if fixtures[1]['words'] else "Twenty-Nine Thousand Five Hundred Forty-Six INR Only PER EACH",
            }
            
            # Apply text replacements using the advanced seek_and_replace function
            doc = seek_and_replace(doc, replacements)
            
            # Insert images in inclusion section after text replacements
            insert_images_in_inclusion_section(doc, fixtures)
            
            # CRITICAL: Handle pricing table AFTER all text replacements to prevent interference
            print("=== STARTING TABLE PROCESSING ===")
            if len(doc.tables) > 1:
                pricing_table = doc.tables[1]  # Second table is the pricing table
                print(f"Found pricing table with {len(pricing_table.rows)} rows")
                
                # AGGRESSIVE: Populate existing fixture rows with forced content
                populate_pricing_table_with_fixtures(pricing_table, fixtures)
                
                # Add additional fixture rows if needed (beyond the first 2)
                if len(fixtures) > 2:
                    print(f"Adding {len(fixtures) - 2} additional fixture rows")
                    add_fixture_rows_to_table(pricing_table, fixtures)
                    
                # FINAL VERIFICATION: Check if our changes took effect
                print("=== POST-PROCESSING VERIFICATION ===")
                for r_idx in range(min(6, len(pricing_table.rows))):
                    try:
                        row = pricing_table.rows[r_idx]
                        first_cell = row.cells[0].text.strip() if len(row.cells) > 0 else "N/A"
                        second_cell = row.cells[1].text.strip()[:50] + "..." if len(row.cells) > 1 and len(row.cells[1].text.strip()) > 50 else row.cells[1].text.strip() if len(row.cells) > 1 else "N/A"
                        print(f"Final Row {r_idx}: Sr='{first_cell}' | Desc='{second_cell}'")
                    except Exception as e:
                        print(f"Final Row {r_idx}: Error - {e}")
                        
            else:
                print("WARNING: Could not find pricing table")
            print("=== TABLE PROCESSING COMPLETE ===")
            
            # Save to buffer and return
            buffer = BytesIO()
            doc.save(buffer)
            buffer.seek(0)
            
            # Update quotation status
            quotation.status = 'generated'
            quotation.save()
            
            messages.success(request, f'Quotation {quotation.quote_number} generated successfully!')
            
            # Return as download
            from django.http import HttpResponse
            response = HttpResponse(
                buffer.read(),
                content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            )
            response['Content-Disposition'] = f'attachment; filename="Quotation_{quote_data["quote_no"]}.docx"'
            return response
            
        except Exception as e:
            messages.error(request, f'Error generating quotation: {str(e)}')
            import traceback
            traceback.print_exc()
            return render(request, 'dashboard/quotation_generator.html', {'error': str(e)})
    
    return render(request, 'dashboard/quotation_generator.html')

@login_required
def quotation_management_view(request):
    """Quotation management page with list of generated quotations"""
    search_query = request.GET.get('search', '')
    
    # Get quotations from database
    quotations = Quotation.objects.all()
    
    # Apply search filter if provided
    if search_query:
        quotations = quotations.filter(
            models.Q(quote_number__icontains=search_query) |
            models.Q(firm__icontains=search_query) |
            models.Q(to_person__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(quotations, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Calculate statistics
    total_count = Quotation.objects.count()
    generated_count = Quotation.objects.filter(status='generated').count()
    draft_count = Quotation.objects.filter(status='draft').count()
    this_month_count = Quotation.objects.filter(
        created_at__month=datetime.now().month,
        created_at__year=datetime.now().year
    ).count()
    
    context = {
        'quotations': page_obj,
        'search_query': search_query,
        'total_count': total_count,
        'generated_count': generated_count,
        'draft_count': draft_count,
        'this_month_count': this_month_count,
    }
    
    return render(request, 'dashboard/quotation_management.html', context)

@login_required
def quotation_view_details(request, quotation_id):
    """View quotation details"""
    quotation = get_object_or_404(Quotation, id=quotation_id)
    context = {
        'quotation': quotation,
        'fixtures': quotation.fixtures_data,
    }
    return render(request, 'dashboard/quotation_details.html', context)

@login_required
def quotation_edit(request, quotation_id):
    """Edit existing quotation"""
    quotation = get_object_or_404(Quotation, id=quotation_id)
    
    if request.method == 'POST':
        try:
            # Update quotation data
            quotation.quote_number = request.POST.get('quote_no', quotation.quote_number)
            quotation.revision = request.POST.get('revision', quotation.revision)
            quotation.quotation_date = request.POST.get('date', quotation.quotation_date)
            quotation.to_person = request.POST.get('to_person', quotation.to_person)
            quotation.firm = request.POST.get('firm', quotation.firm)
            quotation.address = request.POST.get('address', quotation.address)
            quotation.payment_terms = request.POST.get('payment_terms', quotation.payment_terms)
            quotation.delivery_terms = request.POST.get('delivery_terms', quotation.delivery_terms)
            quotation.scope_description = request.POST.get('scope_desc', quotation.scope_description)
            quotation.scope_line_1 = request.POST.get('scope_1', quotation.scope_line_1)
            quotation.scope_line_2 = request.POST.get('scope_2', quotation.scope_line_2)
            
            # Process fixtures
            fixtures_data = []
            fixture_index = 0
            
            while True:
                name_key = f'fixtures[{fixture_index}][name]'
                if name_key not in request.POST:
                    break
                    
                fixture = {
                    'name': request.POST.get(name_key, ''),
                    'desc': request.POST.get(f'fixtures[{fixture_index}][desc]', ''),
                    'hsn': request.POST.get(f'fixtures[{fixture_index}][hsn]', ''),
                    'qty': request.POST.get(f'fixtures[{fixture_index}][qty]', ''),
                    'unit': request.POST.get(f'fixtures[{fixture_index}][unit]', ''),
                    'price': request.POST.get(f'fixtures[{fixture_index}][price]', ''),
                    'total': request.POST.get(f'fixtures[{fixture_index}][total]', ''),
                    'words': request.POST.get(f'fixtures[{fixture_index}][words]', ''),
                    'specifications': request.POST.get(f'fixtures[{fixture_index}][specifications]', ''),
                    'has_image': False,  # For edit, we don't handle image uploads currently
                }
                fixtures_data.append(fixture)
                fixture_index += 1
            
            quotation.fixtures_data = fixtures_data
            quotation.fixtures_count = len(fixtures_data)
            quotation.save()
            
            messages.success(request, f'Quotation {quotation.quote_number} updated successfully!')
            return redirect('dashboard:quotation_management')
            
        except Exception as e:
            messages.error(request, f'Error updating quotation: {str(e)}')
    
    context = {
        'quotation': quotation,
        'is_edit': True,
        'title': 'Edit Quotation',
        'action': 'Edit',
    }
    return render(request, 'dashboard/quotation_form.html', context)

@login_required
def quotation_delete(request, quotation_id):
    """Delete quotation"""
    quotation = get_object_or_404(Quotation, id=quotation_id)
    
    if request.method == 'POST':
        quote_number = quotation.quote_number
        quotation.delete()
        messages.success(request, f'Quotation {quote_number} deleted successfully!')
        return redirect('dashboard:quotation_management')
    
    context = {
        'quotation': quotation,
    }
    return render(request, 'dashboard/quotation_delete.html', context)

@login_required
def quotation_download(request, quotation_id):
    """Download existing quotation with proper functionality"""
    quotation = get_object_or_404(Quotation, id=quotation_id)
    
    try:
        # Prepare replacements for document generation
        replacements = {
            # Basic Info
            "KEC005JN2025": quotation.quote_number,
            "Rev A": quotation.revision,
            "Wednesday, September 24, 2025": quotation.quotation_date,
            "Mr. Mohak Dholakia": quotation.to_person,
            "Schneider Electric India Private Limited": quotation.firm,
            "Electrical & Automation (E&A), Village Ankhol, Behind L&T Knowledge City, N. H. 8, Between Ajwa-Waghodia Junction, Vadodara –390019. India": quotation.address,
            
            # Payment and Delivery
            "Payment: 45 Days from delivery (Being an MSME)": quotation.payment_terms,
            "Delivery: 2-3 weeks per fixture from Purchase Order (Gov. force majeure conditions apply at time of delivery)": quotation.delivery_terms,
            
            # Scope
            "Fixtures as per discussion:": quotation.scope_description,
        }

        # Build specifications from stored fixtures data
        specification_items = []
        for idx, fixture in enumerate(quotation.fixtures_data, 1):
            if fixture.get('specifications', '').strip():
                spec_item = f"{idx}. {fixture.get('name', '')}:\n{fixture.get('specifications', '')}"
                specification_items.append(spec_item)
        specifications_str = "\n\n".join(specification_items) if specification_items else "Specifications as per discussion and drawings."
        
        # Build enhanced inclusion content from stored fixtures data
        inclusion_items = []
        for idx, fixture in enumerate(quotation.fixtures_data, 1):
            if fixture.get('name') or fixture.get('desc'):
                # Enhanced inclusion with Product Name, Description, and Specifications
                inclusion_parts = []
                
                # Product Name
                if fixture.get('name'):
                    inclusion_parts.append(f"Product Name: {fixture['name']}")
                
                # Product Image will be inserted after Product Name (handled separately)
                
                # Description
                if fixture.get('desc'):
                    inclusion_parts.append(f"Description: {fixture['desc']}")
                
                # Additional details
                inclusion_parts.append("(as per annexure)")
                
                if fixture.get('hsn'):
                    inclusion_parts.append(f"HSN Code: {fixture['hsn']}")
                
                # Specifications
                if fixture.get('specifications', '').strip():
                    inclusion_parts.append(f"Specifications: {fixture['specifications']}")
                
                # Note: Images are not available for download (no image bytes stored)
                if fixture.get('has_image'):
                    inclusion_parts.append("Product Image: (Image was included in original quotation)")
                
                # Combine all parts for this fixture
                inclusion_text = f"{idx}. " + "\n   ".join(inclusion_parts)
                inclusion_items.append(inclusion_text)
        
        inclusion_content = "\n\n".join(inclusion_items) if inclusion_items else "Fixtures as per discussion"
        
        # Add inclusion content to replacements
        replacements["<inclusion>"] = inclusion_content
        
        # Add tag-based replacements for specifications
        replacements["<specification>"] = specifications_str
        replacements["< specification>"] = specifications_str  # Handle space variant

        # Add fixture replacements for first 2 fixtures (prices and words only, not names)
        if len(quotation.fixtures_data) >= 1:
            fixture = quotation.fixtures_data[0]
            replacements["26,879/-"] = fixture.get('price', '26,879/-')
            replacements["Twenty-Six Thousand Eight Hundred Seventy-Nine INR Only PER EACH"] = fixture.get('words', 'Twenty-Six Thousand Eight Hundred Seventy-Nine INR Only PER EACH')
        
        if len(quotation.fixtures_data) >= 2:
            fixture = quotation.fixtures_data[1]
            replacements["29,546/-"] = fixture.get('price', '29,546/-')
            replacements["Twenty-Nine Thousand Five Hundred Forty-Six INR Only PER EACH"] = fixture.get('words', 'Twenty-Nine Thousand Five Hundred Forty-Six INR Only PER EACH')

        # Load template
        from pathlib import Path
        BASE_DIR = Path(__file__).resolve().parent.parent
        template_path = os.path.join(BASE_DIR, 'Quote KEC005JN2025 RevA - new format full_1.docx')
        
        doc = Document(template_path)

        # Apply text replacements using the advanced seek_and_replace function
        doc = seek_and_replace(doc, replacements)

        # Handle pricing table with fixtures (without images for download)
        if len(doc.tables) > 1:
            pricing_table = doc.tables[1]  # Second table is the pricing table
            
            # For download, create fixtures without image bytes
            fixtures_for_doc = []
            for fixture in quotation.fixtures_data:
                doc_fixture = dict(fixture)
                doc_fixture['image'] = None  # No image bytes available for download
                doc_fixture['has_image'] = False
                fixtures_for_doc.append(doc_fixture)
            
            # Populate existing fixture rows (first 2)
            populate_pricing_table_with_fixtures(pricing_table, fixtures_for_doc)
            
            # Add additional fixture rows if needed
            if len(fixtures_for_doc) > 2:
                add_fixture_rows_to_table(pricing_table, fixtures_for_doc)

        # Save to buffer
        buffer = BytesIO()
        doc.save(buffer)
        buffer.seek(0)

        # Return as download
        response = HttpResponse(
            buffer.read(),
            content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
        response['Content-Disposition'] = f'attachment; filename="Quotation_{quotation.quote_number}.docx"'
        return response

    except Exception as e:
        messages.error(request, f'Error downloading quotation: {str(e)}')
        import traceback
        traceback.print_exc()
        return redirect('dashboard:quotation_management')

@login_required
def process_po_pdf_ajax(request):
    """
    AJAX endpoint to process uploaded PDF and extract form data using Mistral AI
    """
    if request.method == 'POST' and request.FILES.get('pdf_file'):
        try:
            from .services import extract_po_data_for_form
            
            pdf_file = request.FILES['pdf_file']
            
            # Validate file type
            if not pdf_file.name.lower().endswith('.pdf'):
                return JsonResponse({
                    'success': False,
                    'error': 'Please upload a PDF file only.'
                })
            
            # Validate file size (5MB limit)
            if pdf_file.size > 5 * 1024 * 1024:
                return JsonResponse({
                    'success': False,
                    'error': 'File size must be less than 5MB.'
                })
            
            # Extract data using Mistral AI
            extracted_data = extract_po_data_for_form(pdf_file)
            
            # Map extracted data to form fields
            form_data = {
                'po_number': extracted_data.get('po_number', ''),
                'order_date': extracted_data.get('order_date', ''),
                'customer_name': extracted_data.get('customer_name', ''),
                'order_value': extracted_data.get('order_value', ''),
                'remarks': extracted_data.get('remarks', ''),
            }
            
            return JsonResponse({
                'success': True,
                'data': form_data,
                'message': 'PDF processed successfully!'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Error processing PDF: {str(e)}'
            })
    
    return JsonResponse({
        'success': False,
        'error': 'No PDF file uploaded.'
    })