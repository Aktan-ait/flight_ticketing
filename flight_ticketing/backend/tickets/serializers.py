from rest_framework import serializers
from .models import Ticket
from flights.serializers import FlightSerializer

class TicketSerializer(serializers.ModelSerializer):
    # Для страницы Мои билеты
    flight_detail = FlightSerializer(source='flight', read_only=True)

    class Meta:
        model = Ticket
        fields = [
            'id', 'user', 'flight', 'flight_detail',
            'confirmation_id', 'booked_at', 'status', 'price'
        ]
        read_only_fields = ['id', 'user', 'confirmation_id', 'booked_at', 'status', 'price']


class TicketWithUserSerializer(serializers.ModelSerializer):
    # Для списка пассажиров менеджеру
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = Ticket
        fields = [
            'id',
            'user_id', 'username', 'email',
            'confirmation_id', 'status', 'price', 'booked_at'
        ]
        read_only_fields = fields
