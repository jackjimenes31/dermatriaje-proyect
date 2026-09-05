# DermaTriaje API & PWA

[![CI](https://github.com/jackjimenes31/dermatriaje-api/actions/workflows/ci.yml/badge.svg)](https://github.com/jackjimenes31/dermatriaje-api/actions)
![Python](https://img.shields.io/badge/Python-3.13-blue.svg)
![Django](https://img.shields.io/badge/Django-6.1-green.svg)
![DRF](https://img.shields.io/badge/Django_REST_Framework-3.18-red.svg)
![Testing](https://img.shields.io/badge/PyTest-26%2F26_Passed-success.svg)
![Deploy](https://img.shields.io/badge/Deploy-Render_Active-brightgreen.svg)

**DermaTriaje** es una Progressive Web App (PWA) de tele-interconsulta y triaje dermatológico asistido por Inteligencia Artificial (*Edge AI*, offline-first) diseñada para el personal de salud del primer nivel de atención en Perú (postas y centros de salud I-1 a I-4).

El sistema ejecuta el modelo de clasificación de lesiones en el navegador del usuario garantizando privacidad y resiliencia sin conectividad, y sincroniza los casos clínicos hacia un backend Django con una cola digital de interconsulta para especialistas.

---

## 📌 Entregables Oficiales

* 🌐 **URL de Producción Activa:** [https://dermatriaje-proyect.onrender.com/](https://dermatriaje-proyect.onrender.com/)
* 📊 **Deck de Presentación (Pitch):** [`docs/pitch.md`](docs/pitch.md)
* 📋 **Especificación Técnica de la API:** [`endpoints_spec.md`](endpoints_spec.md)
* 🧪 **Suite de Pruebas Automáticas (Testing Core):** [`test/`](test/) (26/26 pruebas aprobadas)

---

## 🏗️ Arquitectura del Sistema

* **Backend:** Django 6.1 + Django REST Framework + Gunicorn + WhiteNoise.
* **Base de Datos:** SQLite en local, compatible con PostgreSQL en producción mediante la variable de entorno `DATABASE_URL` (vía `django-environ`).
* **Frontend / PWA:** Renderizado por Django (`core`), HTML5 semántico, CSS responsivo y Service Worker con soporte offline (*cache-first / fallback*).
* **Inteligencia Artificial (Edge AI):** Clasificador [Skin-Lesion-Classifier](https://github.com/uyxela/Skin-Lesion-Classifier) basado en MobileNet reentrenado sobre HAM10000 (7 clases de lesiones cutáneas), convertido a TensorFlow.js. Se ejecuta al 100% en el cliente, protegiendo la privacidad del paciente y operando aun sin conexión a internet.
* **Autenticación:**
  * **Sesión Web:** Login/Registro estándar para el flujo de la PWA.
  * **Token DRF:** `POST /api/auth/login/` con `TokenAuthentication` para integración de clientes externos.
* **Roles y flujos diferenciados:** cada `Profesional` tiene un rol (Médico General, Serumista o Especialista). Al loguearse, un médico general cae en `/` (captura y clasificación de casos) y un especialista es redirigido a `/especialista/` (bandeja de interconsulta priorizada, con vista de detalle por caso e imagen).
* **Cola de interconsulta:** los casos de riesgo ALTO/MEDIO se encolan automáticamente (signal de Django) con prioridad URGENTE/ALTA y se asignan al especialista con menor carga de trabajo; los casos de riesgo BAJO pueden resolverse localmente por el médico que los registró.
* **Integración Continua:** GitHub Actions (`.github/workflows/ci.yml`) ejecutando la suite completa de pruebas en cada `push` y `pull request`.

---

## 📂 Estructura del Repositorio

```text
dermatriaje-api/
├── .github/workflows/ci.yml   # Pipeline de Integración Continua (GitHub Actions)
├── core/                      # PWA shell, autenticación web, templates y vistas
├── dermatriaje/               # Configuración del proyecto (settings, urls, wsgi)
├── docs/                      # Entregables anexos (pitch.md)
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

El proyecto cuenta con una suite rigurosa de **26 pruebas automatizadas** que validan tanto el comportamiento esperado como la robustez ante fallos críticos, incluyendo el ciclo completo de la cola de interconsulta (encolamiento automático por riesgo, asignación por menor carga, orden por prioridad, permisos de atender/resolver) y la resolución local de casos de bajo riesgo.

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

5. **Aplicar migraciones y sembrar datos base:**
   ```bash
   python manage.py migrate
   python manage.py seed   # crea admin/admin123, establecimientos, un medico general
                           # y un especialista de ejemplo, y pacientes de ejemplo.
                           # Es idempotente: se puede correr las veces que sea.
   ```

6. **Iniciar el servidor de desarrollo:**
   ```bash
   python manage.py runserver
   ```
   Accede a la aplicación en: `http://127.0.0.1:8000/`.

### Cuentas de prueba (creadas por `python manage.py seed`)

| Usuario | Contraseña | Rol | Flujo al loguearse |
|---|---|---|---|
| `jack` | `jack123` | Médico general | `/` — capturar/clasificar una lesión y guardar el caso |
| `santiago` | `santiago123` | Especialista | `/especialista/` — bandeja de interconsulta priorizada |
| `admin` | `admin123` | Superusuario | `/admin/` — Django admin (gestión completa de datos) |

`jack` está asociado a la Posta de Salud San Juan y `santiago` al Hospital Regional del Cusco, así que un caso de riesgo ALTO/MEDIO creado por `jack` se autoencola y aparece directo en la bandeja de `santiago`.

---

## 🌐 Despliegue en Producción (Render)

El repositorio está configurado y optimizado para despliegue continuo en la nube con **Render**:

* **Procfile:** el proceso `web` corre `migrate` y crea/actualiza el superusuario `admin` antes de levantar Gunicorn (ver [`Procfile`](Procfile) para el comando exacto).
* **Build Command:**
  ```bash
  pip install -r requirements.txt && python manage.py collectstatic --no-input
  ```
* Para tener también los establecimientos, el médico general, el especialista y los pacientes de ejemplo en el ambiente desplegado, corre manualmente `python manage.py seed` (ver [Puesta en Marcha Local](#-puesta-en-marcha-local)) — hoy no está enganchado al Procfile.
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
| `GET` | `/api/pacientes/buscar/?tipo_documento=&numero_documento=` | Búsqueda de paciente por documento (DNI/CE) |
| `GET`, `POST` | `/api/casos-triaje/` | Registro de triajes asistidos por IA (imagen obligatoria, `multipart/form-data`) y evaluación de riesgo |
| `POST` | `/api/casos-triaje/{id}/resolver_local/` | El médico creador cierra en el mismo nivel un caso de riesgo bajo |
| `GET`, `POST` | `/api/cola-interconsulta/` | Gestión de la cola de tele-interconsulta, ordenada por prioridad |
| `GET` | `/api/cola-interconsulta/mia/` | Bandeja del especialista autenticado |
| `POST` | `/api/cola-interconsulta/{id}/atender/` | El especialista toma un caso de su bandeja |
| `POST` | `/api/cola-interconsulta/{id}/resolver/` | El especialista cierra la interconsulta con su diagnóstico |
| `GET`, `POST` | `/api/establecimientos/` | Centros de salud y postas del primer nivel |
| `GET`, `POST` | `/api/profesionales/` | Perfiles de médicos generales, serumistas y especialistas |

Para el detalle completo de campos, validaciones y ejemplos JSON, consulta [`endpoints_spec.md`](endpoints_spec.md).
