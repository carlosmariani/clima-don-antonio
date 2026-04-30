// sw.js — Service Worker para Clima Don Antonio
// Estrategia: cache la última versión del dashboard para que funcione offline
// y en next visit muestre la nueva si hay internet.

const CACHE_NAME = "clima-don-antonio-v3";
const ASSETS = [
  "./",
  "./index.html",
  "./manifest.json",
  "./icon-192.png",
  "./icon-512.png",
  "./apple-touch-icon.png",
];

// Instalación: precachear recursos críticos
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS).catch(() => {}))
  );
  self.skipWaiting();
});

// Activación: limpiar caches viejos
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

// Estrategia network-first para HTML, cache-first para assets estáticos
self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  // No cachear el PDF ni datos de APIs externas
  if (url.pathname.endsWith(".pdf") ||
      url.hostname !== self.location.hostname) {
    return; // browser default
  }

  // Network-first para HTML/JS (siempre intentar tomar la última versión)
  if (event.request.mode === "navigate" ||
      url.pathname.endsWith(".html") ||
      url.pathname === "/") {
    event.respondWith(
      fetch(event.request)
        .then((resp) => {
          // Guardar copia en cache
          const clone = resp.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
          return resp;
        })
        .catch(() => caches.match(event.request).then((cached) => cached || caches.match("./")))
    );
    return;
  }

  // Cache-first para iconos / static
  event.respondWith(
    caches.match(event.request).then((cached) => cached || fetch(event.request))
  );
});
