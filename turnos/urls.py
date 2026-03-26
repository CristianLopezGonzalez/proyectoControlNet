from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CalendarioSemanalViewSet, PlantillaTurnoViewSet,
    PatronRotacionViewSet, VacacionViewSet,
    IncidenciaViewSet, ReportesViewSet,
    AsignacionTurnoViewSet, ConfiguracionReglaViewSet,
)

router = DefaultRouter()
router.register(r'plantillas', PlantillaTurnoViewSet, basename='plantilla')
router.register(r'rotaciones', PatronRotacionViewSet, basename='rotacion')
router.register(r'vacaciones', VacacionViewSet, basename='vacacion')
router.register(r'incidencias', IncidenciaViewSet, basename='incidencia')
router.register(r'semanas', CalendarioSemanalViewSet, basename='semana')
router.register(r'reports', ReportesViewSet, basename='report')
router.register(r'asignaciones', AsignacionTurnoViewSet, basename='asignaciones')
router.register(r'reglas', ConfiguracionReglaViewSet, basename='reglas')

urlpatterns = [
    path('', include(router.urls)),
]
