/* ─── Service Worker v3 ────────────────────────────────────
   Strategy: only cache static assets.
   HTML pages are NEVER cached — always fetched fresh.
   ──────────────────────────────────────────────────────── */
const CACHE_NAME = 'pontons-v3';

const STATIC_ASSETS = [
  '/static/manifest.json',
  'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css',
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(STATIC_ASSETS).catch(() => {}))
  );
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  // Delete ALL old caches (pontons-v1, pontons-v2, etc.)
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET') return;

  // Never intercept HTML navigation requests — let browser handle them fresh
  const accept = event.request.headers.get('Accept') || '';
  if (accept.includes('text/html')) return;

  // For static assets: cache-first, network fallback
  event.respondWith(
    caches.match(event.request).then(cached => {
      if (cached) return cached;
      return fetch(event.request).then(response => {
        if (response && response.ok && response.type !== 'opaque') {
          const clone = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
        }
        return response;
      }).catch(() => cached || new Response('', {status: 503}));
    })
  );
});
