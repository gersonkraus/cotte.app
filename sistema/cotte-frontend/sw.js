const CACHE_NAME = 'cotte-app-v1';
const ASSETS_TO_CACHE = [
  '/',
  '/app/',
  '/app/index.html',
  '/app/css/style.css',
  '/app/js/services/ApiService.js',
  '/app/js/services/CacheService.js',
  '/favicon.svg'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS_TO_CACHE))
  );
});

self.addEventListener('fetch', (event) => {
  event.respondWith(
    caches.match(event.request).then((response) => {
      return response || fetch(event.request);
    })
  );
});