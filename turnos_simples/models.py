from django.db import models
from usuarios.models import Usuario
from turnos.models import CalendarioSemanal


class TurnoSemanal(models.Model):
    """
    Asigna UN empleado a UNA semana completa (sistema round-robin simple).
    """
    ESTADO_CHOICES = [
        ('asignado', 'Asignado'),
        ('intercambiado', 'Intercambiado'),
    ]

    semana = models.ForeignKey(
        CalendarioSemanal,
        on_delete=models.CASCADE,
        related_name='turnos_simples'
    )
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name='turnos_simples'
    )
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='asignado')
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('semana', 'usuario')
        ordering = ['semana__anio', 'semana__numero_semana']

    def __str__(self):
        return f"Semana {self.semana.numero_semana}/{self.semana.anio} → {self.usuario.nombre}"


class SolicitudTurnoSemanal(models.Model):
    """
    Solicitud de intercambio de una semana completa entre dos empleados.
    El solicitante quiere que el receptor le cubra su semana (o intercambiarlas).
    """
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('aprobada', 'Aprobada'),
        ('rechazada', 'Rechazada'),
        ('cancelada', 'Cancelada'),
    ]

    solicitante = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name='solicitudes_turno_semanal_enviadas'
    )
    receptor = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name='solicitudes_turno_semanal_recibidas'
    )
    # El turno que el solicitante NO puede cubrir y quiere intercambiar
    turno_origen = models.ForeignKey(
        TurnoSemanal,
        on_delete=models.CASCADE,
        related_name='solicitudes_como_origen'
    )
    # El turno del receptor (si el intercambio es mutuo). Null si es cesión pura.
    turno_destino = models.ForeignKey(
        TurnoSemanal,
        on_delete=models.CASCADE,
        related_name='solicitudes_como_destino',
        null=True, blank=True
    )
    motivo = models.TextField(blank=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_respuesta = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.solicitante.nombre} → {self.receptor.nombre} | Semana {self.turno_origen.semana.numero_semana} ({self.estado})"
