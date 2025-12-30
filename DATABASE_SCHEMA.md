# Database Schema Documentation

## Overview
This document describes the complete database schema for the KARVI Dashboard Project, a comprehensive business management system for quotations, invoices, purchase orders, and inquiry handling.

**Database Type**: SQLite3  
**Django Version**: 5.2.8  
**Last Updated**: December 29, 2025

---

## Table of Contents
1. [User Management](#user-management)
2. [Company & Contact Management](#company--contact-management)
3. [Purchase Order Management](#purchase-order-management)
4. [Invoice Management](#invoice-management)
5. [Inquiry Management](#inquiry-management)
6. [Quotation Management](#quotation-management)
7. [Additional Supply Management](#additional-supply-management)
8. [Keys and Constraints Overview](#keys-and-constraints-overview)
9. [Relationships Overview](#relationships-overview)
10. [Auto-Generated Fields](#auto-generated-fields)
11. [Business Logic](#business-logic)

---

## User Management

### `auth_user` (Django Built-in)
Standard Django user authentication table.

| Field | Type | Description |
|-------|------|-------------|
| id | AutoField | Primary key |
| username | CharField(150) | Unique username |
| email | EmailField | User email |
| first_name | CharField(150) | First name |
| last_name | CharField(150) | Last name |
| is_active | BooleanField | Account active status |
| is_staff | BooleanField | Staff access |
| is_superuser | BooleanField | Admin access |
| date_joined | DateTimeField | Registration date |
| last_login | DateTimeField | Last login time |

### `dashboard_userprofile`
Extended user profile with role-based permissions.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | AutoField | PK | Primary key |
| user_id | OneToOneField | FK → auth_user | User reference |
| roles | TextField | Default: 'sales' | Comma-separated roles |
| can_access_invoice_generation | BooleanField | Default: False | Invoice form access |
| can_access_inquiry_handler | BooleanField | Default: False | Inquiry form access |
| can_access_quotation_generation | BooleanField | Default: False | Quotation form access |
| can_access_additional_supply | BooleanField | Default: False | Additional supply access |
| created_at | DateTimeField | Auto-add | Creation timestamp |
| updated_at | DateTimeField | Auto-update | Last update timestamp |

**Role Choices**: `sales`, `project_manager`, `admin`, `manager`

---

## Company & Contact Management

### `dashboard_company`
Company master data with multiple locations and addresses.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | AutoField | PK | Primary key |
| company_name | CharField(200) | Required | Company name |
| city_1 | CharField(100) | Required | Primary city |
| city_2 | CharField(100) | Optional | Secondary city |
| address_1 | TextField | Required | Primary address |
| address_2 | TextField | Optional | Secondary address |
| address_3 | TextField | Optional | Tertiary address |
| created_at | DateTimeField | Auto-add | Creation timestamp |
| updated_at | DateTimeField | Auto-update | Last update timestamp |

**Unique Constraint**: `(company_name, city_1)`

### `dashboard_contact`
Contact/client information with company relationships.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | AutoField | PK | Primary key |
| contact_name | CharField(200) | Required | Client/contact name |
| email_1 | EmailField | Required | Primary email |
| email_2 | EmailField | Optional | Secondary email |
| phone_1 | CharField(20) | Required | Primary phone |
| phone_2 | CharField(20) | Optional | Secondary phone |
| phone_3 | CharField(20) | Optional | Tertiary phone |
| company_id | ForeignKey | FK → dashboard_company | Company reference |
| location_city | CharField(100) | Auto-filled | City from company |
| individual_address | TextField | Required | Personal address |
| customer_name | CharField(200) | Legacy | Backward compatibility |
| email | EmailField | Legacy | Backward compatibility |
| plant | CharField(100) | Legacy | Plant location |
| address | TextField | Legacy | Legacy address |
| created_at | DateTimeField | Auto-add | Creation timestamp |
| updated_at | DateTimeField | Auto-update | Last update timestamp |

---

## Purchase Order Management

### `dashboard_purchaseorder`
Purchase order master records.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | AutoField | PK | Primary key |
| po_number | CharField(50) | Required | PO number |
| order_date | DateField | Required | Order date |
| company_id | ForeignKey | FK → dashboard_contact | Company reference |
| customer_name | CharField(200) | Auto-filled | Customer name |
| order_value | DecimalField(12,2) | Required | Order value |
| days_to_mfg | PositiveIntegerField | Required | Manufacturing days |
| delivery_date | DateField | Auto-calculated | Delivery date |
| due_days | IntegerField | Auto-calculated | Days remaining/overdue |
| remarks | TextField | Optional | Remarks |
| payment_terms | PositiveIntegerField | Optional | Payment terms (days) |
| sales_person_id | ForeignKey | FK → auth_user | Sales person |
| sales_percentage | DecimalField(5,2) | Optional | Sales percentage |
| project_manager_id | ForeignKey | FK → auth_user | Project manager |
| project_manager_percentage | DecimalField(5,2) | Optional | PM percentage |
| created_at | DateTimeField | Auto-add | Creation timestamp |
| updated_at | DateTimeField | Auto-update | Last update timestamp |

**Business Logic**:
- `delivery_date = order_date + days_to_mfg`
- `due_days = delivery_date - today`
- `customer_name` auto-fetched from company

### `dashboard_purchaseorderitem`
Individual items within purchase orders.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | AutoField | PK | Primary key |
| purchase_order_id | ForeignKey | FK → dashboard_purchaseorder | PO reference |
| material_code | CharField(100) | Optional | Material/SKU code |
| item_name | CharField(200) | Required | Item name |
| quantity | DecimalField(10,2) | Required | Quantity |
| price | DecimalField(12,2) | Required | Unit price |
| amount | DecimalField(15,2) | Auto-calculated | Total amount |
| created_at | DateTimeField | Auto-add | Creation timestamp |
| updated_at | DateTimeField | Auto-update | Last update timestamp |

**Business Logic**:
- `amount = quantity × price`

---

## Invoice Management

### `dashboard_invoice`
Invoice records with auto-generation and payment tracking.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | AutoField | PK | Primary key |
| invoice_number | CharField(50) | Unique, Auto-generated | Invoice number |
| invoice_date | DateField | Required | Invoice date |
| company_id | ForeignKey | FK → dashboard_contact | Company reference |
| customer_name | CharField(200) | Auto-filled | Customer name |
| purchase_order_id | ForeignKey | FK → dashboard_purchaseorder | PO reference |
| order_value | DecimalField(12,2) | Auto-filled | Order value |
| grn_date | DateField | Required | GRN date |
| payment_due_date | DateField | Auto-calculated | Payment due date |
| due_days | IntegerField | Auto-calculated | Days remaining/overdue |
| remarks | TextField | Optional | Remarks |
| status | CharField(20) | Choices | Invoice status |
| created_at | DateTimeField | Auto-add | Creation timestamp |
| updated_at | DateTimeField | Auto-update | Last update timestamp |

**Status Choices**: `draft`, `sent`, `invoiced`, `paid`, `partial`, `overdue`, `cancelled`

**Business Logic**:
- `invoice_number` format: `KEC/051/2526` (auto-generated)
- `payment_due_date = grn_date + payment_terms` (from PO)
- `due_days = payment_due_date - today`
- `order_value` auto-fetched from selected PO

---

## Inquiry Management

### `dashboard_inquiryhandler`
Inquiry/opportunity tracking with status-based workflow.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | AutoField | PK | Primary key |
| create_id | CharField(15) | Unique, Auto-generated | Create ID |
| status | CharField(20) | Choices | Current status |
| opportunity_id | CharField(20) | Auto-generated | Opportunity ID |
| lead_description | TextField | Optional | Lead description |
| company_id | ForeignKey | FK → dashboard_contact | Company reference |
| customer_name | CharField(200) | Auto-filled | Customer name |
| quote_no | CharField(15) | Auto-filled | Quote number |
| date_of_quote | DateField | Required | Quote date |
| remarks | TextField | Optional | Remarks |
| ba | CharField(100) | Legacy | Business analyst |
| sales_id | ForeignKey | FK → auth_user | Sales person |
| next_date | DateField | Optional | Next follow-up date |
| remarks_add | TextField | Optional | Additional supply remarks |
| created_at | DateTimeField | Auto-add | Creation timestamp |
| updated_at | DateTimeField | Auto-update | Last update timestamp |

**Status Choices**: `Enquiry`, `Inputs`, `Inspection`, `Enquiry Hold`, `Pending`, `Quotation`, `Negotiation`, `PO-Confirm`, `PO Hold`, `Design`, `Design Review`, `Material Receive`, `Manufacturing`, `Stage-Inspection`, `Approval`, `Dispatch`, `GRN`, `Project Closed`, `Lost`

**Business Logic**:
- `create_id` format: `KEC020JY2025` (auto-generated)
- `opportunity_id` format: `e/o/i + create_id` based on status
- `quote_no = create_id`

---

## Quotation Management

### `dashboard_quotation`
Quotation generation and draft management.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | AutoField | PK | Primary key |
| quote_number | CharField(50) | Required | Quote number |
| revision | CharField(10) | Default: 'Rev A' | Revision level |
| quotation_date | CharField(50) | Required | Quotation date |
| to_person | CharField(200) | Required | Recipient person |
| firm | CharField(200) | Required | Firm name |
| address | TextField | Required | Address |
| payment_terms | TextField | Required | Payment terms |
| delivery_terms | TextField | Required | Delivery terms |
| fixtures_data | JSONField | Optional | Fixtures data |
| fixtures_count | IntegerField | Default: 0 | Number of fixtures |
| status | CharField(20) | Choices | Quotation status |
| created_by_id | ForeignKey | FK → auth_user | Creator |
| created_at | DateTimeField | Auto-add | Creation timestamp |
| updated_at | DateTimeField | Auto-update | Last update timestamp |

**Status Choices**: `draft`, `generated`, `sent`, `approved`, `rejected`

**Business Logic**:
- Revision auto-increment: `Rev A` → `Rev B` → `Rev C`
- Draft functionality for incomplete quotations
- JSON storage for dynamic fixture data

### `dashboard_draftimage`
Images associated with draft quotations.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | AutoField | PK | Primary key |
| quotation_id | ForeignKey | FK → dashboard_quotation | Quotation reference |
| fixture_index | IntegerField | Required | Fixture index |
| image | ImageField | Required | Image file |
| original_filename | CharField(255) | Required | Original filename |
| file_size | IntegerField | Required | File size in bytes |
| created_at | DateTimeField | Auto-add | Creation timestamp |
| updated_at | DateTimeField | Auto-update | Last update timestamp |

---

## Additional Supply Management

### `dashboard_additionalsupply`
Additional supplies linked to invoices.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | AutoField | PK | Primary key |
| invoice_id | ForeignKey | FK → dashboard_invoice | Invoice reference |
| supply_date | DateField | Required | Supply date |
| description | TextField | Required | Supply description |
| quantity | DecimalField(10,2) | Required | Quantity |
| unit_price | DecimalField(12,2) | Required | Unit price |
| total_amount | DecimalField(15,2) | Auto-calculated | Total amount |
| remarks | TextField | Optional | Remarks |
| created_at | DateTimeField | Auto-add | Creation timestamp |
| updated_at | DateTimeField | Auto-update | Last update timestamp |

**Business Logic**:
- `total_amount = quantity × unit_price`

---

## Relationships Overview

### Entity Relationship Diagram (Text Format)

```
                    ┌─────────────┐
                    │  auth_user  │
                    │     (PK)    │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │userprofile  │ (1:1)
                    │    (FK)     │
                    └─────────────┘

┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   company   │    │   contact   │    │ auth_user   │
│    (PK)     │◄───┤    (FK)     │    │    (PK)     │
└─────────────┘    └──────┬──────┘    └──────┬──────┘
                          │                  │
                          ▼                  │
                   ┌─────────────┐           │
                   │purchaseorder│           │
                   │   (FK,FK)   │◄──────────┘
                   └──────┬──────┘    (sales_person, project_manager)
                          │
                    ┌─────▼─────┐
                    │ po_item   │ (1:N)
                    │   (FK)    │
                    └───────────┘

                   ┌─────────────┐
                   │   contact   │
                   │    (PK)     │
                   └──────┬──────┘
                          │
                    ┌─────▼─────┐
                    │  invoice  │ (N:1)
                    │  (FK,FK)  │
                    └──────┬────┘
                           │
                    ┌──────▼──────┐
                    │addl_supply  │ (1:N)
                    │    (FK)     │
                    └─────────────┘

                   ┌─────────────┐
                   │   contact   │
                   │    (PK)     │
                   └──────┬──────┘
                          │
                    ┌─────▼─────┐
                    │  inquiry  │ (N:1)
                    │  (FK,FK)  │
                    └───────────┘

                   ┌─────────────┐
                   │ auth_user   │
                   │    (PK)     │
                   └──────┬──────┘
                          │
                    ┌─────▼─────┐
                    │ quotation │ (N:1)
                    │   (FK)    │
                    └──────┬────┘
                           │
                    ┌──────▼──────┐
                    │draft_image  │ (1:N)
                    │    (FK)     │
                    └─────────────┘
```

### Detailed Relationship Mapping

#### User-Centric Relationships
```
auth_user (1) ←→ (1) dashboard_userprofile
    └─ Constraint: OneToOneField, CASCADE delete
    └─ Business Rule: Every user has exactly one profile

auth_user (1) ←→ (N) dashboard_purchaseorder [sales_person]
    └─ Constraint: ForeignKey, SET_NULL on delete
    └─ Business Rule: Sales person can have multiple POs

auth_user (1) ←→ (N) dashboard_purchaseorder [project_manager]
    └─ Constraint: ForeignKey, SET_NULL on delete
    └─ Business Rule: PM can manage multiple POs

auth_user (1) ←→ (N) dashboard_inquiryhandler [sales]
    └─ Constraint: ForeignKey, SET_NULL on delete
    └─ Business Rule: Sales person can handle multiple inquiries

auth_user (1) ←→ (N) dashboard_quotation [created_by]
    └─ Constraint: ForeignKey, CASCADE delete
    └─ Business Rule: User can create multiple quotations
```

#### Company-Contact Hierarchy
```
dashboard_company (1) ←→ (N) dashboard_contact
    └─ Constraint: ForeignKey, CASCADE delete
    └─ Business Rule: Company can have multiple contacts
    └─ Unique Constraint: (company_name, city_1)

dashboard_contact (1) ←→ (N) dashboard_purchaseorder
    └─ Constraint: ForeignKey, CASCADE delete
    └─ Business Rule: Contact can have multiple POs

dashboard_contact (1) ←→ (N) dashboard_invoice
    └─ Constraint: ForeignKey, CASCADE delete
    └─ Business Rule: Contact can have multiple invoices

dashboard_contact (1) ←→ (N) dashboard_inquiryhandler
    └─ Constraint: ForeignKey, CASCADE delete
    └─ Business Rule: Contact can have multiple inquiries
```

#### Purchase Order Chain
```
dashboard_purchaseorder (1) ←→ (N) dashboard_purchaseorderitem
    └─ Constraint: ForeignKey, CASCADE delete
    └─ Business Rule: PO can have multiple line items

dashboard_purchaseorder (1) ←→ (N) dashboard_invoice
    └─ Constraint: ForeignKey, CASCADE delete
    └─ Business Rule: PO can generate multiple invoices
```

#### Invoice Extensions
```
dashboard_invoice (1) ←→ (N) dashboard_additionalsupply
    └─ Constraint: ForeignKey, CASCADE delete
    └─ Business Rule: Invoice can have multiple additional supplies
```

#### Quotation System
```
dashboard_quotation (1) ←→ (N) dashboard_draftimage
    └─ Constraint: ForeignKey, CASCADE delete
    └─ Business Rule: Quotation can have multiple draft images
    └─ Index: fixture_index for ordering
```

### Cascade Behavior Summary

**CASCADE DELETE** (Child records deleted with parent):
- UserProfile → User
- Contact → Company
- PurchaseOrderItem → PurchaseOrder
- Invoice → Contact, PurchaseOrder
- InquiryHandler → Contact
- Quotation → User (created_by)
- AdditionalSupply → Invoice
- DraftImage → Quotation

**SET_NULL** (Foreign key set to NULL):
- PurchaseOrder.sales_person → User
- PurchaseOrder.project_manager → User
- InquiryHandler.sales → User

---

## Auto-Generated Fields

### Invoice Numbers
**Format**: `KEC/051/2526`
- `KEC`: Fixed prefix
- `051`: Sequential number (3 digits, zero-padded)
- `2526`: Fiscal year (April 1st to March 31st)

### Inquiry Create IDs
**Format**: `KEC020JY2025`
- `KEC`: Fixed prefix
- `020`: Sequential number (3 digits)
- `JY`: Month abbreviation (JA, FE, MR, AP, MY, JN, JY, AU, SE, OC, NO, DE)
- `2025`: Year

### Opportunity IDs
**Format**: Based on status
- Early Stage: `eKEC020JY2025`
- Order Stage: `oKEC020JY2025`
- Invoice Stage: `iKEC020JY2025`
- Special: `LOST`, `HOLD`, `DESIGN`, etc.

---

## Business Logic

### Date Calculations
1. **Delivery Date**: `order_date + days_to_mfg`
2. **Payment Due Date**: `grn_date + payment_terms`
3. **Due Days**: `target_date - today` (positive = remaining, negative = overdue)

### Status Workflows
1. **Inquiry Status**: 19 stages from `Inputs` to `Project Closed`
2. **Invoice Status**: 7 stages from `draft` to `paid`
3. **Quotation Status**: 5 stages from `draft` to `approved`

### Auto-Fill Logic
1. **Customer Names**: Auto-fetched from selected company/contact
2. **Order Values**: Auto-fetched from selected purchase order
3. **Location Cities**: Auto-fetched from company selection
4. **Calculated Amounts**: Auto-calculated from quantity × price

### Financial Sustainability
- **Formula**: `TODAY() + ROUNDDOWN((30 * (Total_Invoice_Value - Fixed_Costs + Additional_Revenue) / Monthly_Expenses), 0)`
- **Dynamic Calculation**: Based on current invoice values
- **Status Indicators**: Critical/Warning/Healthy based on runway days

---

## Keys and Constraints Overview

### Primary Keys (PK)
All tables use Django's default auto-incrementing integer primary key:

| Table | Primary Key | Type | Description |
|-------|-------------|------|-------------|
| `auth_user` | `id` | AutoField | Django user ID |
| `dashboard_userprofile` | `id` | AutoField | User profile ID |
| `dashboard_company` | `id` | AutoField | Company ID |
| `dashboard_contact` | `id` | AutoField | Contact ID |
| `dashboard_purchaseorder` | `id` | AutoField | Purchase order ID |
| `dashboard_purchaseorderitem` | `id` | AutoField | PO item ID |
| `dashboard_invoice` | `id` | AutoField | Invoice ID |
| `dashboard_inquiryhandler` | `id` | AutoField | Inquiry ID |
| `dashboard_quotation` | `id` | AutoField | Quotation ID |
| `dashboard_additionalsupply` | `id` | AutoField | Additional supply ID |
| `dashboard_draftimage` | `id` | AutoField | Draft image ID |

### Foreign Keys (FK)
Complete foreign key relationships across the database:

| Source Table | Source Field | Target Table | Target Field | Relationship | On Delete |
|--------------|--------------|--------------|--------------|--------------|-----------|
| `dashboard_userprofile` | `user_id` | `auth_user` | `id` | One-to-One | CASCADE |
| `dashboard_contact` | `company_id` | `dashboard_company` | `id` | Many-to-One | CASCADE |
| `dashboard_purchaseorder` | `company_id` | `dashboard_contact` | `id` | Many-to-One | CASCADE |
| `dashboard_purchaseorder` | `sales_person_id` | `auth_user` | `id` | Many-to-One | SET_NULL |
| `dashboard_purchaseorder` | `project_manager_id` | `auth_user` | `id` | Many-to-One | SET_NULL |
| `dashboard_purchaseorderitem` | `purchase_order_id` | `dashboard_purchaseorder` | `id` | Many-to-One | CASCADE |
| `dashboard_invoice` | `company_id` | `dashboard_contact` | `id` | Many-to-One | CASCADE |
| `dashboard_invoice` | `purchase_order_id` | `dashboard_purchaseorder` | `id` | Many-to-One | CASCADE |
| `dashboard_inquiryhandler` | `company_id` | `dashboard_contact` | `id` | Many-to-One | CASCADE |
| `dashboard_inquiryhandler` | `sales_id` | `auth_user` | `id` | Many-to-One | SET_NULL |
| `dashboard_quotation` | `created_by_id` | `auth_user` | `id` | Many-to-One | CASCADE |
| `dashboard_additionalsupply` | `invoice_id` | `dashboard_invoice` | `id` | Many-to-One | CASCADE |
| `dashboard_draftimage` | `quotation_id` | `dashboard_quotation` | `id` | Many-to-One | CASCADE |

### Unique Constraints
Fields and combinations that must be unique across the database:

| Table | Field(s) | Type | Description |
|-------|----------|------|-------------|
| `auth_user` | `username` | Single Field | Django username uniqueness |
| `dashboard_userprofile` | `user_id` | Single Field | One profile per user |
| `dashboard_company` | `(company_name, city_1)` | Composite | Unique company per city |
| `dashboard_purchaseorder` | None | - | No unique constraints |
| `dashboard_purchaseorderitem` | None | - | No unique constraints |
| `dashboard_invoice` | `invoice_number` | Single Field | Unique invoice numbers |
| `dashboard_inquiryhandler` | `create_id` | Single Field | Unique inquiry IDs |
| `dashboard_quotation` | None | - | No unique constraints |
| `dashboard_additionalsupply` | None | - | No unique constraints |
| `dashboard_draftimage` | None | - | No unique constraints |

### Index Information
Django automatically creates indexes for:

**Automatic Indexes:**
- All primary keys (`id` fields)
- All foreign key fields
- All unique constraint fields

**Custom Indexes:**
- `dashboard_company`: Composite index on `(company_name, city_1)`
- `dashboard_invoice`: Index on `invoice_number`
- `dashboard_inquiryhandler`: Index on `create_id`

### Constraint Details

#### Business Rule Constraints
1. **Invoice Number Format**: Must follow `KEC/###/####` pattern
2. **Inquiry Create ID Format**: Must follow `KEC###MM####` pattern
3. **Status Choices**: Enforced via Django choices (not DB constraints)
4. **Date Validations**: Business logic in Django models
5. **Percentage Ranges**: 0-100% for sales/PM percentages

#### Referential Integrity
- **CASCADE**: Child records deleted when parent is deleted
  - User profiles, contacts, PO items, invoices, additional supplies, draft images
- **SET_NULL**: Foreign key set to NULL when referenced record is deleted
  - Sales person, project manager assignments

#### Data Integrity Rules
1. **Required Fields**: Cannot be NULL or empty
2. **Optional Fields**: Can be NULL or empty
3. **Auto-Generated Fields**: System-managed, not user-editable
4. **Calculated Fields**: Derived from other fields, updated automatically

---

## Database Statistics

**Total Tables**: 11 (including Django built-ins)  
**Custom Models**: 9  
**Primary Keys**: 11 (all auto-incrementing)  
**Foreign Keys**: 13 relationships  
**Unique Constraints**: 4 (including composite)  
**Auto-Generated Fields**: 8  
**JSON Fields**: 1 (fixtures_data)  
**Image Fields**: 1 (draft images)

---

## Migration History

The database schema has evolved through multiple migrations to support:
- Enhanced company/contact structure
- Auto-generated numbering systems
- Financial sustainability calculations
- Draft quotation functionality
- Multi-status inquiry workflows
- Payment tracking and due date calculations

**Current Migration State**: All migrations applied successfully  
**Database File**: `db.sqlite3` (SQLite3 format)