from django.contrib import admin
from .models import BolsaDiasSaldo, BolsaDiasMovimiento

@admin.register(BolsaDiasSaldo)
class BolsaDiasSaldoAdmin(admin.ModelAdmin):
    list_display = ('usuario_a', 'usuario_b', 'saldo_dias_a_favor_de_a', 'saldo_dias_a_favor_de_b', 'ultima_actualizacion')

@admin.register(BolsaDiasMovimiento)
class BolsaDiasMovimientoAdmin(admin.ModelAdmin):
    list_display = ('tipo', 'origen_usuario', 'destino_usuario', 'dias', 'fecha')
    list_filter = ('tipo',)