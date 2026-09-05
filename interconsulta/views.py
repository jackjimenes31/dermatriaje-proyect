from django.db.models import Case, IntegerField, Value, When
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import CasoTriaje, ColaInterconsulta, EstablecimientoSalud, Paciente, Profesional
from .serializers import (
    CasoTriajeSerializer,
    ColaInterconsultaSerializer,
    EstablecimientoSaludSerializer,
    PacienteSerializer,
    ProfesionalSerializer,
)


class EstablecimientoSaludViewSet(viewsets.ModelViewSet):
    queryset = EstablecimientoSalud.objects.all()
    serializer_class = EstablecimientoSaludSerializer


class ProfesionalViewSet(viewsets.ModelViewSet):
    queryset = Profesional.objects.all()
    serializer_class = ProfesionalSerializer


class PacienteViewSet(viewsets.ModelViewSet):
    queryset = Paciente.objects.all()
    serializer_class = PacienteSerializer

    @action(detail=False, methods=['get'])
    def buscar(self, request):
        tipo_documento = request.query_params.get('tipo_documento', Paciente.TipoDocumento.DNI)
        numero_documento = request.query_params.get('numero_documento')
        if not numero_documento:
            return Response({'detail': 'numero_documento es requerido.'}, status=400)

        try:
            paciente = Paciente.objects.get(
                tipo_documento=tipo_documento, numero_documento=numero_documento
            )
        except Paciente.DoesNotExist:
            return Response({'detail': 'Paciente no encontrado.'}, status=404)

        return Response(self.get_serializer(paciente).data)


class CasoTriajeViewSet(viewsets.ModelViewSet):
    queryset = CasoTriaje.objects.all()
    serializer_class = CasoTriajeSerializer


class ColaInterconsultaViewSet(viewsets.ModelViewSet):
    queryset = ColaInterconsulta.objects.all()
    serializer_class = ColaInterconsultaSerializer

    # Orden de atención: URGENTE primero, luego ALTA, luego MEDIA.
    PRIORIDAD_RANGO = {
        ColaInterconsulta.Prioridad.URGENTE: 0,
        ColaInterconsulta.Prioridad.ALTA: 1,
        ColaInterconsulta.Prioridad.MEDIA: 2,
    }

    def get_queryset(self):
        rango_prioridad = Case(
            *[
                When(prioridad=prioridad, then=Value(rango))
                for prioridad, rango in self.PRIORIDAD_RANGO.items()
            ],
            output_field=IntegerField(),
        )
        return ColaInterconsulta.objects.annotate(prioridad_rango=rango_prioridad).order_by(
            'prioridad_rango', 'fecha_ingreso'
        )

    @staticmethod
    def _especialista_solicitante(request):
        profesional = getattr(request.user, 'profesional', None)
        if profesional is None or profesional.rol != Profesional.Rol.ESPECIALISTA:
            return None
        return profesional

    @action(detail=False, methods=['get'])
    def mia(self, request):
        """ Bandeja de interconsultas asignadas al especialista autenticado, ya priorizada. """
        especialista = self._especialista_solicitante(request)
        if especialista is None:
            return Response(
                {'detail': 'Solo un especialista tiene una bandeja de interconsulta.'}, status=403
            )

        casos = self.get_queryset().filter(
            especialista_asignado=especialista,
            estado__in=[ColaInterconsulta.Estado.EN_ESPERA, ColaInterconsulta.Estado.EN_ATENCION],
        )
        return Response(self.get_serializer(casos, many=True).data)

    @action(detail=True, methods=['post'])
    def atender(self, request, pk=None):
        """ El especialista toma el caso de su bandeja para revisarlo (asíncrono, sin cita). """
        especialista = self._especialista_solicitante(request)
        if especialista is None:
            return Response(
                {'detail': 'Solo un especialista puede atender casos de interconsulta.'}, status=403
            )

        cola = self.get_object()
        if cola.estado in (ColaInterconsulta.Estado.RESUELTO, ColaInterconsulta.Estado.CANCELADO):
            return Response({'detail': 'Este caso ya está cerrado.'}, status=400)
        if cola.especialista_asignado_id not in (None, especialista.id):
            return Response(
                {'detail': 'Este caso ya está asignado a otro especialista.'}, status=403
            )

        if cola.especialista_asignado_id is None:
            cola.especialista_asignado = especialista
        if cola.estado == ColaInterconsulta.Estado.EN_ESPERA:
            cola.estado = ColaInterconsulta.Estado.EN_ATENCION
            cola.fecha_atencion = timezone.now()
        cola.save()
        return Response(self.get_serializer(cola).data)

    @action(detail=True, methods=['post'])
    def resolver(self, request, pk=None):
        """ Cierra la interconsulta y el CasoTriaje relacionado. """
        especialista = self._especialista_solicitante(request)
        if especialista is None:
            return Response(
                {'detail': 'Solo un especialista puede resolver casos de interconsulta.'}, status=403
            )

        cola = self.get_object()
        if cola.especialista_asignado_id != especialista.id:
            return Response(
                {'detail': 'Solo el especialista asignado puede resolver este caso.'}, status=403
            )

        cola.estado = ColaInterconsulta.Estado.RESUELTO
        cola.observaciones_especialista = request.data.get(
            'observaciones_especialista', cola.observaciones_especialista
        )
        cola.save()

        CasoTriaje.objects.filter(pk=cola.caso_id).update(
            estado=CasoTriaje.Estado.RESUELTO_INTERCONSULTA,
            profesional_resuelve=especialista,
            fecha_resolucion=timezone.now(),
        )
        return Response(self.get_serializer(cola).data)
