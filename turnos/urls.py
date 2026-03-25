from django.urls import path
from .views import (
    SemanaListCreateView,
    SemanaDetailView,
    SemanaPublicarView,
    AsignacionListCreateView,
    AsignacionDetailView,
)

urlpatterns = [
    path('semanas', SemanaListCreateView.as_view(), name='semana-list-create'),
    path('semanas/<int:pk>', SemanaDetailView.as_view(), name='semana-detail'),
    path('semanas/<int:pk>/publicar', SemanaPublicarView.as_view(), name='semana-publicar'),
    path('asignaciones', AsignacionListCreateView.as_view(), name='asignacion-create'),
    path('asignaciones/<int:pk>', AsignacionDetailView.as_view(), name='asignacion-detail'),
]
