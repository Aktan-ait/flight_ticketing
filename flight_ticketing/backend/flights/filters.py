from django_filters import rest_framework as filters
from .models import Flight

class FlightFilter(filters.FilterSet):
    # Цена
    price_min = filters.NumberFilter(field_name='price', lookup_expr='gte')
    price_max = filters.NumberFilter(field_name='price', lookup_expr='lte')

    # Даты (по дате вылета)
    date_from = filters.DateFilter(method='filter_date_from')
    date_to   = filters.DateFilter(method='filter_date_to')

    # Компания (id)
    company = filters.NumberFilter(field_name='company_id', lookup_expr='exact')

    # Город отправления/назначения (icontains)
    origin = filters.CharFilter(field_name='origin', lookup_expr='icontains')
    destination = filters.CharFilter(field_name='destination', lookup_expr='icontains')

    class Meta:
        model = Flight
        fields = ['company', 'origin', 'destination']  # остальные через кастомные методы

    def filter_date_from(self, queryset, name, value):
        return queryset.filter(departure_time__date__gte=value)

    def filter_date_to(self, queryset, name, value):
        return queryset.filter(departure_time__date__lte=value)
