// Bandeja de interconsulta del especialista: lista priorizada de resúmenes.
// Cada item lleva al detalle del caso (/especialista/casos/<id>/), donde
// vive la imagen y las acciones de atender/resolver.

const PRIORIDAD_INFO = {
    URGENTE: { clase: 'urgente', label: 'URGENTE' },
    ALTA: { clase: 'alta', label: 'ALTA' },
    MEDIA: { clase: 'media', label: 'MEDIA' },
};

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

/* ============ Bandeja (resumen, sin acciones) ============ */

function renderQueueItem(item) {
    const prioridad = PRIORIDAD_INFO[item.prioridad] || { clase: 'media', label: item.prioridad };
    const detalle = item.caso_detalle || {};
    const confianzaPct = typeof detalle.confianza_modelo === 'number'
        ? Math.round(detalle.confianza_modelo * 100)
        : null;

    return `
        <a class="card card-glass queue-item" href="/especialista/casos/${item.id}/">
            <div class="queue-item-header">
                <span class="priority-badge ${prioridad.clase}">${prioridad.label}</span>
                <span class="queue-meta">${tiempoRelativo(item.fecha_ingreso)}</span>
            </div>
            <p style="font-weight:600;">${escapeHtml(detalle.paciente)}</p>
            <p class="text-muted" style="font-size:var(--font-size-sm);">
                ${escapeHtml(detalle.tipo_lesion_predicho_display)}${confianzaPct !== null ? ` · Confianza ${confianzaPct}%` : ''} · ${escapeHtml(detalle.establecimiento)}
            </p>
        </a>
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
    const list = document.getElementById('queueList');
    try {
        const items = await apiFetch('/api/cola-interconsulta/mia/');
        renderQueue(items);
    } catch (err) {
        if (list) {
            list.querySelectorAll('.queue-item').forEach((el) => el.remove());
        }
        const emptyMessage = document.getElementById('queueEmptyMessage');
        if (emptyMessage) {
            emptyMessage.textContent = 'No se pudo cargar tu bandeja. Verifica tu conexión.';
            emptyMessage.style.display = 'block';
        }
    }
}

/* ============ Inicializacion ============ */

document.addEventListener('DOMContentLoaded', () => {
    actualizarConexion();
    window.addEventListener('online', actualizarConexion);
    window.addEventListener('offline', actualizarConexion);
    window.addEventListener('online', cargarMiCola);

    cargarMiCola();
});
