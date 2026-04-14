/**
 * assistente-ia.js - Lógica do Assistente COTTE
 *
 * HTTP: usa ApiService com fallback para cliente legado `api`.
 */

let isLoading = false;
let sessaoId = null; // UUID de sessão para histórico de conversa
let _ultimaPergunta = ''; // Última mensagem enviada, para associar ao feedback
let _assistenteWelcomeHTML = ''; // HTML do card inicial (para Nova conversa)
const httpClient = window.ApiService || window.api;
let currentAbortController = null; // Para o botão de parar geração
let speechRecognition = null; // Para entrada por voz
let isRecording = false;
let slashCommandIndex = -1; // Índice atual da lista de slash commands
let _assistentePrefsCache = null;

const SLASH_COMMANDS = [
    { cmd: '/caixa', desc: 'Ver saldo atual disponível', icon: '💰' },
    { cmd: '/faturamento', desc: 'Total faturado em orçamentos', icon: '📈' },
    { cmd: '/receber', desc: 'Valores em aberto a receber', icon: '📥' },
    { cmd: '/pagar', desc: 'Valores em aberto a pagar', icon: '📤' },
    { cmd: '/resumo', desc: 'Visão geral (Dashboard)', icon: '📊' },
    { cmd: '/devendo', desc: 'Lista de clientes em atraso', icon: '🚨' },
    { cmd: '/previsao', desc: 'Projeção de caixa futuro', icon: '🔮' },
    { cmd: '/orcamento', desc: 'Criar um novo orçamento', icon: '📝' },
    { cmd: '/agendar', desc: 'Fazer novo agendamento', icon: '📅' },
    { cmd: '/agenda', desc: 'Ver agendamentos do dia', icon: '📆' },
    { cmd: '/ajuda', desc: 'Dúvidas sobre como usar o sistema', icon: '❓' }
];

const MOBILE_BREAKPOINT = 768;
const INPUT_MIN_HEIGHT_MOBILE = 40;
const INPUT_MIN_HEIGHT_DESKTOP = 44;
const DEFAULT_MESSAGE_PLACEHOLDER = 'Pergunte algo ou dê um comando...';
const MOBILE_MESSAGE_PLACEHOLDER = 'Digite sua mensagem...';

/** Debug na tela: `?debug_ui=1` ou localStorage `cotte_assistente_debug_ui=1`. Não logar tokens. */
function isAssistenteDebugUiEnabled() {
    try {
        if (new URLSearchParams(window.location.search || '').get('debug_ui') === '1') {
            return true;
        }
        return localStorage.getItem('cotte_assistente_debug_ui') === '1';
    } catch (_) {
        return false;
    }
}
window.isAssistenteDebugUiEnabled = isAssistenteDebugUiEnabled;

window.enableAssistenteDebugUi = function enableAssistenteDebugUi() {
    try {
        localStorage.setItem('cotte_assistente_debug_ui', '1');
    } catch (_) { /* ignore */ }
    window.location.reload();
};

window.disableAssistenteDebugUi = function disableAssistenteDebugUi() {
    try {
        localStorage.removeItem('cotte_assistente_debug_ui');
    } catch (_) { /* ignore */ }
    window.location.reload();
};

function hasHttpClient() {
    return !!httpClient && typeof httpClient.get === 'function' && typeof httpClient.post === 'function';
}

/** Ancora backdrop e card de preferências no body (idempotente). Evita perda do DOM quando o container do assistente é reescrito por scripts inline. */
function mountAssistentePreferenciasLayersToBody() {
    const backdrop = document.getElementById('prefBackdrop');
    const card = document.getElementById('assistentePreferenciasCard');
    if (!backdrop || !card) return;
    if (backdrop.parentElement !== document.body) {
        document.body.appendChild(backdrop);
    }
    if (card.parentElement !== document.body) {
        document.body.appendChild(card);
    }
}

function showAssistentePrefNotice(msg, isError = false) {
    const el = document.getElementById('assistenteInstrucoesPermissaoHint');
    if (!el) return;
    el.textContent = msg || '';
    el.style.color = isError ? '#ef4444' : '';
}

/** Atualiza o ponto verde nas engrenagens quando há preferências personalizadas salvas no servidor. */
function syncAssistenteGearSavedBadge(prefData) {
    const pref = prefData?.preferencia_visualizacao || {};
    const formato = pref?.formato_preferido || 'auto';
    const instr = String(prefData?.instrucoes_empresa ?? '').trim();
    const showPersonalizado = formato !== 'auto' || instr.length > 0;

    const desktopBadge = document.getElementById('assistenteGearSavedBadgeDesktop');
    const mobileBadge = document.getElementById('assistenteGearSavedBadgeMobile');
    [desktopBadge, mobileBadge].forEach((el) => {
        if (el) el.classList.toggle('is-visible', showPersonalizado);
    });

    const baseLabel = 'Abrir preferências';
    const label = showPersonalizado
        ? `${baseLabel}. Há preferências personalizadas salvas.`
        : baseLabel;
    const desktopBtn = document.getElementById('btnPreferenciasGearDesktop');
    const mobileBtn = document.getElementById('btnPreferenciasGear');
    if (desktopBtn) desktopBtn.setAttribute('aria-label', label);
    if (mobileBtn) mobileBtn.setAttribute('aria-label', label);
}

function renderAssistentePreferencesCard(prefData) {
    const resumo = document.getElementById('assistentePreferenciasResumo');
    const setorTag = document.getElementById('assistenteSetorTag');
    const select = document.getElementById('assistenteFormatoSelect');
    const txt = document.getElementById('assistenteInstrucoesInput');
    const btn = document.getElementById('btnSalvarPreferenciasAssistente');
    if (!resumo || !setorTag || !select || !txt || !btn) return;

    const pref = prefData?.preferencia_visualizacao || {};
    const playbook = prefData?.playbook_setor || {};
    const podeEditar = !!prefData?.pode_editar_instrucoes;
    const setor = playbook?.setor || 'geral';
    const formato = pref?.formato_preferido || 'auto';

    _assistentePrefsCache = prefData || null;
    setorTag.textContent = `Setor: ${setor}`;
    resumo.textContent = `Formato atual: ${formato}. Playbook ativo com janelas 7/30/90 dias.`;

    select.value = ['auto', 'resumo', 'tabela'].includes(formato) ? formato : 'auto';
    txt.value = prefData?.instrucoes_empresa || '';
    txt.disabled = !podeEditar;
    btn.disabled = false;
    showAssistentePrefNotice(
        podeEditar
            ? 'Você pode editar as instruções da empresa.'
            : 'Somente gestor/admin pode editar instruções da empresa.'
    );
    syncAssistenteGearSavedBadge(prefData || {});
}

async function loadAssistentePreferences() {
    if (!hasHttpClient() || typeof httpClient.get !== 'function') return;
    try {
        const data = await httpClient.get('/ai/assistente/preferencias');
        renderAssistentePreferencesCard(data || {});
    } catch (e) {
        showAssistentePrefNotice('Não foi possível carregar preferências agora.', true);
    }
}

async function saveAssistentePreferences() {
    if (!hasHttpClient() || typeof httpClient.patch !== 'function') return;
    const select = document.getElementById('assistenteFormatoSelect');
    const txt = document.getElementById('assistenteInstrucoesInput');
    const btn = document.getElementById('btnSalvarPreferenciasAssistente');
    if (!select || !txt || !btn) return;
    const podeEditar = !!(_assistentePrefsCache && _assistentePrefsCache.pode_editar_instrucoes);
    const payload = {
        formato_preferido: select.value || 'auto',
        dominio: 'geral',
    };
    if (podeEditar) {
        payload.instrucoes_empresa = txt.value || '';
    }
    btn.disabled = true;
    showAssistentePrefNotice('Salvando preferências...');
    try {
        const out = await httpClient.patch('/ai/assistente/preferencias', payload);
        renderAssistentePreferencesCard(out || {});
        showAssistentePrefNotice('Preferências salvas com sucesso.');
    } catch (e) {
        showAssistentePrefNotice('Falha ao salvar preferências.', true);
    } finally {
        btn.disabled = false;
    }
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

/** Escapa texto para inserção segura em HTML (mitiga XSS). */
function escapeHtml(s) {
    return String(s ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

/** Escapa valor de atributo HTML. */
function escapeHtmlAttr(s) {
    return String(s ?? '')
        .replace(/&/g, '&amp;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;')
        .replace(/</g, '&lt;');
}

/** Texto plano: escape + quebras (erros, conteúdo sem Markdown). */
function textToHtmlPlain(text) {
    return escapeHtml(String(text ?? '')).replace(/\n/g, '<br>');
}

const _mdPh = (kind, i) => `\uE000${kind}${i}\uE001`;

/**
 * Subconjunto seguro de Markdown para respostas da IA: `código`, **negrito**,
 * links [rótulo](https://...). Apenas URLs http/https. Sem HTML bruto.
 */
function textToHtmlRich(raw) {
    const codes = [];
    const links = [];
    let s = String(raw ?? '');
    s = s.replace(/`([^`]+)`/g, (_, inner) => {
        const i = codes.length;
        codes.push(inner);
        return _mdPh('C', i);
    });
    s = s.replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g, (_, label, url) => {
        const i = links.length;
        links.push({ label, url: url.trim() });
        return _mdPh('L', i);
    });
    s = escapeHtml(s);
    codes.forEach((inner, i) => {
        s = s.replace(_mdPh('C', i), '<code class="assistente-md-code">' + escapeHtml(inner) + '</code>');
    });
    links.forEach((L, i) => {
        const u = L.url.trim();
        if (!/^https?:\/\//i.test(u)) {
            s = s.replace(_mdPh('L', i), escapeHtml(`[${L.label}](${L.url})`));
            return;
        }
        s = s.replace(
            _mdPh('L', i),
            '<a href="' + escapeHtmlAttr(u) + '" class="assistente-md-link" target="_blank" rel="noopener noreferrer">' +
            escapeHtml(L.label) +
            '</a>'
        );
    });
    s = s.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    return s.replace(/\n/g, '<br>');
}

function isRetryableAssistenteError(err) {
    const m = (err && err.message) ? err.message : '';
    if (/Erro (502|503|504)\b/.test(m)) return true;
    if (m.includes('conexão') || m.includes('internet')) return true;
    if (m.includes('servidor')) return true;
    if (m.includes('Failed to fetch')) return true;
    return false;
}

function buildAssistenteErrorCard(message, retryable = true) {
    const safeMsg = escapeHtml(message || 'Não foi possível processar sua solicitação.');
    const retryAction = retryable
        ? `<button type="button" class="error-retry-btn" data-assistente-retry="1">Tentar novamente</button>`
        : '';
    return `<div class="error-card" data-testid="assistente-error-card">
        <div class="error-card-header">
            <span class="error-card-icon" aria-hidden="true">⚠️</span>
            Falha ao gerar resposta
        </div>
        <div class="error-card-body">${safeMsg}</div>
        ${retryAction}
    </div>`;
}

/**
 * Obtém hora atual formatada
 */
function getCurrentTime() {
    const now = new Date();
    return now.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
}

const SUGGESTION_ICONS = {
    'cliente': '👤', 'clientes': '👥', 'novo': '🆕', 'venda': '💰',
    'orcamento': '📋', 'orçamento': '📋', 'faturamento': '📊',
    'receita': '📈', 'despesa': '💸', 'caixa': '🏦', 'saldo': '💵',
    'negócio': '🚀', 'negocio': '🚀', 'vendas': '📈', 'meta': '🎯',
    'lead': '🎣', 'leads': '🎣', 'prospec': '🔍', 'contrato': '✍️',
    'pagamento': '💳', 'receber': '📬', 'pagar': '📤',
    'ticket': '🎟️', 'médio': '📏', 'conversão': '🔄', 'conversao': '🔄',
    'índice': '📐', 'indice': '📐', 'análise': '🔬', 'analise': '🔬',
    'inadimpl': '⚠️', 'devendo': '🚨', 'bloqueado': '🔒',
    'sazonal': '📅', 'feriado': '🎉', 'campanha': '📢',
    'promo': '🔥', 'desconto': '🏷️', 'bonus': '🎁',
    'default': '💡'
};

// Shell do chat extraído para assistente-ia-shell.js.

// Entrada, bootstrap mobile e atalhos extraídos para assistente-ia-input.js.

/**
 * Envia mensagem para o assistente
 */
async function sendMessage() {
    const isSilent = window._silentNextMessage;
    window._silentNextMessage = false;
    if (!hasHttpClient()) {
        addMessage('Serviço de API indisponível. Recarregue a página e tente novamente.', false, true);
        return;
    }

    if (isLoading) return;

    const token = localStorage.getItem('cotte_token');
    if (!token) {
        addMessage('Você precisa estar logado para usar o assistente. Redirecionando...', false, true);
        setTimeout(() => {
            window.location.href = 'login.html';
        }, 2000);
        return;
    }

    const input = document.getElementById('messageInput');
    const message = (input && input.value) ? input.value.trim() : '';

    if (!message) return;

    dismissWelcome();
    input.value = '';
    resizeMessageInput();
    _updateVoiceSendToggle(input);
    _hideQuickReplyChips();
    const isConfirmacaoSilenciosa = message === '__confirmar_acao__' || isSilent;
    if (!isConfirmacaoSilenciosa) {
        _ultimaPergunta = message;
        if (typeof trackAssistenteUserIntent === 'function') {
            trackAssistenteUserIntent(message);
        }
    }
    if (typeof setChatAutoFollow === 'function') {
        setChatAutoFollow(true, { scroll: false });
    }

    // Não exibe user bubble para confirmações silenciosas (pending_action)
    if (!isConfirmacaoSilenciosa) {
        addMessage(escapeHtml(message).replace(/\n/g, '<br>'), true, false, false, { forceScroll: true });
    }

    const loadingMessage = addMessage('', false, false, true);
    isLoading = true;

    const sendButton = document.getElementById('sendButton');
    if (sendButton) {
        sendButton.classList.add('is-loading');
        sendButton.title = 'Parar Geração';
    }
    setAiStatus('loading');

    let lastError = null;
    currentAbortController = new AbortController();
    const confirmationToken = window._pendingConfirmationToken;
    let debugUi = false;

    try {
        debugUi = isAssistenteDebugUiEnabled();
        const debugStreamEvents = [];

        if (!sessaoId) {
            sessaoId = (typeof crypto !== 'undefined' && crypto.randomUUID)
                ? crypto.randomUUID()
                : Math.random().toString(36).substring(2) + Date.now().toString(36);
        }

        const requestBody = { mensagem: message, sessao_id: sessaoId };
        if (confirmationToken) {
            requestBody.confirmation_token = confirmationToken;
            window._pendingConfirmationToken = null;
        }
        if (window._pendingOverrideArgs) {
            requestBody.override_args = window._pendingOverrideArgs;
            window._pendingOverrideArgs = null;
        }

        const baseUrl = typeof API_BASE_URL !== 'undefined' ? API_BASE_URL : (window.location.origin + '/api/v1');
        const fetchUrl = baseUrl + '/ai/assistente/stream';

        const maxRetries = 3;
        let response = null;
        let attempt = 0;
        while (attempt < maxRetries) {
            attempt += 1;
            try {
                response = await fetch(fetchUrl, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': 'Bearer ' + token
                    },
                    body: JSON.stringify(requestBody),
                    signal: currentAbortController.signal
                });

                if (!response.ok) {
                    let errText = await response.text();
                    throw new Error(`Erro ${response.status}: ${errText}`);
                }
                break;
            } catch (err) {
                if (err?.name === 'AbortError') {
                    throw err;
                }
                const canRetry = attempt < maxRetries && isRetryableAssistenteError(err);
                if (!canRetry) {
                    throw err;
                }
                await sleep(250 * attempt);
            }
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let done = false;
        let responseText = '';
        let metadata = null;
        let bubbleNode = null;
        let toolBadge = null;   // Badge temporário de "executando tool"
        let _bubbleReady = false; // true após limpar dots e preparar bubble p/ conteúdo

        // Guarda referência mas NÃO limpa ainda — dots ficam visíveis até 1º conteúdo
        if (loadingMessage) {
            bubbleNode = loadingMessage.querySelector('.message-bubble');
        }

        function _prepareBubble() {
            if (_bubbleReady) return;
            _bubbleReady = true;
            if (loadingMessage) loadingMessage.classList.remove('loading');
            if (bubbleNode) bubbleNode.innerHTML = '';
        }

        while (!done) {
            const { value, done: readerDone } = await reader.read();
            if (value) {
                const chunkStr = decoder.decode(value, { stream: true });
                const lines = chunkStr.split('\n');
                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const dataStr = line.substring(6).trim();
                        if (!dataStr) continue;
                        try {
                            const dataObj = JSON.parse(dataStr);
                            if (dataObj.error) throw new Error(dataObj.error);

                            if (debugUi && debugStreamEvents.length < 100) {
                                const snap = {
                                    phase: dataObj.phase || null,
                                    tool: dataObj.tool || null,
                                    is_final: !!dataObj.is_final,
                                };
                                if (dataObj.chunk) {
                                    snap.chunk_len = String(dataObj.chunk).length;
                                }
                                if (dataObj.error) {
                                    snap.error = String(dataObj.error).slice(0, 500);
                                }
                                debugStreamEvents.push(snap);
                            }

                            // ── Evento de fase (thinking / tool_running) ──────
                            if (dataObj.phase === 'tool_running' && dataObj.tool) {
                                _prepareBubble(); // limpa dots ao primeiro evento real
                                // Criar/atualizar badge animado no bubble
                                if (bubbleNode) {
                                    if (!toolBadge) {
                                        toolBadge = document.createElement('div');
                                        toolBadge.className = 'tool-running-badge';
                                        bubbleNode.appendChild(toolBadge);
                                    }
                                    const toolLabel = dataObj.tool.replace(/_/g, ' ');
                                    toolBadge.innerHTML = `<span class="tool-running-dot" aria-hidden="true"></span> Consultando: <em>${escapeHtml(toolLabel)}</em>`;
                                }
                            }

                            // ── Chunk de texto ────────────────────────────────
                            if (dataObj.chunk) {
                                _prepareBubble(); // limpa dots ao primeiro chunk de texto
                                // Remover badge de tool quando começa o texto
                                if (toolBadge) { toolBadge.remove(); toolBadge = null; }
                                responseText += dataObj.chunk;
                                if (bubbleNode && window.marked) {
                                    bubbleNode.innerHTML = marked.parse(responseText);
                                    const tables = bubbleNode.querySelectorAll('table');
                                    tables.forEach(t => {
                                        if(!t.parentElement.classList.contains('ai-table-wrapper')){
                                            t.classList.add('ai-table');
                                            const wrap = document.createElement('div');
                                            wrap.className = 'ai-table-wrapper';
                                            t.parentNode.insertBefore(wrap, t);
                                            wrap.appendChild(t);
                                        }
                                    });
                                } else if (bubbleNode) {
                                    bubbleNode.textContent = responseText;
                                }
                                scrollChatToBottom();
                            }

                            // ── Evento final ──────────────────────────────────
                            if (dataObj.is_final) {
                                _prepareBubble(); // garante que dots são removidos
                                if (toolBadge) { toolBadge.remove(); toolBadge = null; }
                                metadata = dataObj.metadata || {};
                            }
                        } catch (e) {
                            if (e.message && e.message.includes('JSON')) {} else { throw e; }
                        }
                    }
                }
            }
            done = readerDone;
        }

        setAiStatus('ready');

        const finalData = {
           sucesso: true,
           resposta: responseText
                || (metadata && typeof metadata.final_text === 'string' ? metadata.final_text : '')
                || (metadata && typeof metadata.resposta === 'string' ? metadata.resposta : '')
                || (metadata && metadata.dados && typeof metadata.dados.resposta === 'string' ? metadata.dados.resposta : ''),
           stream_has_chunks: !!(responseText && responseText.trim()),
           tipo_resposta: (metadata && metadata.tipo) ? metadata.tipo : 'geral',
           dados: metadata ? (metadata.dados || null) : null,
           grafico: metadata ? (metadata.grafico || null) : null,
           sugestoes: metadata ? (metadata.sugestoes || null) : null,
           pending_action: metadata ? (metadata.pending_action || null) : null,
           tool_trace: metadata ? (metadata.tool_trace || null) : null,
        };

        if (debugUi) {
            finalData.debug_ui = {
                url: fetchUrl,
                sessao_id: sessaoId,
                mensagem_preview: message === '__confirmar_acao__'
                    ? '[confirmacao_silenciosa]'
                    : String(message || '').slice(0, 240),
                stream_events: debugStreamEvents,
                metadata: metadata || null,
            };
        }

        // CORREÇÃO: Se a ação foi 'aprovar' e o backend respondeu como 'criado' ou 'atualizado',
        // forçamos o tipo para 'aprovado' para renderizar o card correto.
        if (message.toLowerCase().startsWith('aprovar') && ['orcamento_criado', 'orcamento_atualizado', 'operador_resultado'].includes(finalData.tipo_resposta)) {
            const orcData = finalData.dados || finalData.orcamento || finalData;
            if (orcData && orcData.id && orcData.numero) {
                finalData.tipo_resposta = 'orcamento_aprovado';
            }
        }

        processAIResponse(finalData, loadingMessage, true);

    } catch (error) {
        lastError = error;
        console.error('Error:', error);

        if (debugUi) {
            const snippet = JSON.stringify(
                {
                    kind: 'assistente_stream_client_error',
                    message: String(error && error.message ? error.message : error),
                    name: error && error.name ? error.name : null,
                },
                null,
                2
            );
            const pre = escapeHtml(snippet);
            addMessage(
                `<details class="ai-debug-ui" open><summary class="ai-debug-ui__summary">Debug UI (erro no cliente)</summary><pre class="ai-debug-ui__pre" tabindex="0">${pre}</pre><p class="ai-debug-ui__hint">Desative com <code>disableAssistenteDebugUi()</code> no console.</p></details>`,
                false,
                false
            );
        }

        if (error && error.name === 'AbortError') {
            console.log('Geração de resposta interrompida pelo usuário.');
            if (loadingMessage && loadingMessage.querySelector('.loading-dots')) {
                loadingMessage.remove(); // Remove apenas se não gerou nada ainda
            } else if (loadingMessage) {
                loadingMessage.classList.remove('loading');
                const bubble = loadingMessage.querySelector('.message-bubble');
                if (bubble && !bubble.textContent.trim() && !bubble.innerHTML.includes('<br>')) {
                    loadingMessage.remove();
                } else if (bubble) {
                    bubble.innerHTML += '<br><br><em><small>[Geração interrompida]</small></em>';
                }
            }
            setAiStatus('ready');
            return;
        }

        if (loadingMessage && loadingMessage.remove) {
            loadingMessage.remove();
        }

        let errorMessage = 'Não foi possível processar sua solicitação.';
        if (error.message && error.message.includes('Sessão expirada')) {
            errorMessage = 'Sessão expirada. Redirecionando...';
            setTimeout(() => { window.location.href = 'login.html'; }, 2000);
        } else if (error.message && (error.message.includes('Failed to fetch') || error.message.includes('conexão'))) {
            errorMessage = 'Erro de conexão. Verifique sua internet.';
            setAiStatus('offline');
        } else {
            setAiStatus('error');
        }

        addMessage(buildAssistenteErrorCard(errorMessage, isRetryableAssistenteError(error)), false, true);
        setTimeout(() => setAiStatus('ready'), 4500);
    } finally {
        isLoading = false;
        currentAbortController = null;
        if (sendButton) {
            sendButton.classList.remove('is-loading');
            sendButton.title = 'Enviar';
        }

        if (confirmationToken) {
            const card = document.querySelector(`.pending-action-card[data-token="${confirmationToken}"]`);
            if (card) {
                const status = card.querySelector('.pending-action-status');
                if (status) {
                    if (lastError && lastError.name !== 'AbortError') {
                        status.textContent = '❌ Falha na execução';
                        status.style.color = 'var(--ai-red, #ef4444)';
                        card.querySelectorAll('button').forEach(b => b.disabled = false);
                    } else if (!lastError) {
                        status.textContent = '✅ Ação concluída';
                        status.style.color = 'var(--ai-green, #10b981)';
                    } else {
                        status.textContent = 'Ação interrompida';
                        card.querySelectorAll('button').forEach(b => b.disabled = false);
                    }
                }
            }
        }
    }
}

// Camada de render/ações vive em assistente-ia-render.js.
window.sendMessage = sendMessage;
window.buildAssistenteErrorCard = buildAssistenteErrorCard;
window.isRetryableAssistenteError = isRetryableAssistenteError;
