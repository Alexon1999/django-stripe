import pytest
from unittest.mock import patch, Mock
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from payments.serializers import PaymentSerializer


@pytest.mark.django_db
class TestPaymentSerializerPytest:
    """Pytest-style tests for PaymentSerializer"""

    def test_valid_serializer_data(self):
        """Test serializer with valid data using pytest style"""
        data = {
            'amount': 100.00,
            'currency': 'usd',
            'payment_method_id': 'pm_card_visa'
        }
        serializer = PaymentSerializer(data=data)
        assert serializer.is_valid()
        assert serializer.validated_data['amount'] == 100.00
        assert serializer.validated_data['currency'] == 'usd'
        assert serializer.validated_data['payment_method_id'] == 'pm_card_visa'

    def test_invalid_amount(self):
        """Test serializer with invalid amount"""
        data = {
            'amount': 0.50,  # below minimum
            'currency': 'eur',
            'payment_method_id': 'pm_card_visa'
        }
        serializer = PaymentSerializer(data=data)
        assert not serializer.is_valid()
        assert 'amount' in serializer.errors


@pytest.mark.django_db
class TestProcessPaymentViewPytest:
    """Pytest-style tests for ProcessPaymentView"""

    def setup_method(self):
        """Setup for each test method"""
        self.client = APIClient()
        self.url = reverse('process-payment')
        self.valid_data = {
            'amount': 25.00,
            'currency': 'eur',
            'payment_method_id': 'pm_card_visa'
        }

    @patch('payments.views.stripe.PaymentIntent.create')
    def test_successful_payment_pytest(self, mock_stripe_create):
        """Test successful payment using pytest style"""
        # Mock successful Stripe response
        mock_intent = Mock()
        mock_intent.status = 'succeeded'
        mock_stripe_create.return_value = mock_intent

        response = self.client.post(self.url, self.valid_data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['message'] == 'Payment successful!'
        mock_stripe_create.assert_called_once()

    def test_missing_payment_method_id(self):
        """Test API with missing payment method ID"""
        data = {
            'amount': 25.00,
            'currency': 'eur'
            # missing payment_method_id
        }
        response = self.client.post(self.url, data, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST


# Simple function-style pytest tests
@pytest.mark.django_db
def test_payment_serializer_default_currency():
    """Test serializer uses default currency"""
    data = {
        'amount': 15.00,
        'payment_method_id': 'pm_card_mastercard'
    }
    serializer = PaymentSerializer(data=data)
    assert serializer.is_valid()
    assert serializer.validated_data['currency'] == 'eur'


@pytest.mark.django_db  
def test_payment_serializer_validation():
    """Test various serializer validation scenarios"""
    # Test valid data
    valid_data = {
        'amount': 50.00,
        'currency': 'gbp',
        'payment_method_id': 'pm_card_amex'
    }
    serializer = PaymentSerializer(data=valid_data)
    assert serializer.is_valid()
    
    # Test invalid currency (too long)
    invalid_data = {
        'amount': 50.00,
        'currency': 'toolong',
        'payment_method_id': 'pm_card_visa'
    }
    serializer = PaymentSerializer(data=invalid_data)
    assert not serializer.is_valid()
    assert 'currency' in serializer.errors