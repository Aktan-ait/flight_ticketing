"""
URL configuration for backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from users.views import CustomTokenObtainPairView, RegisterView
from rest_framework_simplejwt.views import TokenRefreshView
from users.views import UserViewSet
from flights.views import FlightViewSet
from tickets.views import TicketViewSet
from companies.views import CompanyViewSet
from content.views import BannerViewSet  # ←
from payments.views import PaymentViewSet
from users.views import me




router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'flights', FlightViewSet)
router.register(r'tickets', TicketViewSet)
router.register(r'companies', CompanyViewSet)
router.register(r'banners', BannerViewSet)  # ←
router.register(r'payments', PaymentViewSet)  # ← добавить



urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    # auth
    path('api/auth/login/',  CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/auth/register/', RegisterView.as_view(), name='register'),
    path("api/auth/me/", me),
]
