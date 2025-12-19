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
from .models import UserProfile, Company, Contact, PurchaseOrder, Invoice, InquiryHandler, InquiryItem
from .password_storage import password_storage

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
    return render(request, 'dashboard/index.html')

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
        'title': 'Add New User',
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
    # Add customer_name as a separate field for dropdown selection
    customer_name_select = forms.ModelChoiceField(
        queryset=Contact.objects.all(),
        empty_label="Select Customer",
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'customer-select'}),
        label="Customer Name *"
    )
    
    class Meta:
        model = PurchaseOrder
        fields = ['po_number', 'order_date', 'customer_name_select', 'order_value', 'days_to_mfg', 'remarks', 'sales_person', 'sales_percentage', 'project_manager', 'project_manager_percentage']
        widgets = {
            'po_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter PO Number'}),
            'order_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'order_value': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter order value', 'step': '0.01'}),
            'days_to_mfg': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter manufacturing days'}),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Enter remarks (optional)'}),
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
        
        # Set customer queryset ordered by customer name
        self.fields['customer_name_select'].queryset = Contact.objects.all().order_by('customer_name')
        
        # If editing existing order, set the customer_name_select field
        if self.instance and self.instance.pk and self.instance.company:
            self.fields['customer_name_select'].initial = self.instance.company
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Set company and customer_name based on selected customer
        if self.cleaned_data.get('customer_name_select'):
            selected_contact = self.cleaned_data['customer_name_select']
            instance.company = selected_contact
            instance.customer_name = selected_contact.customer_name
        
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
            messages.success(request, f'Purchase Order {order.po_number} created successfully!')
            return redirect('dashboard:purchase_order_management')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = PurchaseOrderForm()
    
    return render(request, 'dashboard/purchase_order_form.html', {
        'form': form,
        'title': 'Create New Purchase Order',
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
        
        # Sales Person
        sales_person_name = ""
        if order.sales_person:
            sales_person_name = order.sales_person.get_full_name() or order.sales_person.username
        ws.cell(row=row_num, column=8, value=sales_person_name)
        
        # Sales Percentage
        sales_percentage = float(order.sales_percentage) if order.sales_percentage else ""
        ws.cell(row=row_num, column=9, value=sales_percentage)
        
        # Project Manager
        pm_name = ""
        if order.project_manager:
            pm_name = order.project_manager.get_full_name() or order.project_manager.username
        ws.cell(row=row_num, column=10, value=pm_name)
        
        # PM Percentage
        pm_percentage = float(order.project_manager_percentage) if order.project_manager_percentage else ""
        ws.cell(row=row_num, column=11, value=pm_percentage)
    
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
    # Customer selection dropdown - primary field for selection
    customer_select = forms.ModelChoiceField(
        queryset=Contact.objects.all(),
        empty_label="Select Customer",
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'customer-select'}),
        label="Customer *",
        help_text="Select customer from database"
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
        fields = ['invoice_number', 'invoice_date', 'customer_select', 'purchase_order', 'grn_date', 'remarks']
        # Exclude auto-calculated fields: customer_name, order_value, payment_due_date, due_days, client (auto-fetched)
        widgets = {
            'invoice_number': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Enter invoice number manually'
            }),
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
        
        # Set customer queryset ordered by customer name
        self.fields['customer_select'].queryset = Contact.objects.all().order_by('customer_name')
        
        # If editing existing invoice, set the customer_select field and purchase order queryset
        if self.instance and self.instance.pk and self.instance.company:
            self.fields['customer_select'].initial = self.instance.company
            self.fields['purchase_order'].queryset = PurchaseOrder.objects.filter(
                company=self.instance.company
            ).order_by('-created_at')
            if self.instance.purchase_order:
                self.fields['purchase_order'].initial = self.instance.purchase_order
        else:
            # For new forms, show all purchase orders initially
            self.fields['purchase_order'].queryset = PurchaseOrder.objects.all().order_by('-created_at')
    
    def clean(self):
        cleaned_data = super().clean()
        customer_select = cleaned_data.get('customer_select')
        purchase_order = cleaned_data.get('purchase_order')
        
        # Validate that the selected purchase order belongs to the selected customer
        if customer_select and purchase_order:
            if purchase_order.company != customer_select:
                raise forms.ValidationError("The selected purchase order does not belong to the selected customer.")
        
        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Set both company and customer_name based on selected customer
        if self.cleaned_data.get('customer_select'):
            selected_contact = self.cleaned_data['customer_select']
            instance.company = selected_contact  # Set the company relationship
            instance.customer_name = selected_contact.customer_name  # Set customer name
        
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
        purchase_orders = PurchaseOrder.objects.filter(company=contact).order_by('-created_at')
        
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
                'po_number': po.po_number
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
        
        # Set customer queryset ordered by customer name
        self.fields['customer_select'].queryset = Contact.objects.all().order_by('customer_name')
        
        # Set sales queryset ordered by username
        self.fields['sales'].queryset = User.objects.filter(userprofile__roles__contains='sales').order_by('username')
        
        # Set default date to today for new forms
        if not self.instance.pk:
            from datetime import date
            self.fields['date_of_quote'].initial = date.today()
        
        # If editing existing inquiry, set the customer_select field
        if self.instance and self.instance.pk and self.instance.company:
            self.fields['customer_select'].initial = self.instance.company
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Set both company and customer_name based on selected customer
        if self.cleaned_data.get('customer_select'):
            selected_contact = self.cleaned_data['customer_select']
            instance.company = selected_contact  # Set the company relationship
            instance.customer_name = selected_contact.customer_name  # Set customer name
        
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
    """Additional Supply management page - shows only GRN status inquiries"""
    search_query = request.GET.get('search', '')
    
    # Filter only inquiries with status = 'GRN'
    inquiries = InquiryHandler.objects.select_related('company').filter(status='Quotation')
    
    if search_query:
        inquiries = inquiries.filter(
            Q(create_id__icontains=search_query) |
            Q(opportunity_id__icontains=search_query) |
            Q(quote_no__icontains=search_query) |
            Q(company__company__icontains=search_query) |
            Q(customer_name__icontains=search_query) |
            Q(ba__icontains=search_query) |
            Q(remarks_add__icontains=search_query)
        )
    
    inquiries = inquiries.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(inquiries, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Statistics
    total_grn_inquiries = InquiryHandler.objects.filter(status='GRN').count()
    with_additional_remarks = InquiryHandler.objects.filter(status='GRN', remarks_add__isnull=False).exclude(remarks_add='').count()
    without_additional_remarks = total_grn_inquiries - with_additional_remarks
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'total_grn_inquiries': total_grn_inquiries,
        'with_additional_remarks': with_additional_remarks,
        'without_additional_remarks': without_additional_remarks,
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
