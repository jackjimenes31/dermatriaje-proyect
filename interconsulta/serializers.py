from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import CasoTriaje, ColaInterconsulta, EstablecimientoSalud, Paciente, Profesional


class EstablecimientoSaludSerializer(serializers.ModelSerializer):
    class Meta:
        model = EstablecimientoSalud
        fields = '__all__'


class ProfesionalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profesional
        fields = '__all__'


class PacienteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Paciente
        fields = '__all__'

    def validate(self, attrs):
        tipo_documento = attrs.get('tipo_documento', getattr(self.instance, 'tipo_documento', None))
        numero_documento = attrs.get('numero_documento', getattr(self.instance, 'numero_documento', None))
        temp = Paciente(tipo_documento=tipo_documento, numero_documento=numero_documento)
        try:
            temp.clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict)
        return attrs


class CasoTriajeSerializer(serializers.ModelSerializer):
    riesgo_sugerido = serializers.ReadOnlyField()

    class Meta:
        model = CasoTriaje
        fields = '__all__'


class ColaInterconsultaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ColaInterconsulta
        fields = '__all__'
