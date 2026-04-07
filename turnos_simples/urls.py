from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TurnoSemanalViewSet, SolicitudTurnoSemanalViewSet

router = DefaultRouter()
router.register(r'calendario', TurnoSemanalViewSet, basename='turno-semanal')
router.register(r'solicitudes', SolicitudTurnoSemanalViewSet, basename='solicitud-semanal')

urlpatterns = [
    path('', include(router.urls)),
]
