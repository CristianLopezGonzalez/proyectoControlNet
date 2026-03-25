from django.apps import AppConfig

class TurnosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'turnos'

    def ready(self):
        import turnos.signals
