from django.contrib import admin
from .models import Auditoria

@admin.register(Auditoria)
class AuditoriaAdmin(admin.ModelAdmin):
    list_display = ('tipo_evento', 'usuario', 'entidad', 'id_entidad', 'fecha')
    list_filter = ('tipo_evento', 'entidad')