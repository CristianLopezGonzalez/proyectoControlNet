from django.urls import path
from .views import (
    BolsaSaldosView,
    BolsaSaldoUsuarioView,
    BolsaMovimientosView,
    BolsaCompensarView,
)

urlpatterns = [
    path('saldos/', BolsaSaldosView.as_view(), name='bolsa-saldos'),
    path('saldos/<int:usuario_id>/', BolsaSaldoUsuarioView.as_view(), name='bolsa-saldo-usuario'),
    path('movimientos/', BolsaMovimientosView.as_view(), name='bolsa-movimientos'),
    path('compensar/', BolsaCompensarView.as_view(), name='bolsa-compensar'),
]
