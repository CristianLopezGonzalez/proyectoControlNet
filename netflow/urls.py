from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/', include('usuarios.urls')),
    path('turnos/', include('turnos.urls')),
    path('intercambios/', include('intercambios.urls')),
    path('bolsa/', include('bolsa.urls')),
    path('auditoria/', include('auditoria.urls')),
    path('notificaciones/', include('notificaciones.urls')),
]