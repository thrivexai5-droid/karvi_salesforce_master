# Mistral AI Integration Setup

## Overview
This Django project now includes Mistral AI integration for automatic PDF data extraction in the Purchase Order form.

## Setup Instructions

### 1. Install Required Package
```bash
pip install mistralai
```

### 2. Get Mistral API Key
1. Visit [Mistral AI Console](https://console.mistral.ai/)
2. Create an account or sign in
3. Generate an API key
4. Copy the API key

### 3. Configure API Key
Open `dashboard_project/settings.py` and replace the placeholder:

```python
# Replace 'your-mistral-api-key-here' with your actual API key
MISTRAL_API_KEY = 'your-actual-mistral-api-key-here'
```

**For production, use environment variables:**
```python
import os
MISTRAL_API_KEY = os.getenv('MISTRAL_API_KEY', 'your-fallback-key')
```

### 4. How It Works

#### Files Created/Modified:
- `dashboard/services.py` - Contains the Mistral AI processing logic
- `dashboard/views.py` - Added `process_po_pdf_ajax` view
- `dashboard/urls.py` - Added URL pattern for PDF processing
- `dashboard/templates/dashboard/purchase_order_form.html` - Updated JavaScript for AI integration

#### User Flow:
1. User clicks "Upload PO (PDF)" button
2. User selects a PDF file
3. User clicks "Upload" button
4. PDF is sent to Mistral AI for OCR and data extraction
5. Extracted data automatically fills the form fields:
   - PO Number
   - Order Date
   - Customer Name (matched against existing contacts)
   - Order Value
   - Remarks

#### Form Field Mapping:
The AI extracts these fields from the PDF:
- `po_number` → PO Number field
- `order_date` → Order Date field (formatted as YYYY-MM-DD)
- `customer_name` → Customer Name dropdown (matched by name)
- `order_value` → Order Value field (currency symbols removed)
- `remarks` → Remarks field

### 5. Features
- **PDF Validation**: Only accepts PDF files up to 5MB
- **Smart Matching**: Customer names are matched against existing contacts
- **Visual Feedback**: Successfully filled fields are highlighted in green
- **Error Handling**: Clear error messages for failed processing
- **Token Usage**: Displays token usage in console for monitoring

### 6. Testing
1. Create a test PDF with purchase order information
2. Go to Purchase Orders → Create New Purchase Order
3. Click "Upload PO (PDF)" button
4. Select your test PDF
5. Click "Upload" and watch the form auto-fill

### 7. Troubleshooting
- **API Key Error**: Ensure your Mistral API key is correctly set in settings.py
- **File Upload Error**: Check file size (max 5MB) and format (PDF only)
- **Extraction Error**: Ensure the PDF contains clear, readable text
- **Form Filling Error**: Check that customer names in PDF match existing contacts

### 8. Cost Considerations
- Mistral AI charges per token used
- Monitor usage in console logs
- Consider implementing usage limits for production

## Security Notes
- Never commit API keys to version control
- Use environment variables in production
- Implement proper error handling and logging
- Consider rate limiting for the upload endpoint