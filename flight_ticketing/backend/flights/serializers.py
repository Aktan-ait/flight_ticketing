from rest_framework import serializers
from .models import Flight

class FlightSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.name', read_only=True)

    class Meta:
        model = Flight
        fields = [
            'id', 'company', 'company_name', 'flight_number', 'origin', 'destination',
            'departure_time', 'arrival_time', 'price', 'total_seats', 'available_seats'
        ]
        read_only_fields = ['id', 'available_seats', 'company_name']

    def validate(self, attrs):
        dep = attrs.get('departure_time') or getattr(self.instance, 'departure_time', None)
        arr = attrs.get('arrival_time') or getattr(self.instance, 'arrival_time', None)
        if dep and arr and arr <= dep:
            raise serializers.ValidationError('arrival_time должен быть позже departure_time')
        price = attrs.get('price')
        if price is not None and price < 0:
            raise serializers.ValidationError('price не может быть отрицательной')
        total = attrs.get('total_seats')
        if total is not None and total < 0:
            raise serializers.ValidationError('total_seats не может быть отрицательным')
        return attrs

    def create(self, validated_data):
        # если не прислали available_seats — ставим = total_seats
        if 'available_seats' not in validated_data:
            validated_data['available_seats'] = validated_data.get('total_seats', 0)
        return super().create(validated_data)
