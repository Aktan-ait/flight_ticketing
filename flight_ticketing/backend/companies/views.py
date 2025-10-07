from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Company
from .serializers import CompanySerializer
from users.permissions import IsAdmin

class CompanyViewSet(viewsets.ModelViewSet):
    queryset = Company.objects.all().order_by('name')
    serializer_class = CompanySerializer

    def get_permissions(self):
        # Все CRUD на компании — только админ (менеджера привязывает админ)
        if self.action in ['list', 'retrieve', 'create', 'update', 'partial_update', 'destroy',
                           'activate', 'deactivate']:
            return [IsAdmin()]
        return [permissions.IsAuthenticated()]

    @action(detail=True, methods=['patch'])
    def activate(self, request, pk=None):
        company = self.get_object()
        company.is_active = True
        company.save(update_fields=['is_active'])
        return Response({'detail': 'Компания активирована'})

    @action(detail=True, methods=['patch'])
    def deactivate(self, request, pk=None):
        company = self.get_object()
        company.is_active = False
        company.save(update_fields=['is_active'])
        return Response({'detail': 'Компания деактивирована'})
