from django.db import models
from usuarios.models import Usuario
from intercambios.models import SolicitudIntercambio


class BolsaDiasSaldo(models.Model):
    usuario_a = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='saldos_como_a')
    usuario_b = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='saldos_como_b')
    saldo_dias_a_favor_de_a = models.IntegerField(default=0)
    saldo_dias_a_favor_de_b = models.IntegerField(default=0)
    ultima_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('usuario_a', 'usuario_b')

    def __str__(self):
        return f"Saldo: {self.usuario_a.nombre} ↔ {self.usuario_b.nombre}"


class BolsaDiasMovimiento(models.Model):
    TIPO_CHOICES = [
        ('genera_deuda', 'Genera deuda'),
        ('compensa_deuda', 'Compensa deuda'),
    ]

    saldo = models.ForeignKey(BolsaDiasSaldo, on_delete=models.CASCADE, related_name='movimientos')
    origen_usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='movimientos_origen')
    destino_usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='movimientos_destino')
    dias = models.IntegerField()
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    solicitud_intercambio = models.ForeignKey(SolicitudIntercambio, on_delete=models.SET_NULL, null=True, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.tipo} - {self.origen_usuario.nombre} → {self.destino_usuario.nombre} ({self.dias} días)"