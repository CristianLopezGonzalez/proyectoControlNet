from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import AsignacionTurno, Vacacion, Incidencia
from datetime import timedelta

def check_conflicts(asignacion):
    # 1. Conflicto con Vacaciones
    # Buscamos la fecha real de la asignación.
    # Como dia es string ('lunes', etc.), necesitamos calcular la fecha.
    dias_map = {'lunes': 0, 'martes': 1, 'miercoles': 2, 'jueves': 3, 'viernes': 4, 'sabado': 5, 'domingo': 6}
    fecha_asignacion = asignacion.semana.fecha_inicio_semana + timedelta(days=dias_map[asignacion.dia.lower()])
    
    if Vacacion.objects.filter(
        usuario=asignacion.usuario,
        fecha_inicio__lte=fecha_asignacion,
        fecha_fin__gte=fecha_asignacion,
        estado='aprobada'
    ).exists():
        Incidencia.objects.create(
            fecha=fecha_asignacion,
            usuario=asignacion.usuario,
            tipo='conflicto_vacaciones',
            descripcion=f"Turno asignado durante vacaciones aprobadas el día {fecha_asignacion}."
        )

    # 2. Descanso insuficiente (<12h) - Simplificado para el MVP
    # Aquí se compararía el fin del turno anterior con el inicio de este
    # Pero requiere lógica compleja de ordenación de días.
    pass

@receiver(post_save, sender=AsignacionTurno)
def trigger_conflict_check(sender, instance, created, **kwargs):
    if created:
        check_conflicts(instance)

@receiver(post_save, sender=Vacacion)
def trigger_vacation_conflict(sender, instance, **kwargs):
    if instance.estado == 'aprobada':
        # Al aprobar una vacación, buscamos asignaciones que ahora entren en conflicto
        asignaciones = AsignacionTurno.objects.filter(
            usuario=instance.usuario,
            semana__fecha_inicio_semana__lte=instance.fecha_fin,
            semana__fecha_fin_semana__gte=instance.fecha_inicio
        )
        for asig in asignaciones:
            check_conflicts(asig)
