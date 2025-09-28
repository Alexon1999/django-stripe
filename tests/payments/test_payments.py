import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from unittest.mock import patch


@pytest.fixture
def client():
    return APIClient()

@pytest.mark.django_db
def test_create_payment_success(client):
    url = reverse('payments:process-payment')
    data = {
        'amount': 1000,
        'currency': 'usd',
        'payment_method_id': 'pm_card_visa',
    }
    # On mock Stripe pour simuler un paiement réussi :
    # - patch remplace PaymentIntent.create par un mock
    # - on force le retour à un objet avec status='succeeded'
    # - la vue renvoie alors 'Payment successful!' car c'est le comportement attendu
    # Résumé :
    # Le patch permet de simuler un paiement réussi sans contacter Stripe,
    # et le test vérifie que la vue réagit comme attendu à ce succès simulé.
    with patch('payments.views.stripe.PaymentIntent.create') as mock_intent_create:
        mock_intent_create.return_value = type('obj', (object,), {'status': 'succeeded'})()
        response = client.post(url, data, format='json')
        assert response.status_code == 200
        assert response.data['message'] == 'Payment successful!'

@pytest.mark.django_db
def test_create_payment_stripe_error(client):
    url = reverse('payments:process-payment')
    data = {
        'amount': 1000,
        'currency': 'usd',
        'payment_method_id': 'pm_card_visa',
    }
    with patch('payments.views.stripe.Charge.create') as mock_charge_create:
        mock_charge_create.side_effect = Exception('Stripe error')
        response = client.post(url, data, format='json')
        assert response.status_code == 400
        assert 'error' in response.data
