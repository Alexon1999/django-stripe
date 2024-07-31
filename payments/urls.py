from django.urls import path
from .views import ProcessPaymentView

urlpatterns = [
    path('process-payment/', ProcessPaymentView.as_view(), name='process-payment'),
]
