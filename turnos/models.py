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


class PlantillaTurno(models.Model):
    nombre = models.CharField(max_length=50)  # Ej. "Mañana", "Tarde", "Noche"
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    descripcion = models.TextField(blank=True)

    def __str__(self):
        return f"{self.nombre} ({self.hora_inicio} - {self.hora_fin})"


class PatronRotacion(models.Model):
    equipo = models.ForeignKey('usuarios.Equipo', on_delete=models.CASCADE, related_name='patrones_rotacion')
    descripcion = models.CharField(max_length=255)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField(null=True, blank=True)
    # Secuencia de IDs de PlantillaTurno o 'LIBRE'. Ej: [1, 1, 2, 2, null, null]
    secuencia = models.JSONField(help_text="Secuencia de IDs de PlantillaTurno o null para días libres")

    def __str__(self):
        return f"Patrón {self.equipo.nombre}: {self.descripcion}"


class Vacacion(models.Model):
    TIPO_CHOICES = [
        ('vacacion', 'Vacación'),
        ('enfermedad', 'Enfermedad'),
        ('permiso', 'Permiso Especial'),
    ]
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('aprobada', 'Aprobada'),
        ('rechazada', 'Rechazada'),
    ]

    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='vacaciones')
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='vacacion')
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    fecha_solicitud = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.usuario.nombre} ({self.fecha_inicio} al {self.fecha_fin}) - {self.estado}"


class Incidencia(models.Model):
    TIPO_CHOICES = [
        ('cobertura', 'Cobertura Insuficiente'),
        ('exceso_horas', 'Exceso de Horas'),
        ('descanso_insuficiente', 'Descanso Insuficiente (<12h)'),
        ('conflicto_vacaciones', 'Conflicto con Vacaciones'),
    ]

    fecha = models.DateField()
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='incidencias', null=True, blank=True)
    tipo = models.CharField(max_length=30, choices=TIPO_CHOICES)
    descripcion = models.TextField()
    resuelta = models.BooleanField(default=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.tipo} - {self.fecha} (Resuelta: {self.resuelta})"


class AsignacionTurno(models.Model):
    DIA_CHOICES = [
        ('lunes', 'Lunes'),
        ('martes', 'Martes'),
        ('miercoles', 'Miércoles'),
        ('jueves', 'Jueves'),
        ('viernes', 'Viernes'),
        ('sabado', 'Sábado'),
        ('domingo', 'Domingo'),
    ]

    ESTADO_CHOICES = [
        ('asignado', 'Asignado'),
        ('intercambiado', 'Intercambiado'),
    ]

    semana = models.ForeignKey(CalendarioSemanal, on_delete=models.CASCADE, related_name='asignaciones')
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='asignaciones')
    dia = models.CharField(max_length=20, choices=DIA_CHOICES)
    turno_plantilla = models.ForeignKey(PlantillaTurno, on_delete=models.PROTECT, related_name='asignaciones')
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='asignado')

    class Meta:
        unique_together = ('semana', 'usuario', 'dia')

    def __str__(self):
        return f"{self.usuario.nombre} - {self.dia} ({self.turno_plantilla.nombre})"