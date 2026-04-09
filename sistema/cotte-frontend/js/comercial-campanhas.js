// Comercial Campanhas - JavaScript

class ComercialCampanhas {
    constructor() {
        this.campanhas = [];
        this.filteredCampanhas = [];
        this.templates = [];
        this.leads = [];
        this.selectedLeads = new Set();
        this.currentCampanha = null;
        
        this.init();
    }

    init() {
        this.loadUser();
        this.loadCampanhas();
        this.loadTemplates();
        this.loadLeads();
        this.bindEvents();
    }

    bindEvents() {
        document.getElementById('campaign-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.saveCampanha();
        });

        document.getElementById('leads-search').addEventListener('input', (e) => {
            this.filterLeads(e.target.value);
        });
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

    async loadLeads() {
        try {
            const response = await fetch('/comercial/leads');
            this.leads = await response.json();
            this.renderLeadsList();
        } catch (error) {
            console.error('Erro ao carregar leads:', error);
        }
    }

    renderCampanhas() {
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

    renderLeadsList() {
        const list = document.getElementById('leads-list');
        list.innerHTML = '';

        this.leads.forEach(lead => {
            const card = document.createElement('div');
            card.className = 'lead-card';
            card.innerHTML = `
                <div class="lead-info">
                    <h4>${lead.nome_responsavel}</h4>
                    <p>${lead.nome_empresa}</p>
                    <p>${lead.whatsapp || lead.email || '-'}</p>
                </div>
                <div class="lead-actions">
                    <input type="checkbox" class="lead-checkbox" value="${lead.id}" onchange="app.toggleLeadSelection(${lead.id})">
                </div>
            `;
            list.appendChild(card);
        });
    }

    filterLeads(searchTerm) {
        const list = document.getElementById('leads-list');
        list.innerHTML = '';

        const filteredLeads = this.leads.filter(lead => 
            lead.nome_responsavel.toLowerCase().includes(searchTerm.toLowerCase()) ||
            lead.nome_empresa.toLowerCase().includes(searchTerm.toLowerCase()) ||
            (lead.whatsapp && lead.whatsapp.includes(searchTerm)) ||
            (lead.email && lead.email.toLowerCase().includes(searchTerm.toLowerCase()))
        );

        filteredLeads.forEach(lead => {
            const card = document.createElement('div');
            card.className = 'lead-card';
            card.innerHTML = `
                <div class="lead-info">
                    <h4>${lead.nome_responsavel}</h4>
                    <p>${lead.nome_empresa}</p>
                    <p>${lead.whatsapp || lead.email || '-'}</p>
                </div>
                <div class="lead-actions">
                    <input type="checkbox" class="lead-checkbox" value="${lead.id}" ${this.selectedLeads.has(lead.id) ? 'checked' : ''} onchange="app.toggleLeadSelection(${lead.id})">
                </div>
            `;
            list.appendChild(card);
        });
    }

    toggleLeadSelection(leadId) {
        if (this.selectedLeads.has(leadId)) {
            this.selectedLeads.delete(leadId);
        } else {
            this.selectedLeads.add(leadId);
        }
    }

    openCampaignModal() {
        this.currentCampanha = null;
        document.getElementById('campaign-modal-title').textContent = 'Nova Campanha';
        document.getElementById('campaign-form').reset();
        this.selectedLeads.clear();
        this.renderLeadsList();
        document.getElementById('campaign-modal-overlay').style.display = 'flex';
    }

    async saveCampanha() {
        const data = {
            nome: document.getElementById('campaign-nome').value,
            template_id: parseInt(document.getElementById('campaign-template').value),
            canal: document.getElementById('campaign-canal').value,
            lead_ids: Array.from(this.selectedLeads)
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