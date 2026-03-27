from rest_framework import serializers
from .models import Auditoria
from usuarios.serializers import UsuarioSerializer

class AuditoriaSerializer(serializers.ModelSerializer):
    usuario_detalle = UsuarioSerializer(source='usuario', read_only=True)

    class Meta:
        model = Auditoria
        fields = '__all__'
