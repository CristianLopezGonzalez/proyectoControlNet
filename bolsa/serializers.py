from rest_framework import serializers
from .models import BolsaDiasSaldo, BolsaDiasMovimiento, SolicitudCompensacionBolsa
from usuarios.serializers import UsuarioSerializer


class BolsaDiasSaldoSerializer(serializers.ModelSerializer):
    usuario_a_detalle = UsuarioSerializer(source='usuario_a', read_only=True)
    usuario_b_detalle = UsuarioSerializer(source='usuario_b', read_only=True)

    class Meta:
        model = BolsaDiasSaldo
        fields = (
            'id',
            'usuario_a', 'usuario_a_detalle',
            'usuario_b', 'usuario_b_detalle',
            'saldo_dias_a_favor_de_a',
            'saldo_dias_a_favor_de_b',
            'ultima_actualizacion',
        )
        read_only_fields = (
            'saldo_dias_a_favor_de_a',
            'saldo_dias_a_favor_de_b',
            'ultima_actualizacion',
        )


class BolsaDiasMovimientoSerializer(serializers.ModelSerializer):
    origen_usuario_detalle = UsuarioSerializer(source='origen_usuario', read_only=True)
    destino_usuario_detalle = UsuarioSerializer(source='destino_usuario', read_only=True)

    class Meta:
        model = BolsaDiasMovimiento
        fields = (
            'id', 'saldo',
            'origen_usuario', 'origen_usuario_detalle',
            'destino_usuario', 'destino_usuario_detalle',
            'dias', 'tipo', 'solicitud_intercambio', 'fecha',
        )
        read_only_fields = ('fecha',)


class CompensarSerializer(serializers.Serializer):
    """Payload para crear solicitud de compensación."""
    usuario_destino_id = serializers.IntegerField()
    dias = serializers.IntegerField(min_value=1)


class SolicitudCompensacionBolsaSerializer(serializers.ModelSerializer):
    solicitante_detalle = UsuarioSerializer(source='solicitante', read_only=True)
    receptor_detalle = UsuarioSerializer(source='receptor', read_only=True)

    class Meta:
        model = SolicitudCompensacionBolsa
        fields = '__all__'
