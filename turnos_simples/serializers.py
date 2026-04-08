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
            'motivo', 'modo_compensacion', 'estado', 'fecha_creacion', 'fecha_respuesta'
        )
        read_only_fields = ('solicitante', 'estado', 'fecha_creacion', 'fecha_respuesta')


class CrearSolicitudTurnoSemanalSerializer(serializers.ModelSerializer):
    fecha_inicio = serializers.DateField(write_only=True)
    fecha_fin = serializers.DateField(write_only=True)
    fecha_inicio_destino = serializers.DateField(write_only=True, required=False)
    fecha_fin_destino = serializers.DateField(write_only=True, required=False)
    comentario = serializers.CharField(source='motivo', required=False, allow_blank=True)

    class Meta:
        model = SolicitudTurnoSemanal
        fields = ('receptor', 'fecha_inicio', 'fecha_fin', 'fecha_inicio_destino', 'fecha_fin_destino', 'comentario')

    def validate(self, data):
        request = self.context['request']
        user = request.user
        receptor = data.get('receptor')

        if receptor == user:
            raise serializers.ValidationError('No puedes solicitar un intercambio contigo mismo.')

        # Buscar el turno origen
        turno_origen = TurnoSemanal.objects.filter(
            usuario=user,
            semana__fecha_inicio_semana__lte=data['fecha_inicio'],
            semana__fecha_fin_semana__gte=data['fecha_fin']
        ).first()

        if not turno_origen:
            raise serializers.ValidationError({"fecha_inicio": "No tienes un turno asignado en las fechas solicitadas."})

        data['turno_origen'] = turno_origen

        # Buscar el turno destino si es mutuo
        if 'fecha_inicio_destino' in data and 'fecha_fin_destino' in data:
            turno_destino = TurnoSemanal.objects.filter(
                usuario=receptor,
                semana__fecha_inicio_semana__lte=data['fecha_inicio_destino'],
                semana__fecha_fin_semana__gte=data['fecha_fin_destino']
            ).first()

            if not turno_destino:
                raise serializers.ValidationError({"fecha_inicio_destino": "El compañero no tiene turno en esas fechas."})
            data['turno_destino'] = turno_destino

        return data

    def create(self, validated_data):
        # Limpiar los campos virtuales de fecha para que ModelSerializer.create funcione
        validated_data.pop('fecha_inicio', None)
        validated_data.pop('fecha_fin', None)
        validated_data.pop('fecha_inicio_destino', None)
        validated_data.pop('fecha_fin_destino', None)
        return super().create(validated_data)
