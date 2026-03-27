from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import datetime, timedelta
from django.db.models import Count, Q

from .models import (
    CalendarioSemanal, PlantillaTurno, PatronRotacion,
    Vacacion, Incidencia, AsignacionTurno, ConfiguracionRegla
)
from .serializers import (
    CalendarioSemanalSerializer,
    CalendarioSemanalListSerializer,
    PlantillaTurnoSerializer,
    PatronRotacionSerializer,
    VacacionSerializer,
    IncidenciaSerializer,
    AsignacionTurnoSerializer,
    ConfiguracionReglaSerializer,
)
from usuarios.models import Usuario, Equipo


class PlantillaTurnoViewSet(viewsets.ModelViewSet):
    queryset = PlantillaTurno.objects.all()
    serializer_class = PlantillaTurnoSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            # Aquí se podría añadir un permiso custom IsAdmin
            pass
        return super().get_permissions()


class PatronRotacionViewSet(viewsets.ModelViewSet):
    queryset = PatronRotacion.objects.all()
    serializer_class = PatronRotacionSerializer
    permission_classes = [IsAuthenticated]


class VacacionViewSet(viewsets.ModelViewSet):
    queryset = Vacacion.objects.all()
    serializer_class = VacacionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.rol == 'empleado':
            return self.queryset.filter(usuario=user)
        elif user.rol == 'supervisor':
            return self.queryset.filter(usuario__equipo__supervisor=user)
        return self.queryset

    @action(detail=True, methods=['post'], url_path='responder')
    def responder(self, request, pk=None):
        vacacion = self.get_object()
        if request.user.rol not in ('admin', 'supervisor'):
            return Response({'error': 'No tienes permiso'}, status=status.HTTP_403_FORBIDDEN)
        
        nuevo_estado = request.data.get('estado')
        if nuevo_estado not in ('aprobada', 'rechazada'):
            return Response({'error': 'Estado inválido'}, status=status.HTTP_400_BAD_REQUEST)
        
        vacacion.estado = nuevo_estado
        vacacion.save()
        return Response(VacacionSerializer(vacacion).data)


class IncidenciaViewSet(viewsets.ModelViewSet):
    queryset = Incidencia.objects.all()
    serializer_class = IncidenciaSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=['post'], url_path='resolver')
    def resolver(self, request, pk=None):
        incidencia = self.get_object()
        incidencia.resuelta = True
        incidencia.save()
        return Response(IncidenciaSerializer(incidencia).data)


class CalendarioSemanalViewSet(viewsets.ModelViewSet):
    queryset = CalendarioSemanal.objects.all().order_by('-anio', '-numero_semana')
    serializer_class = CalendarioSemanalSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'list':
            return CalendarioSemanalListSerializer
        return CalendarioSemanalSerializer

    @action(detail=False, methods=['get'], url_path='month-view')
    def month_view(self, request):
        anio = request.query_params.get('anio')
        mes = request.query_params.get('mes')
        equipo_id = request.query_params.get('equipo_id')

        if not anio or not mes:
            return Response(
                {'error': 'Se requieren los parámetros "anio" y "mes".'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            anio = int(anio)
            mes = int(mes)
        except ValueError:
            return Response(
                {'error': '"anio" y "mes" deben ser números enteros.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Semanas que pertenecen al mes/año solicitado
        semanas = CalendarioSemanal.objects.filter(
            anio=anio,
            fecha_inicio_semana__month__lte=mes,
            fecha_fin_semana__month__gte=mes,
        )

        asignaciones_qs = AsignacionTurno.objects.filter(semana__in=semanas)
        if equipo_id:
            asignaciones_qs = asignaciones_qs.filter(usuario__equipo_id=equipo_id)

        return Response({
            'asignaciones': AsignacionTurnoSerializer(asignaciones_qs, many=True).data,
            'semanas': CalendarioSemanalListSerializer(semanas, many=True).data,
        })

    @action(detail=True, methods=['post'], url_path='publicar')
    def publicar(self, request, pk=None):
        semana = self.get_object()
        semana.estado = 'publicado'
        semana.save()
        return Response(CalendarioSemanalSerializer(semana).data)

    def _generar_turnos(self, patron_id, anio, numero_semana):
        try:
            patron = PatronRotacion.objects.get(id=patron_id)
            
            # Cálculo preciso de lunes y domingo de la semana ISO
            jan4 = datetime(anio, 1, 4)
            start_of_week1 = jan4 - timedelta(days=jan4.weekday())
            fecha_inicio = start_of_week1 + timedelta(weeks=numero_semana - 1)
            fecha_fin = fecha_inicio + timedelta(days=6)

            semana, _ = CalendarioSemanal.objects.get_or_create(
                anio=anio, numero_semana=numero_semana,
                defaults={
                    'fecha_inicio_semana': fecha_inicio.date(),
                    'fecha_fin_semana': fecha_fin.date()
                }
            )
        except PatronRotacion.DoesNotExist:
            return {'error': f'Patron {patron_id} no encontrado', 'status': status.HTTP_404_NOT_FOUND}

        equipo = patron.equipo
        
        # Limpiar turnos solo para este equipo en esta semana
        AsignacionTurno.objects.filter(semana=semana, usuario__equipo=equipo.id).delete()

        empleados = list(equipo.miembros.all())
        secuencia = patron.secuencia
        
        if not secuencia:
            return None # No hay secuencia, no se genera nada
            
        dias = ['lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado', 'domingo']
        
        # Asegurarnos de usar date()
        fecha_inicio_semana_date = semana.fecha_inicio_semana
        if isinstance(fecha_inicio_semana_date, datetime):
            fecha_inicio_semana_date = fecha_inicio_semana_date.date()
            
        patron_fecha_inicio = patron.fecha_inicio
        if isinstance(patron_fecha_inicio, datetime):
            patron_fecha_inicio = patron_fecha_inicio.date()

        # OPTIMIZACIÓN 1: Obtener TODAS las vacaciones de este equipo para esta semana en 1 sola query
        vacaciones_aprobadas = Vacacion.objects.filter(
            usuario__in=empleados,
            estado='aprobada',
            fecha_inicio__lte=fecha_fin,
            fecha_fin__gte=fecha_inicio
        )
        
        # Guardaremos las fechas de vacaciones por usuario en un diccionario para acceso ultra-rápido en memoria
        vacaciones_por_usuario = {emp.id: [] for emp in empleados}
        for vac in vacaciones_aprobadas:
            current_date = vac.fecha_inicio
            while current_date <= vac.fecha_fin:
                vacaciones_por_usuario[vac.usuario_id].append(current_date)
                current_date += timedelta(days=1)

        # OPTIMIZACIÓN 2: Preparar la lista de asignaciones para hacer un único bulk_create
        nuevas_asignaciones = []

        for i, emp in enumerate(empleados):
            for j, dia in enumerate(dias):
                # Fórmula de rotación
                fecha_dia = fecha_inicio_semana_date + timedelta(days=j)
                desplazamiento_dias = (fecha_dia - patron_fecha_inicio).days
                
                plantilla_id = secuencia[ (i + desplazamiento_dias) % len(secuencia) ]
                
                if plantilla_id:
                    # Verificar si la fecha actual está en las vacaciones del usuario
                    if fecha_dia not in vacaciones_por_usuario[emp.id]:
                        # No necesitamos la instancia PlantillaTurno, podemos pasar el ID directamente
                        nuevas_asignaciones.append(
                            AsignacionTurno(
                                semana=semana,
                                usuario=emp,
                                dia=dia,
                                turno_plantilla_id=plantilla_id
                            )
                        )
                        
        # OPTIMIZACIÓN 3: Guardar en BD todo de golpe
        if nuevas_asignaciones:
            AsignacionTurno.objects.bulk_create(nuevas_asignaciones)
            
        return None

    @action(detail=False, methods=['post'], url_path='generar')
    def generar(self, request):
        if isinstance(request.data, list):
            # Modo bulk
            for item in request.data:
                res = self._generar_turnos(item.get('patron_id'), item.get('anio'), item.get('numero_semana'))
                if res: return Response(res, status=res['status'])
        else:
            res = self._generar_turnos(request.data.get('patron_id'), request.data.get('anio'), request.data.get('numero_semana'))
            if res: return Response(res, status=res['status'])
            
        return Response({'status': 'Generación completada'}, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], url_path='generar-seleccion')
    def generar_seleccion(self, request):
        if isinstance(request.data, list):
            for item in request.data:
                res = self._generar_turnos(item.get('patron_id'), item.get('anio'), item.get('numero_semana'))
                if res: return Response(res, status=res['status'])
        else:
            res = self._generar_turnos(request.data.get('patron_id'), request.data.get('anio'), request.data.get('numero_semana'))
            if res: return Response(res, status=res['status'])
            
        return Response({'status': 'Generación selección completada'}, status=status.HTTP_201_CREATED)


class ReportesViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'], url_path='coverage')
    def coverage(self, request):
        # Ejemplo de reporte de cobertura
        data = AsignacionTurno.objects.values('dia', 'turno_plantilla__nombre').annotate(count=Count('id'))
        return Response(data)


class AsignacionTurnoViewSet(viewsets.ModelViewSet):
    queryset = AsignacionTurno.objects.select_related('semana', 'usuario', 'turno_plantilla').all()
    serializer_class = AsignacionTurnoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        semana_id = self.request.query_params.get('semana_id')
        usuario_id = self.request.query_params.get('usuario_id')
        equipo_id = self.request.query_params.get('equipo_id')
        if semana_id:
            qs = qs.filter(semana_id=semana_id)
        if usuario_id:
            qs = qs.filter(usuario_id=usuario_id)
        if equipo_id:
            qs = qs.filter(usuario__equipo_id=equipo_id)
        return qs


class ConfiguracionReglaViewSet(viewsets.ModelViewSet):
    queryset = ConfiguracionRegla.objects.all()
    serializer_class = ConfiguracionReglaSerializer
    permission_classes = [IsAuthenticated]
