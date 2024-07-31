from rest_framework import serializers


class PaymentSerializer(serializers.Serializer):
    amount = serializers.FloatField(min_value=1)
    currency = serializers.CharField(max_length=3, default='eur')
    payment_method_id = serializers.CharField(
        max_length=255,
    )
