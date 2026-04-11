/**
 * COTTE Service Worker
 * Gerenciado via Workbox (Google)
 * Estratégia: Opção 1 - Carregamento via CDN
 */

importScripts('https://storage.googleapis.com/workbox-cdn/releases/6.4.1/workbox-sw.js');

if (workbox) {
  console.log('COTTE: Workbox carregado 🚀');

  // Forçar o Service Worker a se tornar ativo imediatamente
  workbox.core.skipWaiting();
  workbox.core.clientsClaim();

  // Configuração de nome de cache para facilitar debug
  const CACHE_NAMES = {
    pages: 'cotte-pages-v2',
    assets: 'cotte-assets-v2',
    images: 'cotte-images-v2',
    fonts: 'google-fonts'
  };

  // 1. Páginas HTML (Navegação)
  // NetworkFirst: Tenta a rede, se falhar ou demorar, usa o cache.
  // Ideal para o index.html e páginas principais que mudam pouco a estrutura mas muito o dado.
  workbox.routing.registerRoute(
    ({ request }) => request.mode === 'navigate' || 
                     request.destination === 'document',
    new workbox.strategies.NetworkFirst({
      cacheName: CACHE_NAMES.pages,
      plugins: [
        new workbox.expiration.ExpirationPlugin({
          maxEntries: 20,
        }),
      ],
    })
  );

  // 2. Scripts e Estilos (JS/CSS)
  // StaleWhileRevalidate: Serve do cache INSTANTANEAMENTE e atualiza em background.
  // Melhora drasticamente a percepção de performance.
  workbox.routing.registerRoute(
    ({ request }) => request.destination === 'script' || 
                     request.destination === 'style',
    new workbox.strategies.StaleWhileRevalidate({
      cacheName: CACHE_NAMES.assets,
    })
  );

  // 3. Imagens e Ícones
  // CacheFirst: Como imagens raramente mudam, prioriza o cache.
  workbox.routing.registerRoute(
    ({ request }) => request.destination === 'image',
    new workbox.strategies.CacheFirst({
      cacheName: CACHE_NAMES.images,
      plugins: [
        new workbox.expiration.ExpirationPlugin({
          maxEntries: 100,
          maxAgeSeconds: 60 * 24 * 60 * 60, // 60 dias
        }),
      ],
    })
  );

  // 4. Google Fonts
  // CacheFirst: Armazena fontes externas para evitar round-trips de rede.
  workbox.routing.registerRoute(
    ({ url }) => url.origin === 'https://fonts.googleapis.com' || 
                 url.origin === 'https://fonts.gstatic.com',
    new workbox.strategies.CacheFirst({
      cacheName: CACHE_NAMES.fonts,
      plugins: [
        new workbox.expiration.ExpirationPlugin({
          maxEntries: 10,
          maxAgeSeconds: 365 * 24 * 60 * 60, // 1 ano
        }),
      ],
    })
  );

  // 5. Proteção para API
  // NetworkOnly: Garante que as chamadas de API nunca sejam cacheadas pelo SW.
  // O COTTE já tem um CacheService.js próprio para dados dinâmicos.
  workbox.routing.registerRoute(
    ({ url }) => url.pathname.includes('/api/v1/'),
    new workbox.strategies.NetworkOnly()
  );

  // 6. Offline Fallback (Opcional)
  // Se quisermos uma página específica de "Você está offline", configuraríamos aqui.

} else {
  console.error('COTTE: Workbox falhou ao carregar no Service Worker ❌');
}
