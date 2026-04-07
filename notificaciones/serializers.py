from rest_framework import serializers
from .models import Notificacion

class NotificacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notificacion
        fields = '__all__'
        read_only_fields = ('usuario', 'tipo', 'titulo', 'mensaje', 'fecha', 'enlace_entidad')
