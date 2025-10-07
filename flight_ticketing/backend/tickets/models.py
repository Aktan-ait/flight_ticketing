from django.db import models
from users.models import User
from flights.models import Flight

class Ticket(models.Model):
    STATUS_CHOICES = [
        ('booked', 'Booked'),
        ('refunded', 'Refunded'),
        ('canceled', 'Canceled'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tickets')
    flight = models.ForeignKey(Flight, on_delete=models.CASCADE, related_name='tickets')
    confirmation_id = models.CharField(max_length=20, unique=True)
    booked_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='booked')
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"Ticket {self.confirmation_id} - {self.user.username}"

    class Meta:
        indexes = [
            models.Index(fields=['flight']),
            models.Index(fields=['user']),
            models.Index(fields=['status']),
            models.Index(fields=['booked_at']),
        ]
