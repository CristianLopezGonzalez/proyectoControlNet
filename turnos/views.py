from django.db import models as db_models
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from .models import CalendarioSemanal, AsignacionTarde
from auditoria.models import Auditoria
from .serializers import (
    CalendarioSemanalSerializer,
    CalendarioSemanalListSerializer,
    AsignacionTardeSerializer,
)


class SemanaListCreateView(APIView):
    """
    GET  /semanas        → listar todas las semanas
    POST /semanas        → crear semana (solo admin/supervisor)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        semanas = CalendarioSemanal.objects.all().order_by('-anio', '-numero_semana')
        serializer = CalendarioSemanalListSerializer(semanas, many=True)
        return Response(serializer.data)

    def post(self, request):
        if request.user.rol not in ('admin', 'supervisor'):
            return Response({'error': 'No tienes permiso para crear semanas.'}, status=status.HTTP_403_FORBIDDEN)
        serializer = CalendarioSemanalSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SemanaDetailView(APIView):
    """
    GET /semanas/{id}  → detalle de semana con asignaciones
    """
    permission_classes = [IsAuthenticated]

    def _get_semana(self, pk):
        try:
            return CalendarioSemanal.objects.get(pk=pk)
        except CalendarioSemanal.DoesNotExist:
            return None

    def get(self, request, pk):
        semana = self._get_semana(pk)
        if not semana:
            return Response({'error': 'Semana no encontrada.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = CalendarioSemanalSerializer(semana)
        return Response(serializer.data)


class SemanaPublicarView(APIView):
    """
    POST /semanas/{id}/publicar  → cambiar estado a publicado
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if request.user.rol not in ('admin', 'supervisor'):
            return Response({'error': 'No tienes permiso para publicar semanas.'}, status=status.HTTP_403_FORBIDDEN)
        try:
            semana = CalendarioSemanal.objects.get(pk=pk)
        except CalendarioSemanal.DoesNotExist:
            return Response({'error': 'Semana no encontrada.'}, status=status.HTTP_404_NOT_FOUND)

        if semana.estado == 'publicado':
            return Response({'error': 'La semana ya está publicada.'}, status=status.HTTP_400_BAD_REQUEST)

        semana.estado = 'publicado'
        semana.save()

        Auditoria.objects.create(
            tipo_evento='publicar_semana',
            usuario=request.user,
            entidad='semana',
            id_entidad=semana.id
        )

        return Response(CalendarioSemanalSerializer(semana).data)


class AsignacionListCreateView(APIView):
    """
    POST /asignaciones  → crear asignación (admin/supervisor)
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.rol not in ('admin', 'supervisor'):
            return Response({'error': 'No tienes permiso para crear asignaciones.'}, status=status.HTTP_403_FORBIDDEN)
        serializer = AsignacionTardeSerializer(data=request.data)
        if serializer.is_valid():
            # Validación de solape: mismo usuario, mismo día, misma fecha (vía semana)
            # Aunque unique_together ayuda en la misma semana, esto es más explícito
            data = serializer.validated_data
            if AsignacionTarde.objects.filter(
                usuario=data['usuario'],
                dia=data['dia'],
                semana__fecha_inicio_semana=data['semana'].fecha_inicio_semana
            ).exists():
                return Response({'error': 'Este usuario ya tiene una asignación para este día y semana.'}, status=status.HTTP_400_BAD_REQUEST)

            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AsignacionDetailView(APIView):
    """
    PATCH /asignaciones/{id}  → editar asignación (admin/supervisor)
    """
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        if request.user.rol not in ('admin', 'supervisor'):
            return Response({'error': 'No tienes permiso para editar asignaciones.'}, status=status.HTTP_403_FORBIDDEN)
        try:
            asignacion = AsignacionTarde.objects.get(pk=pk)
        except AsignacionTarde.DoesNotExist:
            return Response({'error': 'Asignación no encontrada.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = AsignacionTardeSerializer(asignacion, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
