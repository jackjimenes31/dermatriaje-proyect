// Bandeja de interconsulta del especialista: revisión asíncrona de casos
// ALTO/MEDIO derivados desde el triaje del médico general. Sin cita ni
// videollamada — el especialista atiende y resuelve cuando puede.

const PRIORIDAD_INFO = {
    URGENTE: { clase: 'urgente', label: 'URGENTE' },
    ALTA: { clase: 'alta', label: 'ALTA' },
    MEDIA: { clase: 'media', label: 'MEDIA' },
};

let toastTimeout = null;

/* ============ Utilidades de red (mismo patrón que triaje.js) ============ */

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

function tiempoRelativo(fechaIso) {
    const minutos = Math.round((Date.now() - new Date(fechaIso).getTime()) / 60000);
    if (minutos < 1) return 'ahora';
    if (minutos < 60) return `hace ${minutos} min`;
    const horas = Math.round(minutos / 60);
    if (horas < 24) return `hace ${horas} h`;
    return `hace ${Math.round(horas / 24)} d`;
}

/* ============ Badge de conexion ============ */

function actualizarConexion() {
    const text = document.getElementById('connectionBadgeText');
    if (!text) return;
    text.textContent = navigator.onLine ? 'EN LÍNEA' : 'SIN CONEXIÓN · SE REQUIERE PARA ATENDER';
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

function mostrarErrorRed(err) {
    if (err.isNetworkError || !navigator.onLine) {
        mostrarToast('Sin conexión', 'Esta acción requiere conexión a Internet. Intenta de nuevo.');
    } else {
        mostrarToast('Ocurrió un error', (err.data && err.data.detail) || 'Intenta de nuevo.');
    }
}

/* ============ Bandeja ============ */

function renderQueueItem(item) {
    const prioridad = PRIORIDAD_INFO[item.prioridad] || { clase: 'media', label: item.prioridad };
    const detalle = item.caso_detalle || {};
    const confianzaPct = typeof detalle.confianza_modelo === 'number'
        ? Math.round(detalle.confianza_modelo * 100)
        : null;

    const acciones = item.estado === 'EN_ESPERA'
        ? `<button class="btn btn-primary btn-full" data-action="atender" data-cola-id="${item.id}">ATENDER CASO</button>`
        : `
            <textarea class="form-input observaciones-input" placeholder="Observaciones del especialista (opcional)" data-observaciones-id="${item.id}"></textarea>
            <button class="btn btn-full" data-action="resolver" data-cola-id="${item.id}">RESOLVER CASO</button>
        `;

    return `
        <div class="card card-glass queue-item" data-cola-id="${item.id}">
            <div class="queue-item-header">
                <span class="priority-badge ${prioridad.clase}">${prioridad.label}</span>
                <span class="queue-meta">${tiempoRelativo(item.fecha_ingreso)}</span>
            </div>
            <p style="font-weight:600;">${escapeHtml(detalle.paciente)}</p>
            <p class="text-muted" style="font-size:var(--font-size-sm);">
                ${escapeHtml(detalle.tipo_lesion_predicho_display)}${confianzaPct !== null ? ` · Confianza ${confianzaPct}%` : ''} · ${escapeHtml(detalle.establecimiento)}
            </p>
            ${detalle.notas_clinicas ? `<p class="text-muted" style="font-size:var(--font-size-sm);"><em>${escapeHtml(detalle.notas_clinicas)}</em></p>` : ''}
            <div class="queue-actions">${acciones}</div>
        </div>
    `;
}

function renderQueue(items) {
    const list = document.getElementById('queueList');
    const emptyMessage = document.getElementById('queueEmptyMessage');
    if (!list) return;

    list.querySelectorAll('.queue-item').forEach((el) => el.remove());

    if (items.length === 0) {
        if (emptyMessage) emptyMessage.style.display = 'block';
        return;
    }
    if (emptyMessage) emptyMessage.style.display = 'none';
    list.insertAdjacentHTML('beforeend', items.map(renderQueueItem).join(''));
}

async function cargarMiCola() {
    try {
        const items = await apiFetch('/api/cola-interconsulta/mia/');
        renderQueue(items);
    } catch (err) {
        mostrarErrorRed(err);
    }
}

async function atenderCaso(colaId) {
    try {
        await apiFetch(`/api/cola-interconsulta/${colaId}/atender/`, { method: 'POST' });
        mostrarToast('Caso en revisión', 'Ahora puedes agregar tus observaciones y resolverlo.');
        cargarMiCola();
    } catch (err) {
        mostrarErrorRed(err);
    }
}

async function resolverCaso(colaId, observaciones) {
    try {
        await apiFetch(`/api/cola-interconsulta/${colaId}/resolver/`, {
            method: 'POST',
            body: JSON.stringify({ observaciones_especialista: observaciones }),
        });
        mostrarToast('Caso resuelto', 'La interconsulta quedó cerrada correctamente.');
        cargarMiCola();
    } catch (err) {
        mostrarErrorRed(err);
    }
}

/* ============ Inicializacion ============ */

document.addEventListener('DOMContentLoaded', () => {
    actualizarConexion();
    window.addEventListener('online', actualizarConexion);
    window.addEventListener('offline', actualizarConexion);
    window.addEventListener('online', cargarMiCola);

    const queueList = document.getElementById('queueList');
    if (queueList) {
        queueList.addEventListener('click', (event) => {
            const btn = event.target.closest('[data-action]');
            if (!btn) return;
            const colaId = btn.dataset.colaId;

            if (btn.dataset.action === 'atender') {
                atenderCaso(colaId);
            } else if (btn.dataset.action === 'resolver') {
                const textarea = queueList.querySelector(`[data-observaciones-id="${colaId}"]`);
                resolverCaso(colaId, textarea ? textarea.value : '');
            }
        });
    }

    cargarMiCola();
});
