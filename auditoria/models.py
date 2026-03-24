from django.db import models
from usuarios.models import Usuario


class Auditoria(models.Model):
    TIPO_EVENTO_CHOICES = [
        ('crear_intercambio', 'Crear intercambio'),
        ('aceptar_intercambio', 'Aceptar intercambio'),
        ('rechazar_intercambio', 'Rechazar intercambio'),
        ('cancelar_intercambio', 'Cancelar intercambio'),
        ('actualizar_bolsa', 'Actualizar bolsa'),
        ('sync_calendar', 'Sincronizar calendario'),
    ]

    ENTIDAD_CHOICES = [
        ('asignacion', 'Asignación'),
        ('solicitud', 'Solicitud'),
        ('bolsa', 'Bolsa'),
    ]

    tipo_evento = models.CharField(max_length=50, choices=TIPO_EVENTO_CHOICES)
    usuario = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, related_name='auditorias')
    entidad = models.CharField(max_length=50, choices=ENTIDAD_CHOICES)
    id_entidad = models.IntegerField()
    metadata = models.JSONField(default=dict, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.tipo_evento} - {self.entidad} ({self.fecha})"