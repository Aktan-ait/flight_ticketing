from django.db import models
from django.utils.timezone import now, timedelta
from users.models import User
from flights.models import Flight
from tickets.models import Ticket

class Payment(models.Model):
    STATUS = (
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('canceled', 'Canceled'),
        ('expired', 'Expired'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    flight = models.ForeignKey(Flight, on_delete=models.PROTECT, related_name='payments')
    ticket = models.OneToOneField(Ticket, on_delete=models.SET_NULL, null=True, blank=True, related_name='payment')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=8, default='USD')
    provider = models.CharField(max_length=32, default='mock')
    provider_intent_id = models.CharField(max_length=64, unique=True)
    idempotency_key = models.CharField(max_length=64, unique=True)
    status = models.CharField(max_length=10, choices=STATUS, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(null=True, blank=True)  # холд до

    def __str__(self):
        return f"{self.provider}:{self.provider_intent_id} [{self.status}]"

    class Meta:
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['flight']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]
