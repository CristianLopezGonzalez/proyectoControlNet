from rest_framework import serializers
from .models import Usuario, Equipo


class EquipoSerializer(serializers.ModelSerializer):
    supervisor_nombre = serializers.ReadOnlyField(source='supervisor.nombre')
    miembros_detalle = serializers.SerializerMethodField()

    class Meta:
        model = Equipo
        fields = ('id', 'nombre', 'descripcion', 'supervisor', 'supervisor_nombre', 'miembros_detalle')

    def get_miembros_detalle(self, obj):
        # Retorna info estructurada para no causar dependencias circulares masivas (nested objects)
        return [{'id': u.id, 'nombre': u.nombre, 'rol': u.rol, 'activo': u.activo} for u in obj.miembros.all()]

    def validate_supervisor(self, value):
        if value and value.rol not in ['supervisor', 'admin']:
            raise serializers.ValidationError("El supervisor asignado debe tener el rol de 'supervisor' o 'admin'.")
        return value


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