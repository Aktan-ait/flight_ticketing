from rest_framework import serializers
from .models import Banner

class BannerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Banner
        fields = ['id', 'title', 'image_url', 'link_url', 'is_active', 'sort_order']
