from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models

class UsuarioManager(BaseUserManager):
    def create_user(self, email, nombre, password=None, **extra_fields):
        if not email:
            raise ValueError('El email es obligatorio')
        email = self.normalize_email(email)
        user = self.model(email=email, nombre=nombre, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, nombre, password=None, **extra_fields):
        extra_fields.setdefault('rol', 'admin')
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, nombre, password, **extra_fields)


class Equipo(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    supervisor = models.ForeignKey('Usuario', on_delete=models.SET_NULL, null=True, related_name='equipos_supervisados')

    def __str__(self):
        return self.nombre


class Usuario(AbstractBaseUser, PermissionsMixin):
    ROL_CHOICES = [
        ('admin', 'Admin'),
        ('supervisor', 'Supervisor'),
        ('empleado', 'Empleado'),
    ]

    nombre = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    rol = models.CharField(max_length=20, choices=ROL_CHOICES, default='empleado')
    equipo = models.ForeignKey(Equipo, on_delete=models.SET_NULL, null=True, blank=True, related_name='miembros')
    activo = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nombre']

    objects = UsuarioManager()

    def __str__(self):
        return f"{self.nombre} ({self.email})"


class IntegracionGoogleCalendar(models.Model):
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE, related_name='google_calendar')
    google_calendar_id = models.CharField(max_length=255, blank=True, null=True)
    sincronizacion_activa = models.BooleanField(default=False)
    ultima_sync = models.DateTimeField(null=True, blank=True)
    
    # Credenciales OAuth
    access_token = models.CharField(max_length=2048, blank=True, null=True)
    refresh_token = models.CharField(max_length=2048, blank=True, null=True)
    token_expiry = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Google Calendar - {self.usuario.nombre}"