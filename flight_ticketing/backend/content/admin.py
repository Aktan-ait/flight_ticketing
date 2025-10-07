from django.contrib import admin
from .models import Banner

@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'is_active', 'sort_order')
    list_editable = ('is_active', 'sort_order')
    search_fields = ('title',)
