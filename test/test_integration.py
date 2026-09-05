"""
Pruebas de integración para la API de DermaTriaje.

Cubre el requisito obligatorio del hackathon:
- Camino feliz (happy path): creación de un paciente y de un caso de triaje.
- Casos de error crítico: validación del documento del paciente y
  referencia a un paciente inexistente en un caso de triaje.

Requiere: pytest, pytest-django, djangorestframework (ya instalados en el venv).
Este archivo reemplaza al test_integration.py de placeholder.
"""

import pytest
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APIClient

from interconsulta.models import (
    CasoTriaje,
    EstablecimientoSalud,
    Paciente,
    Profesional,
)


@pytest.fixture
def establecimiento(db):
    return EstablecimientoSalud.objects.create(
        nombre="Centro de Salud Chachapoyas",
        codigo_renaes="12345",
        nivel="I-1",
        departamento="Amazonas",
        provincia="Chachapoyas",
        distrito="Chachapoyas",
        tiene_conectividad_estable=True,
    )


@pytest.fixture
def profesional(db, establecimiento):
    user = User.objects.create_user(username="medico1", password="pass123")
    profesional = getattr(user, "profesional", None)
    if profesional is None:
        profesional = Profesional.objects.create(
            user=user,
            rol="MEDICO_GENERAL",
            establecimiento=establecimiento,
            especialidad="Dermatología",
        )
    else:
        profesional.establecimiento = establecimiento
        profesional.save()
    return profesional


@pytest.fixture
def api_client(profesional):
    client = APIClient()
    client.force_authenticate(user=profesional.user)
    return client


@pytest.fixture
def paciente(db):
    return Paciente.objects.create(
        tipo_documento="DNI",
        numero_documento="12345678",
        nombres="Juan",
        apellidos="Pérez",
        edad=45,
        sexo="M",
    )


# ---------------------------------------------------------------------------
# HAPPY PATH
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_crear_paciente_happy_path(api_client):
    """Crear un paciente con datos válidos debe devolver 201 y los datos correctos."""
    payload = {
        "tipo_documento": "DNI",
        "numero_documento": "87654321",
        "nombres": "Ana",
        "apellidos": "García",
        "edad": 30,
        "sexo": "F",
    }

    response = api_client.post("/api/pacientes/", payload, format="json")

    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["numero_documento"] == "87654321"
    assert response.data["nombres"] == "Ana"
    assert Paciente.objects.filter(numero_documento="87654321").exists()


@pytest.mark.django_db
def test_crear_caso_triaje_happy_path(api_client, paciente, profesional, establecimiento):
    """
    Camino feliz del núcleo clínico del producto: registrar un caso de triaje
    con una lesión de alto riesgo y verificar que el sistema calcula
    correctamente el nivel de riesgo sugerido (campo read-only).
    """
    payload = {
        "paciente": paciente.id,
        "profesional_creador": profesional.id,
        "establecimiento": establecimiento.id,
        "tipo_lesion_predicho": "mel",
        "confianza_modelo": 0.92,
        "probabilidades_top3": [
            {"tipo": "mel", "confianza": 0.92},
            {"tipo": "nv", "confianza": 0.05},
        ],
        "clasificacion_riesgo": "ALTO",
        "notas_clinicas": "Lesión sospechosa en brazo derecho",
    }

    response = api_client.post("/api/casos-triaje/", payload, format="json")

    assert response.status_code == status.HTTP_201_CREATED
    # 'mel' debe mapear automáticamente a riesgo_sugerido = 'ALTO'
    assert response.data["riesgo_sugerido"] == "ALTO"
    assert response.data["estado"] == "REGISTRADO"
    assert CasoTriaje.objects.filter(paciente=paciente).exists()


# ---------------------------------------------------------------------------
# CASOS DE ERROR CRÍTICO
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_crear_paciente_dni_invalido_error_critico(api_client):
    """
    Caso de error crítico: un DNI que no tiene exactamente 8 dígitos debe ser
    rechazado. Aceptar un documento de identidad mal formado compromete la
    trazabilidad clínica del paciente en todo el sistema.
    """
    payload = {
        "tipo_documento": "DNI",
        "numero_documento": "123",  # inválido: menos de 8 dígitos
        "nombres": "Luis",
        "apellidos": "Torres",
        "edad": 50,
        "sexo": "M",
    }

    response = api_client.post("/api/pacientes/", payload, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "numero_documento" in response.data
    assert not Paciente.objects.filter(numero_documento="123").exists()


@pytest.mark.django_db
def test_crear_caso_triaje_paciente_inexistente_error_critico(
    api_client, profesional, establecimiento
):
    """
    Caso de error crítico: intentar registrar un caso de triaje referenciando
    un paciente que no existe. Si el sistema aceptara esto, un caso de alto
    riesgo quedaría huérfano o mal vinculado en la cola de interconsulta,
    lo cual es inaceptable en un sistema de salud.
    """
    payload = {
        "paciente": 9999,  # ID que no existe
        "profesional_creador": profesional.id,
        "establecimiento": establecimiento.id,
        "tipo_lesion_predicho": "mel",
        "confianza_modelo": 0.92,
        "clasificacion_riesgo": "ALTO",
    }

    response = api_client.post("/api/casos-triaje/", payload, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "paciente" in response.data
    assert CasoTriaje.objects.count() == 0