from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Notificacion
from .serializers import NotificacionSerializer

class NotificacionViewSet(viewsets.ModelViewSet):
    serializer_class = NotificacionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Cada usuario solo ve sus propias notificaciones
        return Notificacion.objects.filter(usuario=self.request.user).order_by('-fecha')

    @action(detail=False, methods=['get'], url_path='no-leidas/count')
    def count_unread(self, request):
        count = self.get_queryset().filter(leida=False).count()
        return Response({'count': count})

    @action(detail=False, methods=['post'], url_path='marcar-todas-leidas')
    def mark_all_read(self, request):
        self.get_queryset().filter(leida=False).update(leida=True)
        return Response({'status': 'todas marcadas como leídas'})
