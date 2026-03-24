from django.contrib import admin
from .models import CalendarioSemanal, AsignacionTarde

@admin.register(CalendarioSemanal)
class CalendarioSemanalAdmin(admin.ModelAdmin):
    list_display = ('anio', 'numero_semana', 'fecha_inicio_semana', 'fecha_fin_semana', 'estado')
    list_filter = ('estado', 'anio')

@admin.register(AsignacionTarde)
class AsignacionTardeAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'semana', 'dia', 'hora_inicio', 'hora_fin', 'estado')
    list_filter = ('dia', 'estado')