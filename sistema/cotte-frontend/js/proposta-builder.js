// COTTE — Proposta Builder (Página Full-Page)
// Reutiliza lógica core de blocos/variáveis do módulo de propostas públicas

// ── Utilitários locais (página standalone) ─────────────────────────────────
function esc(s) {
    if (!s) return '';
    const d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
}

function showToast(msg, type) {
    type = type || 'success';
    const t = document.getElementById('toast');
    if (!t) return;
    t.textContent = msg;
    t.className = 'toast show ' + type;
    clearTimeout(t._tid);
    t._tid = setTimeout(() => { t.className = 'toast'; }, 3500);
}

// ── Dados de blocos padrão ─────────────────────────────────────────────────
const DEFAULT_BLOCOS = [
    {
        tipo: 'hero', nome: 'Hero / Pitch', desc: 'Título principal e apresentação',
        ativo: true, ordem: 0,
        config: { titulo: 'Proposta Comercial Sob Medida', subtitulo: 'Uma solução pensada para {{empresa}}', conteudo: 'Transforme resultados com previsibilidade e escala.' }
    },
    {
        tipo: 'problema_solucao', nome: 'Problema & Solução', desc: 'Descrição do problema e como você resolve',
        ativo: true, ordem: 1,
        config: { titulo: 'Problema & Solução', conteudo: 'Mostre o cenário atual do cliente e como sua solução resolve o problema.' }
    },
    {
        tipo: 'funcionalidades', nome: 'Funcionalidades em Destaque', desc: 'Lista de principais funcionalidades',
        ativo: true, ordem: 2,
        config: { titulo: 'Funcionalidades em destaque', itens: ['Atendimento mais rápido', 'Automação de rotinas', 'Indicadores em tempo real'] }
    },
    {
        tipo: 'planos_precos', nome: 'Planos e Preços', desc: 'Tabela com planos e valores',
        ativo: false, ordem: 3,
        config: { titulo: 'Planos e Preços', conteudo: 'Apresente os planos com clareza e proposta de valor.' }
    },
    {
        tipo: 'depoimentos', nome: 'Depoimentos', desc: 'Depoimentos de clientes',
        ativo: false, ordem: 4,
        config: { titulo: 'Depoimentos', conteudo: '"Excelente solução, aumentamos em 3x nossa eficiência comercial."' }
    },
    {
        tipo: 'roi_estimado', nome: 'ROI Estimado', desc: 'Retorno sobre investimento',
        ativo: false, ordem: 5,
        config: { titulo: 'ROI Estimado', conteudo: 'Retorno previsto em 6-12 meses com base no cenário atual.' }
    },
    {
        tipo: 'cta_aceite', nome: 'CTA de Aceite', desc: 'Call-to-action para aceitar proposta',
        ativo: true, ordem: 6,
        config: { titulo: 'Pronto para avançar?', botao_texto: 'Aceitar proposta', botao_link: '' }
    }
];

const DEFAULT_VARIAVEIS = [
    { nome: 'empresa', label: 'Nome da Empresa', tipo: 'texto', obrigatorio: true },
    { nome: 'responsavel', label: 'Nome do Responsável', tipo: 'texto', obrigatorio: true },
    { nome: 'segmento', label: 'Segmento', tipo: 'texto', obrigatorio: false },
    { nome: 'valor', label: 'Valor Proposto (R$)', tipo: 'numero', obrigatorio: false }
];

function cloneBlocos(src) { return (src || DEFAULT_BLOCOS).map(b => ({ ...b, config: b.config ? { ...b.config } : {} })); }
function cloneVars(src) { return (src || DEFAULT_VARIAVEIS).map(v => ({ ...v })); }

// ── Estado ─────────────────────────────────────────────────────────────────
const state = {
    id: null,
    blocos: [],
    variaveis: [],
    blocoSelecionado: null,
    varEditando: null,
    dirty: false
};

function normalizarBloco(bloco, ordemPadrao = 0) {
    return {
        tipo: bloco.tipo,
        nome: bloco.nome || bloco.tipo,
        desc: bloco.desc || '',
        ativo: bloco.ativo !== false,
        ordem: Number.isFinite(bloco.ordem) ? bloco.ordem : ordemPadrao,
        custom: !!bloco.custom,
        config: bloco.config && typeof bloco.config === 'object' ? { ...bloco.config } : {}
    };
}

// ── Inicialização ──────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
    const params = new URLSearchParams(window.location.search);
    const id = params.get('id');

    if (id) {
        state.id = parseInt(id, 10);
        document.getElementById('pb-page-title').textContent = 'Editar Proposta Pública';
        document.getElementById('pb-status-badge').textContent = 'Editando';
        await carregarProposta(state.id);
    } else {
        inicializarNova();
    }

    bindEventos();
    renderTudo();
});

function inicializarNova() {
    state.id = null;
    state.blocos = cloneBlocos().map(b => ({
        ...b,
        ativo: b.tipo === 'hero' || b.tipo === 'cta_aceite'
    }));
    state.variaveis = cloneVars();
    state.blocoSelecionado = state.blocos[0]?.tipo || null;
}

async function carregarProposta(id) {
    try {
        const proposta = await api.get(`/comercial/propostas-publicas/${id}`);
        if (!proposta) throw new Error('Proposta não encontrada');

        document.getElementById('pb-id').value = proposta.id;
        document.getElementById('pb-nome').value = proposta.nome || '';

        // Mesclar blocos
        const blocosProposta = Array.isArray(proposta.blocos)
            ? proposta.blocos.map((b, idx) => normalizarBloco(b, idx)) : [];
        const blocosPadrao = cloneBlocos().map((b, idx) => normalizarBloco(b, idx));
        const mapaProposta = new Map(blocosProposta.map(b => [b.tipo, b]));

        const blocosMesclados = blocosPadrao.map(base => {
            const existente = mapaProposta.get(base.tipo);
            return existente
                ? normalizarBloco({ ...base, ...existente, config: { ...base.config, ...existente.config } }, base.ordem)
                : base;
        });
        const blocosCustom = blocosProposta.filter(b => !blocosPadrao.some(p => p.tipo === b.tipo));
        state.blocos = [...blocosMesclados, ...blocosCustom].sort((a, b) => (a.ordem || 0) - (b.ordem || 0));

        // Variáveis
        state.variaveis = (proposta.variaveis || []).length > 0
            ? proposta.variaveis.map(v => ({ ...v }))
            : cloneVars();

        state.blocoSelecionado = state.blocos[0]?.tipo || null;
    } catch (error) {
        console.error('Erro ao carregar proposta:', error);
        showToast('Erro ao carregar proposta', 'error');
    }
}

// ── Bindagem de eventos ────────────────────────────────────────────────────
function bindEventos() {
    // Botões topbar
    document.getElementById('pb-btn-salvar').addEventListener('click', salvar);
    document.getElementById('pb-btn-cancelar').addEventListener('click', () => {
        if (state.dirty && !confirm('Tem alterações não salvas. Deseja sair?')) return;
        window.location.href = 'comercial.html';
    });

    // Nome
    document.getElementById('pb-nome').addEventListener('input', () => {
        state.dirty = true;
        renderPreview();
    });

    // Adicionar bloco
    document.getElementById('pb-btn-add-bloco').addEventListener('click', adicionarBlocoCustom);

    // Adicionar variável
    document.getElementById('pb-btn-add-var').addEventListener('click', adicionarVariavel);

    // Fechar editor
    document.getElementById('pb-editor-close').addEventListener('click', () => {
        state.blocoSelecionado = null;
        renderEditor();
        renderBlocos();
    });

    // Device toggle
    document.querySelectorAll('.pb-device-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.pb-device-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            const frame = document.getElementById('pb-preview-frame');
            frame.classList.toggle('mobile', btn.dataset.device === 'mobile');
        });
    });
}

// ── Render tudo ────────────────────────────────────────────────────────────
function renderTudo() {
    renderBlocos();
    renderVariaveis();
    renderEditor();
    renderPreview();
}

// ── Render Blocos (sidebar) ────────────────────────────────────────────────
let _blocosDelegated = false;
function renderBlocos() {
    const container = document.getElementById('pb-blocos-list');
    if (!container) return;

    container.innerHTML = state.blocos.map(bloco => `
        <div class="pb-bloco-item ${state.blocoSelecionado === bloco.tipo ? 'selected' : ''}"
             draggable="true" data-tipo="${bloco.tipo}">
            <span class="pb-bloco-handle" title="Arrastar">⋮⋮</span>
            <div class="pb-bloco-info" data-action="select" data-tipo="${bloco.tipo}">
                <div class="pb-bloco-nome">${esc(bloco.nome)}</div>
                <div class="pb-bloco-desc">${esc(bloco.desc)}</div>
            </div>
            <label class="pb-bloco-toggle">
                <input type="checkbox" ${bloco.ativo ? 'checked' : ''} data-action="toggle" data-tipo="${bloco.tipo}">
                <span class="pb-bloco-toggle-slider"></span>
            </label>
            ${bloco.custom ? `<button class="pb-bloco-delete" data-action="delete" data-tipo="${bloco.tipo}" title="Excluir bloco">🗑</button>` : ''}
        </div>
    `).join('');

    // Event delegation (bindé uma única vez)
    if (!_blocosDelegated) {
        container.addEventListener('click', handleBlocoClick);
        container.addEventListener('change', handleBlocoChange);
        _blocosDelegated = true;
    }
    configurarDragDrop(container);
}

function handleBlocoClick(e) {
    const selectEl = e.target.closest('[data-action="select"]');
    if (selectEl) {
        state.blocoSelecionado = selectEl.dataset.tipo;
        state.dirty = true;
        renderBlocos();
        renderEditor();
        return;
    }
    const deleteEl = e.target.closest('[data-action="delete"]');
    if (deleteEl) {
        const tipo = deleteEl.dataset.tipo;
        state.blocos = state.blocos.filter(b => b.tipo !== tipo);
        if (state.blocoSelecionado === tipo) {
            state.blocoSelecionado = state.blocos[0]?.tipo || null;
        }
        state.dirty = true;
        renderTudo();
    }
}

function handleBlocoChange(e) {
    const toggleEl = e.target.closest('[data-action="toggle"]');
    if (toggleEl) {
        const bloco = state.blocos.find(b => b.tipo === toggleEl.dataset.tipo);
        if (bloco) {
            bloco.ativo = toggleEl.checked;
            state.dirty = true;
            renderPreview();
        }
    }
}

function adicionarBlocoCustom() {
    const id = `custom_${Date.now()}`;
    const bloco = {
        tipo: id, nome: 'Bloco Customizado', desc: 'Conteúdo livre',
        ativo: true, ordem: state.blocos.length, custom: true,
        config: { titulo: 'Novo bloco', conteudo: 'Edite este conteúdo no editor.', itens: [] }
    };
    state.blocos.push(bloco);
    state.blocoSelecionado = bloco.tipo;
    state.dirty = true;
    renderTudo();
}

// ── Drag and Drop ──────────────────────────────────────────────────────────
function configurarDragDrop(container) {
    let draggedEl = null;

    container.querySelectorAll('.pb-bloco-item').forEach(item => {
        item.addEventListener('dragstart', e => {
            draggedEl = e.currentTarget;
            e.currentTarget.classList.add('dragging');
            e.dataTransfer.effectAllowed = 'move';
        });
        item.addEventListener('dragend', e => {
            e.currentTarget.classList.remove('dragging');
            atualizarOrdem(container);
        });
        item.addEventListener('dragover', e => {
            e.preventDefault();
            if (!draggedEl || draggedEl === e.currentTarget) return;
            const rect = e.currentTarget.getBoundingClientRect();
            const midY = rect.top + rect.height / 2;
            if (e.clientY < midY) {
                container.insertBefore(draggedEl, e.currentTarget);
            } else {
                container.insertBefore(draggedEl, e.currentTarget.nextSibling);
            }
        });
    });
}

function atualizarOrdem(container) {
    container.querySelectorAll('.pb-bloco-item').forEach((item, idx) => {
        const bloco = state.blocos.find(b => b.tipo === item.dataset.tipo);
        if (bloco) bloco.ordem = idx;
    });
    state.blocos.sort((a, b) => a.ordem - b.ordem);
    state.dirty = true;
    renderPreview();
}

// ── Render Variáveis (sidebar) ─────────────────────────────────────────────
let _varsDelegated = false;
function renderVariaveis() {
    const container = document.getElementById('pb-variaveis-list');
    if (!container) return;

    if (state.variaveis.length === 0) {
        container.innerHTML = '<div class="pb-var-empty">Nenhuma variável configurada</div>';
        return;
    }

    container.innerHTML = state.variaveis.map((v, idx) => {
        if (state.varEditando === idx) {
            return renderVarEditor(v, idx);
        }
        return `
            <div class="pb-var-item">
                <span class="pb-var-tag">{{${esc(v.nome)}}}</span>
                <span class="pb-var-label">${esc(v.label)}</span>
                <div class="pb-var-actions">
                    <button class="pb-var-edit-btn" data-var-action="edit" data-idx="${idx}" title="Editar">✎</button>
                    <button class="pb-var-del-btn" data-var-action="delete" data-idx="${idx}" title="Remover">✕</button>
                </div>
            </div>
        `;
    }).join('');

    if (!_varsDelegated) {
        container.addEventListener('click', handleVarClick);
        _varsDelegated = true;
    }
}

function renderVarEditor(v, idx) {
    return `
        <div class="pb-var-editor" data-idx="${idx}">
            <div class="fg">
                <label class="fl">Nome (chave)</label>
                <input class="fi" type="text" value="${esc(v.nome)}" data-field="nome">
            </div>
            <div class="fg">
                <label class="fl">Label</label>
                <input class="fi" type="text" value="${esc(v.label)}" data-field="label">
            </div>
            <div style="display:flex;gap:12px;align-items:center">
                <div class="fg" style="flex:1">
                    <label class="fl">Tipo</label>
                    <select class="fs" data-field="tipo">
                        <option value="texto" ${v.tipo === 'texto' ? 'selected' : ''}>Texto</option>
                        <option value="numero" ${v.tipo === 'numero' ? 'selected' : ''}>Número</option>
                        <option value="data" ${v.tipo === 'data' ? 'selected' : ''}>Data</option>
                    </select>
                </div>
                <label style="display:flex;align-items:center;gap:6px;font-size:12px;margin-top:14px;cursor:pointer">
                    <input type="checkbox" ${v.obrigatorio ? 'checked' : ''} data-field="obrigatorio">
                    Obrigatório
                </label>
            </div>
            <div class="pb-var-editor-actions">
                <button class="btn btn-sm btn-secondary" data-var-action="cancel-edit">Cancelar</button>
                <button class="btn btn-sm btn-primary" data-var-action="save-edit" data-idx="${idx}">OK</button>
            </div>
        </div>
    `;
}

function handleVarClick(e) {
    const el = e.target.closest('[data-var-action]');
    if (!el) return;
    const action = el.dataset.varAction;
    const idx = parseInt(el.dataset.idx, 10);

    if (action === 'edit') {
        state.varEditando = idx;
        renderVariaveis();
    } else if (action === 'delete') {
        state.variaveis.splice(idx, 1);
        state.dirty = true;
        state.varEditando = null;
        renderVariaveis();
        renderPreview();
    } else if (action === 'save-edit') {
        const editor = document.querySelector(`.pb-var-editor[data-idx="${idx}"]`);
        if (editor) {
            const v = state.variaveis[idx];
            v.nome = editor.querySelector('[data-field="nome"]').value.trim() || v.nome;
            v.label = editor.querySelector('[data-field="label"]').value.trim() || v.label;
            v.tipo = editor.querySelector('[data-field="tipo"]').value;
            v.obrigatorio = editor.querySelector('[data-field="obrigatorio"]').checked;
            state.dirty = true;
        }
        state.varEditando = null;
        renderVariaveis();
        renderPreview();
    } else if (action === 'cancel-edit') {
        state.varEditando = null;
        renderVariaveis();
    }
}

function adicionarVariavel() {
    state.variaveis.push({
        nome: `variavel_${Date.now()}`,
        label: 'Nova Variável',
        tipo: 'texto',
        obrigatorio: false
    });
    state.varEditando = state.variaveis.length - 1;
    state.dirty = true;
    renderVariaveis();
}

// ── Render Editor (bloco selecionado) ──────────────────────────────────────
function renderEditor() {
    const panel = document.getElementById('pb-editor-panel');
    const body = document.getElementById('pb-editor-body');
    const title = document.getElementById('pb-editor-title');

    const bloco = state.blocos.find(b => b.tipo === state.blocoSelecionado);
    if (!bloco) {
        panel.style.display = 'none';
        return;
    }

    panel.style.display = '';
    title.textContent = `Configuração: ${bloco.nome}`;

    const itensTexto = Array.isArray(bloco.config?.itens) ? bloco.config.itens.join('\n') : '';

    body.innerHTML = `
        <div class="pb-editor-row">
            <div class="fg">
                <label class="fl">Nome do bloco</label>
                <input class="fi" type="text" value="${esc(bloco.nome)}" data-cfg="nome" data-is-campo="1">
            </div>
            <div class="fg">
                <label class="fl">Descrição curta</label>
                <input class="fi" type="text" value="${esc(bloco.desc)}" data-cfg="desc" data-is-campo="1">
            </div>
        </div>
        <div class="pb-editor-row">
            <div class="fg">
                <label class="fl">Título</label>
                <input class="fi" type="text" value="${esc(bloco.config?.titulo || '')}" data-cfg="titulo">
            </div>
            <div class="fg">
                <label class="fl">Subtítulo</label>
                <input class="fi" type="text" value="${esc(bloco.config?.subtitulo || '')}" data-cfg="subtitulo">
            </div>
        </div>
        <div class="fg">
            <label class="fl">Conteúdo</label>
            <textarea class="ft" rows="3" data-cfg="conteudo">${esc(bloco.config?.conteudo || '')}</textarea>
        </div>
        <div class="fg">
            <label class="fl">Itens (1 por linha)</label>
            <textarea class="ft" rows="3" data-cfg="itens">${esc(itensTexto)}</textarea>
        </div>
        <div class="pb-editor-row">
            <div class="fg">
                <label class="fl">Texto do botão</label>
                <input class="fi" type="text" value="${esc(bloco.config?.botao_texto || '')}" data-cfg="botao_texto">
            </div>
            <div class="fg">
                <label class="fl">Link do botão</label>
                <input class="fi" type="text" value="${esc(bloco.config?.botao_link || '')}" data-cfg="botao_link">
            </div>
        </div>
    `;

    // Bind inputs do editor
    body.querySelectorAll('[data-cfg]').forEach(input => {
        input.addEventListener('input', () => {
            const campo = input.dataset.cfg;
            const isCampo = input.dataset.isCampo === '1';
            const valor = input.tagName === 'TEXTAREA' ? input.value : input.value;

            if (isCampo) {
                bloco[campo] = valor;
                renderBlocos();
            } else if (campo === 'itens') {
                bloco.config.itens = valor.split('\n').map(v => v.trim()).filter(Boolean);
            } else {
                bloco.config = bloco.config || {};
                bloco.config[campo] = valor;
            }
            state.dirty = true;
            renderPreview();
        });
    });
}

// ── Render Preview ─────────────────────────────────────────────────────────
function renderPreview() {
    const container = document.getElementById('pb-preview-content');
    if (!container) return;

    const nome = document.getElementById('pb-nome')?.value || 'Nome da Proposta';
    const blocosAtivos = state.blocos.filter(b => b.ativo);

    if (blocosAtivos.length === 0) {
        container.innerHTML = `
            <div class="pb-pv-empty">
                <div class="pb-pv-empty-icon">📄</div>
                <h3>Nenhum bloco ativo</h3>
                <p>Ative pelo menos um bloco na sidebar para ver o preview.</p>
            </div>
        `;
        return;
    }

    let html = '';

    blocosAtivos.forEach(bloco => {
        const titulo = esc(bloco.config?.titulo || bloco.nome || 'Bloco');
        const conteudo = esc(bloco.config?.conteudo || '');
        const itens = Array.isArray(bloco.config?.itens) ? bloco.config.itens : [];

        switch (bloco.tipo) {
            case 'hero':
                html += `
                    <div class="pb-pv-hero">
                        <h2>${titulo}</h2>
                        <p>${esc(bloco.config?.subtitulo || '{{empresa}} • {{responsavel}}')}</p>
                        ${conteudo ? `<p style="margin-top:8px;opacity:0.85">${conteudo}</p>` : ''}
                    </div>
                `;
                break;

            case 'problema_solucao':
                html += `
                    <div class="pb-pv-section">
                        <h3>${titulo}</h3>
                        <p>${conteudo || 'Descrição do problema e como sua solução resolve.'}</p>
                    </div>
                `;
                break;

            case 'funcionalidades':
                html += `
                    <div class="pb-pv-section">
                        <h3>${titulo}</h3>
                        <div class="pb-pv-features-grid">
                            ${(itens.length ? itens : ['Funcionalidade 1', 'Funcionalidade 2', 'Funcionalidade 3']).map(item =>
                                `<div class="pb-pv-feature-item">${esc(item)}</div>`
                            ).join('')}
                        </div>
                    </div>
                `;
                break;

            case 'planos_precos':
                html += `
                    <div class="pb-pv-section">
                        <h3>${titulo}</h3>
                        <p>${conteudo || 'Tabela de planos e preços configuráveis.'}</p>
                    </div>
                `;
                break;

            case 'depoimentos':
                html += `
                    <div class="pb-pv-section">
                        <h3>${titulo}</h3>
                        <div class="pb-pv-testimonial">
                            <p>${conteudo || '"Excelente solução!"'}</p>
                            <p style="font-size:13px;color:var(--color-on-surface-muted);margin-top:8px">— Cliente Satisfeito</p>
                        </div>
                    </div>
                `;
                break;

            case 'roi_estimado':
                html += `
                    <div class="pb-pv-section">
                        <h3>${titulo}</h3>
                        <div class="pb-pv-roi-value">${esc(bloco.config?.valor || '300%')}</div>
                        <p>${conteudo || 'Retorno sobre investimento em 12 meses.'}</p>
                    </div>
                `;
                break;

            case 'cta_aceite':
                html += `
                    <div class="pb-pv-cta">
                        <h3>${titulo}</h3>
                        <button class="pb-pv-cta-btn">${esc(bloco.config?.botao_texto || 'Aceitar Proposta')}</button>
                    </div>
                `;
                break;

            default:
                html += `
                    <div class="pb-pv-section">
                        <h3>${titulo}</h3>
                        <p>${conteudo || 'Bloco customizado'}</p>
                        ${itens.length ? `
                            <div class="pb-pv-features-grid">
                                ${itens.map(item => `<div class="pb-pv-feature-item">${esc(item)}</div>`).join('')}
                            </div>
                        ` : ''}
                    </div>
                `;
                break;
        }
    });

    container.innerHTML = html;
}

// ── Salvar ─────────────────────────────────────────────────────────────────
async function salvar() {
    const nome = document.getElementById('pb-nome').value.trim();
    if (!nome) {
        showToast('Digite o nome da proposta', 'error');
        document.getElementById('pb-nome').focus();
        return;
    }

    const dados = {
        nome: nome,
        blocos: state.blocos,
        variaveis: state.variaveis
    };

    const btn = document.getElementById('pb-btn-salvar');
    btn.disabled = true;
    btn.textContent = 'Salvando...';

    try {
        if (state.id) {
            await api.put(`/comercial/propostas-publicas/${state.id}`, dados);
            showToast('Proposta atualizada com sucesso', 'success');
        } else {
            const result = await api.post('/comercial/propostas-publicas', dados);
            if (result?.id) {
                state.id = result.id;
                const url = new URL(window.location);
                url.searchParams.set('id', result.id);
                window.history.replaceState({}, '', url);
                document.getElementById('pb-id').value = result.id;
                document.getElementById('pb-page-title').textContent = 'Editar Proposta Pública';
                document.getElementById('pb-status-badge').textContent = 'Editando';
            }
            showToast('Proposta criada com sucesso', 'success');
        }
        state.dirty = false;
    } catch (error) {
        console.error('Erro ao salvar proposta:', error);
        showToast(error.message || 'Erro ao salvar proposta', 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = `
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg>
            Salvar
        `;
    }
}

// Aviso ao sair sem salvar
window.addEventListener('beforeunload', (e) => {
    if (state.dirty) {
        e.preventDefault();
        e.returnValue = '';
    }
});
