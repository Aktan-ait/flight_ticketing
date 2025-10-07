from datetime import timedelta, date, datetime
from django.db.models import Sum, Min, Count
from django.utils.timezone import now
from django.db.models.functions import TruncDate
from django.http import HttpResponse
import csv

from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from rest_framework.pagination import PageNumberPagination
from rest_framework.filters import OrderingFilter, SearchFilter
from django_filters.rest_framework import DjangoFilterBackend

from .models import Flight
from .serializers import FlightSerializer
from .permissions import IsManagerOrAdmin, IsOwnerCompanyFlightOrAdmin
from .filters import FlightFilter
from companies.models import Company
from tickets.models import Ticket
from tickets.serializers import TicketWithUserSerializer


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class FlightViewSet(viewsets.ModelViewSet):
    queryset = Flight.objects.all().order_by('-departure_time')
    serializer_class = FlightSerializer
    pagination_class = StandardResultsSetPagination

    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    filterset_class = FlightFilter
    ordering_fields = ['price', 'departure_time', 'arrival_time']
    search_fields = ['flight_number', 'origin', 'destination']

    def get_permissions(self):
        if self.action in ['create']:
            return [IsManagerOrAdmin()]
        elif self.action in ['update', 'partial_update', 'destroy']:
            return [IsOwnerCompanyFlightOrAdmin()]
        elif self.action in ['passengers']:
            return [IsOwnerCompanyFlightOrAdmin()]
        elif self.action in ['stats_my']:
            return [IsManagerOrAdmin()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        qs = super().get_queryset()
        req = self.request
        user = req.user
        mine = req.query_params.get('mine')
        if mine and user.is_authenticated and getattr(user, 'role', None) == 'manager':
            try:
                company = Company.objects.get(manager=user)
                qs = qs.filter(company=company)
            except Company.DoesNotExist:
                return Flight.objects.none()
        return qs

    def perform_create(self, serializer):
        user = self.request.user
        if getattr(user, 'role', None) == 'manager':
            try:
                company = Company.objects.get(manager=user)
            except Company.DoesNotExist:
                raise PermissionDenied('У менеджера нет привязанной компании')
            serializer.save(company=company)
        elif getattr(user, 'role', None) == 'admin':
            serializer.save()
        else:
            raise PermissionDenied('Недостаточно прав для создания рейса')

    def perform_update(self, serializer):
        instance = self.get_object()
        has_bookings = Ticket.objects.filter(flight=instance, status='booked').exists()
        if has_bookings:
            blocked_fields = {'departure_time', 'arrival_time', 'price', 'total_seats'}
            changing = blocked_fields.intersection(set(serializer.validated_data.keys()))
            if changing:
                raise PermissionDenied(
                    f"Нельзя изменять {', '.join(sorted(changing))} — по рейсу есть активные брони"
                )
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if Ticket.objects.filter(flight=instance).exists():
            raise PermissionDenied('Нельзя удалить рейс: существуют связанные билеты')
        return super().destroy(request, *args, **kwargs)

    # 🔸 статистика менеджера (его компании)
    @action(detail=False, methods=['get'], url_path='stats/my', permission_classes=[IsManagerOrAdmin])
    def stats_my(self, request):
        user = request.user
        if user.role == 'admin':
            return Response({"detail": "Для админа используйте статистику сервиса в админ-панели"})
        try:
            company = Company.objects.get(manager=user)
        except Company.DoesNotExist:
            return Response({"detail": "У вас нет привязанной компании"}, status=404)

        window = request.query_params.get('window', 'month')
        now_dt = now()
        start = None
        if window == 'day':
            start = now_dt - timedelta(days=1)
        elif window == 'week':
            start = now_dt - timedelta(weeks=1)
        elif window == 'month':
            start = now_dt - timedelta(days=30)

        flights = Flight.objects.filter(company=company)
        if start:
            flights = flights.filter(departure_time__gte=start)

        total_flights = flights.count()
        upcoming = flights.filter(departure_time__gte=now_dt).count()
        completed = flights.filter(departure_time__lt=now_dt).count()

        tickets_qs = Ticket.objects.filter(flight__in=flights)
        total_passengers = tickets_qs.count()
        revenue = tickets_qs.filter(status='booked').aggregate(s=Sum('price'))['s'] or 0

        return Response({
            'window': window,
            'total_flights': total_flights,
            'upcoming': upcoming,
            'completed': completed,
            'total_passengers': total_passengers,
            'revenue': float(revenue),
        })

    # 🔸 список пассажиров рейса + сводка
    @action(detail=True, methods=['get'], url_path='passengers', permission_classes=[IsOwnerCompanyFlightOrAdmin])
    def passengers(self, request, pk=None):
        """
        Возвращает список пассажиров рейса + сводку.
        """
        flight = self.get_object()
        tickets = Ticket.objects.select_related('user').filter(flight=flight).order_by('seat', '-booked_at')

        data = TicketWithUserSerializer(tickets, many=True).data
        revenue = tickets.filter(status='booked').aggregate(s=Sum('price'))['s'] or 0

        return Response({
            'flight_id': flight.id,
            'flight_number': flight.flight_number,
            'origin': flight.origin,
            'destination': flight.destination,
            'count': len(data),
            'revenue': float(revenue),
            'tickets': data,
        })

    # 🔸 CSV-выгрузка пассажиров
    @action(detail=True, methods=['get'], url_path='passengers/csv', permission_classes=[IsOwnerCompanyFlightOrAdmin])
    def passengers_csv(self, request, pk=None):
        """
        CSV-выгрузка пассажиров по рейсу.
        """
        flight = self.get_object()
        qs = Ticket.objects.select_related('user').filter(flight=flight).order_by('seat', '-booked_at')

        response = HttpResponse(content_type='text/csv; charset=utf-8')
        filename = f'passengers-flight-{flight.flight_number}-{flight.id}.csv'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        writer = csv.writer(response)
        writer.writerow([
            'Confirmation', 'Status', 'Seat', 'Price',
            'Booked at', 'Username', 'Email', 'Flight', 'Origin', 'Destination'
        ])
        for t in qs:
            writer.writerow([
                t.confirmation_id, t.status, t.seat or '',
                f'{t.price}', t.booked_at.strftime('%Y-%m-%d %H:%M'),
                getattr(t.user, 'username', ''), getattr(t.user, 'email', ''),
                flight.flight_number, flight.origin, flight.destination
            ])
        return response

    # 🔸 Календарь минимальных цен
    @action(detail=False, methods=['get'], url_path='price-calendar')
    def price_calendar(self, request):
        """
        GET /api/flights/price-calendar/?origin=&destination=&start=YYYY-MM-DD&days=30
        Возвращает [{date:'YYYY-MM-DD', min_price:float, flights:int}, ...]
        """
        origin = request.query_params.get('origin', '').strip()
        destination = request.query_params.get('destination', '').strip()
        start_str = request.query_params.get('start', '')
        days = int(request.query_params.get('days', '30'))
        if days < 1:
            days = 1
        if days > 120:
            days = 120

        if start_str:
            try:
                start_date = datetime.strptime(start_str, '%Y-%m-%d').date()
            except ValueError:
                start_date = date.today()
        else:
            start_date = date.today()

        end_date = start_date + timedelta(days=days - 1)

        qs = Flight.objects.filter(
            departure_time__date__gte=start_date,
            departure_time__date__lte=end_date
        )
        if origin:
            qs = qs.filter(origin__icontains=origin)
        if destination:
            qs = qs.filter(destination__icontains=destination)

        agg = (
            qs.annotate(d=TruncDate('departure_time'))
            .values('d')
            .annotate(min_price=Min('price'), flights=Count('id'))
            .order_by('d')
        )

        data = [
            {'date': a['d'].isoformat(), 'min_price': float(a['min_price']), 'flights': a['flights']}
            for a in agg
        ]
        return Response({'start': start_date.isoformat(), 'days': days, 'items': data})
