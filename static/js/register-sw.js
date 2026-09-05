// Register Service Worker
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker
            .register('/static/sw.js', { scope: '/' })
            .then((registration) => {
                console.log('[PWA] Service Worker registrado:', registration.scope);

                // Check for updates periodically
                setInterval(() => {
                    registration.update();
                }, 60 * 60 * 1000); // every hour
            })
            .catch((error) => {
                console.error('[PWA] Error registrando SW:', error);
            });
    });
}
