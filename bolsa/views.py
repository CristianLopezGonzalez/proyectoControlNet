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
)
from usuarios.models import Usuario


class BolsaSaldosView(APIView):
    """
    GET /bolsa/saldos  → todos los saldos del usuario autenticado
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
    GET /bolsa/saldos/{usuarioId}  → saldo entre el usuario autenticado y otro usuario
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
    GET /bolsa/movimientos  → historial de movimientos del usuario autenticado
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
    POST /bolsa/compensar  → compensar días manualmente hacia otro usuario
    Body: { "usuario_destino_id": <int>, "dias": <int> }
    """
    permission_classes = [IsAuthenticated]

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

        # Normalizar par
        if request.user.id < destino.id:
            usuario_a, usuario_b = request.user, destino
            saldo_obj, _ = BolsaDiasSaldo.objects.get_or_create(usuario_a=usuario_a, usuario_b=usuario_b)
            if saldo_obj.saldo_dias_a_favor_de_b < dias:
                return Response({'error': f'Solo debes {saldo_obj.saldo_dias_a_favor_de_b} días a este usuario.'}, status=status.HTTP_400_BAD_REQUEST)
            # El solicitante (a) compensa al destino (b) → reduce deuda de a hacia b
            saldo_obj.saldo_dias_a_favor_de_b -= dias
        else:
            usuario_a, usuario_b = destino, request.user
            saldo_obj, _ = BolsaDiasSaldo.objects.get_or_create(usuario_a=usuario_a, usuario_b=usuario_b)
            if saldo_obj.saldo_dias_a_favor_de_a < dias:
                return Response({'error': f'Solo debes {saldo_obj.saldo_dias_a_favor_de_a} días a este usuario.'}, status=status.HTTP_400_BAD_REQUEST)
            # El solicitante (b) compensa al destino (a) → reduce deuda de b hacia a
            saldo_obj.saldo_dias_a_favor_de_a -= dias

        saldo_obj.save()

        movimiento = BolsaDiasMovimiento.objects.create(
            saldo=saldo_obj,
            origen_usuario=request.user,
            destino_usuario=destino,
            dias=dias,
            tipo='compensa_deuda',
        )

        from auditoria.models import Auditoria
        Auditoria.objects.create(
            tipo_evento='actualizar_bolsa',
            usuario=request.user,
            entidad='bolsa',
            id_entidad=saldo_obj.id,
            metadata={'movimiento_id': movimiento.id, 'tipo': 'compensa_deuda', 'dias': dias}
        )

        return Response({
            'saldo': BolsaDiasSaldoSerializer(saldo_obj).data,
            'movimiento': BolsaDiasMovimientoSerializer(movimiento).data,
        }, status=status.HTTP_201_CREATED)
