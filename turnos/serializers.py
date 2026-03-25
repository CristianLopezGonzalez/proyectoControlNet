from rest_framework import serializers
from .models import CalendarioSemanal, AsignacionTarde
from usuarios.serializers import UsuarioSerializer


class AsignacionTardeSerializer(serializers.ModelSerializer):
    usuario_detalle = UsuarioSerializer(source='usuario', read_only=True)

    class Meta:
        model = AsignacionTarde
        fields = (
            'id', 'semana', 'usuario', 'usuario_detalle',
            'dia', 'hora_inicio', 'hora_fin', 'estado'
        )
        read_only_fields = ('estado',)


class CalendarioSemanalSerializer(serializers.ModelSerializer):
    asignaciones = AsignacionTardeSerializer(many=True, read_only=True)

    class Meta:
        model = CalendarioSemanal
        fields = (
            'id', 'anio', 'numero_semana',
            'fecha_inicio_semana', 'fecha_fin_semana',
            'estado', 'asignaciones'
        )
        read_only_fields = ('estado',)


class CalendarioSemanalListSerializer(serializers.ModelSerializer):
    """Serializer ligero para listados (sin asignaciones anidadas)."""

    class Meta:
        model = CalendarioSemanal
        fields = (
            'id', 'anio', 'numero_semana',
            'fecha_inicio_semana', 'fecha_fin_semana', 'estado'
        )
