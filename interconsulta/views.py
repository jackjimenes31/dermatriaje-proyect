from rest_framework import viewsets

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


class CasoTriajeViewSet(viewsets.ModelViewSet):
    queryset = CasoTriaje.objects.all()
    serializer_class = CasoTriajeSerializer


class ColaInterconsultaViewSet(viewsets.ModelViewSet):
    queryset = ColaInterconsulta.objects.all()
    serializer_class = ColaInterconsultaSerializer
