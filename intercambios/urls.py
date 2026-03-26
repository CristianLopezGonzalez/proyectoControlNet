from django.urls import path
from .views import (
    IntercambioListCreateView,
    IntercambioMiasView,
    IntercambioAceptarView,
    IntercambioRechazarView,
    IntercambioCancelarView,
)

urlpatterns = [
    path('', IntercambioListCreateView.as_view(), name='intercambio-create'),
    path('mias/', IntercambioMiasView.as_view(), name='intercambio-mias'),
    path('<int:pk>/aceptar/', IntercambioAceptarView.as_view(), name='intercambio-aceptar'),
    path('<int:pk>/rechazar/', IntercambioRechazarView.as_view(), name='intercambio-rechazar'),
    path('<int:pk>/cancelar/', IntercambioCancelarView.as_view(), name='intercambio-cancelar'),
]
