from rest_framework import serializers
from .models import SolicitudIntercambio
from usuarios.serializers import UsuarioSerializer
from turnos.serializers import AsignacionTurnoSerializer


class SolicitudIntercambioSerializer(serializers.ModelSerializer):
    solicitante_detalle = UsuarioSerializer(source='solicitante', read_only=True)
    receptor_detalle = UsuarioSerializer(source='receptor', read_only=True)
    
    asignacion_origen_detalle = AsignacionTurnoSerializer(source='asignacion_origen', read_only=True)
    asignacion_destino_detalle = AsignacionTurnoSerializer(source='asignacion_destino', read_only=True)

    class Meta:
        model = SolicitudIntercambio
        fields = (
            'id',
            'solicitante', 'solicitante_detalle',
            'receptor', 'receptor_detalle',
            'tipo',
            'asignacion_origen', 'asignacion_origen_detalle',
            'asignacion_destino', 'asignacion_destino_detalle',
            'motivo', 'modo_compensacion',
            'estado', 'fecha_creacion', 'fecha_respuesta',
        )
        read_only_fields = ('estado', 'fecha_creacion', 'fecha_respuesta', 'solicitante')


class CrearSolicitudSerializer(serializers.ModelSerializer):
    """Serializer de escritura para crear una solicitud de intercambio."""

    class Meta:
        model = SolicitudIntercambio
        fields = (
            'receptor', 'tipo',
            'asignacion_origen', 'asignacion_destino',
            'motivo', 'modo_compensacion',
        )
