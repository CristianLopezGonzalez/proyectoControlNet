from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import datetime, timedelta
from django.db.models import Count, Q

from .models import (
    CalendarioSemanal, PlantillaTurno, PatronRotacion,
    Vacacion, Incidencia, AsignacionTurno
)
from .serializers import (
    CalendarioSemanalSerializer,
    CalendarioSemanalListSerializer,
    PlantillaTurnoSerializer,
    PatronRotacionSerializer,
    VacacionSerializer,
    IncidenciaSerializer,
    AsignacionTurnoSerializer,
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

    @action(detail=True, methods=['post'], url_path='publicar')
    def publicar(self, request, pk=None):
        semana = self.get_object()
        semana.estado = 'publicado'
        semana.save()
        return Response(CalendarioSemanalSerializer(semana).data)

    def _generar_turnos(self, patron_id, anio, numero_semana):
        try:
            patron = PatronRotacion.objects.get(id=patron_id)
            semana, _ = CalendarioSemanal.objects.get_or_create(
                anio=anio, numero_semana=numero_semana,
                defaults={'fecha_inicio_semana': datetime.now(), 'fecha_fin_semana': datetime.now() + timedelta(days=7)}
            )
        except PatronRotacion.DoesNotExist:
            return {'error': f'Patron {patron_id} no encontrado', 'status': status.HTTP_404_NOT_FOUND}

        equipo = patron.equipo
        
        # Limpiar turnos solo para este equipo en esta semana (modo bulk-friendly)
        AsignacionTurno.objects.filter(semana=semana, usuario__equipo=equipo.id).delete()

        empleados = equipo.miembros.all()
        secuencia = patron.secuencia
        
        dias = ['lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado', 'domingo']
        
        # Asegurarnos de que fecha_inicio_semana sea date (por si django lo guarda como tal)
        fecha_inicio_semana_date = semana.fecha_inicio_semana
        if isinstance(fecha_inicio_semana_date, datetime):
            fecha_inicio_semana_date = fecha_inicio_semana_date.date()
            
        patron_fecha_inicio = patron.fecha_inicio
        if isinstance(patron_fecha_inicio, datetime):
            patron_fecha_inicio = patron_fecha_inicio.date()

        for i, emp in enumerate(empleados):
            for j, dia in enumerate(dias):
                # Fórmula de rotación basada en el desplazamiento temporal continuo
                fecha_dia = fecha_inicio_semana_date + timedelta(days=j)
                desplazamiento_dias = (fecha_dia - patron_fecha_inicio).days
                
                if len(secuencia) > 0:
                    plantilla_id = secuencia[ (i + desplazamiento_dias) % len(secuencia) ]
                else:
                    plantilla_id = None
                
                if plantilla_id:
                    try:
                        plantilla = PlantillaTurno.objects.get(id=plantilla_id)
                        # Verificar vacaciones
                        if not Vacacion.objects.filter(
                            usuario=emp, 
                            fecha_inicio__lte=fecha_dia,
                            fecha_fin__gte=fecha_dia,
                            estado='aprobada'
                        ).exists():
                            AsignacionTurno.objects.update_or_create(
                                semana=semana, usuario=emp, dia=dia,
                                defaults={'turno_plantilla': plantilla}
                            )
                    except PlantillaTurno.DoesNotExist:
                        pass
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
