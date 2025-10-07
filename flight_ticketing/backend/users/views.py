from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from .serializers import RegisterSerializer, UserSerializer, AdminUserSerializer
from .models import User
from .permissions import IsAdmin


# 🔹 JWT токен с username и role
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["username"] = user.username
        token["role"] = user.role
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data["username"] = self.user.username
        data["role"] = self.user.role
        return data


# 🔹 Авторизация (JWT Login)
class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


# 🔹 Регистрация
class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"detail": "User successfully registered!"},
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# 🔹 Управление пользователями (только для админа)
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by('-date_joined')

    def get_serializer_class(self):
        """Для админа — расширенный сериализатор"""
        if self.request.user.is_authenticated and getattr(self.request.user, 'role', '') == 'admin':
            return AdminUserSerializer
        return UserSerializer

    def get_permissions(self):
        """Права доступа зависят от действия"""
        if self.action in ['list', 'retrieve', 'create', 'destroy', 'update', 'partial_update',
                           'block', 'unblock', 'set_role']:
            return [IsAdmin()]
        return [permissions.IsAuthenticated()]

    # 🔸 Блокировка пользователя
    @action(detail=True, methods=['patch'])
    def block(self, request, pk=None):
        user = self.get_object()
        if user.role == 'admin':
            return Response({'detail': 'Нельзя блокировать администратора'}, status=status.HTTP_400_BAD_REQUEST)
        user.is_active = False
        user.save(update_fields=['is_active'])
        return Response({'detail': 'Пользователь заблокирован'}, status=status.HTTP_200_OK)

    # 🔸 Разблокировка пользователя
    @action(detail=True, methods=['patch'])
    def unblock(self, request, pk=None):
        user = self.get_object()
        user.is_active = True
        user.save(update_fields=['is_active'])
        return Response({'detail': 'Пользователь разблокирован'}, status=status.HTTP_200_OK)

    # 🔸 Изменение роли
    @action(detail=True, methods=['patch'], url_path='set-role')
    def set_role(self, request, pk=None):
        user = self.get_object()
        role = request.data.get('role')
        if role not in ['user', 'manager', 'admin']:
            return Response({'detail': 'Недопустимая роль'}, status=status.HTTP_400_BAD_REQUEST)
        user.role = role
        user.save(update_fields=['role'])
        return Response({'detail': f'Роль изменена на {user.role}'}, status=status.HTTP_200_OK)


# 🔹 Эндпоинт для получения текущего пользователя
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    """Возвращает данные текущего пользователя по токену JWT"""
    return Response(UserSerializer(request.user).data)
