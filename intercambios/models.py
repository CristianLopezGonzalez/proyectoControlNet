from django.db import models
from usuarios.models import Usuario
from turnos.models import AsignacionTurno


class SolicitudIntercambio(models.Model):
    TIPO_CHOICES = [
        ('dia', 'Día'),
        ('semana', 'Semana'),
    ]

    MODO_COMPENSACION_CHOICES = [
        ('inmediata', 'Inmediata'),
        ('bolsa', 'Bolsa'),
    ]

    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('aceptada', 'Aprobada'),
        ('rechazada', 'Rechazada'),
        ('cancelada', 'Cancelada'),
    ]

    solicitante = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='solicitudes_enviadas')
    receptor = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='solicitudes_recibidas')
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    asignacion_origen = models.ForeignKey(AsignacionTurno, on_delete=models.CASCADE, related_name='intercambios_origen')
    asignacion_destino = models.ForeignKey(AsignacionTurno, on_delete=models.CASCADE, related_name='intercambios_destino', null=True, blank=True)
    motivo = models.TextField(blank=True)
    modo_compensacion = models.CharField(max_length=20, choices=MODO_COMPENSACION_CHOICES, default='inmediata')
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_respuesta = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.solicitante.nombre} → {self.receptor.nombre} ({self.tipo} - {self.estado})"