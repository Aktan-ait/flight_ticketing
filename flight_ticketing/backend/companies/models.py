from django.db import models
from users.models import User

class Company(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    manager = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name
