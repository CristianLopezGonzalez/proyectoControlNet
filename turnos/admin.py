from django.contrib import admin
from .models import CalendarioSemanal, PlantillaTurno, PatronRotacion, Vacacion, Incidencia, AsignacionTurno

@admin.register(CalendarioSemanal)
class CalendarioSemanalAdmin(admin.ModelAdmin):
    list_display = ('anio', 'numero_semana', 'fecha_inicio_semana', 'fecha_fin_semana', 'estado')
    list_filter = ('estado', 'anio')

@admin.register(PlantillaTurno)
class PlantillaTurnoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'hora_inicio', 'hora_fin')

@admin.register(PatronRotacion)
class PatronRotacionAdmin(admin.ModelAdmin):
    list_display = ('equipo', 'descripcion', 'fecha_inicio', 'fecha_fin')

@admin.register(Vacacion)
class VacacionAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'fecha_inicio', 'fecha_fin', 'tipo', 'estado')
    list_filter = ('tipo', 'estado')

@admin.register(Incidencia)
class IncidenciaAdmin(admin.ModelAdmin):
    list_display = ('tipo', 'fecha', 'usuario', 'resuelta')
    list_filter = ('tipo', 'resuelta')

@admin.register(AsignacionTurno)
class AsignacionTurnoAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'semana', 'dia', 'turno_plantilla', 'estado')
    list_filter = ('dia', 'estado')