# Especificación de Endpoints y Modelos para Pruebas (pytest) - Dermatriaje API

Este documento contiene la información técnica detallada de todos los endpoints, modelos, serializers y reglas de validación de la API en Django para la construcción de pruebas automatizadas con `pytest`.

---

## 1. Resumen de URLs y Nombres para `reverse()`

Los endpoints REST de la aplicación **`interconsulta`** están montados bajo el prefijo `/api/` mediante un `DefaultRouter` de Django REST Framework (DRF):

| Método HTTP | Ruta de la API | Nombre para `reverse()` | Vista / Archivo |
| :--- | :--- | :--- | :--- |
| `GET`, `POST` | `/api/establecimientos/` | `reverse('establecimientosalud-list')` | `EstablecimientoSaludViewSet` (`interconsulta/views.py`) |
| `GET`, `PUT`, `PATCH`, `DELETE` | `/api/establecimientos/{id}/` | `reverse('establecimientosalud-detail', kwargs={'pk': id})` | `EstablecimientoSaludViewSet` (`interconsulta/views.py`) |
| `GET`, `POST` | `/api/profesionales/` | `reverse('profesional-list')` | `ProfesionalViewSet` (`interconsulta/views.py`) |
| `GET`, `PUT`, `PATCH`, `DELETE` | `/api/profesionales/{id}/` | `reverse('profesional-detail', kwargs={'pk': id})` | `ProfesionalViewSet` (`interconsulta/views.py`) |
| `GET`, `POST` | `/api/pacientes/` | `reverse('paciente-list')` | `PacienteViewSet` (`interconsulta/views.py`) |
| `GET`, `PUT`, `PATCH`, `DELETE` | `/api/pacientes/{id}/` | `reverse('paciente-detail', kwargs={'pk': id})` | `PacienteViewSet` (`interconsulta/views.py`) |
| `GET`, `POST` | `/api/casos-triaje/` | `reverse('casotriaje-list')` | `CasoTriajeViewSet` (`interconsulta/views.py`) |
| `GET`, `PUT`, `PATCH`, `DELETE` | `/api/casos-triaje/{id}/` | `reverse('casotriaje-detail', kwargs={'pk': id})` | `CasoTriajeViewSet` (`interconsulta/views.py`) |
| `GET`, `POST` | `/api/cola-interconsulta/` | `reverse('colainterconsulta-list')` | `ColaInterconsultaViewSet` (`interconsulta/views.py`) |
| `GET`, `PUT`, `PATCH`, `DELETE` | `/api/cola-interconsulta/{id}/` | `reverse('colainterconsulta-detail', kwargs={'pk': id})` | `ColaInterconsultaViewSet` (`interconsulta/views.py`) |
| `POST` | `/api/auth/login/` | Ruta directa: `'/api/auth/login/'` | `obtain_auth_token` (`rest_framework.authtoken.views`) |

---

## 2. Detalle de los Endpoints API

### A. Endpoint `/api/pacientes/`

- **Serializer:** `PacienteSerializer` en `interconsulta/serializers.py`
- **Modelo:** `Paciente` (`interconsulta/models.py`)

#### `Model.objects.create()` para pruebas:
```python
from interconsulta.models import Paciente

paciente = Paciente.objects.create(
    tipo_documento='DNI',
    numero_documento='12345678',
    nombres='Juan',
    apellidos='Pérez',
    edad=45,
    sexo='M'
)
```

#### Request Body esperado (`POST /api/pacientes/`):
```json
{
  "tipo_documento": "DNI",
  "numero_documento": "12345678",
  "nombres": "Juan",
  "apellidos": "Pérez",
  "edad": 45,
  "sexo": "M"
}
```
*Campos obligatorios:* `numero_documento`, `nombres`, `apellidos`, `edad`, `sexo`.
- `tipo_documento` (opcional, opciones: `'DNI'`, `'CE'`, por defecto `'DNI'`).
- `sexo` (opciones: `'M'`, `'F'`, `'OTRO'`).
- `edad` (entero no negativo).

#### Respuesta exitosa (`201 Created`):
```json
{
  "id": 1,
  "tipo_documento": "DNI",
  "numero_documento": "12345678",
  "nombres": "Juan",
  "apellidos": "Pérez",
  "edad": 45,
  "sexo": "M",
  "creado_en": "2026-09-05T10:00:00.000000Z"
}
```

#### Validaciones del serializer (`400 Bad Request`):
1. **Formato DNI:** Si `tipo_documento='DNI'`, el `numero_documento` **debe tener exactamente 8 dígitos numéricos**.
   - Error: `{"numero_documento": ["El DNI debe tener exactamente 8 dígitos."]}`
2. **Formato CE:** Si `tipo_documento='CE'`, el `numero_documento` **debe tener entre 8 y 12 caracteres alfanuméricos**.
   - Error: `{"numero_documento": ["El Carné de Extranjería debe tener entre 8 y 12 caracteres alfanuméricos."]}`
3. **Documento duplicado:** La combinación (`tipo_documento`, `numero_documento`) es **única**.
   - Error: `{"non_field_errors": ["Los campos tipo_documento, numero_documento deben formar un conjunto único."]}`

---

### B. Endpoint `/api/establecimientos/`

- **Serializer:** `EstablecimientoSaludSerializer`
- **Modelo:** `EstablecimientoSalud` (`interconsulta/models.py`)

#### `Model.objects.create()` para pruebas:
```python
from interconsulta.models import EstablecimientoSalud

establecimiento = EstablecimientoSalud.objects.create(
    nombre='Centro de Salud Chachapoyas',
    codigo_renaes='12345',
    nivel='I-1',
    departamento='Amazonas',
    provincia='Chachapoyas',
    distrito='Chachapoyas',
    tiene_conectividad_estable=True
)
```

#### Request Body esperado (`POST /api/establecimientos/`):
```json
{
  "nombre": "Centro de Salud Chachapoyas",
  "codigo_renaes": "12345",
  "nivel": "I-1",
  "departamento": "Amazonas",
  "provincia": "Chachapoyas",
  "distrito": "Chachapoyas",
  "tiene_conectividad_estable": true
}
```
*Campos obligatorios:* `nombre`, `nivel`, `departamento`, `provincia`, `distrito`.
- `nivel` (opciones: `'I-1'`, `'I-2'`, `'I-3'`, `'I-4'`).
- `codigo_renaes` (opcional, string).
- `tiene_conectividad_estable` (opcional, booleano, por defecto `false`).

#### Respuesta exitosa (`201 Created`):
```json
{
  "id": 1,
  "nombre": "Centro de Salud Chachapoyas",
  "codigo_renaes": "12345",
  "nivel": "I-1",
  "departamento": "Amazonas",
  "provincia": "Chachapoyas",
  "distrito": "Chachapoyas",
  "tiene_conectividad_estable": true,
  "creado_en": "2026-09-05T10:00:00.000000Z"
}
```

---

### C. Endpoint `/api/profesionales/`

- **Serializer:** `ProfesionalSerializer`
- **Modelo:** `Profesional` (`interconsulta/models.py`)

#### `Model.objects.create()` para pruebas:
```python
from django.contrib.auth.models import User
from interconsulta.models import Profesional, EstablecimientoSalud

user = User.objects.create_user(username='medico1', password='pass123')
# Nota: La signal post_save en interconsulta/signals.py crea un Profesional automático con rol='MEDICO_GENERAL'.
# Si deseas obtenerlo o crearlo explícitamente:
profesional = getattr(user, 'profesional', None) or Profesional.objects.create(
    user=user,
    rol='MEDICO_GENERAL',
    establecimiento=establecimiento,
    especialidad='Dermatología'
)
```

#### Request Body esperado (`POST /api/profesionales/`):
```json
{
  "user": 1,
  "rol": "MEDICO_GENERAL",
  "establecimiento": 1,
  "especialidad": "Dermatología"
}
```
*Campos obligatorios:* `user`, `rol`.
- `user` (ID entero del modelo `User`).
- `rol` (opciones: `'MEDICO_GENERAL'`, `'SERUMISTA'`, `'ESPECIALISTA'`).
- `establecimiento` (opcional, ID entero de `EstablecimientoSalud`).
- `especialidad` (opcional, string).

#### Validaciones (`400 Bad Request`):
- `user` no existe o el `User` ya tiene un perfil profesional asociado (`OneToOneField` único).

---

### D. Endpoint `/api/casos-triaje/`

- **Serializer:** `CasoTriajeSerializer`
- **Modelo:** `CasoTriaje` (`interconsulta/models.py`)

#### `Model.objects.create()` para pruebas:
```python
from interconsulta.models import CasoTriaje

caso = CasoTriaje.objects.create(
    paciente=paciente,
    profesional_creador=profesional,
    establecimiento=establecimiento,
    tipo_lesion_predicho='mel',
    confianza_modelo=0.92,
    probabilidades_top3=[{"tipo": "mel", "confianza": 0.92}, {"tipo": "nv", "confianza": 0.05}],
    clasificacion_riesgo='ALTO',
    estado='REGISTRADO',
    notas_clinicas='Lesión sospechosa en brazo derecho'
)
```

#### Request Body esperado (`POST /api/casos-triaje/`):
```json
{
  "paciente": 1,
  "profesional_creador": 1,
  "establecimiento": 1,
  "tipo_lesion_predicho": "mel",
  "confianza_modelo": 0.92,
  "probabilidades_top3": [
    {"tipo": "mel", "confianza": 0.92},
    {"tipo": "nv", "confianza": 0.05}
  ],
  "clasificacion_riesgo": "ALTO",
  "estado": "REGISTRADO",
  "notas_clinicas": "Lesión sospechosa en brazo derecho"
}
```

*Campos obligatorios:* `paciente` (ID), `profesional_creador` (ID), `establecimiento` (ID), `tipo_lesion_predicho`, `confianza_modelo`, `clasificacion_riesgo`.
- `tipo_lesion_predicho` (opciones: `'akiec'`, `'bcc'`, `'bkl'`, `'df'`, `'mel'`, `'nv'`, `'vasc'`).
- `confianza_modelo` (float entre `0.0` y `1.0`).
- `clasificacion_riesgo` (opciones: `'BAJO'`, `'MEDIO'`, `'ALTO'`).
- `estado` (opciones: `'REGISTRADO'`, `'RESUELTO_LOCAL'`, `'EN_COLA_INTERCONSULTA'`, por defecto `'REGISTRADO'`).

#### Campo Read-Only calculado automáticamente:
- **`riesgo_sugerido`**: Devuelve automáticamente el nivel de riesgo recomendado por el tipo de lesión:
  - `'mel'`, `'bcc'`, `'akiec'` -> `'ALTO'`
  - `'bkl'` -> `'MEDIO'`
  - `'nv'`, `'df'`, `'vasc'` -> `'BAJO'`

#### Respuesta exitosa (`201 Created`):
```json
{
  "id": 1,
  "riesgo_sugerido": "ALTO",
  "fecha_evaluacion": "2026-09-05T10:00:00.000000Z",
  "tipo_lesion_predicho": "mel",
  "confianza_modelo": 0.92,
  "probabilidades_top3": [
    {"tipo": "mel", "confianza": 0.92},
    {"tipo": "nv", "confianza": 0.05}
  ],
  "modelo_version": "skin-lesion-classifier-mobilenet-ham10000-tfjs",
  "clasificacion_riesgo": "ALTO",
  "estado": "REGISTRADO",
  "fecha_resolucion": null,
  "notas_clinicas": "Lesión sospechosa en brazo derecho",
  "actualizado_en": "2026-09-05T10:00:00.000000Z",
  "paciente": 1,
  "profesional_creador": 1,
  "establecimiento": 1,
  "profesional_resuelve": null
}
```

---

### E. Endpoint `/api/cola-interconsulta/`

- **Serializer:** `ColaInterconsultaSerializer`
- **Modelo:** `ColaInterconsulta` (`interconsulta/models.py`)

#### `Model.objects.create()` para pruebas:
```python
from interconsulta.models import ColaInterconsulta

cola = ColaInterconsulta.objects.create(
    caso=caso,
    prioridad='URGENTE',
    estado='EN_ESPERA'
)
```

#### Request Body esperado (`POST /api/cola-interconsulta/`):
```json
{
  "caso": 1,
  "prioridad": "URGENTE",
  "especialista_asignado": null,
  "estado": "EN_ESPERA",
  "observaciones_especialista": ""
}
```
*Campos obligatorios:* `caso` (ID de `CasoTriaje`), `prioridad`.
- `prioridad` (opciones: `'URGENTE'`, `'ALTA'`, `'MEDIA'`).
- `estado` (opciones: `'EN_ESPERA'`, `'EN_ATENCION'`, `'RESUELTO'`, `'CANCELADO'`, por defecto `'EN_ESPERA'`).
- `especialista_asignado` (opcional, ID del `Profesional` con `rol='ESPECIALISTA'`).

#### Validaciones (`400 Bad Request`):
- `caso` es un `OneToOneField`. Si el caso ya existe en la cola de interconsulta, retorna error de unicidad.

---

### F. Endpoint Autenticación Token (`POST /api/auth/login/`)

#### Request Body:
```json
{
  "username": "medico1",
  "password": "pass123"
}
```

#### Respuesta exitosa (`200 OK`):
```json
{
  "token": "9944b09199c62bcf9418ad846d0d4bbd60ee479d"
}
```

#### Error de autenticación (`400 Bad Request`):
```json
{
  "non_field_errors": ["Unable to log in with provided credentials."]
}
```

---

## 3. Vistas Web Tradicionales (App `core`)

- `GET /` (`reverse('index')`): Renderiza `core/index.html`. Requiere autenticación (`@login_required`). Si no está autenticado, devuelve `302 Found` (Redirige a `/login/?next=/`).
- `GET, POST /login/` (`reverse('login')`): Vista de inicio de sesión web con HTML.
- `GET, POST /registro/` (`reverse('register')`): Vista de registro de usuario con `UserCreationForm`.
- `GET /logout/` (`reverse('logout')`): Cierra sesión y redirige a `/login/`.
