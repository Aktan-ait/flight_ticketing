from django.db import models
from django.db.models import Q, F
from companies.models import Company

class Flight(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='flights')
    flight_number = models.CharField(max_length=10)
    origin = models.CharField(max_length=100)
    destination = models.CharField(max_length=100)
    departure_time = models.DateTimeField()
    arrival_time = models.DateTimeField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    total_seats = models.IntegerField()
    available_seats = models.IntegerField()

    def __str__(self):
        return f"{self.flight_number} - {self.origin} → {self.destination}"

    class Meta:
        indexes = [
            models.Index(fields=['departure_time']),
            models.Index(fields=['price']),
            models.Index(fields=['company']),
            models.Index(fields=['origin']),
            models.Index(fields=['destination']),
        ]
        constraints = [
            models.CheckConstraint(check=Q(available_seats__gte=0), name='flight_available_seats_gte_0'),
            models.CheckConstraint(check=Q(total_seats__gte=0), name='flight_total_seats_gte_0'),
            models.CheckConstraint(check=Q(price__gte=0), name='flight_price_gte_0'),
            models.CheckConstraint(check=Q(available_seats__lte=F('total_seats')), name='flight_available_le_total'),
            models.UniqueConstraint(fields=['company', 'flight_number', 'departure_time'], name='uniq_company_flightnumber_departuretime'),
        ]
