from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import datetime, timedelta

from .models import TurnoSemanal, SolicitudTurnoSemanal
from .serializers import (
    TurnoSemanalSerializer,
    SolicitudTurnoSemanalSerializer,
    CrearSolicitudTurnoSemanalSerializer,
)
from turnos.models import CalendarioSemanal
from usuarios.models import Usuario
from usuarios.permissions import IsAdminOrSupervisor
from notificaciones.utils import crear_notificacion
from auditoria.models import Auditoria
from bolsa.models import BolsaDiasSaldo, BolsaDiasMovimiento

def _actualizar_bolsa_semanal(solicitante, receptor, modo_compensacion, solicitud):
    if modo_compensacion != 'bolsa':
        return
    # Cada semana se contabiliza como 7 días de deuda
    dias_deuda = 7
    if solicitante.id < receptor.id:
        usuario_a, usuario_b = solicitante, receptor
        saldo_obj, _ = BolsaDiasSaldo.objects.get_or_create(usuario_a=usuario_a, usuario_b=usuario_b)
        saldo_obj.saldo_dias_a_favor_de_b += dias_deuda
    else:
        usuario_a, usuario_b = receptor, solicitante
        saldo_obj, _ = BolsaDiasSaldo.objects.get_or_create(usuario_a=usuario_a, usuario_b=usuario_b)
        saldo_obj.saldo_dias_a_favor_de_a += dias_deuda

    saldo_obj.save()
    movimiento = BolsaDiasMovimiento.objects.create(
        saldo=saldo_obj,
        origen_usuario=solicitante,
        destino_usuario=receptor,
        dias=dias_deuda,
        tipo='genera_deuda',
        solicitud_semanal=solicitud,
    )
    Auditoria.objects.create(
        tipo_evento='actualizar_bolsa',
        usuario=solicitante,
        entidad='bolsa',
        id_entidad=saldo_obj.id,
        metadata={'movimiento_id': movimiento.id, 'tipo': 'genera_deuda', 'dias': dias_deuda}
    )

def _actualizar_bolsa_rechazo_semanal(solicitante, receptor, modo_compensacion, solicitud):
    if modo_compensacion != 'bolsa':
        return
    dias_deuda = 7
    if solicitante.id < receptor.id:
        usuario_a, usuario_b = solicitante, receptor
        saldo_obj, _ = BolsaDiasSaldo.objects.get_or_create(usuario_a=usuario_a, usuario_b=usuario_b)
        saldo_obj.saldo_dias_a_favor_de_a += dias_deuda
    else:
        usuario_a, usuario_b = receptor, solicitante
        saldo_obj, _ = BolsaDiasSaldo.objects.get_or_create(usuario_a=usuario_a, usuario_b=usuario_b)
        saldo_obj.saldo_dias_a_favor_de_b += dias_deuda

    saldo_obj.save()
    movimiento = BolsaDiasMovimiento.objects.create(
        saldo=saldo_obj,
        origen_usuario=receptor,
        destino_usuario=solicitante,
        dias=dias_deuda,
        tipo='genera_deuda',
        solicitud_semanal=solicitud,
    )
    Auditoria.objects.create(
        tipo_evento='actualizar_bolsa',
        usuario=receptor,
        entidad='bolsa',
        id_entidad=saldo_obj.id,
        metadata={'movimiento_id': movimiento.id, 'tipo': 'genera_deuda', 'dias': dias_deuda, 'motivo': 'rechazo'}
    )


class TurnoSemanalViewSet(viewsets.ModelViewSet):
    """
    CRUD de asignaciones semanales simples (1 empleado por semana).
    Incluye acción para generar el año completo en modo round-robin.
    """
    serializer_class = TurnoSemanalSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'generar']:
            return [IsAdminOrSupervisor()]
        return [IsAuthenticated()]

    def get_queryset(self):
        qs = TurnoSemanal.objects.select_related('semana', 'usuario').all()
        anio = self.request.query_params.get('anio')
        usuario_id = self.request.query_params.get('usuario_id')
        if anio:
            qs = qs.filter(semana__anio=anio)
        if usuario_id:
            qs = qs.filter(usuario_id=usuario_id)
        return qs

    @action(detail=False, methods=['post'], url_path='generar')
    def generar(self, request):
        """
        Genera asignaciones round-robin para todo un año dado.
        Body: { "anio": 2026, "usuario_ids": [1, 2, 3, 4, 5] }
        Los usuarios rotan semana a semana en el orden dado.
        """
        anio = request.data.get('anio')
        usuario_ids = request.data.get('usuario_ids', [])

        if not anio or not usuario_ids:
            return Response(
                {'error': 'Se requieren "anio" y "usuario_ids".'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            anio = int(anio)
            usuarios = list(Usuario.objects.filter(id__in=usuario_ids))
            if not usuarios:
                return Response({'error': 'No se encontraron usuarios con los IDs dados.'}, status=status.HTTP_404_NOT_FOUND)
        except (ValueError, TypeError):
            return Response({'error': '"anio" debe ser un número entero.'}, status=status.HTTP_400_BAD_REQUEST)

        # Calcular todas las semanas del año
        jan4 = datetime(anio, 1, 4)
        start_of_week1 = jan4 - timedelta(days=jan4.weekday())
        semanas_creadas = []
        nuevos_turnos = []
        semana_num = 1

        while True:
            fecha_inicio = (start_of_week1 + timedelta(weeks=semana_num - 1)).date()
            if fecha_inicio.year > anio and semana_num > 52:
                break
            fecha_fin = fecha_inicio + timedelta(days=6)

            semana, _ = CalendarioSemanal.objects.get_or_create(
                anio=anio, numero_semana=semana_num,
                defaults={'fecha_inicio_semana': fecha_inicio, 'fecha_fin_semana': fecha_fin}
            )

            # Round-robin: el índice del usuario depende del numero de semana
            usuario = usuarios[(semana_num - 1) % len(usuarios)]

            # Evitar duplicados: solo crear si no existe ya
            if not TurnoSemanal.objects.filter(semana=semana).exists():
                nuevos_turnos.append(TurnoSemanal(semana=semana, usuario=usuario))

            semana_num += 1
            if semana_num > 53:
                break

        TurnoSemanal.objects.bulk_create(nuevos_turnos)

        return Response({
            'status': f'{len(nuevos_turnos)} turnos semanales generados para {anio}.',
            'anio': anio,
            'total_semanas': len(nuevos_turnos),
        }, status=status.HTTP_201_CREATED)


class SolicitudTurnoSemanalViewSet(viewsets.ModelViewSet):
    """
    Gestión de solicitudes de intercambio de semana completa.
    - Empleado crea solicitud → notifica al receptor
    - Receptor aprueba/rechaza → notifica al solicitante
    - Supervisor puede aprobar también
    """
    def get_permissions(self):
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == 'create':
            return CrearSolicitudTurnoSemanalSerializer
        return SolicitudTurnoSemanalSerializer

    def get_queryset(self):
        user = self.request.user
        if user.rol in ('admin', 'supervisor'):
            return SolicitudTurnoSemanal.objects.select_related(
                'solicitante', 'receptor', 'turno_origen__semana', 'turno_destino__semana'
            ).all().order_by('-fecha_creacion')
        # Empleados solo ven las suyas
        from django.db.models import Q
        return SolicitudTurnoSemanal.objects.select_related(
            'solicitante', 'receptor', 'turno_origen__semana', 'turno_destino__semana'
        ).filter(
            Q(solicitante=user) | Q(receptor=user)
        ).order_by('-fecha_creacion')

    def perform_create(self, serializer):
        solicitud = serializer.save(solicitante=self.request.user)

        Auditoria.objects.create(
            tipo_evento='crear_intercambio',
            usuario=self.request.user,
            entidad='solicitud_semanal',
            id_entidad=solicitud.id,
            metadata={'semana': solicitud.turno_origen.semana.numero_semana, 'receptor': solicitud.receptor.id}
        )
        crear_notificacion(
            usuario=solicitud.receptor,
            tipo='intercambio_solicitado',
            titulo='Nueva solicitud de intercambio de semana',
            mensaje=f'{self.request.user.nombre} quiere intercambiar contigo la semana {solicitud.turno_origen.semana.numero_semana}/{solicitud.turno_origen.semana.anio}.',
            enlace_entidad=f'turnos-simples/solicitudes/{solicitud.id}'
        )

    @action(detail=True, methods=['post'], url_path='aprobar')
    def aprobar(self, request, pk=None):
        solicitud = self.get_object()

        # Solo el receptor o admin/supervisor pueden aprobar
        if solicitud.receptor != request.user and request.user.rol not in ('admin', 'supervisor'):
            return Response({'error': 'No tienes permiso para aprobar esta solicitud.'}, status=status.HTTP_403_FORBIDDEN)

        if solicitud.estado != 'pendiente':
            return Response({'error': f'La solicitud ya está en estado "{solicitud.estado}".'}, status=status.HTTP_400_BAD_REQUEST)

        solicitud.estado = 'aprobada'
        solicitud.fecha_respuesta = timezone.now()
        solicitud.save()

        # Intercambiar los usuarios de los turnos
        turno_origen = solicitud.turno_origen
        usuario_original = turno_origen.usuario
        turno_origen.usuario = solicitud.receptor
        turno_origen.estado = 'intercambiado'
        turno_origen.save()

        # Si es intercambio mutuo (hay turno destino), también intercambiar el otro
        if solicitud.turno_destino:
            turno_destino = solicitud.turno_destino
            turno_destino.usuario = usuario_original
            turno_destino.estado = 'intercambiado'
            turno_destino.save()

        # Generar deuda en la Bolsa de Días
        _actualizar_bolsa_semanal(
            solicitante=solicitud.solicitante,
            receptor=request.user,
            modo_compensacion=solicitud.modo_compensacion,
            solicitud=solicitud
        )

        Auditoria.objects.create(
            tipo_evento='aceptar_intercambio',
            usuario=request.user,
            entidad='solicitud_semanal',
            id_entidad=solicitud.id,
            metadata={'semana': turno_origen.semana.numero_semana}
        )
        crear_notificacion(
            usuario=solicitud.solicitante,
            tipo='intercambio_aprobado',
            titulo='Intercambio de semana aprobado',
            mensaje=f'{request.user.nombre} ha aceptado cubrir tu semana {turno_origen.semana.numero_semana}/{turno_origen.semana.anio}.',
            enlace_entidad=f'turnos-simples/solicitudes/{solicitud.id}'
        )

        return Response(SolicitudTurnoSemanalSerializer(solicitud).data)

    @action(detail=True, methods=['post'], url_path='rechazar')
    def rechazar(self, request, pk=None):
        solicitud = self.get_object()

        if solicitud.receptor != request.user and request.user.rol not in ('admin', 'supervisor'):
            return Response({'error': 'No tienes permiso para rechazar esta solicitud.'}, status=status.HTTP_403_FORBIDDEN)

        if solicitud.estado != 'pendiente':
            return Response({'error': f'La solicitud ya está en estado "{solicitud.estado}".'}, status=status.HTTP_400_BAD_REQUEST)

        solicitud.estado = 'rechazada'
        solicitud.fecha_respuesta = timezone.now()
        solicitud.save()

        # Registrar penalización en la bolsa por rechazo
        _actualizar_bolsa_rechazo_semanal(
            solicitante=solicitud.solicitante,
            receptor=request.user,
            modo_compensacion=solicitud.modo_compensacion,
            solicitud=solicitud
        )

        Auditoria.objects.create(
            tipo_evento='rechazar_intercambio',
            usuario=request.user,
            entidad='solicitud_semanal',
            id_entidad=solicitud.id,
        )
        crear_notificacion(
            usuario=solicitud.solicitante,
            tipo='intercambio_rechazado',
            titulo='Intercambio de semana rechazado',
            mensaje=f'{request.user.nombre} no puede cubrir tu semana {solicitud.turno_origen.semana.numero_semana}/{solicitud.turno_origen.semana.anio}.',
            enlace_entidad=f'turnos-simples/solicitudes/{solicitud.id}'
        )

        return Response(SolicitudTurnoSemanalSerializer(solicitud).data)

    @action(detail=True, methods=['post'], url_path='cancelar')
    def cancelar(self, request, pk=None):
        solicitud = self.get_object()

        if solicitud.solicitante != request.user:
            return Response({'error': 'Solo el solicitante puede cancelar.'}, status=status.HTTP_403_FORBIDDEN)

        if solicitud.estado != 'pendiente':
            return Response({'error': f'No se puede cancelar una solicitud en estado "{solicitud.estado}".'}, status=status.HTTP_400_BAD_REQUEST)

        solicitud.estado = 'cancelada'
        solicitud.fecha_respuesta = timezone.now()
        solicitud.save()

        return Response(SolicitudTurnoSemanalSerializer(solicitud).data)
