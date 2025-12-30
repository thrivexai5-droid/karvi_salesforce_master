# KARVI Dashboard Project

A comprehensive Django-based business management system for quotations, invoices, purchase orders, and inquiry handling with financial sustainability tracking.

## 🚀 Features

### Core Modules
- **📊 Dashboard**: Financial sustainability tracking with dynamic charts
- **📋 Quotation Management**: Draft and generate quotations with revision control
- **🧾 Invoice Generation**: Auto-generated invoice numbers with payment tracking
- **📦 Purchase Order Management**: PO tracking with delivery and payment terms
- **🔍 Inquiry Handler**: Lead management with 19-stage workflow
- **➕ Additional Supply**: Manage additional supplies linked to invoices

### Key Capabilities
- **🤖 AI Integration**: Mistral AI for PDF processing and data extraction
- **📈 Financial Analytics**: Real-time sustainability calculations and burn rate analysis
- **🔄 Auto-Generation**: Invoice numbers, inquiry IDs, and opportunity tracking
- **👥 Role-Based Access**: Sales, Project Manager, Admin, and Manager roles
- **📱 Responsive Design**: Modern UI with Bootstrap and ApexCharts
- **🔒 Security**: Django authentication with role-based permissions

## 🛠️ Technology Stack

- **Backend**: Django 6.0, Python 3.13
- **Database**: SQLite3 (production-ready for small to medium businesses)
- **Frontend**: HTML5, CSS3, JavaScript, Bootstrap 5
- **Charts**: ApexCharts.js for interactive data visualization
- **AI/ML**: Mistral AI for document processing
- **PDF Generation**: ReportLab, WeasyPrint
- **Image Processing**: Pillow

## 📋 Prerequisites

- Python 3.11 or higher
- pip (Python package installer)
- Git (for version control)

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/karvi-dashboard.git
cd karvi-dashboard
```

### 2. Create Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Environment Setup
Create a `.env` file in the project root:
```env
# Mistral AI API Key (optional - for PDF processing)
MISTRAL_API_KEY=your-mistral-api-key-here

# Django Settings (optional)
DEBUG=True
SECRET_KEY=your-secret-key-here
```

### 5. Database Setup
```bash
python manage.py migrate
python manage.py createsuperuser
```

### 6. Run Development Server
```bash
python manage.py runserver
```

Visit `http://127.0.0.1:8000` to access the application.

## 📊 Financial Sustainability Formula

The system calculates business sustainability using:

```
Sustainability Days = 30 × (Total Invoice Value - Fixed Costs + Additional Revenue) / Monthly Expenses
Sustainability Date = Today + Sustainability Days
```

**Components:**
- **Total Invoice Value**: Dynamic from database
- **Fixed Costs**: ₹17,14,000 (configurable)
- **Additional Revenue**: ₹2,50,000 (configurable)
- **Monthly Expenses**: ₹2,29,083 (configurable)

## 🗄️ Database Schema

The system uses 11 tables with comprehensive relationships:

### Core Tables
- `dashboard_company` - Company master data
- `dashboard_contact` - Client/contact information
- `dashboard_purchaseorder` - Purchase order management
- `dashboard_invoice` - Invoice generation and tracking
- `dashboard_inquiryhandler` - Lead and inquiry management
- `dashboard_quotation` - Quotation system with drafts
- `dashboard_additionalsupply` - Additional supply management

See [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) for complete documentation.

## 🔧 Configuration

### User Roles and Permissions
- **Sales**: Access to inquiries, quotations, and basic reporting
- **Project Manager**: Access to purchase orders and project tracking
- **Admin**: Full system access and user management
- **Manager**: Dashboard access and reporting

### Auto-Generated IDs
- **Invoice Numbers**: `KEC/051/2526` (KEC/sequence/fiscal-year)
- **Inquiry IDs**: `KEC020JY2025` (KEC/sequence/month/year)
- **Opportunity IDs**: `eKEC020JY2025` (prefix based on status)

## 🧪 Testing

### Run System Checks
```bash
python manage.py check
python manage.py check --deploy
```

### Test Financial Calculations
```bash
python manage.py check_sustainability
```

### Quick Database Status
```bash
python quick_check.py
```

## 📁 Project Structure

```
karvi-dashboard/
├── dashboard/                 # Main Django app
│   ├── models.py             # Database models
│   ├── views.py              # Business logic
│   ├── services.py           # Utility functions
│   ├── templates/            # HTML templates
│   ├── static/               # CSS, JS, images
│   └── management/           # Custom commands
├── dashboard_project/        # Django project settings
├── media/                    # User uploads
├── staticfiles/              # Collected static files
├── requirements.txt          # Python dependencies
├── DATABASE_SCHEMA.md        # Database documentation
└── README.md                # This file
```

## 🔒 Security Features

- Django CSRF protection
- Role-based access control
- Secure file upload handling
- SQL injection prevention
- XSS protection

## 🚀 Deployment

### Production Checklist
1. Set `DEBUG=False` in settings
2. Configure proper `SECRET_KEY`
3. Set up SSL/HTTPS
4. Configure static file serving
5. Set up database backups
6. Configure logging

### Environment Variables
```env
DEBUG=False
SECRET_KEY=your-production-secret-key
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
MISTRAL_API_KEY=your-mistral-api-key
```

## 📈 Performance

- **Database**: Optimized queries with select_related and prefetch_related
- **Caching**: Template fragment caching for charts
- **Static Files**: Compressed CSS/JS for production
- **Images**: Pillow optimization for uploads

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md)
- **Issues**: GitHub Issues
- **Email**: support@karvi-dashboard.com

## 🎯 Roadmap

- [ ] Multi-company support
- [ ] Advanced reporting and analytics
- [ ] Mobile app integration
- [ ] API development
- [ ] Cloud deployment guides
- [ ] Advanced AI features

## 📊 System Requirements

**Minimum:**
- Python 3.11+
- 2GB RAM
- 1GB disk space

**Recommended:**
- Python 3.13+
- 4GB RAM
- 5GB disk space
- SSD storage

---

**Built with ❤️ for efficient business management**