from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from unittest.mock import patch, Mock
import stripe
from .serializers import PaymentSerializer


class PaymentSerializerTestCase(TestCase):
    """Test cases for PaymentSerializer"""

    def test_valid_serializer_with_required_fields(self):
        """Test serializer with valid required data"""
        data = {
            'amount': 10.50,
            'currency': 'usd',
            'payment_method_id': 'pm_card_visa'
        }
        serializer = PaymentSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['amount'], 10.50)
        self.assertEqual(serializer.validated_data['currency'], 'usd')
        self.assertEqual(serializer.validated_data['payment_method_id'], 'pm_card_visa')

    def test_valid_serializer_with_default_currency(self):
        """Test serializer uses default currency when not provided"""
        data = {
            'amount': 25.00,
            'payment_method_id': 'pm_card_mastercard'
        }
        serializer = PaymentSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['currency'], 'eur')  # Default currency

    def test_invalid_serializer_missing_amount(self):
        """Test serializer fails when amount is missing"""
        data = {
            'currency': 'gbp',
            'payment_method_id': 'pm_card_visa'
        }
        serializer = PaymentSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('amount', serializer.errors)

    def test_invalid_serializer_missing_payment_method_id(self):
        """Test serializer fails when payment_method_id is missing"""
        data = {
            'amount': 15.75,
            'currency': 'eur'
        }
        serializer = PaymentSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('payment_method_id', serializer.errors)

    def test_invalid_serializer_negative_amount(self):
        """Test serializer fails with negative amount"""
        data = {
            'amount': -5.00,
            'currency': 'usd',
            'payment_method_id': 'pm_card_visa'
        }
        serializer = PaymentSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('amount', serializer.errors)

    def test_invalid_serializer_zero_amount(self):
        """Test serializer fails with zero amount"""
        data = {
            'amount': 0.00,
            'currency': 'usd',
            'payment_method_id': 'pm_card_visa'
        }
        serializer = PaymentSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('amount', serializer.errors)

    def test_invalid_serializer_currency_too_long(self):
        """Test serializer fails when currency is longer than 3 characters"""
        data = {
            'amount': 10.00,
            'currency': 'usdollars',
            'payment_method_id': 'pm_card_visa'
        }
        serializer = PaymentSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('currency', serializer.errors)

    def test_invalid_serializer_payment_method_id_too_long(self):
        """Test serializer fails when payment_method_id is too long"""
        data = {
            'amount': 10.00,
            'currency': 'usd',
            'payment_method_id': 'a' * 256  # Exceeds max_length of 255
        }
        serializer = PaymentSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('payment_method_id', serializer.errors)

    def test_invalid_serializer_amount_below_minimum(self):
        """Test serializer fails with amount below minimum (1.0)"""
        data = {
            'amount': 0.99,
            'currency': 'usd',
            'payment_method_id': 'pm_card_visa'
        }
        serializer = PaymentSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('amount', serializer.errors)


class ProcessPaymentViewTestCase(APITestCase):
    """Test cases for ProcessPaymentView"""

    def setUp(self):
        self.url = reverse('process-payment')
        self.valid_payload = {
            'amount': 25.00,
            'currency': 'usd',
            'payment_method_id': 'pm_card_visa'
        }

    @patch('payments.views.stripe.PaymentIntent.create')
    def test_successful_payment(self, mock_create):
        """Test successful payment processing"""
        # Mock successful Stripe response
        mock_intent = Mock()
        mock_intent.status = 'succeeded'
        mock_create.return_value = mock_intent

        response = self.client.post(self.url, self.valid_payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Payment successful!')
        
        # Verify Stripe API was called with correct parameters
        mock_create.assert_called_once_with(
            amount=2500,  # 25.00 * 100
            currency='usd',
            payment_method='pm_card_visa',
            confirm=True,
            automatic_payment_methods={
                "allow_redirects": "never",
                "enabled": True
            }
        )

    @patch('payments.views.stripe.PaymentIntent.create')
    def test_payment_requires_action(self, mock_create):
        """Test payment that requires additional action"""
        # Mock Stripe response requiring action
        mock_intent = Mock()
        mock_intent.status = 'requires_action'
        mock_create.return_value = mock_intent

        response = self.client.post(self.url, self.valid_payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['message'], 'Payment failed or requires additional action.')

    @patch('payments.views.stripe.PaymentIntent.create')
    def test_payment_failed(self, mock_create):
        """Test failed payment"""
        # Mock failed Stripe response
        mock_intent = Mock()
        mock_intent.status = 'failed'
        mock_create.return_value = mock_intent

        response = self.client.post(self.url, self.valid_payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['message'], 'Payment failed or requires additional action.')

    @patch('payments.views.stripe.PaymentIntent.create')
    def test_card_declined_error(self, mock_create):
        """Test handling of card declined error"""
        # Mock Stripe CardError
        mock_create.side_effect = stripe.error.CardError(
            message='Your card was declined.',
            param='card',
            code='card_declined'
        )

        response = self.client.post(self.url, self.valid_payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        self.assertIn('card was declined', response.data['error'])

    @patch('payments.views.stripe.PaymentIntent.create')
    def test_generic_stripe_error(self, mock_create):
        """Test handling of generic Stripe errors"""
        # Mock generic Stripe error
        mock_create.side_effect = stripe.error.StripeError('Something went wrong')

        response = self.client.post(self.url, self.valid_payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        self.assertIn('Something went wrong', response.data['error'])

    @patch('payments.views.stripe.PaymentIntent.create')
    def test_unexpected_exception(self, mock_create):
        """Test handling of unexpected exceptions"""
        # Mock unexpected exception
        mock_create.side_effect = Exception('Unexpected error')

        response = self.client.post(self.url, self.valid_payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        self.assertIn('Unexpected error', response.data['error'])

    def test_invalid_payload_missing_amount(self):
        """Test request with missing amount field"""
        invalid_payload = {
            'currency': 'usd',
            'payment_method_id': 'pm_card_visa'
        }
        response = self.client.post(self.url, invalid_payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_payload_missing_payment_method_id(self):
        """Test request with missing payment_method_id field"""
        invalid_payload = {
            'amount': 25.00,
            'currency': 'usd'
        }
        response = self.client.post(self.url, invalid_payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_payload_negative_amount(self):
        """Test request with negative amount"""
        invalid_payload = {
            'amount': -10.00,
            'currency': 'usd',
            'payment_method_id': 'pm_card_visa'
        }
        response = self.client.post(self.url, invalid_payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_payload_zero_amount(self):
        """Test request with zero amount"""
        invalid_payload = {
            'amount': 0.00,
            'currency': 'usd',
            'payment_method_id': 'pm_card_visa'
        }
        response = self.client.post(self.url, invalid_payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_payload_amount_below_minimum(self):
        """Test request with amount below minimum (1.0)"""
        invalid_payload = {
            'amount': 0.99,
            'currency': 'usd',
            'payment_method_id': 'pm_card_visa'
        }
        response = self.client.post(self.url, invalid_payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_empty_payload(self):
        """Test request with empty payload"""
        response = self.client.post(self.url, {}, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_malformed_json(self):
        """Test request with malformed JSON"""
        response = self.client.post(
            self.url,
            'invalid json',
            content_type='application/json'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch('payments.views.stripe.PaymentIntent.create')
    def test_amount_conversion_to_cents(self, mock_create):
        """Test that amount is correctly converted to cents"""
        mock_intent = Mock()
        mock_intent.status = 'succeeded'
        mock_create.return_value = mock_intent

        # Test various amounts (all must be >= 1 due to serializer validation)
        test_amounts = [
            (1.00, 100),
            (10.50, 1050),
            (99.99, 9999),
            (1.01, 101),
        ]

        for amount, expected_cents in test_amounts:
            with self.subTest(amount=amount):
                payload = self.valid_payload.copy()
                payload['amount'] = amount
                
                # Reset mock for each iteration
                mock_create.reset_mock()
                mock_create.return_value = mock_intent

                response = self.client.post(self.url, payload, format='json')

                self.assertEqual(response.status_code, status.HTTP_200_OK)
                
                # Check that the amount was converted correctly
                mock_create.assert_called_once_with(
                    amount=expected_cents,
                    currency='usd',
                    payment_method='pm_card_visa',
                    confirm=True,
                    automatic_payment_methods={
                        "allow_redirects": "never",
                        "enabled": True
                    }
                )

    @patch('payments.views.stripe.PaymentIntent.create')
    def test_default_currency(self, mock_create):
        """Test that default currency is used when not specified"""
        mock_intent = Mock()
        mock_intent.status = 'succeeded'
        mock_create.return_value = mock_intent

        payload = {
            'amount': 15.00,
            'payment_method_id': 'pm_card_mastercard'
        }

        response = self.client.post(self.url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify default currency (eur) was used
        mock_create.assert_called_with(
            amount=1500,
            currency='eur',  # Default currency from serializer
            payment_method='pm_card_mastercard',
            confirm=True,
            automatic_payment_methods={
                "allow_redirects": "never",
                "enabled": True
            }
        )

    def test_only_post_method_allowed(self):
        """Test that only POST method is allowed"""
        # Test GET method
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        # Test PUT method
        response = self.client.put(self.url, self.valid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        # Test DELETE method
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
