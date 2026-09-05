// Clasificacion de lesiones cutaneas (Edge AI, offline-first) con el modelo
// Skin-Lesion-Classifier (MobileNet retrenado sobre HAM10000, 7 clases).
// https://github.com/uyxela/Skin-Lesion-Classifier
//
// El orden de las 7 clases es el mismo con el que se entreno el modelo
// (alfabetico por codigo dx de HAM10000) y coincide con CasoTriaje.TipoLesion
// en el backend.
const TIPO_LESION_INFO = [
    { code: 'akiec', label: 'Queratosis actínica / enfermedad de Bowen', riesgo: 'ALTO' },
    { code: 'bcc', label: 'Carcinoma basocelular', riesgo: 'ALTO' },
    { code: 'bkl', label: 'Lesión queratósica benigna', riesgo: 'MEDIO' },
    { code: 'df', label: 'Dermatofibroma', riesgo: 'BAJO' },
    { code: 'mel', label: 'Melanoma', riesgo: 'ALTO' },
    { code: 'nv', label: 'Nevo melanocítico', riesgo: 'BAJO' },
    { code: 'vasc', label: 'Lesión vascular', riesgo: 'BAJO' },
];

// Copys/CTA por nivel de riesgo (siguiendo el prototipo de Figma).
const RISK_CONFIG = {
    BAJO: {
        emoji: '🟢',
        word: 'VERDE',
        sublabel: 'BAJO RIESGO',
        cssClass: 'riesgo-bajo',
        nextStepTitle: 'Manejo en primer nivel',
        nextStepDetail: 'Puede resolverse en este establecimiento. Registra el caso para mantener el historial del paciente.',
        ctaLabel: 'GUARDAR EVALUACIÓN',
        ctaClass: 'btn-primary',
        showAlert: false,
    },
    MEDIO: {
        emoji: '🟡',
        word: 'AMARILLO',
        sublabel: 'RIESGO INTERMEDIO',
        cssClass: 'riesgo-medio',
        nextStepTitle: 'Revisión clínica',
        nextStepDetail: 'Se recomienda seguimiento o revisión adicional antes de descartar el caso.',
        ctaLabel: 'GUARDAR Y REVISAR',
        ctaClass: 'btn-primary',
        showAlert: false,
    },
    ALTO: {
        emoji: '🔴',
        word: 'ROJO',
        sublabel: 'ALTO RIESGO',
        cssClass: 'riesgo-alto',
        nextStepTitle: 'Interconsulta priorizada',
        nextStepDetail: 'Este caso debe derivarse a un especialista con prioridad.',
        ctaLabel: 'DERIVAR Y GUARDAR CASO',
        ctaClass: 'btn-danger',
        showAlert: true,
    },
};

const MODEL_URL = '/static/models/skin-lesion/model.json';
const PENDING_KEY = 'dermatriaje_casos_pendientes';

let modelPromise = null;
let ultimoResultado = null;
let pacienteEncontrado = null;
let toastTimeout = null;

/* ============ Modelo / inferencia ============ */

function loadModel() {
    if (!modelPromise) {
        modelPromise = tf.loadLayersModel(MODEL_URL);
    }
    return modelPromise;
}

function preprocessImage(imgEl) {
    return tf.tidy(() => {
        const tensor = tf.browser.fromPixels(imgEl).resizeBilinear([224, 224]).toFloat();
        // Mismo preprocesamiento usado en el entrenamiento (keras.applications.mobilenet.preprocess_input): [-1, 1].
        const normalized = tensor.sub(127.5).div(127.5);
        return normalized.expandDims(0);
    });
}

/* ============ Utilidades de red ============ */

function getCookie(name) {
    const match = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
    return match ? decodeURIComponent(match[2]) : null;
}

async function apiFetch(url, options) {
    options = options || {};
    const headers = Object.assign(
        { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
        options.headers || {}
    );

    let response;
    try {
        response = await fetch(url, Object.assign({ credentials: 'same-origin' }, options, { headers }));
    } catch (networkErr) {
        const error = new Error('network_error');
        error.isNetworkError = true;
        throw error;
    }

    const data = await response.json().catch(() => null);
    if (!response.ok) {
        const error = new Error('api_error');
        error.data = data;
        error.status = response.status;
        throw error;
    }
    return data;
}

/* ============ Navegacion entre pantallas ============ */

function mostrarPantalla(id) {
    ['homeScreen', 'analyzingScreen', 'resultScreen'].forEach((sid) => {
        const el = document.getElementById(sid);
        if (el) el.style.display = sid === id ? 'block' : 'none';
    });
}

/* ============ Badge de conexion (nunca alarmante, sigue el tono del Figma) ============ */

function actualizarConexion() {
    const text = document.getElementById('connectionBadgeText');
    if (!text) return;
    text.textContent = navigator.onLine ? 'EN LÍNEA' : 'SIN CONEXIÓN · IA ACTIVA';
}

/* ============ Toast ============ */

function mostrarToast(titulo, subtitulo) {
    const toast = document.getElementById('toast');
    if (!toast) return;
    document.getElementById('toastTitle').textContent = titulo;
    document.getElementById('toastSubtitle').textContent = subtitulo || '';
    toast.hidden = false;
    if (toastTimeout) clearTimeout(toastTimeout);
    toastTimeout = setTimeout(() => { toast.hidden = true; }, 3200);
}

/* ============ Cola offline (guardado local + reintento) ============ */

function leerColaPendientes() {
    try {
        return JSON.parse(localStorage.getItem(PENDING_KEY)) || [];
    } catch (err) {
        return [];
    }
}

function guardarColaPendientes(cola) {
    try {
        localStorage.setItem(PENDING_KEY, JSON.stringify(cola));
    } catch (err) {
        // almacenamiento no disponible (modo privado, cuota llena, etc.): el caso ya quedo mostrado como guardado localmente
    }
}

function encolarCasoPendiente(payload) {
    const cola = leerColaPendientes();
    cola.push(payload);
    guardarColaPendientes(cola);
}

async function sincronizarPendientes() {
    const cola = leerColaPendientes();
    if (cola.length === 0) return;

    const restantes = [];
    for (const payload of cola) {
        try {
            await apiFetch('/api/casos-triaje/', { method: 'POST', body: JSON.stringify(payload) });
        } catch (err) {
            restantes.push(payload);
        }
    }
    guardarColaPendientes(restantes);

    const sincronizados = cola.length - restantes.length;
    if (sincronizados > 0) {
        mostrarToast('Casos sincronizados', `${sincronizados} caso(s) pendiente(s) se enviaron correctamente.`);
        const guardarBtn = document.getElementById('guardarCasoBtn');
        if (guardarBtn) cargarUltimasEvaluaciones(guardarBtn.dataset.profesionalId);
    }
}

/* ============ Establecimientos ============ */

async function cargarEstablecimientos(preferidoId) {
    const select = document.getElementById('establecimientoCaso');
    if (!select) return;
    try {
        const data = await apiFetch('/api/establecimientos/');
        select.innerHTML = data.map((e) => `<option value="${e.id}">${e.nombre} (${e.nivel})</option>`).join('');
        if (preferidoId && data.some((e) => String(e.id) === String(preferidoId))) {
            select.value = preferidoId;
        }
    } catch (err) {
        select.innerHTML = '<option value="">No se pudieron cargar los establecimientos</option>';
    }
}

/* ============ Ultimas evaluaciones ============ */

function tiempoRelativo(fechaIso) {
    const minutos = Math.round((Date.now() - new Date(fechaIso).getTime()) / 60000);
    if (minutos < 1) return 'ahora';
    if (minutos < 60) return `hace ${minutos} min`;
    const horas = Math.round(minutos / 60);
    if (horas < 24) return `hace ${horas} h`;
    return `hace ${Math.round(horas / 24)} d`;
}

async function cargarUltimasEvaluaciones(profesionalId) {
    const list = document.getElementById('recentList');
    if (!list || !profesionalId) return;

    try {
        const casos = await apiFetch('/api/casos-triaje/');
        const propios = casos
            .filter((c) => String(c.profesional_creador) === String(profesionalId))
            .sort((a, b) => new Date(b.fecha_evaluacion) - new Date(a.fecha_evaluacion))
            .slice(0, 5);

        if (propios.length === 0) {
            list.innerHTML = '<p class="text-muted" style="font-size:var(--font-size-sm);">Aún no tienes evaluaciones registradas.</p>';
            return;
        }

        list.innerHTML = propios
            .map((c) => {
                const info = TIPO_LESION_INFO.find((t) => t.code === c.tipo_lesion_predicho);
                const riesgoClase = 'riesgo-' + c.clasificacion_riesgo.toLowerCase();
                return `
                    <div class="recent-item">
                        <span class="recent-dot ${riesgoClase}"></span>
                        <span class="recent-label">${info ? info.label : c.tipo_lesion_predicho}</span>
                        <span class="recent-time">${tiempoRelativo(c.fecha_evaluacion)}</span>
                        <span class="recent-badge ${riesgoClase}">${c.clasificacion_riesgo}</span>
                    </div>`;
            })
            .join('');
    } catch (err) {
        list.innerHTML = '<p class="text-muted" style="font-size:var(--font-size-sm);">No se pudieron cargar las evaluaciones recientes.</p>';
    }
}

/* ============ Resultado del analisis ============ */

function renderResultados(ranked) {
    ultimoResultado = ranked;
    pacienteEncontrado = null;

    const top = ranked[0];
    const config = RISK_CONFIG[top.riesgo];

    const riskCard = document.getElementById('riskCard');
    riskCard.className = 'risk-card ' + config.cssClass;
    document.getElementById('riskEmoji').textContent = config.emoji;
    document.getElementById('riskWord').textContent = config.word;
    document.getElementById('riskSublabel').textContent = config.sublabel;

    document.getElementById('resultLabel').textContent = top.label;
    const porcentaje = (top.confianza * 100).toFixed(0);
    document.getElementById('resultConfidenceText').textContent = porcentaje + '%';
    const fill = document.getElementById('confidenceBarFill');
    fill.className = 'confidence-bar-fill ' + config.cssClass;
    fill.style.width = porcentaje + '%';

    document.getElementById('top3List').textContent =
        'Top 3: ' + ranked.slice(0, 3).map((r) => `${r.label} (${(r.confianza * 100).toFixed(1)}%)`).join(' · ');

    const nextStepCard = document.getElementById('nextStepCard');
    nextStepCard.className = 'card card-glass next-step-card ' + config.cssClass;
    document.getElementById('nextStepTitle').textContent = config.nextStepTitle;
    document.getElementById('nextStepDetail').textContent = config.nextStepDetail;
    document.getElementById('alertBanner').style.display = config.showAlert ? 'flex' : 'none';

    const guardarBtn = document.getElementById('guardarCasoBtn');
    guardarBtn.textContent = config.ctaLabel;
    guardarBtn.className = 'btn btn-full ' + config.ctaClass;
    guardarBtn.disabled = true;

    document.getElementById('patientResult').style.display = 'none';
    document.getElementById('numeroDocumento').value = '';
    document.getElementById('saveCaseMessage').style.display = 'none';
}

/* ============ Buscar paciente por documento ============ */

async function buscarPaciente() {
    const tipo = document.getElementById('tipoDocumento').value;
    const numero = document.getElementById('numeroDocumento').value.trim();
    const resultDiv = document.getElementById('patientResult');
    const guardarBtn = document.getElementById('guardarCasoBtn');

    if (!numero) {
        pacienteEncontrado = null;
        resultDiv.textContent = 'Ingresa un número de documento.';
        resultDiv.className = 'patient-result not-found';
        resultDiv.style.display = 'block';
        guardarBtn.disabled = true;
        return;
    }

    try {
        const paciente = await apiFetch(
            `/api/pacientes/buscar/?tipo_documento=${encodeURIComponent(tipo)}&numero_documento=${encodeURIComponent(numero)}`
        );
        pacienteEncontrado = paciente;
        resultDiv.textContent = `✓ ${paciente.nombres} ${paciente.apellidos}`;
        resultDiv.className = 'patient-result';
        resultDiv.style.display = 'block';
        guardarBtn.disabled = false;
    } catch (err) {
        pacienteEncontrado = null;
        resultDiv.textContent = 'Paciente no encontrado. Verifica el documento.';
        resultDiv.className = 'patient-result not-found';
        resultDiv.style.display = 'block';
        guardarBtn.disabled = true;
    }
}

/* ============ Guardar caso ============ */

function mostrarMensajeGuardado(texto) {
    const msg = document.getElementById('saveCaseMessage');
    msg.textContent = texto;
    msg.style.display = 'block';
}

function volverAHomeTrasGuardar(profesionalId) {
    mostrarPantalla('homeScreen');
    document.getElementById('previewSection').style.display = 'none';
    document.getElementById('uploadZone').style.display = 'block';
    document.getElementById('imageInput').value = '';
    cargarUltimasEvaluaciones(profesionalId);
}

async function guardarCaso() {
    const btn = document.getElementById('guardarCasoBtn');
    document.getElementById('saveCaseMessage').style.display = 'none';

    const profesionalId = btn.dataset.profesionalId;
    const establecimientoId = document.getElementById('establecimientoCaso').value;

    if (!profesionalId) {
        mostrarMensajeGuardado('Tu usuario no tiene un perfil de profesional asociado.');
        return;
    }
    if (!pacienteEncontrado) {
        mostrarMensajeGuardado('Busca un paciente por su documento antes de guardar.');
        return;
    }
    if (!establecimientoId) {
        mostrarMensajeGuardado('Selecciona un establecimiento.');
        return;
    }
    if (!ultimoResultado) {
        mostrarMensajeGuardado('Primero analiza una imagen con IA.');
        return;
    }

    const top = ultimoResultado[0];
    const payload = {
        paciente: pacienteEncontrado.id,
        profesional_creador: parseInt(profesionalId, 10),
        establecimiento: parseInt(establecimientoId, 10),
        tipo_lesion_predicho: top.code,
        confianza_modelo: top.confianza,
        probabilidades_top3: ultimoResultado.slice(0, 3).map((r) => ({ tipo: r.code, confianza: r.confianza })),
        clasificacion_riesgo: top.riesgo,
        notas_clinicas: document.getElementById('notasClinicas').value,
    };

    const textoOriginal = btn.textContent;
    btn.disabled = true;
    btn.textContent = 'Guardando...';

    try {
        const caso = await apiFetch('/api/casos-triaje/', { method: 'POST', body: JSON.stringify(payload) });
        mostrarToast('Caso guardado correctamente', `Caso #${caso.id} · guardado y sincronizado`);
        volverAHomeTrasGuardar(profesionalId);
    } catch (err) {
        if (err.isNetworkError || !navigator.onLine) {
            encolarCasoPendiente(payload);
            mostrarToast('Caso priorizado', 'Guardado localmente · se enviará cuando haya conexión');
            volverAHomeTrasGuardar(profesionalId);
        } else {
            mostrarMensajeGuardado(err.data ? JSON.stringify(err.data) : 'Ocurrió un error al guardar el caso.');
            btn.disabled = false;
            btn.textContent = textoOriginal;
        }
    }
}

/* ============ Inicializacion ============ */

document.addEventListener('DOMContentLoaded', () => {
    actualizarConexion();
    window.addEventListener('online', actualizarConexion);
    window.addEventListener('offline', actualizarConexion);
    window.addEventListener('online', sincronizarPendientes);

    // ---- Captura / subida de imagen ----
    const uploadZone = document.getElementById('uploadZone');
    const imageInput = document.getElementById('imageInput');
    const selectImageBtn = document.getElementById('selectImageBtn');
    const previewSection = document.getElementById('previewSection');
    const previewImage = document.getElementById('previewImage');
    const cancelBtn = document.getElementById('cancelBtn');
    const analyzeBtn = document.getElementById('analyzeBtn');

    if (uploadZone && imageInput && selectImageBtn) {
        selectImageBtn.addEventListener('click', () => imageInput.click());

        uploadZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadZone.classList.add('drag-over');
        });
        uploadZone.addEventListener('dragleave', () => uploadZone.classList.remove('drag-over'));
        uploadZone.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadZone.classList.remove('drag-over');
            const file = e.dataTransfer.files[0];
            if (file && file.type.startsWith('image/')) showPreview(file);
        });

        imageInput.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) showPreview(file);
        });
    }

    function showPreview(file) {
        const reader = new FileReader();
        reader.onload = (e) => {
            previewImage.src = e.target.result;
            uploadZone.style.display = 'none';
            previewSection.style.display = 'block';
            previewSection.classList.add('fade-in');
        };
        reader.readAsDataURL(file);
    }

    if (cancelBtn) {
        cancelBtn.addEventListener('click', () => {
            previewSection.style.display = 'none';
            uploadZone.style.display = 'block';
            imageInput.value = '';
        });
    }

    if (analyzeBtn) {
        analyzeBtn.addEventListener('click', async () => {
            document.getElementById('analyzingThumb').src = previewImage.src;
            mostrarPantalla('analyzingScreen');

            try {
                const model = await loadModel();
                const inputTensor = preprocessImage(previewImage);
                const predictionTensor = model.predict(inputTensor);
                const probabilidades = await predictionTensor.data();
                inputTensor.dispose();
                predictionTensor.dispose();

                const ranked = TIPO_LESION_INFO.map((info, idx) => ({
                    ...info,
                    confianza: probabilidades[idx],
                })).sort((a, b) => b.confianza - a.confianza);

                renderResultados(ranked);
                mostrarPantalla('resultScreen');
            } catch (err) {
                console.error(err);
                alert('No se pudo analizar la imagen: ' + err.message);
                mostrarPantalla('homeScreen');
            }
        });
    }

    // ---- Resultado / guardado ----
    const backToHomeBtn = document.getElementById('backToHomeBtn');
    if (backToHomeBtn) backToHomeBtn.addEventListener('click', () => mostrarPantalla('homeScreen'));

    const buscarPacienteBtn = document.getElementById('buscarPacienteBtn');
    if (buscarPacienteBtn) buscarPacienteBtn.addEventListener('click', buscarPaciente);

    const guardarCasoBtn = document.getElementById('guardarCasoBtn');
    if (guardarCasoBtn) {
        guardarCasoBtn.addEventListener('click', guardarCaso);
        cargarEstablecimientos(guardarCasoBtn.dataset.establecimientoId);
        cargarUltimasEvaluaciones(guardarCasoBtn.dataset.profesionalId);
    }

    sincronizarPendientes();
});
