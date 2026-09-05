# DermaTriaje

Progressive Web App (PWA) que clasifica lesiones cutáneas a partir de una fotografía, pensada para el personal de salud del primer nivel de atención en Perú (postas y centros de salud). El modelo de IA corre en el navegador (Edge AI, offline-first) y los casos se registran en un backend Django con una cola digital de interconsulta hacia especialistas.

## Stack

- **Backend**: Django 6.1.1 + Django REST Framework
- **Base de datos**: SQLite por defecto, configurable a Postgres vía la variable de entorno `DATABASE_URL` (usando `django-environ`)
- **Autenticación**: sesión (login web) y token (DRF `TokenAuthentication`) para la API
- **Frontend**: PWA renderizada por Django (app `core`), con manifest y Service Worker offline-first
- **IA**: [Skin-Lesion-Classifier](https://github.com/uyxela/Skin-Lesion-Classifier) (MobileNet reentrenado sobre HAM10000, 7 clases), convertido a TensorFlow.js y ejecutado 100% en el navegador
- **Tests**: pytest + pytest-django
- **CI**: GitHub Actions

## Estructura del proyecto

```
dermatriaje/       Configuración del proyecto (settings, urls, pytest.ini)
core/               PWA shell, login/registro/logout, manifest y service worker
interconsulta/      Dominio clínico: modelos, API REST y admin
static/             CSS, JS, iconos, manifest, service worker y el modelo TF.js
test/               Suite de pytest a nivel de proyecto
```

## Apps de Django

### `core`

Shell de la PWA y autenticación de usuarios (médicos/serumistas):

- `/` — pantalla principal (requiere login): captura/subida de foto, clasificación con IA y registro del caso.
- `/login/`, `/registro/`, `/logout/` — autenticación por sesión con los formularios estándar de Django.
- `/offline/` — página de respaldo cuando no hay conexión (usada por el service worker).

Al registrarse un usuario nuevo, una señal en `interconsulta` le crea automáticamente un perfil `Profesional` (rol `MEDICO_GENERAL` por defecto).

### `interconsulta`

Dominio clínico y API REST:

- **`EstablecimientoSalud`** — posta/centro de salud (nivel I-1 a I-4, ubicación).
- **`Profesional`** — perfil asociado a `auth.User` (rol: médico general, serumista o especialista; establecimiento).
- **`Paciente`** — identidad del paciente (DNI o Carné de Extranjería, con validación de formato; nombres/apellidos; edad; sexo).
- **`CasoTriaje`** — un caso de triaje: tipo de lesión predicho por el modelo (una de las 7 clases de HAM10000), confianza, top-3 de predicciones, clasificación de riesgo confirmada, estado y quién resuelve el caso.
- **`ColaInterconsulta`** — cola de interconsulta hacia especialistas (prioridad, especialista asignado, estado).

## Instalación y ejecución local

```bash
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt

copy .env.example .env       # y ajusta valores si hace falta

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

La app queda disponible en `http://127.0.0.1:8000/`.

## Autenticación

- **Web (sesión)**: registrarse/loguearse en `/registro/` o `/login/`. Esta sesión ya sirve para llamar a la API desde la propia PWA (autenticación por cookie + CSRF).
- **API (token)**: `POST /api/auth/login/` con `username` y `password` devuelve un token para usar como header `Authorization: Token <token>`.

Todos los endpoints de `/api/` requieren autenticación (token o sesión).

## API REST

Expuesta bajo `/api/` mediante un `DefaultRouter` de DRF:

| Endpoint | Recurso |
|---|---|
| `/api/establecimientos/` | `EstablecimientoSalud` |
| `/api/profesionales/` | `Profesional` |
| `/api/pacientes/` | `Paciente` |
| `/api/casos-triaje/` | `CasoTriaje` |
| `/api/cola-interconsulta/` | `ColaInterconsulta` |

Todos soportan las operaciones estándar de un `ModelViewSet` (list, retrieve, create, update, delete).

## Clasificación con IA

En la pantalla principal (`/`), el flujo es:

1. Se toma o sube una foto de la lesión.
2. `static/js/triaje.js` carga el modelo TensorFlow.js (`static/models/skin-lesion/`) directamente en el navegador y corre la inferencia sobre la imagen — sin enviarla a ningún servidor.
3. Se muestra el tipo de lesión predicho, la confianza y el top-3 de predicciones del modelo.
4. Se completa un formulario con los datos del paciente y se guarda el caso vía la API (`/api/pacientes/` y `/api/casos-triaje/`), usando la sesión del profesional logueado.

## Tests

La configuración de pytest está en `dermatriaje/pytest.ini`. Desde la raíz del repo:

```bash
pytest
```

## CI

`.github/workflows/ci.yml` corre en cada push y pull request: instala las dependencias de `requirements.txt` y ejecuta `pytest` sobre Python 3.13.
