import os
import django
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cloud_dashboard.settings')
django.setup()
application = get_wsgi_application()
