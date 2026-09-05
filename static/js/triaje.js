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

const MODEL_URL = '/static/models/skin-lesion/model.json';

let modelPromise = null;
let ultimoResultado = null;

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
    const response = await fetch(url, Object.assign({ credentials: 'same-origin' }, options, { headers }));
    const data = await response.json().catch(() => null);
    if (!response.ok) {
        const error = new Error('api_error');
        error.data = data;
        throw error;
    }
    return data;
}

function renderResultados(ranked) {
    ultimoResultado = ranked;
    const top = ranked[0];

    const priorityBadge = document.getElementById('priorityBadge');
    priorityBadge.textContent = `Riesgo ${top.riesgo}`;
    priorityBadge.style.background =
        top.riesgo === 'ALTO' ? 'var(--color-danger)' : top.riesgo === 'MEDIO' ? 'var(--color-warning)' : 'var(--color-success)';
    priorityBadge.style.color = '#1a1a1a';

    const resultsBody = document.getElementById('resultsBody');
    resultsBody.innerHTML =
        `<p><strong>${top.label}</strong> — ${(top.confianza * 100).toFixed(1)}% de confianza</p>` +
        '<p class="text-muted">Top 3 predicciones del modelo:</p>' +
        '<ul>' +
        ranked
            .slice(0, 3)
            .map((r) => `<li>${r.label}: ${(r.confianza * 100).toFixed(1)}%</li>`)
            .join('') +
        '</ul>';

    document.getElementById('resultsSection').style.display = 'block';

    const riesgoConfirmado = document.getElementById('riesgoConfirmado');
    if (riesgoConfirmado) riesgoConfirmado.value = top.riesgo;

    document.getElementById('saveCaseSection').style.display = 'block';
}

async function cargarEstablecimientos() {
    const select = document.getElementById('establecimientoCaso');
    if (!select) return;
    try {
        const data = await apiFetch('/api/establecimientos/');
        select.innerHTML = data
            .map((e) => `<option value="${e.id}">${e.nombre} (${e.nivel})</option>`)
            .join('');
    } catch (err) {
        select.innerHTML = '<option value="">No se pudieron cargar los establecimientos</option>';
    }
}

function mostrarMensajeGuardado(texto, esError) {
    const msg = document.getElementById('saveCaseMessage');
    msg.textContent = texto;
    msg.style.color = esError ? 'var(--color-danger)' : 'var(--color-success)';
    msg.style.display = 'block';
}

async function guardarCaso() {
    const btn = document.getElementById('guardarCasoBtn');
    const saveCaseSection = document.getElementById('saveCaseSection');
    const profesionalId = saveCaseSection.dataset.profesionalId;

    if (!profesionalId) {
        mostrarMensajeGuardado('Tu usuario no tiene un perfil de profesional asociado.', true);
        return;
    }
    if (!ultimoResultado) {
        mostrarMensajeGuardado('Primero analiza una imagen con IA.', true);
        return;
    }

    btn.disabled = true;
    btn.textContent = 'Guardando...';

    try {
        const paciente = await apiFetch('/api/pacientes/', {
            method: 'POST',
            body: JSON.stringify({
                tipo_documento: document.getElementById('tipoDocumento').value,
                numero_documento: document.getElementById('numeroDocumento').value,
                nombres: document.getElementById('nombresPaciente').value,
                apellidos: document.getElementById('apellidosPaciente').value,
                edad: parseInt(document.getElementById('edadPaciente').value, 10),
                sexo: document.getElementById('sexoPaciente').value,
            }),
        });

        const top = ultimoResultado[0];
        const top3 = ultimoResultado.slice(0, 3).map((r) => ({ tipo: r.code, confianza: r.confianza }));

        const caso = await apiFetch('/api/casos-triaje/', {
            method: 'POST',
            body: JSON.stringify({
                paciente: paciente.id,
                profesional_creador: parseInt(profesionalId, 10),
                establecimiento: parseInt(document.getElementById('establecimientoCaso').value, 10),
                tipo_lesion_predicho: top.code,
                confianza_modelo: top.confianza,
                probabilidades_top3: top3,
                clasificacion_riesgo: document.getElementById('riesgoConfirmado').value,
                notas_clinicas: document.getElementById('notasClinicas').value,
            }),
        });

        mostrarMensajeGuardado(`Caso #${caso.id} guardado correctamente.`, false);
    } catch (err) {
        const detalle = err.data ? JSON.stringify(err.data) : 'Ocurrió un error al guardar el caso.';
        mostrarMensajeGuardado(detalle, true);
    } finally {
        btn.disabled = false;
        btn.textContent = 'Guardar caso';
    }
}

document.addEventListener('DOMContentLoaded', () => {
    cargarEstablecimientos();

    const analyzeBtn = document.getElementById('analyzeBtn');
    if (analyzeBtn) {
        analyzeBtn.addEventListener('click', async () => {
            const previewImage = document.getElementById('previewImage');
            analyzeBtn.disabled = true;
            const textoOriginal = analyzeBtn.textContent;
            analyzeBtn.textContent = 'Analizando...';

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
            } catch (err) {
                console.error(err);
                alert('No se pudo analizar la imagen: ' + err.message);
            } finally {
                analyzeBtn.disabled = false;
                analyzeBtn.textContent = textoOriginal;
            }
        });
    }

    const guardarCasoBtn = document.getElementById('guardarCasoBtn');
    if (guardarCasoBtn) {
        guardarCasoBtn.addEventListener('click', guardarCaso);
    }
});
