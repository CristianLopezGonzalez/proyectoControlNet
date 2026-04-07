from .models import Notificacion

def crear_notificacion(usuario, tipo, titulo, mensaje, enlace_entidad=None):
    """
    Helper para disparar notificaciones de manera segura desde cualquier ViewSet o Signal.
    """
    if not usuario:
        return None
        
    return Notificacion.objects.create(
        usuario=usuario,
        tipo=tipo,
        titulo=titulo,
        mensaje=mensaje,
        enlace_entidad=enlace_entidad
    )
