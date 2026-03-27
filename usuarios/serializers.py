from rest_framework import serializers
from .models import Usuario, Equipo


class EquipoSerializer(serializers.ModelSerializer):
    supervisor_nombre = serializers.ReadOnlyField(source='supervisor.nombre')

    class Meta:
        model = Equipo
        fields = ('id', 'nombre', 'descripcion', 'supervisor', 'supervisor_nombre')


class UsuarioSerializer(serializers.ModelSerializer):
    equipo_nombre = serializers.ReadOnlyField(source='equipo.nombre')

    class Meta:
        model = Usuario
        fields = ('id', 'nombre', 'email', 'rol', 'activo', 'equipo', 'equipo_nombre')


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = Usuario
        fields = ('nombre', 'email', 'password', 'rol', 'equipo')

    def create(self, validated_data):
        return Usuario.objects.create_user(**validated_data)