from rest_framework import serializers
from .models import TurnoSemanal, SolicitudTurnoSemanal
from usuarios.serializers import UsuarioSerializer
from turnos.serializers import CalendarioSemanalListSerializer


class TurnoSemanalSerializer(serializers.ModelSerializer):
    usuario_detalle = UsuarioSerializer(source='usuario', read_only=True)
    semana_detalle = CalendarioSemanalListSerializer(source='semana', read_only=True)

    class Meta:
        model = TurnoSemanal
        fields = ('id', 'semana', 'semana_detalle', 'usuario', 'usuario_detalle', 'estado', 'fecha_creacion')
        read_only_fields = ('estado', 'fecha_creacion')


class SolicitudTurnoSemanalSerializer(serializers.ModelSerializer):
    solicitante_detalle = UsuarioSerializer(source='solicitante', read_only=True)
    receptor_detalle = UsuarioSerializer(source='receptor', read_only=True)
    turno_origen_detalle = TurnoSemanalSerializer(source='turno_origen', read_only=True)
    turno_destino_detalle = TurnoSemanalSerializer(source='turno_destino', read_only=True)

    class Meta:
        model = SolicitudTurnoSemanal
        fields = (
            'id', 'solicitante', 'solicitante_detalle',
            'receptor', 'receptor_detalle',
            'turno_origen', 'turno_origen_detalle',
            'turno_destino', 'turno_destino_detalle',
            'motivo', 'estado', 'fecha_creacion', 'fecha_respuesta'
        )
        read_only_fields = ('solicitante', 'estado', 'fecha_creacion', 'fecha_respuesta')


class CrearSolicitudTurnoSemanalSerializer(serializers.ModelSerializer):
    class Meta:
        model = SolicitudTurnoSemanal
        fields = ('receptor', 'turno_origen', 'turno_destino', 'motivo')

    def validate(self, data):
        request = self.context['request']
        turno_origen = data.get('turno_origen')
        turno_destino = data.get('turno_destino')
        receptor = data.get('receptor')

        # El turno de origen debe pertenecer al solicitante
        if turno_origen.usuario != request.user:
            raise serializers.ValidationError('El turno de origen no te pertenece.')

        # No puedes solicitarte a ti mismo
        if receptor == request.user:
            raise serializers.ValidationError('No puedes solicitar un intercambio contigo mismo.')

        # Si hay turno destino, debe pertenecer al receptor
        if turno_destino and turno_destino.usuario != receptor:
            raise serializers.ValidationError('El turno de destino no pertenece al receptor.')

        return data
