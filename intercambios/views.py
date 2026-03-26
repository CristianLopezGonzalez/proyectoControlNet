from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.db import models as db_models
from .models import SolicitudIntercambio
from .serializers import SolicitudIntercambioSerializer, CrearSolicitudSerializer
from bolsa.models import BolsaDiasSaldo, BolsaDiasMovimiento
from auditoria.models import Auditoria


def _actualizar_saldo_bolsa(solicitante, receptor, modo_compensacion, solicitud):
    """
    Si el modo es bolsa, registra movimiento y actualiza el saldo entre los dos usuarios.
    El solicitante toma un turno del receptor → genera una deuda del solicitante hacia el receptor.
    """
    if modo_compensacion != 'bolsa':
        return

    # Normalizar el par (siempre usuario_a < usuario_b por id)
    if solicitante.id < receptor.id:
        usuario_a, usuario_b = solicitante, receptor
        saldo_obj, _ = BolsaDiasSaldo.objects.get_or_create(usuario_a=usuario_a, usuario_b=usuario_b)
        # El solicitante (a) debe un día al receptor (b) → b gana un punto a favor
        saldo_obj.saldo_dias_a_favor_de_b += 1
    else:
        usuario_a, usuario_b = receptor, solicitante
        saldo_obj, _ = BolsaDiasSaldo.objects.get_or_create(usuario_a=usuario_a, usuario_b=usuario_b)
        # El solicitante (b) debe un día al receptor (a) → a gana un punto a favor
        saldo_obj.saldo_dias_a_favor_de_a += 1

    saldo_obj.save()

    movimiento = BolsaDiasMovimiento.objects.create(
        saldo=saldo_obj,
        origen_usuario=solicitante,
        destino_usuario=receptor,
        dias=1,
        tipo='genera_deuda',
        solicitud_intercambio=solicitud,
    )

    from auditoria.models import Auditoria
    Auditoria.objects.create(
        tipo_evento='actualizar_bolsa',
        usuario=solicitante,
        entidad='bolsa',
        id_entidad=saldo_obj.id,
        metadata={'movimiento_id': movimiento.id, 'tipo': 'genera_deuda', 'dias': 1}
    )


class IntercambioListCreateView(APIView):
    """
    GET  /intercambios/  - Lista solicitudes (todas para admin/supervisor, propias para empleado)
    POST /intercambios/  - Crea una nueva solicitud de intercambio.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if user.rol in ('admin', 'supervisor'):
            solicitudes = SolicitudIntercambio.objects.all().order_by('-fecha_creacion')
        else:
            solicitudes = SolicitudIntercambio.objects.filter(
                db_models.Q(solicitante=user) | db_models.Q(receptor=user)
            ).order_by('-fecha_creacion')
        return Response(SolicitudIntercambioSerializer(solicitudes, many=True).data)

    def post(self, request):
        serializer = CrearSolicitudSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data

            # Validaciones de negocio
            if not data['receptor'].activo:
                return Response({'error': 'El usuario receptor no está activo.'}, status=status.HTTP_400_BAD_REQUEST)
            if data['asignacion_origen'].usuario != request.user:
                return Response({'error': 'La asignación de origen no te pertenece.'}, status=status.HTTP_403_FORBIDDEN)
            if data.get('asignacion_destino') and data['asignacion_destino'].usuario != data['receptor']:
                return Response({'error': 'La asignación de destino no pertenece al receptor.'}, status=status.HTTP_400_BAD_REQUEST)

            solicitud = serializer.save(solicitante=request.user)

            # Auditoria
            Auditoria.objects.create(
                tipo_evento='crear_intercambio',
                usuario=request.user,
                entidad='solicitud',
                id_entidad=solicitud.id,
                metadata={'tipo': solicitud.tipo, 'receptor': solicitud.receptor.id}
            )

            return Response(
                SolicitudIntercambioSerializer(solicitud).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class IntercambioMiasView(APIView):
    """
    GET /intercambios/mias
    Lista todas las solicitudes enviadas y recibidas por el usuario actual.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        enviadas = SolicitudIntercambio.objects.filter(solicitante=request.user)
        recibidas = SolicitudIntercambio.objects.filter(receptor=request.user)
        return Response({
            'enviadas': SolicitudIntercambioSerializer(enviadas, many=True).data,
            'recibidas': SolicitudIntercambioSerializer(recibidas, many=True).data,
        })


from turnos.models import AsignacionTurno


class IntercambioAceptarView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            solicitud = SolicitudIntercambio.objects.get(pk=pk)
        except SolicitudIntercambio.DoesNotExist:
            return Response({'error': 'Solicitud no encontrada.'}, status=status.HTTP_404_NOT_FOUND)

        # Solo el receptor o un supervisor/admin pueden "aceptar/aprobar"
        if solicitud.receptor != request.user and request.user.rol not in ('admin', 'supervisor'):
            return Response({'error': 'No tienes permiso para responder a esta solicitud.'}, status=status.HTTP_403_FORBIDDEN)

        if solicitud.estado != 'pendiente':
            return Response({'error': f'La solicitud ya está en estado "{solicitud.estado}".'}, status=status.HTTP_400_BAD_REQUEST)

        solicitud.estado = 'aprobada'
        solicitud.fecha_respuesta = timezone.now()
        solicitud.save()

        solicitud.asignacion_origen.estado = 'intercambiado'
        solicitud.asignacion_origen.save()
        if solicitud.asignacion_destino:
            solicitud.asignacion_destino.estado = 'intercambiado'
            solicitud.asignacion_destino.save()

        _actualizar_saldo_bolsa(
            solicitud.solicitante,
            solicitud.receptor,
            solicitud.modo_compensacion,
            solicitud,
        )

        Auditoria.objects.create(
            tipo_evento='aceptar_intercambio',
            usuario=request.user,
            entidad='solicitud',
            id_entidad=solicitud.id,
            metadata={'modo_compensacion': solicitud.modo_compensacion}
        )

        return Response(SolicitudIntercambioSerializer(solicitud).data)


class IntercambioRechazarView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            solicitud = SolicitudIntercambio.objects.get(pk=pk)
        except SolicitudIntercambio.DoesNotExist:
            return Response({'error': 'Solicitud no encontrada.'}, status=status.HTTP_404_NOT_FOUND)

        if solicitud.receptor != request.user:
            return Response({'error': 'Solo el receptor puede rechazar esta solicitud.'}, status=status.HTTP_403_FORBIDDEN)

        if solicitud.estado != 'pendiente':
            return Response({'error': f'La solicitud ya está en estado "{solicitud.estado}".'}, status=status.HTTP_400_BAD_REQUEST)

        solicitud.estado = 'rechazada'
        solicitud.fecha_respuesta = timezone.now()
        solicitud.save()

        Auditoria.objects.create(
            tipo_evento='rechazar_intercambio',
            usuario=request.user,
            entidad='solicitud',
            id_entidad=solicitud.id
        )

        return Response(SolicitudIntercambioSerializer(solicitud).data)


class IntercambioCancelarView(APIView):
    
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            solicitud = SolicitudIntercambio.objects.get(pk=pk)
        except SolicitudIntercambio.DoesNotExist:
            return Response({'error': 'Solicitud no encontrada.'}, status=status.HTTP_404_NOT_FOUND)

        if solicitud.solicitante != request.user:
            return Response({'error': 'Solo el solicitante puede cancelar esta solicitud.'}, status=status.HTTP_403_FORBIDDEN)

        if solicitud.estado != 'pendiente':
            return Response({'error': f'No se puede cancelar una solicitud en estado "{solicitud.estado}".'}, status=status.HTTP_400_BAD_REQUEST)

        solicitud.estado = 'cancelada'
        solicitud.fecha_respuesta = timezone.now()
        solicitud.save()

        Auditoria.objects.create(
            tipo_evento='cancelar_intercambio',
            usuario=request.user,
            entidad='solicitud',
            id_entidad=solicitud.id
        )

        return Response(SolicitudIntercambioSerializer(solicitud).data)
