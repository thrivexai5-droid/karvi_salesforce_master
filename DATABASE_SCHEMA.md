# Karvi Salesforce CRM - Complete Database Schema

## Overview
This document defines the complete normalized database schema for the Karvi Salesforce CRM system. The schema is designed for scalability, data integrity, and optimal performance.

---

## Table Definitions

### 1. COMPANY (Master Table)
```sql
CREATE TABLE company (
    id                  BIGINT PRIMARY KEY AUTO_INCREMENT,
    company_name        VARCHAR(200) NOT NULL,
    city_1              VARCHAR(100) NOT NULL,
    city_2              VARCHAR(100) NULL,
    address_1           TEXT NOT NULL,
    address_2           TEXT NULL,
    address_3           TEXT NULL,
    created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Constraints
ALTER TABLE company ADD CONSTRAINT uk_company_name_city UNIQUE (company_name, city_1);
```

**Primary Key:** id  
**Unique Keys:** (company_name, city_1)  
**Foreign Keys:** None  
**Dependencies:** None (Root table)

---

### 2. CONTACT (Master Table)
```sql
CREATE TABLE contact (
    id                  BIGINT PRIMARY KEY AUTO_INCREMENT,
    contact_name        VARCHAR(200) NOT NULL,
    email_1             VARCHAR(254) NOT NULL,
    email_2             VARCHAR(254) NULL,
    phone_1             VARCHAR(20) NOT NULL,
    phone_2             VARCHAR(20) NULL,
    phone_3             VARCHAR(20) NULL,
    company_id          BIGINT NOT NULL,
    location_city       VARCHAR(100) NULL,
    individual_address  TEXT NOT NULL,
    -- Legacy fields for backward compatibility
    customer_name       VARCHAR(200) NULL,
    email               VARCHAR(254) NULL,
    plant               VARCHAR(100) NULL,
    address             TEXT NULL,
    created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Constraints
ALTER TABLE contact ADD CONSTRAINT fk_contact_company 
    FOREIGN KEY (company_id) REFERENCES company(id) ON DELETE CASCADE;
```

**Primary Key:** id  
**Unique Keys:** None  
**Foreign Keys:** company_id → company(id)  
**Dependencies:** company (Parent)

---

### 3. USER (Django Auth Extended)
```sql
CREATE TABLE auth_user (
    id              INTEGER PRIMARY KEY AUTO_INCREMENT,
    username        VARCHAR(150) NOT NULL UNIQUE,
    first_name      VARCHAR(150) NOT NULL,
    last_name       VARCHAR(150) NOT NULL,
    email           VARCHAR(254) NOT NULL,
    password        VARCHAR(128) NOT NULL,
    is_staff        BOOLEAN NOT NULL DEFAULT FALSE,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    is_superuser    BOOLEAN NOT NULL DEFAULT FALSE,
    last_login      DATETIME NULL,
    date_joined     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE userprofile (
    id                              BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id                         INTEGER NOT NULL UNIQUE,
    roles                           TEXT NOT NULL DEFAULT 'sales',
    can_access_invoice_generation   BOOLEAN NOT NULL DEFAULT FALSE,
    can_access_inquiry_handler      BOOLEAN NOT NULL DEFAULT FALSE,
    can_access_quotation_generation BOOLEAN NOT NULL DEFAULT FALSE,
    can_access_additional_supply    BOOLEAN NOT NULL DEFAULT FALSE,
    created_at                      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at                      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Constraints
ALTER TABLE userprofile ADD CONSTRAINT fk_userprofile_user 
    FOREIGN KEY (user_id) REFERENCES auth_user(id) ON DELETE CASCADE;
```

**Primary Key:** id (userprofile), id (auth_user)  
**Unique Keys:** username (auth_user), user_id (userprofile)  
**Foreign Keys:** user_id → auth_user(id)  
**Dependencies:** auth_user (Parent)

---

### 4. INQUIRY_HANDLER (Transactional Table)
```sql
CREATE TABLE inquiry_handler (
    id              BIGINT PRIMARY KEY AUTO_INCREMENT,
    create_id       VARCHAR(15) NOT NULL UNIQUE,
    status          VARCHAR(20) NOT NULL DEFAULT 'Inputs',
    opportunity_id  VARCHAR(20) NOT NULL UNIQUE,
    company_id      BIGINT NOT NULL,
    customer_name   VARCHAR(200) NULL,
    quote_no        VARCHAR(15) NULL,
    date_of_quote   DATE NOT NULL,
    remarks         TEXT NULL,
    ba              VARCHAR(100) NULL,
    sales_id        INTEGER NULL,
    next_date       DATE NULL,
    remarks_add     TEXT NULL,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Constraints
ALTER TABLE inquiry_handler ADD CONSTRAINT fk_inquiry_company 
    FOREIGN KEY (company_id) REFERENCES contact(id) ON DELETE CASCADE;
ALTER TABLE inquiry_handler ADD CONSTRAINT fk_inquiry_sales 
    FOREIGN KEY (sales_id) REFERENCES auth_user(id) ON DELETE SET NULL;
ALTER TABLE inquiry_handler ADD CONSTRAINT uk_inquiry_create_id UNIQUE (create_id);
ALTER TABLE inquiry_handler ADD CONSTRAINT uk_inquiry_opportunity_id UNIQUE (opportunity_id);
```

**Primary Key:** id  
**Unique Keys:** create_id, opportunity_id  
**Foreign Keys:** company_id → contact(id), sales_id → auth_user(id)  
**Dependencies:** contact, auth_user (Parents)

---

### 5. INQUIRY_ITEM (Internal/Child Table)
```sql
CREATE TABLE inquiry_item (
    id          BIGINT PRIMARY KEY AUTO_INCREMENT,
    inquiry_id  BIGINT NOT NULL,
    item_name   VARCHAR(200) NOT NULL,
    quantity    DECIMAL(10,2) NOT NULL,
    price       DECIMAL(12,2) NOT NULL,
    amount      DECIMAL(15,2) NOT NULL,
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Constraints
ALTER TABLE inquiry_item ADD CONSTRAINT fk_inquiry_item_inquiry 
    FOREIGN KEY (inquiry_id) REFERENCES inquiry_handler(id) ON DELETE CASCADE;
```

**Primary Key:** id  
**Unique Keys:** None  
**Foreign Keys:** inquiry_id → inquiry_handler(id)  
**Dependencies:** inquiry_handler (Parent) - CASCADE DELETE

---

### 6. PURCHASE_ORDER (Transactional Table)
```sql
CREATE TABLE purchase_order (
    id                          BIGINT PRIMARY KEY AUTO_INCREMENT,
    po_number                   VARCHAR(50) NOT NULL UNIQUE,
    order_date                  DATE NOT NULL,
    company_id                  BIGINT NOT NULL,
    customer_name               VARCHAR(200) NOT NULL,
    order_value                 DECIMAL(12,2) NOT NULL,
    days_to_mfg                 INTEGER NOT NULL,
    delivery_date               DATE NULL,
    due_days                    INTEGER NULL,
    remarks                     TEXT NULL,
    sales_person_id             INTEGER NULL,
    sales_percentage            DECIMAL(5,2) NULL,
    project_manager_id          INTEGER NULL,
    project_manager_percentage  DECIMAL(5,2) NULL,
    created_at                  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at                  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Constraints
ALTER TABLE purchase_order ADD CONSTRAINT fk_po_company 
    FOREIGN KEY (company_id) REFERENCES contact(id) ON DELETE CASCADE;
ALTER TABLE purchase_order ADD CONSTRAINT fk_po_sales 
    FOREIGN KEY (sales_person_id) REFERENCES auth_user(id) ON DELETE SET NULL;
ALTER TABLE purchase_order ADD CONSTRAINT fk_po_pm 
    FOREIGN KEY (project_manager_id) REFERENCES auth_user(id) ON DELETE SET NULL;
ALTER TABLE purchase_order ADD CONSTRAINT uk_po_number UNIQUE (po_number);
```

**Primary Key:** id  
**Unique Keys:** po_number  
**Foreign Keys:** company_id → contact(id), sales_person_id → auth_user(id), project_manager_id → auth_user(id)  
**Dependencies:** contact, auth_user (Parents)

---

### 7. INVOICE (Transactional Table)
```sql
CREATE TABLE invoice (
    id                  BIGINT PRIMARY KEY AUTO_INCREMENT,
    invoice_number      VARCHAR(50) NOT NULL UNIQUE,
    invoice_date        DATE NOT NULL,
    company_id          BIGINT NOT NULL,
    customer_name       VARCHAR(200) NULL,
    purchase_order_id   BIGINT NOT NULL,
    order_value         DECIMAL(12,2) NULL,
    grn_date            DATE NOT NULL,
    payment_due_date    DATE NULL,
    due_days            INTEGER NULL,
    remarks             TEXT NULL,
    created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Constraints
ALTER TABLE invoice ADD CONSTRAINT fk_invoice_company 
    FOREIGN KEY (company_id) REFERENCES contact(id) ON DELETE CASCADE;
ALTER TABLE invoice ADD CONSTRAINT fk_invoice_po 
    FOREIGN KEY (purchase_order_id) REFERENCES purchase_order(id) ON DELETE CASCADE;
ALTER TABLE invoice ADD CONSTRAINT uk_invoice_number UNIQUE (invoice_number);
```

**Primary Key:** id  
**Unique Keys:** invoice_number  
**Foreign Keys:** company_id → contact(id), purchase_order_id → purchase_order(id)  
**Dependencies:** contact, purchase_order (Parents)

---

### 8. INVOICE_ITEM (Internal/Child Table)
```sql
CREATE TABLE invoice_item (
    id          BIGINT PRIMARY KEY AUTO_INCREMENT,
    invoice_id  BIGINT NOT NULL,
    item_name   VARCHAR(200) NOT NULL,
    quantity    DECIMAL(10,2) NOT NULL,
    price       DECIMAL(12,2) NOT NULL,
    amount      DECIMAL(15,2) NOT NULL,
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Constraints
ALTER TABLE invoice_item ADD CONSTRAINT fk_invoice_item_invoice 
    FOREIGN KEY (invoice_id) REFERENCES invoice(id) ON DELETE CASCADE;
```

**Primary Key:** id  
**Unique Keys:** None  
**Foreign Keys:** invoice_id → invoice(id)  
**Dependencies:** invoice (Parent) - CASCADE DELETE

---

### 9. QUOTATION (Transactional Table)
```sql
CREATE TABLE quotation (
    id              BIGINT PRIMARY KEY AUTO_INCREMENT,
    quotation_number VARCHAR(50) NOT NULL UNIQUE,
    inquiry_id      BIGINT NOT NULL UNIQUE,
    quotation_date  DATE NOT NULL,
    total_amount    DECIMAL(15,2) NOT NULL,
    validity_days   INTEGER NOT NULL DEFAULT 30,
    terms_conditions TEXT NULL,
    status          VARCHAR(20) NOT NULL DEFAULT 'Draft',
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Constraints
ALTER TABLE quotation ADD CONSTRAINT fk_quotation_inquiry 
    FOREIGN KEY (inquiry_id) REFERENCES inquiry_handler(id) ON DELETE CASCADE;
ALTER TABLE quotation ADD CONSTRAINT uk_quotation_number UNIQUE (quotation_number);
ALTER TABLE quotation ADD CONSTRAINT uk_quotation_inquiry UNIQUE (inquiry_id);
```

**Primary Key:** id  
**Unique Keys:** quotation_number, inquiry_id  
**Foreign Keys:** inquiry_id → inquiry_handler(id)  
**Dependencies:** inquiry_handler (Parent)

---

### 10. ADDITIONAL_SUPPLY (Transactional Table)
```sql
CREATE TABLE additional_supply (
    id              BIGINT PRIMARY KEY AUTO_INCREMENT,
    invoice_id      BIGINT NOT NULL,
    supply_date     DATE NOT NULL,
    description     TEXT NOT NULL,
    quantity        DECIMAL(10,2) NOT NULL,
    unit_price      DECIMAL(12,2) NOT NULL,
    total_amount    DECIMAL(15,2) NOT NULL,
    remarks         TEXT NULL,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Constraints
ALTER TABLE additional_supply ADD CONSTRAINT fk_additional_supply_invoice 
    FOREIGN KEY (invoice_id) REFERENCES invoice(id) ON DELETE CASCADE;
```

**Primary Key:** id  
**Unique Keys:** None  
**Foreign Keys:** invoice_id → invoice(id)  
**Dependencies:** invoice (Parent)

---

## Relationship Summary

### Parent → Child Dependencies
```
company (1) → contact (N)
contact (1) → inquiry_handler (N)
contact (1) → purchase_order (N)
contact (1) → invoice (N)
inquiry_handler (1) → inquiry_item (N) [CASCADE DELETE]
inquiry_handler (1) → quotation (1)
purchase_order (1) → invoice (N)
invoice (1) → invoice_item (N) [CASCADE DELETE]
invoice (1) → additional_supply (N)
auth_user (1) → userprofile (1)
auth_user (1) → inquiry_handler (N) [sales_id]
auth_user (1) → purchase_order (N) [sales_person_id, project_manager_id]
```

### Data Flow Hierarchy
```
1. company (Root Master)
   └── contact (Master)
       ├── inquiry_handler (Transaction)
       │   ├── inquiry_item (Internal)
       │   └── quotation (Transaction)
       ├── purchase_order (Transaction)
       │   └── invoice (Transaction)
       │       ├── invoice_item (Internal)
       │       └── additional_supply (Transaction)
       └── [Direct invoice creation possible]

2. auth_user (Root Master)
   ├── userprofile (Profile)
   ├── inquiry_handler (via sales_id)
   └── purchase_order (via sales_person_id, project_manager_id)
```

### Critical Constraints Applied

#### Uniqueness Constraints:
- `company`: (company_name, city_1) - Same company cannot exist in same city
- `inquiry_handler`: create_id, opportunity_id - Global uniqueness
- `purchase_order`: po_number - Global uniqueness
- `invoice`: invoice_number - Global uniqueness
- `quotation`: quotation_number, inquiry_id - Global uniqueness
- `auth_user`: username - Global uniqueness

#### Cascade Relationships:
- **ON DELETE CASCADE**: All internal tables (inquiry_item, invoice_item)
- **ON DELETE CASCADE**: All transactional tables linked to masters
- **ON DELETE SET NULL**: User references (sales, project manager)

#### Data Type Standards:
- **Financial Fields**: DECIMAL(12,2) for amounts, DECIMAL(5,2) for percentages
- **Text Fields**: VARCHAR with appropriate limits, TEXT for long content
- **Dates**: DATE for date-only, DATETIME for timestamps
- **IDs**: BIGINT for scalability

#### Nullable Fields:
- Optional business fields: remarks, secondary contacts, legacy fields
- Auto-calculated fields: delivery_date, due_days, payment_due_date
- Reference fields with SET NULL: sales_id, project_manager_id

---

## Index Recommendations

### Primary Indexes (Automatic):
- All PRIMARY KEY fields
- All UNIQUE constraint fields

### Recommended Additional Indexes:
```sql
-- Performance indexes for common queries
CREATE INDEX idx_contact_company ON contact(company_id);
CREATE INDEX idx_inquiry_company ON inquiry_handler(company_id);
CREATE INDEX idx_inquiry_sales ON inquiry_handler(sales_id);
CREATE INDEX idx_inquiry_status ON inquiry_handler(status);
CREATE INDEX idx_po_company ON purchase_order(company_id);
CREATE INDEX idx_invoice_company ON invoice(company_id);
CREATE INDEX idx_invoice_po ON invoice(purchase_order_id);

-- Date-based indexes for reporting
CREATE INDEX idx_inquiry_date ON inquiry_handler(date_of_quote);
CREATE INDEX idx_po_order_date ON purchase_order(order_date);
CREATE INDEX idx_invoice_date ON invoice(invoice_date);
CREATE INDEX idx_invoice_due_date ON invoice(payment_due_date);
```

---

## Schema Validation Rules

### Business Logic Constraints:
1. **Company-Contact**: One company can have multiple contacts, but each contact belongs to exactly one company
2. **Inquiry-Items**: Inquiry items cannot exist without parent inquiry (CASCADE DELETE)
3. **Invoice-PO**: Every invoice must reference a valid purchase order
4. **Quotation-Inquiry**: One-to-one relationship between quotation and inquiry
5. **User Roles**: Sales users can be assigned to inquiries and purchase orders
6. **Financial Precision**: All monetary values use DECIMAL for accuracy

### Data Integrity Rules:
1. **No Orphaned Records**: All child tables have proper foreign key constraints
2. **Unique Business Keys**: Critical business identifiers are globally unique
3. **Audit Trail**: All tables have created_at and updated_at timestamps
4. **Soft Dependencies**: User references use SET NULL to preserve data integrity

---

**Schema Version:** 1.0  
**Last Updated:** December 22, 2025  
**Database Engine:** MySQL/PostgreSQL Compatible  
**Django ORM:** Fully Compatible