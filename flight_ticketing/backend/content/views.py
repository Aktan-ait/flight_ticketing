from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from users.permissions import IsAdmin
from .models import Banner
from .serializers import BannerSerializer

class BannerViewSet(viewsets.ModelViewSet):
    queryset = Banner.objects.all().order_by('sort_order', 'id')
    serializer_class = BannerSerializer

    def get_permissions(self):
        # Публичный доступ только к /api/banners/active/
        if getattr(self, 'action', None) == 'active':
            return [permissions.AllowAny()]
        # Всё остальное (CRUD, list, retrieve) — только админ
        return [IsAdmin()]

    @action(detail=False, methods=['get'], url_path='active')
    def active(self, request):
        qs = Banner.objects.filter(is_active=True).order_by('sort_order', 'id')
        data = self.get_serializer(qs, many=True).data
        return Response(data)
