// Detalle de un caso de la bandeja del especialista: imagen + info completa +
// atender/resolver (revisión asíncrona, sin cita).

const PRIORIDAD_INFO = {
    URGENTE: { clase: 'urgente', label: 'URGENTE' },
    ALTA: { clase: 'alta', label: 'ALTA' },
    MEDIA: { clase: 'media', label: 'MEDIA' },
};

let toastTimeout = null;

/* ============ Utilidades de red (mismo patrón que triaje.js/especialista.js) ============ */

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

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text || '';
    return div.innerHTML;
}

function mostrarToast(titulo, subtitulo) {
    const toast = document.getElementById('toast');
    if (!toast) return;
    document.getElementById('toastTitle').textContent = titulo;
    document.getElementById('toastSubtitle').textContent = subtitulo || '';
    toast.hidden = false;
    if (toastTimeout) clearTimeout(toastTimeout);
    toastTimeout = setTimeout(() => { toast.hidden = true; }, 3200);
}

function mostrarErrorRed(err) {
    if (err.isNetworkError || !navigator.onLine) {
        mostrarToast('Sin conexión', 'Esta acción requiere conexión a Internet. Intenta de nuevo.');
    } else {
        mostrarToast('Ocurrió un error', (err.data && err.data.detail) || 'Intenta de nuevo.');
    }
}

/* ============ Render del detalle ============ */

function renderCaso(item, colaId) {
    const contenedor = document.getElementById('casoDetalle');
    if (!contenedor) return;

    const prioridad = PRIORIDAD_INFO[item.prioridad] || { clase: 'media', label: item.prioridad };
    const detalle = item.caso_detalle || {};
    const confianzaPct = typeof detalle.confianza_modelo === 'number'
        ? Math.round(detalle.confianza_modelo * 100)
        : null;

    const imagenHtml = detalle.imagen_url
        ? `<div class="caso-imagen-wrap"><img class="caso-imagen" src="${detalle.imagen_url}" alt="Imagen de la lesión"></div>`
        : `<div class="caso-imagen-wrap"><p class="caso-sin-imagen">Sin imagen registrada</p></div>`;

    let accionesHtml = '';
    if (item.estado === 'EN_ESPERA') {
        accionesHtml = `<button class="btn btn-primary btn-full" id="btnAtender">ATENDER CASO</button>`;
    } else if (item.estado === 'EN_ATENCION') {
        accionesHtml = `
            <div class="form-group">
                <label for="observacionesEspecialista">Observaciones del especialista</label>
                <textarea id="observacionesEspecialista" class="form-input observaciones-input" placeholder="Diagnóstico, recomendación o indicación para el establecimiento de origen"></textarea>
            </div>
            <button class="btn btn-full" id="btnResolver">RESOLVER CASO</button>
        `;
    } else {
        accionesHtml = `<p class="text-muted" style="font-size:var(--font-size-sm);">Este caso ya está cerrado (${item.estado}).</p>`;
    }

    contenedor.innerHTML = `
        ${imagenHtml}
        <div class="card card-glass" style="margin-bottom:var(--space-4);">
            <div class="queue-item-header" style="margin-bottom:var(--space-3);">
                <span class="priority-badge ${prioridad.clase}">${prioridad.label}</span>
            </div>
            <p style="font-weight:600; font-size:var(--font-size-md);">${escapeHtml(detalle.paciente)}</p>
            <p class="text-muted" style="font-size:var(--font-size-sm); margin-top:var(--space-2);">
                ${escapeHtml(detalle.tipo_lesion_predicho_display)}${confianzaPct !== null ? ` · Confianza ${confianzaPct}%` : ''}
            </p>
            <p class="text-muted" style="font-size:var(--font-size-sm);">${escapeHtml(detalle.establecimiento)}</p>
            ${detalle.notas_clinicas ? `<p style="margin-top:var(--space-3);"><em>${escapeHtml(detalle.notas_clinicas)}</em></p>` : ''}
        </div>
        <div class="card card-glass">
            ${accionesHtml}
        </div>
    `;

    const btnAtender = document.getElementById('btnAtender');
    if (btnAtender) btnAtender.addEventListener('click', () => atender(colaId));

    const btnResolver = document.getElementById('btnResolver');
    if (btnResolver) {
        btnResolver.addEventListener('click', () => {
            const textarea = document.getElementById('observacionesEspecialista');
            resolver(colaId, textarea ? textarea.value : '');
        });
    }
}

async function cargarCaso(colaId) {
    try {
        const item = await apiFetch(`/api/cola-interconsulta/${colaId}/`);
        renderCaso(item, colaId);
    } catch (err) {
        const contenedor = document.getElementById('casoDetalle');
        if (contenedor) {
            contenedor.innerHTML = '<p class="text-muted" style="font-size:var(--font-size-sm);">No se pudo cargar el caso. Verifica tu conexión.</p>';
        }
    }
}

async function atender(colaId) {
    try {
        await apiFetch(`/api/cola-interconsulta/${colaId}/atender/`, { method: 'POST' });
        mostrarToast('Caso en revisión', 'Ahora puedes agregar tus observaciones y resolverlo.');
        cargarCaso(colaId);
    } catch (err) {
        mostrarErrorRed(err);
    }
}

async function resolver(colaId, observaciones) {
    try {
        await apiFetch(`/api/cola-interconsulta/${colaId}/resolver/`, {
            method: 'POST',
            body: JSON.stringify({ observaciones_especialista: observaciones }),
        });
        mostrarToast('Caso resuelto', 'La interconsulta quedó cerrada correctamente.');
        setTimeout(() => { window.location.href = '/especialista/'; }, 1200);
    } catch (err) {
        mostrarErrorRed(err);
    }
}

/* ============ Inicializacion ============ */

document.addEventListener('DOMContentLoaded', () => {
    const colaId = document.querySelector('.app-shell').dataset.colaId;
    if (colaId) cargarCaso(colaId);
});
