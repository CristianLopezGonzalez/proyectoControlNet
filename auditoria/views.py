from rest_framework import viewsets
from .models import Auditoria
from .serializers import AuditoriaSerializer
from usuarios.permissions import IsAdminOrSupervisor

class AuditoriaViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Permite acceder de forma global a los registros de auditoría (logs de transacciones y acciones de turnos/bolsa).
    Solo Admins y Supervisores pueden leer la auditoría. Es ReadOnlyModelViewSet porque los registros no se deben crear ni alterar vía REST API.
    """
    queryset = Auditoria.objects.select_related('usuario').all().order_by('-fecha')
    serializer_class = AuditoriaSerializer
    permission_classes = [IsAdminOrSupervisor]
