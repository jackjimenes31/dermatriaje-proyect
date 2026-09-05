"""
Pruebas de integración para la API de DermaTriaje.

Cubre el requisito obligatorio del hackathon:
- Camino feliz (happy path): creación de un paciente y de un caso de triaje.
- Casos de error crítico: validación del documento del paciente y
  referencia a un paciente inexistente en un caso de triaje.

Requiere: pytest, pytest-django, djangorestframework (ya instalados en el venv).
Este archivo reemplaza al test_integration.py de placeholder.
"""

import io
import json

import pytest
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework import status
from rest_framework.test import APIClient

from interconsulta.models import (
    CasoTriaje,
    ColaInterconsulta,
    EstablecimientoSalud,
    Paciente,
    Profesional,
)


def _imagen_prueba():
    """Genera un JPEG chico y válido en memoria (CasoTriaje.imagen es obligatorio)."""
    buffer = io.BytesIO()
    Image.new("RGB", (10, 10), color="red").save(buffer, format="JPEG")
    buffer.seek(0)
    return SimpleUploadedFile("lesion.jpg", buffer.read(), content_type="image/jpeg")


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


def _crear_especialista(username):
    """
    El signal crear_perfil_profesional ya crea un Profesional(MEDICO_GENERAL)
    apenas se crea el User, así que aquí solo lo ajustamos a ESPECIALISTA en
    vez de intentar crear uno nuevo (rompería el OneToOne).
    """
    user = User.objects.create_user(username=username, password="pass123")
    profesional = getattr(user, "profesional", None)
    if profesional is None:
        profesional = Profesional.objects.create(user=user, rol="ESPECIALISTA")
    else:
        profesional.rol = "ESPECIALISTA"
        profesional.save()
    return profesional


@pytest.fixture
def especialista(db, establecimiento):
    return _crear_especialista("especialista1")


@pytest.fixture
def api_client_especialista(especialista):
    client = APIClient()
    client.force_authenticate(user=especialista.user)
    return client


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
    correctamente el nivel de riesgo sugerido (campo read-only). La imagen es
    obligatoria, así que el POST va como multipart/form-data.
    """
    payload = {
        "paciente": paciente.id,
        "profesional_creador": profesional.id,
        "establecimiento": establecimiento.id,
        "tipo_lesion_predicho": "mel",
        "confianza_modelo": 0.92,
        "probabilidades_top3": json.dumps([
            {"tipo": "mel", "confianza": 0.92},
            {"tipo": "nv", "confianza": 0.05},
        ]),
        "clasificacion_riesgo": "ALTO",
        "notas_clinicas": "Lesión sospechosa en brazo derecho",
        "imagen": _imagen_prueba(),
    }

    response = api_client.post("/api/casos-triaje/", payload, format="multipart")

    assert response.status_code == status.HTTP_201_CREATED
    # 'mel' debe mapear automáticamente a riesgo_sugerido = 'ALTO'
    assert response.data["riesgo_sugerido"] == "ALTO"
    assert response.data["estado"] == "REGISTRADO"
    assert response.data["probabilidades_top3"] == [
        {"tipo": "mel", "confianza": 0.92},
        {"tipo": "nv", "confianza": 0.05},
    ]
    assert response.data["imagen"]
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
        "imagen": _imagen_prueba(),
    }

    response = api_client.post("/api/casos-triaje/", payload, format="multipart")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "paciente" in response.data
    assert CasoTriaje.objects.count() == 0


# ---------------------------------------------------------------------------
# COLA DE INTERCONSULTA
# ---------------------------------------------------------------------------

def _payload_caso(paciente, profesional, establecimiento, tipo_lesion, riesgo):
    return {
        "paciente": paciente.id,
        "profesional_creador": profesional.id,
        "establecimiento": establecimiento.id,
        "tipo_lesion_predicho": tipo_lesion,
        "confianza_modelo": 0.9,
        "clasificacion_riesgo": riesgo,
        "imagen": _imagen_prueba(),
    }


@pytest.mark.django_db
def test_caso_riesgo_alto_encola_automaticamente(
    api_client, paciente, profesional, establecimiento, especialista
):
    """
    Un caso ALTO debe encolarse solo, con prioridad URGENTE, y el CasoTriaje
    debe pasar a EN_COLA_INTERCONSULTA (aunque la respuesta del POST siga
    mostrando el estado previo a la actualización, ver test happy path).
    """
    payload = _payload_caso(paciente, profesional, establecimiento, "mel", "ALTO")
    response = api_client.post("/api/casos-triaje/", payload, format="multipart")
    caso_id = response.data["id"]

    cola = ColaInterconsulta.objects.get(caso_id=caso_id)
    assert cola.prioridad == "URGENTE"
    assert cola.especialista_asignado_id == especialista.id
    assert CasoTriaje.objects.get(pk=caso_id).estado == "EN_COLA_INTERCONSULTA"


@pytest.mark.django_db
def test_caso_riesgo_bajo_no_se_encola(api_client, paciente, profesional, establecimiento):
    """Un caso BAJO se resuelve en el mismo nivel: no debe generar interconsulta."""
    payload = _payload_caso(paciente, profesional, establecimiento, "nv", "BAJO")
    response = api_client.post("/api/casos-triaje/", payload, format="multipart")
    caso_id = response.data["id"]

    assert not ColaInterconsulta.objects.filter(caso_id=caso_id).exists()
    assert CasoTriaje.objects.get(pk=caso_id).estado == "REGISTRADO"


@pytest.mark.django_db
def test_asignacion_automatica_por_menor_carga(
    api_client, paciente, profesional, establecimiento, especialista
):
    """
    Si un especialista ya tiene un caso en espera, el siguiente caso ALTO debe
    asignarse al especialista con menos carga, no al ya ocupado.
    """
    especialista_ocupado = _crear_especialista("especialista2")
    caso_previo = CasoTriaje.objects.create(
        paciente=paciente,
        profesional_creador=profesional,
        establecimiento=establecimiento,
        tipo_lesion_predicho="nv",
        confianza_modelo=0.8,
        clasificacion_riesgo="BAJO",  # no dispara el signal de encolamiento
        imagen=_imagen_prueba(),
    )
    ColaInterconsulta.objects.create(
        caso=caso_previo,
        prioridad="URGENTE",
        especialista_asignado=especialista_ocupado,
        estado="EN_ESPERA",
    )

    payload = _payload_caso(paciente, profesional, establecimiento, "mel", "ALTO")
    response = api_client.post("/api/casos-triaje/", payload, format="multipart")
    caso_id = response.data["id"]

    cola = ColaInterconsulta.objects.get(caso_id=caso_id)
    assert cola.especialista_asignado_id == especialista.id


@pytest.mark.django_db
def test_cola_ordenada_por_prioridad(api_client, paciente, profesional, establecimiento):
    """La cola debe devolver primero URGENTE aunque se haya creado después que ALTA."""
    payload_medio = _payload_caso(paciente, profesional, establecimiento, "bkl", "MEDIO")
    api_client.post("/api/casos-triaje/", payload_medio, format="multipart")

    payload_alto = _payload_caso(paciente, profesional, establecimiento, "mel", "ALTO")
    response_alto = api_client.post("/api/casos-triaje/", payload_alto, format="multipart")
    caso_alto_id = response_alto.data["id"]

    response = api_client.get("/api/cola-interconsulta/")

    assert response.status_code == status.HTTP_200_OK
    assert response.data[0]["prioridad"] == "URGENTE"
    assert response.data[0]["caso"] == caso_alto_id


@pytest.mark.django_db
def test_especialista_atiende_y_resuelve_caso(
    api_client, api_client_especialista, paciente, profesional, establecimiento, especialista
):
    """Loop completo: atender pasa a EN_ATENCION, resolver cierra cola y caso."""
    payload = _payload_caso(paciente, profesional, establecimiento, "mel", "ALTO")
    response = api_client.post("/api/casos-triaje/", payload, format="multipart")
    caso_id = response.data["id"]
    cola_id = ColaInterconsulta.objects.get(caso_id=caso_id).id

    response_atender = api_client_especialista.post(f"/api/cola-interconsulta/{cola_id}/atender/")
    assert response_atender.status_code == status.HTTP_200_OK
    assert response_atender.data["estado"] == "EN_ATENCION"

    response_resolver = api_client_especialista.post(
        f"/api/cola-interconsulta/{cola_id}/resolver/",
        {"observaciones_especialista": "Biopsia recomendada"},
        format="json",
    )
    assert response_resolver.status_code == status.HTTP_200_OK
    assert response_resolver.data["estado"] == "RESUELTO"

    caso = CasoTriaje.objects.get(pk=caso_id)
    assert caso.estado == "RESUELTO_INTERCONSULTA"
    assert caso.profesional_resuelve_id == especialista.id
    assert caso.fecha_resolucion is not None


@pytest.mark.django_db
def test_caso_detalle_incluye_url_de_imagen(
    api_client, api_client_especialista, paciente, profesional, establecimiento, especialista
):
    """La bandeja del especialista debe poder mostrar la imagen del caso."""
    payload = _payload_caso(paciente, profesional, establecimiento, "mel", "ALTO")
    response = api_client.post("/api/casos-triaje/", payload, format="multipart")
    cola_id = ColaInterconsulta.objects.get(caso_id=response.data["id"]).id

    response_mia = api_client_especialista.get("/api/cola-interconsulta/mia/")

    assert response_mia.status_code == status.HTTP_200_OK
    item = next(i for i in response_mia.data if i["id"] == cola_id)
    assert item["caso_detalle"]["imagen_url"]
    assert "/media/" in item["caso_detalle"]["imagen_url"]


# ---------------------------------------------------------------------------
# COLA DE INTERCONSULTA — CASOS DE ERROR CRÍTICO
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_medico_general_no_puede_atender_interconsulta(
    api_client, paciente, profesional, establecimiento, especialista
):
    """
    Solo un especialista puede atender la cola. Si un médico general pudiera
    hacerlo, se rompe la separación de responsabilidades del triaje escalonado.
    """
    payload = _payload_caso(paciente, profesional, establecimiento, "mel", "ALTO")
    response = api_client.post("/api/casos-triaje/", payload, format="multipart")
    cola_id = ColaInterconsulta.objects.get(caso_id=response.data["id"]).id

    response_atender = api_client.post(f"/api/cola-interconsulta/{cola_id}/atender/")

    assert response_atender.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_especialista_no_asignado_no_puede_resolver(
    api_client, paciente, profesional, establecimiento, especialista
):
    """
    Un especialista distinto al asignado no puede resolver el caso de otro:
    si lo hiciera, dos especialistas podrían pisarse el diagnóstico del mismo
    paciente.
    """
    otro_especialista = _crear_especialista("especialista3")
    api_client_otro = APIClient()
    api_client_otro.force_authenticate(user=otro_especialista.user)

    payload = _payload_caso(paciente, profesional, establecimiento, "mel", "ALTO")
    response = api_client.post("/api/casos-triaje/", payload, format="multipart")
    cola_id = ColaInterconsulta.objects.get(caso_id=response.data["id"]).id
    # el único especialista disponible al momento de crear el caso fue `especialista`
    assert ColaInterconsulta.objects.get(pk=cola_id).especialista_asignado_id == especialista.id

    response_resolver = api_client_otro.post(f"/api/cola-interconsulta/{cola_id}/resolver/")

    assert response_resolver.status_code == status.HTTP_403_FORBIDDEN
