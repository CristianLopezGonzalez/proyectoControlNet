from rest_framework import serializers
from .models import Usuario


class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ('id', 'nombre', 'email', 'rol', 'activo')


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = Usuario
        fields = ('nombre', 'email', 'password', 'rol')

    def create(self, validated_data):
        return Usuario.objects.create_user(**validated_data)