import secrets
from io import BytesIO
from datetime import timedelta

from django.db import transaction
from django.utils.timezone import now
from django.shortcuts import get_object_or_404
from django.http import FileResponse

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, PermissionDenied

from .models import Ticket
from .serializers import TicketSerializer
from flights.models import Flight

# PDF/QR
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import black
import qrcode
from reportlab.lib.utils import ImageReader


def generate_confirmation_id(length=10):
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return ''.join(secrets.choice(alphabet) for _ in range(length))


class TicketViewSet(viewsets.ModelViewSet):
    queryset = Ticket.objects.all()
    serializer_class = TicketSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = Ticket.objects.select_related('flight', 'user').order_by('-booked_at')
        if getattr(user, 'role', '') == 'admin':
            return qs
        return qs.filter(user=user)

    @transaction.atomic
    @action(detail=False, methods=['post'], url_path='buy')
    def buy(self, request):
        user = request.user
        flight_id = request.data.get('flight')
        if not flight_id:
            raise ValidationError({'flight': 'Обязательное поле'})

        flight = Flight.objects.select_for_update().filter(id=flight_id).first()
        if not flight:
            raise ValidationError({'flight': 'Рейс не найден'})
        if flight.available_seats <= 0:
            raise ValidationError({'detail': 'Нет свободных мест'})
        if flight.departure_time <= now():
            raise ValidationError({'detail': 'Рейс уже вылетел'})

        for _ in range(5):
            cid = generate_confirmation_id()
            if not Ticket.objects.filter(confirmation_id=cid).exists():
                break
        else:
            raise ValidationError({'detail': 'Не удалось сгенерировать confirmation id'})

        ticket = Ticket.objects.create(
            user=user,
            flight=flight,
            confirmation_id=cid,
            status='booked',
            price=flight.price,
        )

        flight.available_seats -= 1
        flight.save(update_fields=['available_seats'])

        return Response(TicketSerializer(ticket).data, status=status.HTTP_201_CREATED)

    @transaction.atomic
    @action(detail=True, methods=['post'], url_path='cancel')
    def cancel(self, request, pk=None):
        ticket = get_object_or_404(self.get_queryset(), pk=pk)
        flight = Flight.objects.select_for_update().get(pk=ticket.flight_id)

        if ticket.status != 'booked':
            raise ValidationError({'detail': 'Билет уже отменён или возмещён'})
        if flight.departure_time <= now():
            raise ValidationError({'detail': 'Рейс уже вылетел — отмена невозможна'})

        hours_left = (flight.departure_time - now()).total_seconds() / 3600.0
        if hours_left >= 24:
            ticket.status = 'refunded'
            flight.available_seats = min(flight.available_seats + 1, flight.total_seats)
            flight.save(update_fields=['available_seats'])
        else:
            ticket.status = 'canceled'

        ticket.save(update_fields=['status'])
        return Response(TicketSerializer(ticket).data)

    @action(detail=True, methods=['get'], url_path='eticket')
    def eticket(self, request, pk=None):
        ticket = get_object_or_404(self.get_queryset(), pk=pk)
        f = ticket.flight

        buf = BytesIO()
        c = canvas.Canvas(buf, pagesize=A4)
        w, h = A4

        c.setFillColor(black)
        c.setFont("Helvetica-Bold", 18)
        c.drawString(20*mm, h-25*mm, "E-TICKET / BOARDING PASS")

        c.setFont("Helvetica", 12)
        c.drawString(20*mm, h-35*mm, f"Passenger: {ticket.user.username}")
        c.drawString(20*mm, h-43*mm, f"Confirmation: {ticket.confirmation_id}")
        c.drawString(20*mm, h-51*mm, f"Flight: {f.flight_number}  ({f.company.name if hasattr(f,'company') else ''})")
        c.drawString(20*mm, h-59*mm, f"Route: {f.origin}  →  {f.destination}")
        c.drawString(20*mm, h-67*mm, f"Departure: {f.departure_time.strftime('%Y-%m-%d %H:%M')}")
        c.drawString(20*mm, h-75*mm, f"Arrival:   {f.arrival_time.strftime('%Y-%m-%d %H:%M')}")
        c.drawString(20*mm, h-83*mm, f"Price: ${ticket.price}")

        # QR c полезной строкой для валидации
        qr_payload = f"CONF:{ticket.confirmation_id}|USER:{ticket.user_id}|FLIGHT:{f.id}"
        qr_img = qrcode.make(qr_payload)
        qr_reader = ImageReader(qr_img)
        c.drawImage(qr_reader, w-60*mm, h-90*mm, 40*mm, 40*mm, mask='auto')

        c.showPage()
        c.save()
        buf.seek(0)
        filename = f"e-ticket-{ticket.confirmation_id}.pdf"
        return FileResponse(buf, as_attachment=True, filename=filename)
