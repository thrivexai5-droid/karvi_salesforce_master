# WSGI Configuration for PythonAnywhere
# This file should be used in the PythonAnywhere Web tab

import os
import sys

# Add your project directory to the Python path
path = '/home/yourusername/karvi_salesforce_master'  # Update with your actual path
if path not in sys.path:
    sys.path.insert(0, path)

# Set the Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dashboard_project.settings')

# Import Django WSGI application
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

# Instructions for PythonAnywhere:
# 1. Upload your project to /home/yourusername/karvi_salesforce_master
# 2. Update the 'path' variable above with your actual username
# 3. In PythonAnywhere Web tab, set:
#    - Source code: /home/yourusername/karvi_salesforce_master
#    - Working directory: /home/yourusername/karvi_salesforce_master
#    - WSGI configuration file: Copy this file content to the WSGI file
# 4. Set up virtual environment path: /home/yourusername/karvi_salesforce_master/venv
# 5. Configure static files:
#    - URL: /static/
#    - Directory: /home/yourusername/karvi_salesforce_master/staticfiles/