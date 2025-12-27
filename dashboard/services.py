import base64
import json
import re
from datetime import datetime
from mistralai import Mistral
from django.conf import settings

def generate_invoice_number():
    """
    Generate auto-incremented invoice number in format: KEC/051/2526
    - KEC: Fixed prefix
    - 051: Sequential number (3 digits, zero-padded)
    - 2526: Fiscal year (April 1st to March 31st, so April 2025 to March 2026 becomes 2526)
    """
    from django.db import transaction
    from .models import Invoice
    
    # Get current fiscal year (April 1st to March 31st)
    now = datetime.now()
    if now.month >= 4:  # April 1st to December 31st
        fiscal_start_year = now.year
        fiscal_end_year = now.year + 1
    else:  # January 1st to March 31st
        fiscal_start_year = now.year - 1
        fiscal_end_year = now.year
    
    # Format fiscal year as 2526 (25 from 2025, 26 from 2026)
    fiscal_year = f"{str(fiscal_start_year)[-2:]}{str(fiscal_end_year)[-2:]}"
    
    with transaction.atomic():
        # Get the latest invoice number for the current fiscal year
        latest_invoice = Invoice.objects.filter(
            invoice_number__startswith=f"KEC/",
            invoice_number__endswith=f"/{fiscal_year}"
        ).order_by('-invoice_number').first()
        
        if latest_invoice:
            # Extract sequence number from the latest invoice
            try:
                parts = latest_invoice.invoice_number.split('/')
                if len(parts) == 3 and parts[0] == 'KEC' and parts[2] == fiscal_year:
                    sequence = int(parts[1]) + 1
                else:
                    sequence = 1
            except (ValueError, IndexError):
                sequence = 1
        else:
            sequence = 1
        
        # Format: KEC/051/2526
        invoice_number = f"KEC/{sequence:03d}/{fiscal_year}"
        
        # Ensure uniqueness (in case of race conditions)
        while Invoice.objects.filter(invoice_number=invoice_number).exists():
            sequence += 1
            invoice_number = f"KEC/{sequence:03d}/{fiscal_year}"
        
        return invoice_number

def extract_payment_days(payment_terms_text):
    """
    Extract number of days from payment terms text.
    Examples: "45 days" -> 45, "Net 30" -> 30, "Payment within 60 days" -> 60
    """
    if not payment_terms_text:
        return None
    
    # Convert to string and clean
    text = str(payment_terms_text).strip()
    
    # Look for patterns like "45 days", "Net 30", "30 days", etc.
    patterns = [
        r'(\d+)\s*days?',  # "45 days" or "45 day"
        r'net\s*(\d+)',    # "Net 30" or "NET 45"
        r'(\d+)\s*day',    # "45 day"
        r'within\s*(\d+)',  # "within 45"
        r'(\d+)',          # Just a number
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                days = int(match.group(1))
                # Reasonable range check (1-365 days)
                if 1 <= days <= 365:
                    return days
            except (ValueError, IndexError):
                continue
    
    return None

def extract_po_data_from_pdf(pdf_file):
    """
    Uses Mistral OCR and LLM to extract structured data from a PO PDF.
    Extracts: po_number, po_date, material_code, material_description, quantity, net_value, delivery_date, payment_terms
    """
    client = Mistral(api_key=settings.MISTRAL_API_KEY)
    
    # 1. OCR Process: Convert file to base64 and process
    encoded_file = base64.b64encode(pdf_file.read()).decode('utf-8')
    ocr_response = client.ocr.process(
        model="mistral-ocr-latest",
        document={
            "type": "document_url", 
            "document_url": f"data:application/pdf;base64,{encoded_file}"
        }
    )
    
    # Combine markdown text from all pages
    full_text = "\n\n".join([page.markdown for page in ocr_response.pages])

    # 2. Field Extraction: Enhanced prompt for comprehensive PO data extraction
    system_prompt = (
        "You are a Purchase Order data extraction specialist. Extract the following fields into a JSON object:\n\n"
        "MAIN FIELDS:\n"
        "- po_number: Purchase Order number/reference\n"
        "- po_date: PO date (format YYYY-MM-DD)\n"
        "- customer_name: Customer/buyer company name\n"
        "- net_value: Total net value/amount (number only, no currency)\n"
        "- delivery_date: Required delivery date (format YYYY-MM-DD)\n"
        "- payment_terms: Payment terms in days only (extract number, e.g., '45 days' -> 45)\n"
        "- remarks: Any additional notes or remarks\n\n"
        "ITEMS ARRAY:\n"
        "- items: Array of line items, each containing:\n"
        "  - material_code: Item/material code or SKU\n"
        "  - material_description: Item/material description\n"
        "  - quantity: Quantity ordered (number only)\n"
        "  - unit_price: Price per unit (number only)\n"
        "  - line_total: Total for this line item (number only)\n\n"
        "EXTRACTION RULES:\n"
        "1. If a field is not found, use empty string for text fields, 0 for numbers, empty array for items\n"
        "2. For dates, use YYYY-MM-DD format only\n"
        "3. For numbers, extract only numeric values without currency symbols\n"
        "4. Extract ALL line items found in the document\n"
        "5. Material codes might be labeled as: Item Code, SKU, Part Number, Material Code, etc.\n"
        "6. Quantities might have units (pcs, kg, etc.) - extract only the number\n"
        "7. Look for tables or structured data for line items\n\n"
        "OUTPUT: Valid JSON object only, no additional text."
    )
    
    chat_response = client.chat.complete(
        model="mistral-medium-latest",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Extract PO data from this document:\n\n{full_text}"}
        ],
        response_format={"type": "json_object"},
        temperature=0
    )
    
    extracted_data = json.loads(chat_response.choices[0].message.content)
    
    # Post-process the data to ensure consistency
    processed_data = {
        "po_number": extracted_data.get("po_number", ""),
        "po_date": extracted_data.get("po_date", ""),
        "customer_name": extracted_data.get("customer_name", ""),
        "net_value": extracted_data.get("net_value", 0),
        "delivery_date": extracted_data.get("delivery_date", ""),
        "payment_terms": extract_payment_days(extracted_data.get("payment_terms", "")),
        "remarks": extracted_data.get("remarks", ""),
        "items": extracted_data.get("items", [])
    }
    
    # Validate and clean items data
    cleaned_items = []
    for item in processed_data["items"]:
        if isinstance(item, dict) and item.get("material_description"):
            cleaned_item = {
                "material_code": str(item.get("material_code", "")),
                "material_description": str(item.get("material_description", "")),
                "quantity": float(item.get("quantity", 0)) if item.get("quantity") else 0,
                "unit_price": float(item.get("unit_price", 0)) if item.get("unit_price") else 0,
                "line_total": float(item.get("line_total", 0)) if item.get("line_total") else 0
            }
            # Calculate line total if not provided
            if cleaned_item["line_total"] == 0 and cleaned_item["quantity"] > 0 and cleaned_item["unit_price"] > 0:
                cleaned_item["line_total"] = cleaned_item["quantity"] * cleaned_item["unit_price"]
            
            cleaned_items.append(cleaned_item)
    
    processed_data["items"] = cleaned_items
    
    # Calculate total net value from items if not provided
    if processed_data["net_value"] == 0 and cleaned_items:
        processed_data["net_value"] = sum(item["line_total"] for item in cleaned_items)
    
    return processed_data