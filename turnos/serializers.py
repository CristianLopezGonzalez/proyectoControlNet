from rest_framework import serializers
from .models import (
    CalendarioSemanal, PlantillaTurno, PatronRotacion,
    Vacacion, Incidencia, AsignacionTurno
)
from usuarios.serializers import UsuarioSerializer


class PlantillaTurnoSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlantillaTurno
        fields = '__all__'


class PatronRotacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatronRotacion
        fields = '__all__'


class VacacionSerializer(serializers.ModelSerializer):
    usuario_detalle = UsuarioSerializer(source='usuario', read_only=True)

    class Meta:
        model = Vacacion
        fields = '__all__'
        read_only_fields = ('estado', 'fecha_solicitud')


class IncidenciaSerializer(serializers.ModelSerializer):
    usuario_detalle = UsuarioSerializer(source='usuario', read_only=True)

    class Meta:
        model = Incidencia
        fields = '__all__'
        read_only_fields = ('fecha_creacion',)


class AsignacionTurnoSerializer(serializers.ModelSerializer):
    usuario_detalle = UsuarioSerializer(source='usuario', read_only=True)
    turno_plantilla_detalle = PlantillaTurnoSerializer(source='turno_plantilla', read_only=True)

    class Meta:
        model = AsignacionTurno
        fields = (
            'id', 'semana', 'usuario', 'usuario_detalle',
            'dia', 'turno_plantilla', 'turno_plantilla_detalle', 'estado'
        )
        read_only_fields = ('estado',)


class CalendarioSemanalSerializer(serializers.ModelSerializer):
    asignaciones = AsignacionTurnoSerializer(many=True, read_only=True)

    class Meta:
        model = CalendarioSemanal
        fields = (
            'id', 'anio', 'numero_semana',
            'fecha_inicio_semana', 'fecha_fin_semana',
            'estado', 'asignaciones'
        )
        read_only_fields = ('estado',)


class CalendarioSemanalListSerializer(serializers.ModelSerializer):
    class Meta:
        model = CalendarioSemanal
        fields = (
            'id', 'anio', 'numero_semana',
            'fecha_inicio_semana', 'fecha_fin_semana', 'estado'
        )
