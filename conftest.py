import pytest
import django
from django.conf import settings


@pytest.fixture(scope='session')
def django_db_setup():
    """Set up the Django database for testing."""
    pass


# This ensures Django is properly configured for pytest
if not settings.configured:
    import os
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_stripe.settings')
    django.setup()