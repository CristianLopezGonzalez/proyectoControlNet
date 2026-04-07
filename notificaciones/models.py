from django.db import models
from usuarios.models import Usuario

class Notificacion(models.Model):
    TIPO_CHOICES = [
        ('intercambio_solicitado', 'Intercambio Solicitado'),
        ('intercambio_aprobado', 'Intercambio Aprobado'),
        ('intercambio_rechazado', 'Intercambio Rechazado'),
        ('vacacion_aprobada', 'Vacacion Aprobada'),
        ('vacacion_rechazada', 'Vacacion Rechazada'),
        ('semana_publicada', 'Semana Publicada'),
        ('incidencia', 'Incidencia'),
    ]

    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='notificaciones')
    tipo = models.CharField(max_length=50, choices=TIPO_CHOICES)
    titulo = models.CharField(max_length=255)
    mensaje = models.TextField()
    leida = models.BooleanField(default=False)
    fecha = models.DateTimeField(auto_now_add=True)
    enlace_entidad = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.usuario.nombre} - {self.titulo}"
