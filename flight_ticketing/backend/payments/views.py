import uuid
from datetime import timedelta
from django.db import transaction
from django.utils.timezone import now
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, PermissionDenied

from .models import Payment
from .serializers import PaymentSerializer
from flights.models import Flight
from tickets.models import Ticket
from tickets.views import generate_confirmation_id  # используем генератор из tickets

class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.select_related('flight','user','ticket').order_by('-created_at')
    serializer_class = PaymentSerializer

    def get_permissions(self):
        if self.action in ['create_intent', 'webhook', 'mock_capture']:
            return [permissions.AllowAny()] if self.action=='webhook' else [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if getattr(user,'role','') == 'admin':
            return super().get_queryset()
        return super().get_queryset().filter(user=user)

    def _get_idem_key(self, request):
        key = request.headers.get('Idempotency-Key') or request.data.get('idempotency_key')
        if not key:
            raise ValidationError({'idempotency_key': 'Требуется Idempotency-Key (в заголовке или body).'})
        return key

    @transaction.atomic
    @action(detail=False, methods=['post'], url_path='create-intent')
    def create_intent(self, request):
        """
        Создать платежный интент и удержать место.
        body: { flight: <id> }, + Idempotency-Key.
        """
        user = request.user
        flight_id = request.data.get('flight')
        if not flight_id:
            raise ValidationError({'flight':'Обязательное поле'})

        idem = self._get_idem_key(request)

        existing = Payment.objects.filter(idempotency_key=idem, user=user).first()
        if existing:
            # Вернём как есть (идемпотентность)
            return Response(PaymentSerializer(existing).data, status=200)

        flight = Flight.objects.select_for_update().filter(id=flight_id).first()
        if not flight:
            raise ValidationError({'flight':'Рейс не найден'})
        if flight.departure_time <= now():
            raise ValidationError({'detail':'Рейс уже вылетел'})
        if flight.available_seats <= 0:
            raise ValidationError({'detail':'Нет свободных мест'})

        # удерживаем место
        flight.available_seats -= 1
        flight.save(update_fields=['available_seats'])

        pay = Payment.objects.create(
            user=user,
            flight=flight,
            amount=flight.price,
            provider='mock',
            provider_intent_id=str(uuid.uuid4()),
            idempotency_key=idem,
            status='pending',
            expires_at=now() + timedelta(minutes=15),
        )
        return Response(PaymentSerializer(pay).data, status=status.HTTP_201_CREATED)

    @transaction.atomic
    @action(detail=False, methods=['post'], url_path='webhook')
    def webhook(self, request):
        """
        Псевдо-webhook провайдера.
        body: { provider_intent_id: str, event: 'payment_succeeded'|'payment_failed' }
        """
        intent = request.data.get('provider_intent_id')
        event = request.data.get('event')
        if not intent or event not in ('payment_succeeded','payment_failed'):
            raise ValidationError({'detail':'Некорректные данные'})

        pay = get_object_or_404(Payment.objects.select_for_update(), provider_intent_id=intent)

        if pay.status == 'paid':
            return Response({'detail':'Уже оплачено'}, status=200)
        if pay.status not in ('pending',):
            return Response({'detail':f'Статус: {pay.status} — операция игнорируется'}, status=200)

        if event == 'payment_succeeded':
            # создаём билет (если нет)
            if not pay.ticket:
                # защитимся от вылетевшего рейса
                if pay.flight.departure_time <= now():
                    pay.status = 'canceled'
                    pay.save(update_fields=['status'])
                    # возвращаем место
                    pay.flight.available_seats += 1
                    pay.flight.save(update_fields=['available_seats'])
                    return Response({'detail':'Рейс истёк, оплата отменена'}, status=200)

                cid = generate_confirmation_id()
                ticket = Ticket.objects.create(
                    user=pay.user,
                    flight=pay.flight,
                    confirmation_id=cid,
                    status='booked',
                    price=pay.amount,
                )
                pay.ticket = ticket
            pay.status = 'paid'
            pay.save(update_fields=['status','ticket'])
            return Response({'detail':'OK', 'ticket_id': pay.ticket_id}, status=200)

        # failed — вернуть удержанное место, если билета нет
        if not pay.ticket:
            pay.flight.available_seats += 1
            pay.flight.save(update_fields=['available_seats'])
        pay.status = 'failed'
        pay.save(update_fields=['status'])
        return Response({'detail':'FAILED'}, status=200)

    @transaction.atomic
    @action(detail=True, methods=['post'], url_path='mock-capture')
    def mock_capture(self, request, pk=None):
        """
        Тестовый капчур без внешнего провайдера.
        body: { status: 'paid' | 'failed' }  (default: 'paid')
        """
        pay = get_object_or_404(self.get_queryset().select_for_update(), pk=pk)
        status_want = (request.data.get('status') or 'paid').lower()
        if status_want == 'paid':
            # имитируем webhook успеха
            req = type("Obj", (), {"data": {'provider_intent_id': pay.provider_intent_id, 'event': 'payment_succeeded'}})
        else:
            req = type("Obj", (), {"data": {'provider_intent_id': pay.provider_intent_id, 'event': 'payment_failed'}})
        return PaymentViewSet().webhook(req)
