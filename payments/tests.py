import pytest
from unittest.mock import patch, Mock
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from .serializers import PaymentSerializer
from .views import ProcessPaymentView


class PaymentSerializerTestCase(TestCase):
    """Test cases for PaymentSerializer"""

    def test_valid_serializer_data(self):
        """Test serializer with valid data"""
        data = {
            'amount': 10.50,
            'currency': 'eur',
            'payment_method_id': 'pm_card_visa'
        }
        serializer = PaymentSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['amount'], 10.50)
        self.assertEqual(serializer.validated_data['currency'], 'eur')
        self.assertEqual(serializer.validated_data['payment_method_id'], 'pm_card_visa')

    def test_valid_serializer_with_default_currency(self):
        """Test serializer with default currency"""
        data = {
            'amount': 25.99,
            'payment_method_id': 'pm_card_mastercard'
        }
        serializer = PaymentSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['currency'], 'eur')  # default

    def test_invalid_amount_too_low(self):
        """Test serializer with amount below minimum"""
        data = {
            'amount': 0.50,
            'currency': 'usd',
            'payment_method_id': 'pm_card_visa'
        }
        serializer = PaymentSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('amount', serializer.errors)

    def test_invalid_amount_negative(self):
        """Test serializer with negative amount"""
        data = {
            'amount': -5.00,
            'currency': 'eur',
            'payment_method_id': 'pm_card_visa'
        }
        serializer = PaymentSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('amount', serializer.errors)

    def test_missing_required_fields(self):
        """Test serializer with missing required fields"""
        data = {
            'amount': 10.00
            # missing payment_method_id
        }
        serializer = PaymentSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('payment_method_id', serializer.errors)

    def test_currency_max_length(self):
        """Test currency field max length"""
        data = {
            'amount': 10.00,
            'currency': 'toolong',  # more than 3 chars
            'payment_method_id': 'pm_card_visa'
        }
        serializer = PaymentSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('currency', serializer.errors)

    def test_empty_payment_method_id(self):
        """Test empty payment method ID"""
        data = {
            'amount': 10.00,
            'currency': 'eur',
            'payment_method_id': ''
        }
        serializer = PaymentSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('payment_method_id', serializer.errors)


class ProcessPaymentViewTestCase(APITestCase):
    """Test cases for ProcessPaymentView API endpoint"""

    def setUp(self):
        self.client = APIClient()
        self.url = reverse('process-payment')
        self.valid_data = {
            'amount': 10.50,
            'currency': 'eur',
            'payment_method_id': 'pm_card_visa'
        }

    @patch('payments.views.stripe.PaymentIntent.create')
    def test_successful_payment(self, mock_stripe_create):
        """Test successful payment processing"""
        # Mock successful Stripe response
        mock_intent = Mock()
        mock_intent.status = 'succeeded'
        mock_stripe_create.return_value = mock_intent

        response = self.client.post(self.url, self.valid_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Payment successful!')
        
        # Verify Stripe was called with correct parameters
        mock_stripe_create.assert_called_once_with(
            amount=1050,  # 10.50 * 100
            currency='eur',
            payment_method='pm_card_visa',
            confirm=True,
            automatic_payment_methods={
                "allow_redirects": "never",
                "enabled": True
            }
        )

    @patch('payments.views.stripe.PaymentIntent.create')
    def test_failed_payment_intent_status(self, mock_stripe_create):
        """Test payment with failed intent status"""
        # Mock failed Stripe response
        mock_intent = Mock()
        mock_intent.status = 'requires_action'
        mock_stripe_create.return_value = mock_intent

        response = self.client.post(self.url, self.valid_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['message'], 'Payment failed or requires additional action.')

    @patch('payments.views.stripe.PaymentIntent.create')
    def test_stripe_card_error(self, mock_stripe_create):
        """Test handling of Stripe CardError"""
        from stripe.error import CardError
        
        # Mock Stripe CardError
        mock_stripe_create.side_effect = CardError('Your card was declined.', None, 'card_declined')

        response = self.client.post(self.url, self.valid_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)

    @patch('payments.views.stripe.PaymentIntent.create')
    def test_generic_exception(self, mock_stripe_create):
        """Test handling of generic exception"""
        # Mock generic exception
        mock_stripe_create.side_effect = Exception('Something went wrong')

        response = self.client.post(self.url, self.valid_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)

    def test_invalid_serializer_data(self):
        """Test with invalid serializer data"""
        invalid_data = {
            'amount': -5.00,  # invalid amount
            'currency': 'eur',
            'payment_method_id': 'pm_card_visa'
        }

        response = self.client.post(self.url, invalid_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_required_fields(self):
        """Test with missing required fields"""
        incomplete_data = {
            'amount': 10.00
            # missing payment_method_id
        }

        response = self.client.post(self.url, incomplete_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_method_not_allowed(self):
        """Test that GET method is not allowed"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    @patch('payments.views.stripe.PaymentIntent.create')
    def test_amount_conversion_to_cents(self, mock_stripe_create):
        """Test that amount is correctly converted to cents"""
        mock_intent = Mock()
        mock_intent.status = 'succeeded'
        mock_stripe_create.return_value = mock_intent

        test_data = {
            'amount': 15.75,
            'currency': 'usd',
            'payment_method_id': 'pm_card_visa'
        }

        response = self.client.post(self.url, test_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify amount was converted to cents correctly
        mock_stripe_create.assert_called_once_with(
            amount=1575,  # 15.75 * 100
            currency='usd',
            payment_method='pm_card_visa',
            confirm=True,
            automatic_payment_methods={
                "allow_redirects": "never",
                "enabled": True
            }
        )

    @patch('payments.views.stripe.PaymentIntent.create')
    def test_different_currencies(self, mock_stripe_create):
        """Test payment processing with different currencies"""
        mock_intent = Mock()
        mock_intent.status = 'succeeded'
        mock_stripe_create.return_value = mock_intent

        currencies = ['usd', 'eur', 'gbp']
        
        for currency in currencies:
            test_data = {
                'amount': 20.00,
                'currency': currency,
                'payment_method_id': 'pm_card_visa'
            }

            response = self.client.post(self.url, test_data, format='json')
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch('payments.views.stripe.PaymentIntent.create')
    def test_different_payment_methods(self, mock_stripe_create):
        """Test payment processing with different payment methods"""
        mock_intent = Mock()
        mock_intent.status = 'succeeded'
        mock_stripe_create.return_value = mock_intent

        payment_methods = ['pm_card_visa', 'pm_card_mastercard', 'pm_card_amex']
        
        for pm in payment_methods:
            test_data = {
                'amount': 30.00,
                'currency': 'eur',
                'payment_method_id': pm
            }

            response = self.client.post(self.url, test_data, format='json')
            self.assertEqual(response.status_code, status.HTTP_200_OK)


@pytest.mark.django_db
class PyTestExampleTestCase:
    """Example pytest-style test class"""

    def test_payment_serializer_with_pytest(self):
        """Test serializer using pytest style"""
        data = {
            'amount': 50.00,
            'currency': 'usd',
            'payment_method_id': 'pm_card_visa'
        }
        serializer = PaymentSerializer(data=data)
        assert serializer.is_valid()
        assert serializer.validated_data['amount'] == 50.00
