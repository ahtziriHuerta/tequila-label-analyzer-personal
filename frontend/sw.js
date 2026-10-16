// Service worker de la PWA: guarda la interfaz para que abra aunque no haya red.
// Estrategia "red primero": con conexión siempre se ve la última versión (útil mientras desarrollamos)
// y la caché solo se usa como respaldo. Las llamadas a la API nunca se guardan.
// Si agregas un archivo a la interfaz, súmalo a NUCLEO y cambia la versión de CACHE.
const CACHE = "tla-v11";
const NUCLEO = [
  "./", "index.html", "manifest.json", "css/styles.css",
  "js/app.js", "js/api.js", "js/catalogos.js", "js/ejemplo.js", "js/ui.js",
  "js/vistas/inicio.js", "js/vistas/historial.js", "js/vistas/nuevo.js", "js/vistas/resultado.js", "js/vistas/configuracion.js",
  "img/icono.svg", "img/portada.webp", "img/fondo-agave.webp", "img/logo-crt.png", "fonts/cormorant-garamond-latin.woff2", "fonts/cormorant-garamond-italic-latin.woff2",
  "fonts/source-sans-3-latin.woff2", "fonts/ibm-plex-mono-500-latin.woff2", "fonts/ibm-plex-mono-600-latin.woff2",
  "img/icono-192.png", "img/icono-512.png",
];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(NUCLEO)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", e => {
  e.waitUntil(caches.keys()
    .then(claves => Promise.all(claves.filter(k => k !== CACHE).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener("fetch", e => {
  // Solo los archivos de la interfaz (dentro de /app/). La API (/analisis, /imagenes, /salud)
  // está en el mismo servidor pero fuera de este alcance, así que nunca se guarda en caché.
  if (e.request.method !== "GET" || !e.request.url.startsWith(self.registration.scope)) return;

  e.respondWith(
    // cache: "no-cache" pide al servidor la versión vigente (sin esto el navegador podía
    // entregar un .js viejo de su caché junto con un .css nuevo).
    fetch(e.request, { cache: "no-cache" })
      .then(res => {
        if (res.ok) {
          const copia = res.clone();
          caches.open(CACHE).then(c => c.put(e.request, copia));
        }
        return res;
      })
      .catch(async () =>
        (await caches.match(e.request, { ignoreSearch: true }))
        ?? (e.request.mode === "navigate" ? caches.match("index.html") : Response.error()))
  );
});
