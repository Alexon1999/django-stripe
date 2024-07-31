from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import PaymentSerializer
import stripe
from django.conf import settings

stripe.api_key = settings.STRIPE_SECRET_KEY


class ProcessPaymentView(APIView):
    permission_classes = []
    serializer_class = PaymentSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            # Create a PaymentIntent and confirm it
            intent = stripe.PaymentIntent.create(
                amount=int(data['amount'] * 100),
                currency=data['currency'],
                # payment_method_id is created in ClienSide using Stripe.js for web applications or @stripe/stripe-react-native for React Native apps
                # testing payment_method_id: pm_card_visa (visa testing card) or you have this list here https://docs.stripe.com/testing?testing-method=payment-methods
                payment_method=data['payment_method_id'],
                confirm=True,
                # automatic payment moethods allow redirect never
                automatic_payment_methods={
                    "allow_redirects": "never",
                    "enabled": True
                }
            )

            if intent.status == 'succeeded':
                return Response({'message': 'Payment successful!'}, status=status.HTTP_200_OK)
            else:
                return Response({'message': 'Payment failed or requires additional action.'}, status=status.HTTP_400_BAD_REQUEST)

        except stripe.error.CardError as e:
            # Handle declined card
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
