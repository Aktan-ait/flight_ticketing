from rest_framework import serializers
from .models import Payment

class PaymentSerializer(serializers.ModelSerializer):
  class Meta:
    model = Payment
    fields = '__all__'
    read_only_fields = ['id','user','status','provider','provider_intent_id','created_at','updated_at','ticket']
