"""
Pruebas unitarias para los modelos y señales del dominio clínico (interconsulta).

Verifica la lógica de negocio a nivel de modelo:
- Validaciones de formato de documento de Paciente (DNI y CE).
- Cálculo automático de la propiedad `riesgo_sugerido` en CasoTriaje.
- Señal post_save para la creación de perfil Profesional al crear un User.
- Métodos __str__ de los modelos.
"""

import pytest
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from interconsulta.models import (
    CasoTriaje,
    EstablecimientoSalud,
    Paciente,
    Profesional,
)


@pytest.mark.django_db
class TestPacienteModel:

    def test_paciente_dni_valido_clean(self):
        """Un DNI de 8 dígitos numéricos debe pasar la validación clean()."""
        paciente = Paciente(
            tipo_documento="DNI",
            numero_documento="12345678",
            nombres="Juan",
            apellidos="Pérez",
            edad=40,
            sexo="M",
        )
        paciente.clean()

    def test_paciente_dni_invalido_caracteres_clean(self):
        """Un DNI con menos de 8 dígitos debe lanzar ValidationError."""
        paciente = Paciente(
            tipo_documento="DNI",
            numero_documento="12345",
            nombres="Pedro",
            apellidos="Gómez",
            edad=30,
            sexo="M",
        )
        with pytest.raises(ValidationError) as exc_info:
            paciente.clean()
        assert "numero_documento" in exc_info.value.message_dict

    def test_paciente_ce_valido_clean(self):
        """Un Carné de Extranjería alfanumérico entre 8 y 12 caracteres es válido."""
        paciente = Paciente(
            tipo_documento="CE",
            numero_documento="E12345678",
            nombres="Maria",
            apellidos="Silva",
            edad=35,
            sexo="F",
        )
        paciente.clean()

    def test_paciente_ce_invalido_clean(self):
        """Un CE con menos de 8 caracteres debe ser rechazado por clean()."""
        paciente = Paciente(
            tipo_documento="CE",
            numero_documento="CE123",
            nombres="Maria",
            apellidos="Silva",
            edad=35,
            sexo="F",
        )
        with pytest.raises(ValidationError) as exc_info:
            paciente.clean()
        assert "numero_documento" in exc_info.value.message_dict

    def test_paciente_str(self):
        """Verifica la representación en string del paciente."""
        paciente = Paciente(
            tipo_documento="DNI",
            numero_documento="12345678",
            nombres="Carlos",
            apellidos="Rios",
            edad=25,
            sexo="M",
        )
        assert str(paciente) == "Carlos Rios (DNI 12345678)"


@pytest.mark.django_db
class TestCasoTriajeModel:

    def test_riesgo_sugerido_por_tipo_lesion(self):
        """La propiedad riesgo_sugerido calcula el nivel según la lesión."""
        caso_melanoma = CasoTriaje(tipo_lesion_predicho="mel")
        assert caso_melanoma.riesgo_sugerido == CasoTriaje.ClasificacionRiesgo.ALTO

        caso_bkl = CasoTriaje(tipo_lesion_predicho="bkl")
        assert caso_bkl.riesgo_sugerido == CasoTriaje.ClasificacionRiesgo.MEDIO

        caso_nevo = CasoTriaje(tipo_lesion_predicho="nv")
        assert caso_nevo.riesgo_sugerido == CasoTriaje.ClasificacionRiesgo.BAJO


@pytest.mark.django_db
class TestProfesionalSignal:

    def test_signal_crea_perfil_profesional(self):
        """Al crear un User normal, la señal post_save debe crear un Profesional."""
        user = User.objects.create_user(username="medico_nuevo", password="password123")
        assert hasattr(user, "profesional")
        assert user.profesional.rol == Profesional.Rol.MEDICO_GENERAL


@pytest.mark.django_db
class TestEstablecimientoSaludModel:

    def test_establecimiento_str(self):
        est = EstablecimientoSalud(nombre="CS Chachapoyas", nivel="I-1")
        assert str(est) == "CS Chachapoyas (I-1)"
