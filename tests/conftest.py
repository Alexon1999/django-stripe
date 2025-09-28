import os
import django

def pytest_configure():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_stripe.settings')
    django.setup()
