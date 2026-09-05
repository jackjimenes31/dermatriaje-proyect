# DermaTriaje API & PWA

[![CI](https://github.com/jackjimenes31/dermatriaje-api/actions/workflows/ci.yml/badge.svg)](https://github.com/jackjimenes31/dermatriaje-api/actions)
![Python](https://img.shields.io/badge/Python-3.13-blue.svg)
![Django](https://img.shields.io/badge/Django-6.1-green.svg)
![DRF](https://img.shields.io/badge/Django_REST_Framework-3.18-red.svg)
![Testing](https://img.shields.io/badge/PyTest-13%2F13_Passed-success.svg)
![Deploy](https://img.shields.io/badge/Deploy-Render_Active-brightgreen.svg)

**DermaTriaje** es una Progressive Web App (PWA) de tele-interconsulta y triaje dermatológico asistido por Inteligencia Artificial (*Edge AI*, offline-first) diseñada para el personal de salud del primer nivel de atención en Perú (postas y centros de salud I-1 a I-4).

El sistema ejecuta el modelo de clasificación de lesiones en el navegador del usuario garantizando privacidad y resiliencia sin conectividad, y sincroniza los casos clínicos hacia un backend Django con una cola digital de interconsulta para especialistas.

---

## 📌 Entregables Oficiales

* 🌐 **URL de Producción Activa:** [https://dermatriaje-proyect.onrender.com/](https://dermatriaje-proyect.onrender.com/)
* 📊 **Deck de Presentación (Pitch):** [`docs/pitch.pdf`](docs/pitch.pdf)
* 📋 **Especificación Técnica de la API:** [`endpoints_spec.md`](endpoints_spec.md)
* 🧪 **Suite de Pruebas Automáticas (Testing Core):** [`test/`](test/) (13/13 pruebas aprobadas)

---

## 🏗️ Arquitectura del Sistema

* **Backend:** Django 6.1 + Django REST Framework + Gunicorn + WhiteNoise.
* **Base de Datos:** SQLite en local, compatible con PostgreSQL en producción mediante la variable de entorno `DATABASE_URL` (vía `django-environ`).
* **Frontend / PWA:** Renderizado por Django (`core`), HTML5 semántico, CSS responsivo y Service Worker con soporte offline (*cache-first / fallback*).
* **Inteligencia Artificial (Edge AI):** Clasificador [Skin-Lesion-Classifier](https://github.com/uyxela/Skin-Lesion-Classifier) basado en MobileNet reentrenado sobre HAM10000 (7 clases de lesiones cutáneas), convertido a TensorFlow.js. Se ejecuta al 100% en el cliente, protegiendo la privacidad del paciente y operando aun sin conexión a internet.
* **Autenticación:**
  * **Sesión Web:** Login/Registro estándar para el flujo de la PWA.
  * **Token DRF:** `POST /api/auth/login/` con `TokenAuthentication` para integración de clientes externos.
* **Integración Continua:** GitHub Actions (`.github/workflows/ci.yml`) ejecutando la suite completa de pruebas en cada `push` y `pull request`.

---

## 📂 Estructura del Repositorio

```text
dermatriaje-api/
├── .github/workflows/ci.yml   # Pipeline de Integración Continua (GitHub Actions)
├── core/                      # PWA shell, autenticación web, templates y vistas
├── dermatriaje/               # Configuración del proyecto (settings, urls, wsgi)
├── docs/                      # Entregables anexos (pitch.pdf)
├── interconsulta/             # Dominio clínico: modelos, serializers, vistas y signals
├── static/                    # Archivos estáticos, Service Worker y modelo TF.js HAM10000
├── test/                      # Suite de pruebas automatizadas (pytest)
│   ├── test_integration.py   # Pruebas de integración E2E (Happy path y Errores críticos)
│   ├── test_unit.py          # Pruebas unitarias de modelos y validaciones
│   └── test_setup.py         # Smoke test del entorno de pruebas
├── endpoints_spec.md          # Especificación detallada de endpoints, payloads y respuestas
├── manage.py                  # CLI de gestión de Django
├── Procfile                   # Definición del proceso de ejecución para producción (Gunicorn)
├── pytest.ini                 # Configuración de PyTest y Django Settings
└── requirements.txt           # Dependencias de producción y testing
```

---

## 🧪 Testing Core (Pruebas Automáticas)

El proyecto cuenta con una suite rigurosa de **13 pruebas automatizadas** que validan tanto el comportamiento esperado como la robustez ante fallos críticos:

### 1. Camino Feliz (Happy Path)
* **Creación de Paciente:** Registro vía API (`POST /api/pacientes/`) con datos válidos, validando persistencia y código de estado `201 Created`.
* **Registro de Caso de Triaje con IA:** Creación de caso (`POST /api/casos-triaje/`) con predicción del modelo y validación del cálculo automático del campo calculado `riesgo_sugerido` (`mel` ➔ `ALTO`).

### 2. Casos de Error Crítico
* **Validación Estricta de Documento de Identidad:** Rechazo con `HTTP 400 Bad Request` ante DNIs que no cumplan con exactamente 8 dígitos numéricos o Carnés de Extranjería inválidos, impidiendo la corrupción de la identidad clínica.
* **Integridad Referencial (Paciente Inexistente):** Rechazo con `HTTP 400 Bad Request` al intentar registrar un caso de triaje asociado a un paciente que no existe, evitando casos clínicos huérfanos.

### 3. Pruebas Unitarias de Lógica de Negocio
* Validación del método `clean()` de los modelos de pacientes bajo expresiones regulares.
* Mapeo del riesgo sugerido por tipo de lesión (`mel`, `bcc`, `akiec` ➔ `ALTO`, `bkl` ➔ `MEDIO`, `nv`, `df`, `vasc` ➔ `BAJO`).
* Creación reactiva del perfil `Profesional` tras el registro de usuarios mediante `post_save signals`.

### Ejecución de Pruebas:
```bash
# Ejecutar toda la suite con detalle:
pytest -v

# Ejecutar con reporte de cobertura de código:
pytest --cov=interconsulta --cov=core
```

---

## 🚀 Puesta en Marcha Local

### Prerrequisitos
* Python 3.13+ instalado.
* Git.

### Pasos:

1. **Clonar el repositorio:**
   ```bash
   git clone https://github.com/jackjimenes31/dermatriaje-api.git
   cd dermatriaje-api
   ```

2. **Crear y activar el entorno virtual:**
   ```bash
   # En Windows:
   python -m venv venv
   .\venv\Scripts\activate

   # En Linux / macOS:
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Variables de entorno:**
   ```bash
   # Copiar la plantilla de configuración
   cp .env.example .env     # Linux / macOS
   copy .env.example .env   # Windows
   ```

5. **Aplicar migraciones y crear superusuario:**
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```

6. **Iniciar el servidor de desarrollo:**
   ```bash
   python manage.py runserver
   ```
   Accede a la aplicación en: `http://127.0.0.1:8000/`.

---

## 🌐 Despliegue en Producción (Render)

El repositorio está configurado y optimizado para despliegue continuo en la nube con **Render**:

* **Procfile:**
  ```text
  web: gunicorn dermatriaje.wsgi:application
  ```
* **Build Command:**
  ```bash
  pip install -r requirements.txt && python manage.py collectstatic --no-input && python manage.py migrate
  ```
* **Start Command:**
  ```bash
  gunicorn dermatriaje.wsgi:application
  ```
* **Archivos Estáticos:** Servidos y comprimidos en producción mediante `WhiteNoise` (`CompressedManifestStaticFilesStorage`).
* **Variables de Entorno Clave:**
  * `DEBUG=False`
  * `SECRET_KEY=<tu_clave_segura>`
  * `ALLOWED_HOSTS=.onrender.com,localhost,127.0.0.1`

---

## 📡 Resumen de Endpoints Principales

Todos los endpoints REST se encuentran bajo `/api/` y requieren autenticación (`Token` o sesión activa):

| Método | Endpoint | Descripción |
|---|---|---|
| `POST` | `/api/auth/login/` | Autenticación y obtención de token de acceso |
| `GET`, `POST` | `/api/pacientes/` | Listado y registro de pacientes con validación de documento |
| `GET`, `POST` | `/api/casos-triaje/` | Registro de triajes asistidos por IA y evaluación de riesgo |
| `GET`, `POST` | `/api/cola-interconsulta/` | Gestión de la cola de tele-interconsulta hacia especialistas |
| `GET`, `POST` | `/api/establecimientos/` | Centros de salud y postas del primer nivel |
| `GET`, `POST` | `/api/profesionales/` | Perfiles de médicos generales, serumistas y especialistas |

Para el detalle completo de campos, validaciones y ejemplos JSON, consulta [`endpoints_spec.md`](endpoints_spec.md).
