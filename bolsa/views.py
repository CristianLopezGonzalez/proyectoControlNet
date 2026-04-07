from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from .models import BolsaDiasSaldo, BolsaDiasMovimiento
from .serializers import (
    BolsaDiasSaldoSerializer,
    BolsaDiasMovimientoSerializer,
    CompensarSerializer,
    SolicitudCompensacionBolsaSerializer,
)
from .models import SolicitudCompensacionBolsa
from django.utils import timezone
from usuarios.models import Usuario


class BolsaSaldosView(APIView):
    """
    Muestra los saldos de días (deudas/ahorros) con los compañeros.
    Devuelve todos los registros donde el usuario sea integrante (a ó b).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        saldos = BolsaDiasSaldo.objects.filter(
            Q(usuario_a=request.user) | Q(usuario_b=request.user)
        )
        serializer = BolsaDiasSaldoSerializer(saldos, many=True)
        return Response(serializer.data)


class BolsaSaldoUsuarioView(APIView):
    """
    Muestra el balance de días específico entre el usuario actual y otro compañero.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, usuario_id):
        try:
            otro = Usuario.objects.get(pk=usuario_id)
        except Usuario.DoesNotExist:
            return Response({'error': 'Usuario no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        saldo = BolsaDiasSaldo.objects.filter(
            Q(usuario_a=request.user, usuario_b=otro) |
            Q(usuario_a=otro, usuario_b=request.user)
        ).first()

        if not saldo:
            return Response({'mensaje': 'No existe saldo entre estos usuarios.'}, status=status.HTTP_200_OK)

        return Response(BolsaDiasSaldoSerializer(saldo).data)


class BolsaMovimientosView(APIView):
    """
    Historial completo de movimientos de la bolsa (generaciones y compensaciones de deuda).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        movimientos = BolsaDiasMovimiento.objects.filter(
            Q(origen_usuario=request.user) | Q(destino_usuario=request.user)
        ).order_by('-fecha')
        serializer = BolsaDiasMovimientoSerializer(movimientos, many=True)
        return Response(serializer.data)


class BolsaCompensarView(APIView):
    """
    Permite proponer una compensación de deuda (devolver días).
    Crea una SolicitudCompensacionBolsa en estado pendiente.
    También permite obtener las peticiones de compensación del usuario (GET).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        solicitudes = SolicitudCompensacionBolsa.objects.filter(
            Q(solicitante=request.user) | Q(receptor=request.user)
        ).order_by('-fecha_creacion')
        return Response(SolicitudCompensacionBolsaSerializer(solicitudes, many=True).data)

    def post(self, request):
        serializer = CompensarSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        usuario_destino_id = serializer.validated_data['usuario_destino_id']
        dias = serializer.validated_data['dias']

        if usuario_destino_id == request.user.id:
            return Response({'error': 'No puedes compensar días contigo mismo.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            destino = Usuario.objects.get(pk=usuario_destino_id)
        except Usuario.DoesNotExist:
            return Response({'error': 'Usuario destino no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        # Validación: solo el que debe días puede ofrecer compensación sin intercambio explícito
        # Normalizar par
        if request.user.id < destino.id:
            usuario_a, usuario_b = request.user, destino
            saldo_obj = BolsaDiasSaldo.objects.filter(usuario_a=usuario_a, usuario_b=usuario_b).first()
            dias_a_favor = saldo_obj.saldo_dias_a_favor_de_b if saldo_obj else 0
        else:
            usuario_a, usuario_b = destino, request.user
            saldo_obj = BolsaDiasSaldo.objects.filter(usuario_a=usuario_a, usuario_b=usuario_b).first()
            dias_a_favor = saldo_obj.saldo_dias_a_favor_de_a if saldo_obj else 0

        if dias_a_favor < dias:
            return Response({'error': f'Solo debes {dias_a_favor} días a este usuario.'}, status=status.HTTP_400_BAD_REQUEST)

        solicitud = SolicitudCompensacionBolsa.objects.create(
            solicitante=request.user,
            receptor=destino,
            dias=dias,
            estado='pendiente'
        )

        return Response(
            SolicitudCompensacionBolsaSerializer(solicitud).data, 
            status=status.HTTP_201_CREATED
        )


class BolsaCompensarAceptarView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            solicitud = SolicitudCompensacionBolsa.objects.get(pk=pk)
        except SolicitudCompensacionBolsa.DoesNotExist:
            return Response({'error': 'Solicitud no encontrada.'}, status=status.HTTP_404_NOT_FOUND)

        if solicitud.receptor != request.user:
            return Response({'error': 'Solo el receptor puede aceptar.'}, status=status.HTTP_403_FORBIDDEN)
        if solicitud.estado != 'pendiente':
            return Response({'error': f'La solicitud ya está {solicitud.estado}.'}, status=status.HTTP_400_BAD_REQUEST)

        # Confirmar que sigue habiendo deuda suficiente
        solicitante = solicitud.solicitante
        receptor = solicitud.receptor
        dias = solicitud.dias

        if solicitante.id < receptor.id:
            usuario_a, usuario_b = solicitante, receptor
            saldo_obj = BolsaDiasSaldo.objects.filter(usuario_a=usuario_a, usuario_b=usuario_b).first()
            if not saldo_obj or saldo_obj.saldo_dias_a_favor_de_b < dias:
                return Response({'error': 'La deuda actual es insuficiente para esta compensación.'}, status=status.HTTP_400_BAD_REQUEST)
            saldo_obj.saldo_dias_a_favor_de_b -= dias
        else:
            usuario_a, usuario_b = receptor, solicitante
            saldo_obj = BolsaDiasSaldo.objects.filter(usuario_a=usuario_a, usuario_b=usuario_b).first()
            if not saldo_obj or saldo_obj.saldo_dias_a_favor_de_a < dias:
                return Response({'error': 'La deuda actual es insuficiente para esta compensación.'}, status=status.HTTP_400_BAD_REQUEST)
            saldo_obj.saldo_dias_a_favor_de_a -= dias

        solicitud.estado = 'aprobada'
        solicitud.fecha_respuesta = timezone.now()
        solicitud.save()
        saldo_obj.save()

        movimiento = BolsaDiasMovimiento.objects.create(
            saldo=saldo_obj,
            origen_usuario=solicitante,
            destino_usuario=receptor,
            dias=dias,
            tipo='compensa_deuda',
        )

        from auditoria.models import Auditoria
        Auditoria.objects.create(
            tipo_evento='actualizar_bolsa',
            usuario=request.user,
            entidad='bolsa',
            id_entidad=saldo_obj.id,
            metadata={'movimiento_id': movimiento.id, 'tipo': 'compensa_deuda_aprobada', 'dias': dias}
        )

        from usuarios.utils_google_calendar import pre_sync_google_calendar
        pre_sync_google_calendar(solicitud.receptor, {"tipo": "compensacion_bolsa_aceptada", "rol": "receptor"})
        pre_sync_google_calendar(solicitud.solicitante, {"tipo": "compensacion_bolsa_aceptada", "rol": "solicitante"})

        return Response(SolicitudCompensacionBolsaSerializer(solicitud).data)


class BolsaCompensarRechazarView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            solicitud = SolicitudCompensacionBolsa.objects.get(pk=pk)
        except SolicitudCompensacionBolsa.DoesNotExist:
            return Response({'error': 'Solicitud no encontrada.'}, status=status.HTTP_404_NOT_FOUND)

        if solicitud.receptor != request.user:
            return Response({'error': 'Solo el receptor puede rechazar.'}, status=status.HTTP_403_FORBIDDEN)
        if solicitud.estado != 'pendiente':
            return Response({'error': f'La solicitud ya está {solicitud.estado}.'}, status=status.HTTP_400_BAD_REQUEST)

        solicitud.estado = 'rechazada'
        solicitud.fecha_respuesta = timezone.now()
        solicitud.save()

        from auditoria.models import Auditoria
        Auditoria.objects.create(
            tipo_evento='actualizar_bolsa',
            usuario=request.user,
            entidad='solicitud_compensacion',
            id_entidad=solicitud.id,
            metadata={'tipo': 'rechazada'}
        )

        return Response(SolicitudCompensacionBolsaSerializer(solicitud).data)
