// Comercial Templates - JavaScript

class ComercialTemplates {
    constructor() {
        this.templates = [];
        this.filteredTemplates = [];
        this.currentTemplate = null;
        
        this.init();
    }

    init() {
        this.loadUser();
        this.loadTemplates();
        this.bindEvents();
    }

    bindEvents() {
        document.getElementById('template-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.saveTemplate();
        });

        document.getElementById('template-canal').addEventListener('change', (e) => {
            this.toggleAssuntoField(e.target.value);
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

    async loadTemplates() {
        try {
            const response = await fetch('/comercial/templates');
            this.templates = await response.json();
            this.filteredTemplates = [...this.templates];
            this.renderTemplates();
        } catch (error) {
            console.error('Erro ao carregar templates:', error);
            toastr.error('Erro ao carregar templates.');
        }
    }

    renderTemplates() {
        const grid = document.getElementById('templates-grid');
        grid.innerHTML = '';

        if (this.filteredTemplates.length === 0) {
            grid.innerHTML = '<div class="no-data">Nenhum template encontrado.</div>';
            return;
        }

        this.filteredTemplates.forEach(template => {
            const card = document.createElement('div');
            card.className = 'template-card';
            card.innerHTML = `
                <div class="template-header">
                    <h3>${template.nome}</h3>
                    <div class="template-badges">
                        <span class="badge">${this.getTipoLabel(template.tipo)}</span>
                        <span class="badge">${this.getCanalLabel(template.canal)}</span>
                        <span class="badge ${template.ativo ? 'badge-success' : 'badge-error'}">${template.ativo ? 'Ativo' : 'Inativo'}</span>
                    </div>
                </div>
                <div class="template-content">
                    <p>${this.truncateText(template.conteudo, 100)}</p>
                </div>
                <div class="template-actions">
                    <button class="btn btn-sm btn-secondary" onclick="app.editTemplate(${template.id})">Editar</button>
                    <button class="btn btn-sm btn-ghost" onclick="app.previewTemplate(${template.id})">Pré-visualizar</button>
                    <button class="btn btn-sm btn-error" onclick="app.deleteTemplate(${template.id})">Excluir</button>
                </div>
            `;
            grid.appendChild(card);
        });
    }

    getTipoLabel(tipo) {
        const labels = {
            'mensagem_inicial': 'Mensagem Inicial',
            'followup': 'Follow-up',
            'proposta_comercial': 'Proposta Comercial',
            'email_comercial': 'Email Comercial'
        };
        return labels[tipo] || tipo;
    }

    getCanalLabel(canal) {
        const labels = {
            'whatsapp': 'WhatsApp',
            'email': 'Email',
            'ambos': 'Ambos'
        };
        return labels[canal] || canal;
    }

    truncateText(text, maxLength) {
        if (text.length <= maxLength) return text;
        return text.substring(0, maxLength) + '...';
    }

    openTemplateModal() {
        this.currentTemplate = null;
        document.getElementById('modal-title').textContent = 'Novo Template';
        document.getElementById('template-form').reset();
        document.getElementById('template-id').value = '';
        document.getElementById('assunto-group').style.display = 'none';
        document.getElementById('template-modal-overlay').style.display = 'flex';
    }

    editTemplate(id) {
        const template = this.templates.find(t => t.id === id);
        if (!template) return;

        this.currentTemplate = template;
        document.getElementById('modal-title').textContent = 'Editar Template';
        document.getElementById('template-id').value = template.id;
        document.getElementById('template-nome').value = template.nome;
        document.getElementById('template-tipo').value = template.tipo;
        document.getElementById('template-canal').value = template.canal;
        document.getElementById('template-assunto').value = template.assunto || '';
        document.getElementById('template-conteudo').value = template.conteudo;
        document.getElementById('template-ativo').checked = template.ativo;

        this.toggleAssuntoField(template.canal);
        document.getElementById('template-modal-overlay').style.display = 'flex';
    }

    async saveTemplate() {
        const id = document.getElementById('template-id').value;
        const data = {
            nome: document.getElementById('template-nome').value,
            tipo: document.getElementById('template-tipo').value,
            canal: document.getElementById('template-canal').value,
            assunto: document.getElementById('template-assunto').value,
            conteudo: document.getElementById('template-conteudo').value,
            ativo: document.getElementById('template-ativo').checked
        };

        try {
            let response;
            if (id) {
                response = await fetch(`/comercial/templates/${id}`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(data)
                });
            } else {
                response = await fetch('/comercial/templates', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(data)
                });
            }

            if (!response.ok) {
                throw new Error('Erro ao salvar template');
            }

            toastr.success('Template salvo com sucesso!');
            this.closeTemplateModal();
            this.loadTemplates();

        } catch (error) {
            console.error('Erro ao salvar template:', error);
            toastr.error('Erro ao salvar template.');
        }
    }

    async deleteTemplate(id) {
        if (!confirm('Tem certeza que deseja excluir este template?')) {
            return;
        }

        try {
            const response = await fetch(`/comercial/templates/${id}`, {
                method: 'DELETE'
            });

            if (!response.ok) {
                throw new Error('Erro ao excluir template');
            }

            toastr.success('Template excluído com sucesso!');
            this.loadTemplates();

        } catch (error) {
            console.error('Erro ao excluir template:', error);
            toastr.error('Erro ao excluir template.');
        }
    }

    async previewTemplate(templateId) {
        // Para simplificar, vamos usar um lead de exemplo
        // Na prática, você poderia permitir selecionar um lead real
        const leadId = 1; // ID de exemplo

        try {
            const response = await fetch(`/comercial/templates/${templateId}/preview?lead_id=${leadId}`);
            const preview = await response.json();

            const content = document.getElementById('preview-content');
            content.innerHTML = `
                <div class="preview-section">
                    <h4>Assunto:</h4>
                    <p>${preview.assunto || 'Sem assunto'}</p>
                </div>
                <div class="preview-section">
                    <h4>Conteúdo:</h4>
                    <div class="preview-text">${preview.conteudo}</div>
                </div>
            `;

            document.getElementById('preview-modal-overlay').style.display = 'flex';

        } catch (error) {
            console.error('Erro ao pré-visualizar template:', error);
            toastr.error('Erro ao pré-visualizar template.');
        }
    }

    toggleAssuntoField(canal) {
        const assuntoGroup = document.getElementById('assunto-group');
        if (canal === 'email' || canal === 'ambos') {
            assuntoGroup.style.display = 'block';
        } else {
            assuntoGroup.style.display = 'none';
        }
    }

    applyFilters() {
        const tipo = document.getElementById('filter-tipo').value;
        const canal = document.getElementById('filter-canal').value;
        const ativo = document.getElementById('filter-ativo').value;

        this.filteredTemplates = this.templates.filter(template => {
            const matchesTipo = !tipo || template.tipo === tipo;
            const matchesCanal = !canal || template.canal === canal;
            const matchesAtivo = ativo === '' || template.ativo.toString() === ativo;
            
            return matchesTipo && matchesCanal && matchesAtivo;
        });

        this.renderTemplates();
    }

    clearFilters() {
        document.getElementById('filter-tipo').value = '';
        document.getElementById('filter-canal').value = '';
        document.getElementById('filter-ativo').value = '';
        this.filteredTemplates = [...this.templates];
        this.renderTemplates();
    }

    closeTemplateModal() {
        document.getElementById('template-modal-overlay').style.display = 'none';
    }

    closePreviewModal() {
        document.getElementById('preview-modal-overlay').style.display = 'none';
    }
}

// Inicializar quando o DOM estiver pronto
document.addEventListener('DOMContentLoaded', () => {
    window.app = new ComercialTemplates();
});