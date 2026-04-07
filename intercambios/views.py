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

    dias_deuda = 7 if solicitud.tipo == 'semana' else 1

    # Normalizar el par (siempre usuario_a < usuario_b por id)
    if solicitante.id < receptor.id:
        usuario_a, usuario_b = solicitante, receptor
        saldo_obj, _ = BolsaDiasSaldo.objects.get_or_create(usuario_a=usuario_a, usuario_b=usuario_b)
        # El solicitante (a) debe al receptor (b) → b gana puntos a favor
        saldo_obj.saldo_dias_a_favor_de_b += dias_deuda
    else:
        usuario_a, usuario_b = receptor, solicitante
        saldo_obj, _ = BolsaDiasSaldo.objects.get_or_create(usuario_a=usuario_a, usuario_b=usuario_b)
        # El solicitante (b) debe al receptor (a) → a gana puntos a favor
        saldo_obj.saldo_dias_a_favor_de_a += dias_deuda

    saldo_obj.save()

    movimiento = BolsaDiasMovimiento.objects.create(
        saldo=saldo_obj,
        origen_usuario=solicitante,
        destino_usuario=receptor,
        dias=dias_deuda,
        tipo='genera_deuda',
        solicitud_intercambio=solicitud,
    )

    from auditoria.models import Auditoria
    Auditoria.objects.create(
        tipo_evento='actualizar_bolsa',
        usuario=solicitante,
        entidad='bolsa',
        id_entidad=saldo_obj.id,
        metadata={'movimiento_id': movimiento.id, 'tipo': 'genera_deuda', 'dias': dias_deuda}
    )


def _actualizar_saldo_bolsa_rechazo(solicitante, receptor, modo_compensacion, solicitud):
    """
    Si el receptor rechaza la solicitud de cambio, el sistema registra una deuda en la bolsa:
    el receptor (que rechaza) pasa a deber días al solicitante.
    """
    if modo_compensacion != 'bolsa':
        return

    dias_deuda = 7 if solicitud.tipo == 'semana' else 1

    # Normalizar el par (siempre usuario_a < usuario_b por id)
    if solicitante.id < receptor.id:
        usuario_a, usuario_b = solicitante, receptor
        saldo_obj, _ = BolsaDiasSaldo.objects.get_or_create(usuario_a=usuario_a, usuario_b=usuario_b)
        # El receptor (b) debe al solicitante (a) → a gana puntos a favor
        saldo_obj.saldo_dias_a_favor_de_a += dias_deuda
    else:
        usuario_a, usuario_b = receptor, solicitante
        saldo_obj, _ = BolsaDiasSaldo.objects.get_or_create(usuario_a=usuario_a, usuario_b=usuario_b)
        # El receptor (a) debe al solicitante (b) → b gana puntos a favor
        saldo_obj.saldo_dias_a_favor_de_b += dias_deuda

    saldo_obj.save()

    movimiento = BolsaDiasMovimiento.objects.create(
        saldo=saldo_obj,
        origen_usuario=receptor,      # el que genera la deuda es el que rechaza
        destino_usuario=solicitante,  # a favor del solicitante
        dias=dias_deuda,
        tipo='genera_deuda',
        solicitud_intercambio=solicitud,
    )

    from auditoria.models import Auditoria
    Auditoria.objects.create(
        tipo_evento='actualizar_bolsa',
        usuario=receptor,
        entidad='bolsa',
        id_entidad=saldo_obj.id,
        metadata={'movimiento_id': movimiento.id, 'tipo': 'genera_deuda', 'dias': dias_deuda, 'motivo': 'rechazo'}
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

            asig_origen = data['asignacion_origen']

            # Validación de solapes de turnos (Regla 1: No se permiten solapes de tarde/turno para un mismo usuario ese día)
            # Si el receptor ya tiene un turno asignado ese día en esa misma semana, no puede recibir el de origen.
            from turnos.models import AsignacionTurno
            if AsignacionTurno.objects.filter(
                semana=asig_origen.semana,
                usuario=data['receptor'],
                dia=asig_origen.dia,
                estado='asignado'
            ).exists():
                return Response({'error': f"El receptor ya tiene un turno asignado el {asig_origen.dia} de esa semana."}, status=status.HTTP_400_BAD_REQUEST)

            solicitud = serializer.save(solicitante=request.user)

            # Auditoria
            Auditoria.objects.create(
                tipo_evento='crear_intercambio',
                usuario=request.user,
                entidad='solicitud',
                id_entidad=solicitud.id,
                metadata={'tipo': solicitud.tipo, 'receptor': solicitud.receptor.id}
            )

            # Notificacion
            from notificaciones.utils import crear_notificacion
            crear_notificacion(
                usuario=solicitud.receptor,
                tipo='intercambio_solicitado',
                titulo="Nueva Solicitud de Intercambio",
                mensaje=f"{request.user.nombre} te ha solicitado un intercambio de turno.",
                enlace_entidad=f"intercambios/{solicitud.id}"
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

        # Al aceptar, transferimos el turno del origen al receptor
        asig_origen = solicitud.asignacion_origen
        asig_origen.estado = 'intercambiado'
        asig_origen.save()
        
        AsignacionTurno.objects.create(
            semana=asig_origen.semana,
            usuario=solicitud.receptor,
            dia=asig_origen.dia,
            turno_plantilla=asig_origen.turno_plantilla,
            estado='asignado'
        )

        if solicitud.asignacion_destino:
            # Si hay un turno de vuelta, lo transferimos del receptor al solicitante
            asig_destino = solicitud.asignacion_destino
            asig_destino.estado = 'intercambiado'
            asig_destino.save()
            
            AsignacionTurno.objects.create(
                semana=asig_destino.semana,
                usuario=solicitud.solicitante,
                dia=asig_destino.dia,
                turno_plantilla=asig_destino.turno_plantilla,
                estado='asignado'
            )

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

        from notificaciones.utils import crear_notificacion
        crear_notificacion(
            usuario=solicitud.solicitante,
            tipo='intercambio_aprobado',
            titulo="Intercambio Aceptado",
            mensaje=f"{request.user.nombre} ha aceptado tu solicitud de intercambio.",
            enlace_entidad=f"intercambios/{solicitud.id}"
        )

        from usuarios.utils_google_calendar import pre_sync_google_calendar
        # Sincronizar calendarios de ambos involucrados
        pre_sync_google_calendar(solicitud.receptor, {"tipo": "intercambio_aceptado", "rol": "receptor"})
        pre_sync_google_calendar(solicitud.solicitante, {"tipo": "intercambio_aceptado", "rol": "solicitante"})

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

        # Registrar deuda en la bolsa por el rechazo
        _actualizar_saldo_bolsa_rechazo(
            solicitud.solicitante,
            solicitud.receptor,
            solicitud.modo_compensacion,
            solicitud
        )

        Auditoria.objects.create(
            tipo_evento='rechazar_intercambio',
            usuario=request.user,
            entidad='solicitud',
            id_entidad=solicitud.id
        )

        from notificaciones.utils import crear_notificacion
        crear_notificacion(
            usuario=solicitud.solicitante,
            tipo='intercambio_rechazado',
            titulo="Intercambio Rechazado",
            mensaje=f"{request.user.nombre} ha rechazado tu solicitud de intercambio.",
            enlace_entidad=f"intercambios/{solicitud.id}"
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
