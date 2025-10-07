from rest_framework import serializers
#from django.contrib.auth.password_validation import validate_password
from .models import User


# 🔹 Регистрация
class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)


    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'role']

    def create(self, validated_data):
        user = User(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            role=validated_data.get('role', 'user')
        )
        user.set_password(validated_data['password'])
        user.save()
        return user


# 🔹 Обычный пользователь (просмотр профиля)
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "role"]
        read_only_fields = ['id', 'date_joined']


# 🔹 Администратор (видит всё)
class AdminUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'role', 'is_active', 'date_joined']
