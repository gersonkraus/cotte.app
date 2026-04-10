const CACHE_NAME = 'cotte-app-v2'; // Incrementado para v2 para invalidar caches antigos
const ASSETS_TO_CACHE = [
  '/',
  '/app/',
  '/app/index.html',
  '/app/css/style.css',
  '/app/js/services/ApiService.js',
  '/app/js/services/CacheService.js',
  '/favicon.svg'
];

// Instalação: pré-cache de assets essenciais
self.addEventListener('install', (event) => {
  self.skipWaiting(); // Força a ativação imediata
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS_TO_CACHE))
  );
});

// Ativação: limpa caches antigos
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== CACHE_NAME) {
            console.log('[SW] Removendo cache antigo:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
});

// Fetch: Estratégia Network-First (Tenta rede, se falhar/offline usa cache)
self.addEventListener('fetch', (event) => {
  // Ignorar requisições de API para não cachear dados dinâmicos do banco no SW
  if (event.request.url.includes('/api/v1/')) {
    return;
  }

  event.respondWith(
    fetch(event.request)
      .then((response) => {
        // Se a rede respondeu, atualiza o cache e retorna a resposta
        if (response && response.status === 200 && response.type === 'basic') {
          const responseToCache = response.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, responseToCache);
          });
        }
        return response;
      })
      .catch(() => {
        // Se a rede falhar (offline), tenta o cache
        return caches.match(event.request);
      })
  );
});
