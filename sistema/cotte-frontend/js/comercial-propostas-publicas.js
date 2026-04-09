// COTTE — Comercial - Propostas Públicas
// Módulo para gestão de propostas públicas interativas

const DEFAULT_BLOCOS_DISPONIVEIS = [
        {
            tipo: 'hero',
            nome: 'Hero / Pitch',
            desc: 'Título principal e apresentação',
            ativo: true,
            ordem: 0,
            config: {
                titulo: 'Proposta Comercial Sob Medida',
                subtitulo: 'Uma solução pensada para {{empresa}}',
                conteudo: 'Transforme resultados com previsibilidade e escala.'
            }
        },
        {
            tipo: 'problema_solucao',
            nome: 'Problema & Solução',
            desc: 'Descrição do problema e como você resolve',
            ativo: true,
            ordem: 1,
            config: {
                titulo: 'Problema & Solução',
                conteudo: 'Mostre o cenário atual do cliente e como sua solução resolve o problema.'
            }
        },
        {
            tipo: 'funcionalidades',
            nome: 'Funcionalidades em Destaque',
            desc: 'Lista de principais funcionalidades',
            ativo: true,
            ordem: 2,
            config: {
                titulo: 'Funcionalidades em destaque',
                itens: ['Atendimento mais rápido', 'Automação de rotinas', 'Indicadores em tempo real']
            }
        },
        {
            tipo: 'planos_precos',
            nome: 'Planos e Preços',
            desc: 'Tabela com planos e valores',
            ativo: false,
            ordem: 3,
            config: {
                titulo: 'Planos e Preços',
                conteudo: 'Apresente os planos com clareza e proposta de valor.'
            }
        },
        {
            tipo: 'depoimentos',
            nome: 'Depoimentos',
            desc: 'Depoimentos de clientes',
            ativo: false,
            ordem: 4,
            config: {
                titulo: 'Depoimentos',
                conteudo: '"Excelente solução, aumentamos em 3x nossa eficiência comercial."'
            }
        },
        {
            tipo: 'roi_estimado',
            nome: 'ROI Estimado',
            desc: 'Retorno sobre investimento',
            ativo: false,
            ordem: 5,
            config: {
                titulo: 'ROI Estimado',
                conteudo: 'Retorno previsto em 6-12 meses com base no cenário atual.'
            }
        },
        {
            tipo: 'cta_aceite',
            nome: 'CTA de Aceite',
            desc: 'Call-to-action para aceitar proposta',
            ativo: true,
            ordem: 6,
            config: {
                titulo: 'Pronto para avançar?',
                botao_texto: 'Aceitar proposta',
                botao_link: ''
            }
        }
    ];

const DEFAULT_VARIAVEIS_PADRAO = [
        { nome: 'empresa', label: 'Nome da Empresa', tipo: 'texto', obrigatorio: true },
        { nome: 'responsavel', label: 'Nome do Responsável', tipo: 'texto', obrigatorio: true },
        { nome: 'segmento', label: 'Segmento', tipo: 'texto', obrigatorio: false },
        { nome: 'valor', label: 'Valor Proposto (R$)', tipo: 'numero', obrigatorio: false }
    ];

function cloneBlocosPadrao() {
    return DEFAULT_BLOCOS_DISPONIVEIS.map(bloco => ({ ...bloco }));
}

function cloneVariaveisPadrao() {
    return DEFAULT_VARIAVEIS_PADRAO.map(variavel => ({ ...variavel }));
}

// Estado global
let propostasPublicasState = {
    propostas: [],
    propostaEditando: null,
    blocosDisponiveis: cloneBlocosPadrao(),
    variaveisPadrao: cloneVariaveisPadrao(),
    blocoSelecionadoTipo: null
};

function clonarBloco(bloco) {
    return {
        ...bloco,
        config: bloco.config ? { ...bloco.config } : {}
    };
}

function getBlocoByTipo(tipo) {
    return propostasPublicasState.blocosDisponiveis.find(b => b.tipo === tipo);
}

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

function selecionarBlocoProposta(tipo) {
    propostasPublicasState.blocoSelecionadoTipo = tipo;
    renderModalPropostaBlocos();
    renderEditorBlocoSelecionado();
}

// Carregar propostas públicas
async function carregarPropostasPublicas() {
    try {
        const response = await api.get('/comercial/propostas-publicas');
        propostasPublicasState.propostas = Array.isArray(response) ? response : [];
        renderPropostasPublicas();
    } catch (error) {
        console.error('Erro ao carregar propostas públicas:', error);
        showToast('Erro ao carregar propostas públicas', 'error');
    }
}

// Renderizar tabela de propostas públicas
function renderPropostasPublicas() {
    const tbody = document.getElementById('propostas-publicas-tbody');
    const container = document.getElementById('propostas-publicas-cards-mobile');
    
    if (!tbody || !container) return;
    
    if (propostasPublicasState.propostas.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:24px;color:var(--muted)">Nenhuma proposta encontrada</td></tr>';
        container.innerHTML = '<div style="text-align:center;padding:24px;color:var(--muted)">Nenhuma proposta encontrada</div>';
        return;
    }
    
    // Tabela desktop
    tbody.innerHTML = propostasPublicasState.propostas.map(pp => {
        const blocosAtivos = (pp.blocos || []).filter(b => b.ativo).length;
        const totalVariaveis = (pp.variaveis || []).length;

        return `
        <tr>
            <td>${esc(pp.nome || 'Sem nome')}</td>
            <td>${blocosAtivos} ativos</td>
            <td>${totalVariaveis} variáveis</td>
            <td>
                <span class="badge ${pp.ativo ? 'ok' : ''}">
                    ${pp.ativo ? 'Ativo' : 'Inativo'}
                </span>
            </td>
            <td>${fmtData(pp.criado_em)}</td>
            <td>
                <button class="btn btn-sm btn-secondary" onclick="editarPropostaPublica(${pp.id})">Editar</button>
                <button class="btn btn-sm btn-primary" onclick="duplicarPropostaPublica(${pp.id})">Duplicar</button>
            </td>
        </tr>
        `;
    }).join('');
    
    // Cards mobile
    container.innerHTML = propostasPublicasState.propostas.map(pp => {
        const blocosAtivos = (pp.blocos || []).filter(b => b.ativo).length;
        const totalVariaveis = (pp.variaveis || []).length;

        return `
        <div class="mobile-card">
            <div class="mobile-card-header">
                <h3>${esc(pp.nome || 'Sem nome')}</h3>
                <span class="badge ${pp.ativo ? 'ok' : ''}">${pp.ativo ? 'Ativo' : 'Inativo'}</span>
            </div>
            <div class="mobile-card-body">
                <p>${blocosAtivos} blocos ativos • ${totalVariaveis} variáveis</p>
                <p class="mobile-card-meta">Criado em ${fmtData(pp.criado_em)}</p>
            </div>
            <div class="mobile-card-actions">
                <button class="btn btn-sm btn-secondary" onclick="editarPropostaPublica(${pp.id})">Editar</button>
                <button class="btn btn-sm btn-primary" onclick="duplicarPropostaPublica(${pp.id})">Duplicar</button>
            </div>
        </div>
        `;
    }).join('');
}

function resetTabsModalPropostaPublica() {
    document.querySelectorAll('#modal-proposta-publica [data-tab-pp]').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tabPp === 'blocos');
    });

    document.querySelectorAll('#modal-proposta-publica .tab-panel').forEach(panel => {
        panel.classList.toggle('active', panel.id === 'tab-pp-blocos');
    });
}

// Redireciona para página builder (nova proposta)
function novaPropostaPublica() {
    window.location.href = 'proposta-builder.html';
}

// Redireciona para página builder (editar proposta)
function editarPropostaPublica(id) {
    window.location.href = `proposta-builder.html?id=${id}`;
}

// Renderizar blocos no modal
function renderModalPropostaBlocos() {
    const container = document.getElementById('pp-blocos-list');
    if (!container) return;
    
    container.innerHTML = propostasPublicasState.blocosDisponiveis.map((bloco, index) => `
        <div class="pp-bloco-item ${propostasPublicasState.blocoSelecionadoTipo === bloco.tipo ? 'selected' : ''}" draggable="true" data-tipo="${bloco.tipo}">
            <span class="pp-bloco-handle">⋮⋮</span>
            <div class="pp-bloco-info">
                <div class="pp-bloco-nome">${bloco.nome}</div>
                <div class="pp-bloco-desc">${bloco.desc}</div>
            </div>
            <button class="btn btn-sm btn-ghost" type="button" onclick="selecionarBlocoProposta('${bloco.tipo}')">Editar</button>
            <label class="pp-bloco-toggle">
                <input type="checkbox" ${bloco.ativo ? 'checked' : ''} 
                       onchange="toggleBlocoProposta('${bloco.tipo}', this.checked)">
                <span class="pp-bloco-toggle-slider"></span>
            </label>
            ${bloco.custom ? `<button class="btn btn-sm btn-ghost" type="button" onclick="removerBlocoProposta('${bloco.tipo}')">Excluir</button>` : ''}
        </div>
    `).join('');
    
    // Configurar drag and drop
    configurarDragAndDropBlocos();
}

// Toggle bloco ativo/inativo
function toggleBlocoProposta(tipo, ativo) {
    const bloco = propostasPublicasState.blocosDisponiveis.find(b => b.tipo === tipo);
    if (bloco) {
        bloco.ativo = ativo;
        renderModalPropostaPreview();
    }
}

function removerBlocoProposta(tipo) {
    propostasPublicasState.blocosDisponiveis = propostasPublicasState.blocosDisponiveis.filter(b => b.tipo !== tipo);
    if (propostasPublicasState.blocoSelecionadoTipo === tipo) {
        propostasPublicasState.blocoSelecionadoTipo = propostasPublicasState.blocosDisponiveis[0]?.tipo || null;
    }
    atualizarOrdemBlocos();
    renderModalPropostaBlocos();
    renderEditorBlocoSelecionado();
    renderModalPropostaPreview();
}

function adicionarBlocoCustomizado() {
    const id = `custom_${Date.now()}`;
    const bloco = {
        tipo: id,
        nome: 'Bloco Customizado',
        desc: 'Conteúdo livre',
        ativo: true,
        ordem: propostasPublicasState.blocosDisponiveis.length,
        custom: true,
        config: {
            titulo: 'Novo bloco',
            conteudo: 'Edite este conteúdo no painel de configuração do bloco.',
            itens: []
        }
    };
    propostasPublicasState.blocosDisponiveis.push(bloco);
    propostasPublicasState.blocoSelecionadoTipo = bloco.tipo;
    renderModalPropostaBlocos();
    renderEditorBlocoSelecionado();
    renderModalPropostaPreview();
}

function atualizarCampoBloco(tipo, campo, valor) {
    const bloco = getBlocoByTipo(tipo);
    if (!bloco) return;
    bloco[campo] = valor;
    renderModalPropostaBlocos();
    renderModalPropostaPreview();
}

function atualizarConfigBloco(tipo, campo, valor) {
    const bloco = getBlocoByTipo(tipo);
    if (!bloco) return;
    bloco.config = bloco.config || {};
    bloco.config[campo] = valor;
    renderModalPropostaPreview();
}

function renderEditorBlocoSelecionado() {
    const container = document.getElementById('pp-bloco-config-editor');
    if (!container) return;
    const tipo = propostasPublicasState.blocoSelecionadoTipo;
    const bloco = getBlocoByTipo(tipo);
    if (!bloco) {
        container.style.display = 'none';
        container.innerHTML = '';
        return;
    }

    const itensTexto = Array.isArray(bloco.config?.itens) ? bloco.config.itens.join('\n') : '';
    container.style.display = 'block';
    container.innerHTML = `
      <div style="display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:10px">
        <strong>Configuração do bloco</strong>
        <span style="font-size:12px;color:var(--muted)">${esc(bloco.tipo)}</span>
      </div>
      <div class="fr">
        <div class="fg">
          <label class="fl">Nome do bloco</label>
          <input class="fi" type="text" value="${esc(bloco.nome || '')}" onchange="atualizarCampoBloco('${bloco.tipo}','nome', this.value)">
        </div>
        <div class="fg">
          <label class="fl">Descrição</label>
          <input class="fi" type="text" value="${esc(bloco.desc || '')}" onchange="atualizarCampoBloco('${bloco.tipo}','desc', this.value)">
        </div>
      </div>
      <div class="fg">
        <label class="fl">Título</label>
        <input class="fi" type="text" value="${esc(bloco.config?.titulo || '')}" onchange="atualizarConfigBloco('${bloco.tipo}','titulo', this.value)">
      </div>
      <div class="fg">
        <label class="fl">Subtítulo</label>
        <input class="fi" type="text" value="${esc(bloco.config?.subtitulo || '')}" onchange="atualizarConfigBloco('${bloco.tipo}','subtitulo', this.value)">
      </div>
      <div class="fg">
        <label class="fl">Conteúdo</label>
        <textarea class="ft" rows="3" onchange="atualizarConfigBloco('${bloco.tipo}','conteudo', this.value)">${esc(bloco.config?.conteudo || '')}</textarea>
      </div>
      <div class="fg">
        <label class="fl">Itens (1 por linha)</label>
        <textarea class="ft" rows="3" onchange="atualizarConfigBloco('${bloco.tipo}','itens', this.value.split('\n').map(v => v.trim()).filter(Boolean))">${esc(itensTexto)}</textarea>
      </div>
      <div class="fr">
        <div class="fg">
          <label class="fl">Texto do botão</label>
          <input class="fi" type="text" value="${esc(bloco.config?.botao_texto || '')}" onchange="atualizarConfigBloco('${bloco.tipo}','botao_texto', this.value)">
        </div>
        <div class="fg">
          <label class="fl">Link do botão</label>
          <input class="fi" type="text" value="${esc(bloco.config?.botao_link || '')}" onchange="atualizarConfigBloco('${bloco.tipo}','botao_link', this.value)">
        </div>
      </div>
    `;
}

// Configurar drag and drop dos blocos
function configurarDragAndDropBlocos() {
    const container = document.getElementById('pp-blocos-list');
    if (!container) return;
    
    let draggedElement = null;
    
    container.querySelectorAll('.pp-bloco-item').forEach(item => {
        item.addEventListener('dragstart', (e) => {
            draggedElement = e.currentTarget;
            e.currentTarget.classList.add('dragging');
        });
        
        item.addEventListener('dragend', (e) => {
            e.currentTarget.classList.remove('dragging');
        });
        
        item.addEventListener('dragover', (e) => {
            e.preventDefault();
            const afterElement = getDragAfterElement(container, e.clientY);
            if (afterElement == null) {
                container.appendChild(draggedElement);
            } else {
                container.insertBefore(draggedElement, afterElement);
            }
        });
        
        item.addEventListener('drop', (e) => {
            e.preventDefault();
            atualizarOrdemBlocos();
        });
    });
}

// Obter elemento após posição de drag
function getDragAfterElement(container, y) {
    const draggableElements = [...container.querySelectorAll('.pp-bloco-item:not(.dragging)')];
    
    return draggableElements.reduce((closest, child) => {
        const box = child.getBoundingClientRect();
        const offset = y - box.top - box.height / 2;
        
        if (offset < 0 && offset > closest.offset) {
            return { offset: offset, element: child };
        } else {
            return closest;
        }
    }, { offset: Number.NEGATIVE_INFINITY }).element;
}

// Atualizar ordem dos blocos
function atualizarOrdemBlocos() {
    const items = document.querySelectorAll('#pp-blocos-list .pp-bloco-item');
    items.forEach((item, index) => {
        const tipo = item.dataset.tipo;
        const bloco = propostasPublicasState.blocosDisponiveis.find(b => b.tipo === tipo);
        if (bloco) {
            bloco.ordem = index;
        }
    });
    
    // Ordenar array
    propostasPublicasState.blocosDisponiveis.sort((a, b) => a.ordem - b.ordem);
    renderModalPropostaPreview();
}

// Renderizar variáveis no modal
function renderModalPropostaVariaveis() {
    const container = document.getElementById('pp-variaveis-list');
    if (!container) return;
    
    if (propostasPublicasState.variaveisPadrao.length === 0) {
        container.innerHTML = '<p style="text-align:center;color:var(--muted);padding:20px">Nenhuma variável configurada</p>';
        return;
    }
    
    container.innerHTML = propostasPublicasState.variaveisPadrao.map((variavel, index) => `
        <div class="pp-variavel-item">
            <div class="pp-variavel-header">
                <span class="pp-variavel-title">{{${variavel.nome}}}</span>
                <button class="btn btn-sm btn-ghost" onclick="removerVariavelProposta(${index})">Remover</button>
            </div>
            <div class="pp-variavel-fields">
                <div class="fg">
                    <label class="fl">Label</label>
                    <input type="text" class="fi" value="${variavel.label}" 
                           onchange="atualizarVariavelProposta(${index}, 'label', this.value)">
                </div>
                <div class="fg">
                    <label class="fl">Tipo</label>
                    <select class="fs" onchange="atualizarVariavelProposta(${index}, 'tipo', this.value)">
                        <option value="texto" ${variavel.tipo === 'texto' ? 'selected' : ''}>Texto</option>
                        <option value="numero" ${variavel.tipo === 'numero' ? 'selected' : ''}>Número</option>
                        <option value="data" ${variavel.tipo === 'data' ? 'selected' : ''}>Data</option>
                    </select>
                </div>
            </div>
            <div style="margin-top:8px">
                <label style="display:flex;align-items:center;gap:8px;font-size:13px">
                    <input type="checkbox" ${variavel.obrigatorio ? 'checked' : ''} 
                           onchange="atualizarVariavelProposta(${index}, 'obrigatorio', this.checked)">
                    Campo obrigatório
                </label>
            </div>
        </div>
    `).join('');
}

// Adicionar variável
function adicionarVariavelProposta() {
    const novaVariavel = {
        nome: `variavel_${Date.now()}`,
        label: 'Nova Variável',
        tipo: 'texto',
        obrigatorio: false
    };
    propostasPublicasState.variaveisPadrao.push(novaVariavel);
    renderModalPropostaVariaveis();
}

// Remover variável
function removerVariavelProposta(index) {
    propostasPublicasState.variaveisPadrao.splice(index, 1);
    renderModalPropostaVariaveis();
    renderModalPropostaPreview();
}

// Atualizar variável
function atualizarVariavelProposta(index, campo, valor) {
    const variavel = propostasPublicasState.variaveisPadrao[index];
    if (variavel) {
        variavel[campo] = valor;
        renderModalPropostaPreview();
    }
}

// Renderizar preview
function renderModalPropostaPreview() {
    const container = document.getElementById('pp-preview-content');
    if (!container) return;
    
    const nome = document.getElementById('pp-nome').value || 'Nome da Proposta';
    const blocosAtivos = propostasPublicasState.blocosDisponiveis.filter(b => b.ativo);
    
    if (blocosAtivos.length === 0) {
        container.innerHTML = '<p style="text-align:center;color:var(--muted);padding:40px">Ative pelo menos um bloco para ver o preview</p>';
        return;
    }
    
    const hero = blocosAtivos.find(b => b.tipo === 'hero');
    const heroTitulo = hero?.config?.titulo || nome;
    const heroSub = hero?.config?.subtitulo || '{{empresa}} • {{responsavel}}';
    const heroConteudo = hero?.config?.conteudo || '';

    let previewHTML = `
        <div class="pp-preview-container">
            <div class="pp-preview-hero">
                <h2 class="pp-preview-title">${esc(heroTitulo)}</h2>
                <p class="pp-preview-subtitle">${esc(heroSub)}</p>
                ${heroConteudo ? `<p style="margin-top:8px">${esc(heroConteudo)}</p>` : ''}
            </div>
    `;
    
    blocosAtivos.forEach(bloco => {
        if (bloco.tipo === 'hero') {
            return;
        }
        const titulo = esc(bloco.config?.titulo || bloco.nome || 'Bloco');
        const conteudo = esc(bloco.config?.conteudo || '');
        const itens = Array.isArray(bloco.config?.itens) ? bloco.config.itens : [];

        switch (bloco.tipo) {
            case 'problema_solucao':
                previewHTML += `
                    <div style="margin-bottom:24px">
                        <h3 style="margin:0 0 8px 0">${titulo}</h3>
                        <p style="color:var(--muted)">${conteudo || 'Descrição do problema e como sua solução resolve'}</p>
                    </div>
                `;
                break;
            case 'funcionalidades':
                previewHTML += `
                    <div style="margin-bottom:24px">
                        <h3 style="margin:0 0 12px 0">${titulo}</h3>
                        <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
                            ${(itens.length ? itens : ['Funcionalidade 1', 'Funcionalidade 2']).map(item => `<div style="padding:12px;background:var(--surface);border-radius:8px">• ${esc(item)}</div>`).join('')}
                        </div>
                    </div>
                `;
                break;
            case 'planos_precos':
                previewHTML += `
                    <div style="margin-bottom:24px">
                        <h3 style="margin:0 0 12px 0">${titulo}</h3>
                        <p style="color:var(--muted)">${conteudo || 'Tabela de planos e preços configuráveis'}</p>
                    </div>
                `;
                break;
            case 'depoimentos':
                previewHTML += `
                    <div style="margin-bottom:24px">
                        <h3 style="margin:0 0 12px 0">${titulo}</h3>
                        <div style="padding:16px;background:var(--surface);border-radius:8px">
                            <p>${conteudo || '"Excelente solução!"'}</p>
                            <p style="font-size:14px;color:var(--muted)">- Cliente Satisfeito</p>
                        </div>
                    </div>
                `;
                break;
            case 'roi_estimado':
                previewHTML += `
                    <div style="margin-bottom:24px">
                        <h3 style="margin:0 0 12px 0">${titulo}</h3>
                        <p style="font-size:32px;font-weight:700;color:var(--success)">${esc(bloco.config?.valor || '300%')}</p>
                        <p style="color:var(--muted)">${conteudo || 'Retorno sobre investimento em 12 meses'}</p>
                    </div>
                `;
                break;
            case 'cta_aceite':
                previewHTML += `
                    <div style="text-align:center;margin-top:32px">
                        <h3 style="margin-bottom:12px">${titulo}</h3>
                        <button class="btn btn-primary" style="font-size:18px;padding:16px 32px">${esc(bloco.config?.botao_texto || 'Aceitar Proposta')}</button>
                    </div>
                `;
                break;
            default:
                previewHTML += `
                    <div style="margin-bottom:24px">
                        <h3 style="margin:0 0 8px 0">${titulo}</h3>
                        <p style="color:var(--muted)">${conteudo || 'Bloco customizado'}</p>
                    </div>
                `;
                break;
        }
    });
    
    previewHTML += '</div>';
    container.innerHTML = previewHTML;
}

// Salvar proposta pública
async function salvarPropostaPublica() {
    try {
        const nome = document.getElementById('pp-nome').value.trim();
        if (!nome) {
            showToast('Digite o nome da proposta', 'error');
            return;
        }
        
        const dados = {
            nome: nome,
            blocos: propostasPublicasState.blocosDisponiveis,
            variaveis: propostasPublicasState.variaveisPadrao
        };
        
        const id = document.getElementById('pp-id').value;
        
        if (id) {
            // Editar
            await api.put(`/comercial/propostas-publicas/${id}`, dados);
            showToast('Proposta atualizada com sucesso', 'success');
        } else {
            // Criar
            await api.post('/comercial/propostas-publicas', dados);
            showToast('Proposta criada com sucesso', 'success');
        }
        
        document.getElementById('modal-proposta-publica').classList.remove('open');
        carregarPropostasPublicas();
    } catch (error) {
        console.error('Erro ao salvar proposta:', error);
        showToast(error.message || 'Erro ao salvar proposta', 'error');
    }
}

// Duplicar proposta pública
async function duplicarPropostaPublica(id) {
    try {
        const proposta = propostasPublicasState.propostas.find(p => p.id === id);
        if (!proposta) return;
        
        const dados = {
            nome: `${proposta.nome} (cópia)`,
            blocos: proposta.blocos,
            variaveis: proposta.variaveis
        };
        
        await api.post('/comercial/propostas-publicas', dados);
        showToast('Proposta duplicada com sucesso', 'success');
        carregarPropostasPublicas();
    } catch (error) {
        console.error('Erro ao duplicar proposta:', error);
        showToast('Erro ao duplicar proposta', 'error');
    }
}

function fecharModalEnviarProposta() {
    document.getElementById('modal-enviar-proposta')?.classList.remove('open');
}

function fecharModalAnalyticsProposta() {
    document.getElementById('modal-analytics-proposta')?.classList.remove('open');
}

// Inicialização dos listeners (apenas elementos que ainda existem na página)
document.addEventListener('DOMContentLoaded', () => {
    // Botão nova proposta (redireciona para builder)
    const btnNova = document.getElementById('btn-nova-proposta-publica');
    if (btnNova) {
        btnNova.addEventListener('click', novaPropostaPublica);
    }

    // Modais que continuam existindo (enviar e analytics)
    document.querySelector('#modal-enviar-proposta .modal-close')?.addEventListener('click', fecharModalEnviarProposta);
    document.querySelector('#modal-enviar-proposta .modal-footer .btn-secondary')?.addEventListener('click', fecharModalEnviarProposta);

    document.querySelector('#modal-analytics-proposta .modal-close')?.addEventListener('click', fecharModalAnalyticsProposta);
    document.querySelector('#modal-analytics-proposta .modal-footer .btn-secondary')?.addEventListener('click', fecharModalAnalyticsProposta);
});

// Exportar funções para uso global
window.novaPropostaPublica = novaPropostaPublica;
window.editarPropostaPublica = editarPropostaPublica;
window.duplicarPropostaPublica = duplicarPropostaPublica;
window.toggleBlocoProposta = toggleBlocoProposta;
window.selecionarBlocoProposta = selecionarBlocoProposta;
window.removerBlocoProposta = removerBlocoProposta;
window.atualizarCampoBloco = atualizarCampoBloco;
window.atualizarConfigBloco = atualizarConfigBloco;
window.adicionarVariavelProposta = adicionarVariavelProposta;
window.removerVariavelProposta = removerVariavelProposta;
window.atualizarVariavelProposta = atualizarVariavelProposta;
window.salvarPropostaPublica = salvarPropostaPublica;
