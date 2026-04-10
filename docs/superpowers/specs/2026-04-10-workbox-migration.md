# Spec: Migração de Service Worker para Workbox (Opção 1 - CDN)

## 1. Objetivo
Modernizar o gerenciamento de cache e o ciclo de vida do Service Worker do COTTE, substituindo a implementação manual por Google Workbox via CDN. Isso visa melhorar a velocidade de carregamento (especialmente em conexões móveis/lentas) e simplificar a manutenção do PWA.

## 2. Abordagem: Workbox via CDN
Optamos por carregar o Workbox diretamente no Service Worker (`importScripts`) para manter a arquitetura Vanilla JS (sem build step) do projeto.

## 3. Estratégias de Cache Definidas

| Tipo de Ativo | Extensões / Caminho | Estratégia | Justificativa |
| :--- | :--- | :--- | :--- |
| **App Shell (Navegação)** | `/app/`, `/index.html` | `NetworkFirst` | Garante a versão mais nova se houver rede; abre cache instantaneamente se falhar. |
| **Estilos e Scripts** | `.js`, `.css` | `StaleWhileRevalidate` | **Carregamento instantâneo.** Usa o cache enquanto atualiza silenciosamente em background. |
| **Imagens e Ícones** | `.png`, `.svg`, `.jpg`, `.ico` | `CacheFirst` | Performance máxima; raramente mudam. Limite de 50 itens / 60 dias. |
| **Fontes Externas** | Google Fonts (Inter, Jakarta) | `CacheFirst` | Evita rede para ativos de sistema que não mudam. |
| **API Backend** | `/api/v1/` | **Bypass (Network Only)** | Dados dinâmicos não são gerenciados pelo SW (delegado ao `ApiService.js`). |

## 4. Mudanças Técnicas

### 4.1. `sistema/cotte-frontend/sw.js`
- Substituição da lógica manual de `install`, `activate` e `fetch` por chamadas declarativas ao `workbox`.
- Implementação de `skipWaiting()` e `clientsClaim()` para ativação imediata.

### 4.2. `sistema/cotte-frontend/index.html`
- Manter o registro atual, mas garantir que o `/sw.js` seja servido sem cache no servidor (FastAPI).

## 5. Plano de Implementação
1. Identificar todos os assets críticos para o precache.
2. Atualizar o `sw.js` com a nova sintaxe do Workbox.
3. Testar a ativação do novo Service Worker e verificar se as estratégias de cache estão sendo aplicadas (via DevTools).

## 6. Riscos e Mitigação
- **Cache Poisoning:** Arquivos JS "presos" em versões antigas. 
- **Solução:** O `StaleWhileRevalidate` do Workbox atualiza o cache assim que detecta uma mudança, garantindo que o próximo reload do usuário já tenha a versão nova.
