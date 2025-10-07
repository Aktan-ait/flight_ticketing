from django.contrib import admin
from .models import Payment

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id','provider','provider_intent_id','user','flight','amount','status','created_at')
    list_filter = ('status','provider','currency')
    search_fields = ('provider_intent_id','idempotency_key','user__username')
