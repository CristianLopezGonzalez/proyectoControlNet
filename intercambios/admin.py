from django.contrib import admin
from .models import SolicitudIntercambio

@admin.register(SolicitudIntercambio)
class SolicitudIntercambioAdmin(admin.ModelAdmin):
    list_display = ('solicitante', 'receptor', 'tipo', 'modo_compensacion', 'estado', 'fecha_creacion')
    list_filter = ('tipo', 'estado', 'modo_compensacion')