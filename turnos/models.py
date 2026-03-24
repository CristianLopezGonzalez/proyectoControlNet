from django.db import models
from usuarios.models import Usuario


class CalendarioSemanal(models.Model):
    ESTADO_CHOICES = [
        ('borrador', 'Borrador'),
        ('publicado', 'Publicado'),
    ]

    anio = models.IntegerField()
    numero_semana = models.IntegerField()
    fecha_inicio_semana = models.DateField()
    fecha_fin_semana = models.DateField()
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='borrador')

    class Meta:
        unique_together = ('anio', 'numero_semana')

    def __str__(self):
        return f"Semana {self.numero_semana} - {self.anio} ({self.estado})"


class AsignacionTarde(models.Model):
    DIA_CHOICES = [
        ('lunes', 'Lunes'),
        ('martes', 'Martes'),
        ('miercoles', 'Miércoles'),
        ('jueves', 'Jueves'),
        ('viernes', 'Viernes'),
    ]

    ESTADO_CHOICES = [
        ('asignado', 'Asignado'),
        ('intercambiado', 'Intercambiado'),
    ]

    semana = models.ForeignKey(CalendarioSemanal, on_delete=models.CASCADE, related_name='asignaciones')
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='asignaciones')
    dia = models.CharField(max_length=20, choices=DIA_CHOICES)
    hora_inicio = models.TimeField(default='14:00')
    hora_fin = models.TimeField(default='22:00')
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='asignado')

    class Meta:
        unique_together = ('semana', 'usuario', 'dia')

    def __str__(self):
        return f"{self.usuario.nombre} - {self.dia} (Semana {self.semana.numero_semana})"