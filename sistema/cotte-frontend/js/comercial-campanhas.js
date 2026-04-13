// Comercial Campanhas - JavaScript

class ComercialCampanhas {
    constructor() {
        this.campanhas = [];
        this.filteredCampanhas = [];
        this.templates = [];
        this.leads = [];
        this.selectedLeads = new Map(); // Armazena id => objeto do lead
        this.currentCampanha = null;

        // Infinite scroll params
        this.leadsPage = 1;
        this.hasMoreLeads = true;
        this.isLoadingLeads = false;
        
        this.init();
    }

    init() {
        this.loadUser();
        this.loadCampanhas();
        this.loadTemplates();
        this.bindEvents();
    }

    bindEvents() {
        document.getElementById('campaign-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.saveCampanha();
        });

        document.getElementById('campaign-canal').addEventListener('change', () => {
            this.updateSelectionPanel();
            this.loadLeads(true);
        });

        // Setup intersection observer for infinite scroll
        const container = document.querySelector('.leads-list-container');
        if (container) {
            container.addEventListener('scroll', () => {
                if (this.isLoadingLeads || !this.hasMoreLeads) return;
                if (container.scrollTop + container.clientHeight >= container.scrollHeight - 50) {
                    this.loadLeads(false);
                }
            });
        }
    }

    async loadUser() {
        try {
            const response = await fetch('/auth/me');
            const user = await response.json();
            document.getElementById('user-name').textContent = user.nome;
        } catch (error) {
            console.error('Erro ao carregar usuário:', error);
        }
    }

    async loadCampanhas() {
        try {
            const response = await fetch('/comercial/campaigns');
            this.campanhas = await response.json();
            this.filteredCampanhas = [...this.campanhas];
            this.renderCampanhas();
        } catch (error) {
            console.error('Erro ao carregar campanhas:', error);
            toastr.error('Erro ao carregar campanhas.');
        }
    }

    async loadTemplates() {
        try {
            const response = await fetch('/comercial/templates');
            this.templates = await response.json();
            this.renderTemplatesSelect();
        } catch (error) {
            console.error('Erro ao carregar templates:', error);
        }
    }

    filterLeadsAPI() {
        this.loadLeads(true);
    }

    applySmartList() {
        this.loadLeads(true);
    }

    async loadLeads(reset = true) {
        if (this.isLoadingLeads) return;
        this.isLoadingLeads = true;

        if (reset) {
            this.leadsPage = 1;
            this.leads = [];
            this.hasMoreLeads = true;
            document.getElementById('leads-list').innerHTML = '';
        }

        document.getElementById('leads-loading').style.display = 'block';

        try {
            const search = document.getElementById('leads-search').value || '';
            const smartList = document.getElementById('smart-list-select').value;
            
            let query = `?page=${this.leadsPage}&per_page=50`;
            if (search) query += `&search=${encodeURIComponent(search)}`;
            
            // Nunca trazer leads já fechados
            query += `&status_pipeline_notin=fechado_ganho,fechado_perdido`;

            // Smart Lists conditions
            if (smartList === 'novos_7d') {
                query += `&novo_dias=7`;
            } else if (smartList === 'sem_contato_30d') {
                query += `&sem_contato_dias=30`;
            }

            // Considera o canal da campanha, caso selecionado, para não trazer contatos inúteis
            const canal = document.getElementById('campaign-canal')?.value;
            if (canal === 'whatsapp') {
                query += `&has_whatsapp=true`;
            } else if (canal === 'email') {
                query += `&has_email=true`;
            }

            const response = await fetch(`/comercial/leads${query}`);
            const data = await response.json();
            
            const newLeads = data.items || [];
            this.leads = this.leads.concat(newLeads);
            
            if (newLeads.length < 50) {
                this.hasMoreLeads = false;
            }

            this.leadsPage++;
            this.renderLeadsList(newLeads);

        } catch (error) {
            console.error('Erro ao carregar leads:', error);
            toastr.error('Erro ao carregar lista de leads.');
        } finally {
            this.isLoadingLeads = false;
            document.getElementById('leads-loading').style.display = 'none';
        }
    }

    renderLeadsList(leadsToRender) {
        const list = document.getElementById('leads-list');
        if (this.leads.length === 0) {
            list.innerHTML = '<div class="no-data" style="color:var(--muted);text-align:center;padding:20px;">Nenhum lead encontrado com estes filtros.</div>';
            return;
        }

        const now = new Date();

        leadsToRender.forEach(lead => {
            const card = document.createElement('div');
            card.className = 'lead-card';
            card.style.display = 'flex';
            card.style.justifyContent = 'space-between';
            card.style.alignItems = 'center';
            card.style.padding = '10px 15px';
            card.style.border = '1px solid var(--border)';
            card.style.borderRadius = '6px';
            card.style.background = 'var(--surface)';

            // Termostato de spam: alerta visual se contatado nas últimas 48h
            let spamAlertHtml = '';
            if (lead.ultimo_disparo_em) {
                const ultimoDisparo = new Date(lead.ultimo_disparo_em);
                const diffHoras = (now - ultimoDisparo) / (1000 * 60 * 60);
                if (diffHoras < 48) {
                    spamAlertHtml = `<span title="Recebeu campanha recente (há ${Math.round(diffHoras)}h)" style="background:#fef08a;color:#854d0e;font-size:10px;padding:2px 6px;border-radius:12px;margin-left:8px;display:inline-block;">⚠️ Disparo Recente</span>`;
                }
            }

            const wppDisplay = lead.whatsapp ? `WhatsApp: ${lead.whatsapp}` : '';
            const emailDisplay = lead.email ? `Email: ${lead.email}` : '';
            const separator = (wppDisplay && emailDisplay) ? ' | ' : '';
            
            const isChecked = this.selectedLeads.has(lead.id) ? 'checked' : '';

            card.innerHTML = `
                <div class="lead-info" style="flex:1;">
                    <div style="font-weight:600;margin-bottom:4px;">
                        ${lead.nome_responsavel || lead.nome_empresa} ${spamAlertHtml}
                    </div>
                    <div style="font-size:12px;color:var(--muted);">
                        ${wppDisplay}${separator}${emailDisplay}
                        ${!wppDisplay && !emailDisplay ? 'Sem contato' : ''}
                    </div>
                </div>
                <div class="lead-actions" style="margin-left:15px;">
                    <input type="checkbox" class="lead-checkbox" value="${lead.id}" ${isChecked} style="width:18px;height:18px;cursor:pointer;">
                </div>
            `;

            // Setup the event listener via js to pass the full object
            const cb = card.querySelector('.lead-checkbox');
            cb.addEventListener('change', () => this.toggleLeadSelection(lead.id, lead, cb.checked));

            list.appendChild(card);
        });
    }

    toggleLeadSelection(leadId, leadObj, isChecked) {
        if (isChecked) {
            this.selectedLeads.set(leadId, leadObj);
        } else {
            this.selectedLeads.delete(leadId);
        }
        this.updateSelectionPanel();
    }

    selectAllVisible() {
        const checkboxes = document.querySelectorAll('.lead-checkbox');
        checkboxes.forEach(cb => {
            if (!cb.checked) {
                cb.checked = true;
                const leadId = parseInt(cb.value);
                const leadObj = this.leads.find(l => l.id === leadId);
                if (leadObj) this.selectedLeads.set(leadId, leadObj);
            }
        });
        this.updateSelectionPanel();
    }

    clearSelection() {
        this.selectedLeads.clear();
        document.querySelectorAll('.lead-checkbox').forEach(cb => cb.checked = false);
        this.updateSelectionPanel();
    }

    updateSelectionPanel() {
        const countEl = document.getElementById('sel-count');
        const waEl = document.getElementById('sel-wa');
        const emEl = document.getElementById('sel-em');
        const btnSubmit = document.getElementById('btn-submit-campaign');

        let waValidos = 0;
        let emValidos = 0;

        for (const [id, lead] of this.selectedLeads.entries()) {
            if (lead.whatsapp) waValidos++;
            if (lead.email) emValidos++;
        }

        const total = this.selectedLeads.size;
        countEl.textContent = total;
        waEl.textContent = waValidos;
        emEl.textContent = emValidos;

        // Disabling logic based on selected channel
        const canal = document.getElementById('campaign-canal')?.value;
        let blockSubmit = false;

        if (total === 0) {
            blockSubmit = true;
        } else if (canal === 'whatsapp' && waValidos === 0) {
            blockSubmit = true;
        } else if (canal === 'email' && emValidos === 0) {
            blockSubmit = true;
        }

        btnSubmit.disabled = blockSubmit;
    }
        const list = document.getElementById('campaigns-list');
        list.innerHTML = '';

        if (this.filteredCampanhas.length === 0) {
            list.innerHTML = '<div class="no-data">Nenhuma campanha encontrada.</div>';
            return;
        }

        this.filteredCampanhas.forEach(campanha => {
            const card = document.createElement('div');
            card.className = 'campaign-card';
            card.innerHTML = `
                <div class="campaign-header">
                    <h3>${campanha.nome}</h3>
                    <div class="campaign-badges">
                        <span class="badge">${this.getStatusLabel(campanha.status)}</span>
                        <span class="badge">${this.getCanalLabel(campanha.canal)}</span>
                    </div>
                </div>
                <div class="campaign-info">
                    <p><strong>Template:</strong> ${campanha.template.nome}</p>
                    <p><strong>Total de Leads:</strong> ${campanha.total_leads}</p>
                    <p><strong>Enviados:</strong> ${campanha.enviados}</p>
                    <p><strong>Entregues:</strong> ${campanha.entregues}</p>
                    <p><strong>Respondidos:</strong> ${campanha.respondidos}</p>
                    <p><strong>Criado em:</strong> ${this.formatDate(campanha.criado_em)}</p>
                </div>
                <div class="campaign-actions">
                    <button class="btn btn-sm btn-secondary" onclick="app.viewMetrics(${campanha.id})">Métricas</button>
                    <button class="btn btn-sm btn-primary" onclick="app.startDisparo(${campanha.id})">Iniciar Disparo</button>
                    <button class="btn btn-sm btn-error" onclick="app.deleteCampanha(${campanha.id})">Excluir</button>
                </div>
            `;
            list.appendChild(card);
        });
    }

    getStatusLabel(status) {
        const labels = {
            'agendada': 'Agendada',
            'em_andamento': 'Em Andamento',
            'concluida': 'Concluída',
            'cancelada': 'Cancelada'
        };
        return labels[status] || status;
    }

    getCanalLabel(canal) {
        const labels = {
            'whatsapp': 'WhatsApp',
            'email': 'Email',
            'ambos': 'Ambos'
        };
        return labels[canal] || canal;
    }

    formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleString('pt-BR');
    }

    renderTemplatesSelect() {
        const select = document.getElementById('campaign-template');
        select.innerHTML = '<option value="">Selecione um template</option>';
        
        this.templates.forEach(template => {
            const option = document.createElement('option');
            option.value = template.id;
            option.textContent = template.nome;
            select.appendChild(option);
        });
    }

    openCampaignModal() {
        this.currentCampanha = null;
        document.getElementById('campaign-modal-title').textContent = 'Nova Campanha';
        document.getElementById('campaign-form').reset();
        this.selectedLeads.clear();
        this.updateSelectionPanel();
        this.loadLeads(true);
        document.getElementById('campaign-modal-overlay').style.display = 'flex';
    }

    async saveCampanha() {
        const data = {
            nome: document.getElementById('campaign-nome').value,
            template_id: parseInt(document.getElementById('campaign-template').value),
            canal: document.getElementById('campaign-canal').value,
            lead_ids: Array.from(this.selectedLeads.keys())
        };

        if (data.lead_ids.length === 0) {
            toastr.error('Selecione ao menos um lead para a campanha.');
            return;
        }

        try {
            const response = await fetch('/comercial/campaigns', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            });

            if (!response.ok) {
                throw new Error('Erro ao criar campanha');
            }

            toastr.success('Campanha criada com sucesso!');
            this.closeCampaignModal();
            this.loadCampanhas();

        } catch (error) {
            console.error('Erro ao criar campanha:', error);
            toastr.error('Erro ao criar campanha.');
        }
    }

    async startDisparo(campanhaId) {
        if (!confirm('Iniciar disparo da campanha?')) {
            return;
        }

        try {
            const response = await fetch(`/comercial/campaigns/${campanhaId}/disparo`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    lead_ids: [],
                    canal: null
                })
            });

            if (!response.ok) {
                throw new Error('Erro ao iniciar disparo');
            }

            toastr.success('Disparo iniciado em background!');
            this.loadCampanhas();

        } catch (error) {
            console.error('Erro ao iniciar disparo:', error);
            toastr.error('Erro ao iniciar disparo.');
        }
    }

    async viewMetrics(campanhaId) {
        try {
            const response = await fetch(`/comercial/campaigns/${campanhaId}/metrics`);
            const metrics = await response.json();

            const content = document.getElementById('metrics-content');
            content.innerHTML = `
                <div class="metrics-grid">
                    <div class="metric-card">
                        <h4>Total de Leads</h4>
                        <span class="metric-value">${metrics.total_leads}</span>
                    </div>
                    <div class="metric-card">
                        <h4>Enviados</h4>
                        <span class="metric-value">${metrics.enviados}</span>
                    </div>
                    <div class="metric-card">
                        <h4>Entregues</h4>
                        <span class="metric-value">${metrics.entregues}</span>
                    </div>
                    <div class="metric-card">
                        <h4>Respondidos</h4>
                        <span class="metric-value">${metrics.respondidos}</span>
                    </div>
                    <div class="metric-card">
                        <h4>Taxa de Entrega</h4>
                        <span class="metric-value">${metrics.taxa_entrega.toFixed(2)}%</span>
                    </div>
                    <div class="metric-card">
                        <h4>Taxa de Resposta</h4>
                        <span class="metric-value">${metrics.taxa_resposta.toFixed(2)}%</span>
                    </div>
                </div>
                <div class="metrics-details">
                    <h4>Detalhes por Status:</h4>
                    <ul>
                        ${Object.entries(metrics.leads_por_status).map(([status, count]) => `
                            <li><strong>${status}:</strong> ${count}</li>
                        `).join('')}
                    </ul>
                </div>
            `;

            document.getElementById('metrics-modal-overlay').style.display = 'flex';

        } catch (error) {
            console.error('Erro ao carregar métricas:', error);
            toastr.error('Erro ao carregar métricas.');
        }
    }

    async deleteCampanha(campanhaId) {
        if (!confirm('Tem certeza que deseja excluir esta campanha?')) {
            return;
        }

        try {
            const response = await fetch(`/comercial/campaigns/${campanhaId}`, {
                method: 'DELETE'
            });

            if (!response.ok) {
                throw new Error('Erro ao excluir campanha');
            }

            toastr.success('Campanha excluída com sucesso!');
            this.loadCampanhas();

        } catch (error) {
            console.error('Erro ao excluir campanha:', error);
            toastr.error('Erro ao excluir campanha.');
        }
    }

    applyCampaignFilters() {
        const status = document.getElementById('filter-status').value;
        const canal = document.getElementById('filter-canal').value;

        this.filteredCampanhas = this.campanhas.filter(campanha => {
            const matchesStatus = !status || campanha.status === status;
            const matchesCanal = !canal || campanha.canal === canal;
            
            return matchesStatus && matchesCanal;
        });

        this.renderCampanhas();
    }

    clearCampaignFilters() {
        document.getElementById('filter-status').value = '';
        document.getElementById('filter-canal').value = '';
        this.filteredCampanhas = [...this.campanhas];
        this.renderCampanhas();
    }

    closeCampaignModal() {
        document.getElementById('campaign-modal-overlay').style.display = 'none';
    }

    closeMetricsModal() {
        document.getElementById('metrics-modal-overlay').style.display = 'none';
    }
}

// Inicializar quando o DOM estiver pronto
document.addEventListener('DOMContentLoaded', () => {
    window.app = new ComercialCampanhas();
});