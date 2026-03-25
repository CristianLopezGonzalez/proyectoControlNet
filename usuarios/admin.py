from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario, Equipo, IntegracionGoogleCalendar

admin.site.register(Equipo)
admin.site.register(IntegracionGoogleCalendar)

class UsuarioAdmin(UserAdmin):
    list_display = ('email', 'nombre', 'rol', 'activo')
    ordering = ('email',)
    list_filter = ('rol', 'activo', 'is_staff')
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Información personal', {'fields': ('nombre', 'rol', 'activo')}),
        ('Permisos', {'fields': ('is_staff', 'is_superuser', 'groups', 'user_permissions')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'nombre', 'password1', 'password2', 'rol'),
        }),
    )

admin.site.register(Usuario, UsuarioAdmin)