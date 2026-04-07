from django.urls import path
from .views import (
    BolsaSaldosView,
    BolsaSaldoUsuarioView,
    BolsaMovimientosView,
    BolsaCompensarView,
    BolsaCompensarAceptarView,
    BolsaCompensarRechazarView,
)

urlpatterns = [
    path('saldos/', BolsaSaldosView.as_view(), name='bolsa-saldos'),
    path('saldos/<int:usuario_id>/', BolsaSaldoUsuarioView.as_view(), name='bolsa-saldo-usuario'),
    path('movimientos/', BolsaMovimientosView.as_view(), name='bolsa-movimientos'),
    path('compensar/', BolsaCompensarView.as_view(), name='bolsa-compensar'),
    path('compensar/<int:pk>/aceptar/', BolsaCompensarAceptarView.as_view(), name='bolsa-compensar-aceptar'),
    path('compensar/<int:pk>/rechazar/', BolsaCompensarRechazarView.as_view(), name='bolsa-compensar-rechazar'),
]
