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
