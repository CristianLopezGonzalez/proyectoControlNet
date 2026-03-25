from django.core.management.base import BaseCommand
from django.utils import timezone
from usuarios.models import Usuario, Equipo
from turnos.models import PlantillaTurno, CalendarioSemanal, AsignacionTurno, Vacacion
from datetime import datetime, timedelta

class Command(BaseCommand):
    help = 'Puebla la base de datos con datos de prueba para WFM'

    def handle(self, *args, **kwargs):
        self.stdout.write('Iniciando seeder...')

        # 1. Admin
        admin, created = Usuario.objects.get_or_create(
            email='admin@netflow.com',
            defaults={
                'nombre': 'Administrador Principal',
                'rol': 'admin',
                'is_staff': True,
                'is_superuser': True
            }
        )
        if created: admin.set_password('Admin123!'); admin.save()

        # 2. Supervisor
        supervisor, created = Usuario.objects.get_or_create(
            email='supervisor@netflow.com',
            defaults={
                'nombre': 'Supervisor de Turnos',
                'rol': 'supervisor',
            }
        )
        if created: supervisor.set_password('Super123!'); supervisor.save()

        # 3. Equipos
        equipo_a, _ = Equipo.objects.get_or_create(nombre='Equipo Alpha', defaults={'supervisor': supervisor})
        equipo_b, _ = Equipo.objects.get_or_create(nombre='Equipo Beta', defaults={'supervisor': supervisor})

        # 4. Plantillas de Turno
        m_t, _ = PlantillaTurno.objects.get_or_create(
            nombre='Mañana', 
            defaults={'hora_inicio': '06:00', 'hora_fin': '14:00'}
        )
        t_t, _ = PlantillaTurno.objects.get_or_create(
            nombre='Tarde', 
            defaults={'hora_inicio': '14:00', 'hora_fin': '22:00'}
        )
        n_t, _ = PlantillaTurno.objects.get_or_create(
            nombre='Noche', 
            defaults={'hora_inicio': '22:00', 'hora_fin': '06:00'}
        )

        # 5. Empleados (10 repartidos)
        for i in range(1, 11):
            equipo = equipo_a if i <= 5 else equipo_b
            emp, created = Usuario.objects.get_or_create(
                email=f'empleado{i}@netflow.com',
                defaults={
                    'nombre': f'Empleado {i}',
                    'rol': 'empleado',
                    'equipo': equipo
                }
            )
            if created: emp.set_password('Emp123!'); emp.save()

        # 6. Vacaciones
        emp1 = Usuario.objects.get(email='empleado1@netflow.com')
        Vacacion.objects.get_or_create(
            usuario=emp1,
            fecha_inicio=timezone.now().date() + timedelta(days=2),
            fecha_fin=timezone.now().date() + timedelta(days=5),
            defaults={'estado': 'aprobada', 'tipo': 'vacacion'}
        )

        emp2 = Usuario.objects.get(email='empleado2@netflow.com')
        Vacacion.objects.get_or_create(
            usuario=emp2,
            fecha_inicio=timezone.now().date() + timedelta(days=10),
            fecha_fin=timezone.now().date() + timedelta(days=15),
            defaults={'estado': 'pendiente', 'tipo': 'vacacion'}
        )

        self.stdout.write(self.style.SUCCESS('Base de datos poblada con éxito.'))
