// Comercial Import - JavaScript

class ComercialImport {
    constructor() {
        this.currentStep = 1;
        this.method = null;
        this.previewData = null;
        this.segments = [];
        
        this.init();
    }

    init() {
        this.loadUser();
        this.loadSegments();
        this.bindEvents();
    }

    /** Resposta da API pode ser lista ou objeto com lista aninhada. */
    normalizeSegmentList(data) {
        if (Array.isArray(data)) return data;
        if (data && Array.isArray(data.items)) return data.items;
        if (data && Array.isArray(data.segmentos)) return data.segmentos;
        return [];
    }

    bindEvents() {
        const form = document.getElementById('import-config-form');
        if (!form) return;
        form.addEventListener('submit', (e) => {
            e.preventDefault();
            this.confirmImport();
        });
    }

    async loadUser() {
        try {
            const user = await api.get('/auth/me');
            const nome = user && (user.nome || user.name);
            if (!nome) return;
            const el =
                document.getElementById('sidebar-user-name') ||
                document.getElementById('user-name');
            if (el) el.textContent = nome;
        } catch (error) {
            console.error('Erro ao carregar usuário:', error);
        }
    }

    async loadSegments() {
        try {
            const raw = await api.get('/comercial/import/segments');
            this.segments = this.normalizeSegmentList(raw);
            this.renderSegments();
        } catch (error) {
            console.error('Erro ao carregar segmentos:', error);
            this.segments = [];
            this.renderSegments();
        }
    }

    renderSegments() {
        const select = document.getElementById('segment-select');
        if (!select) return;
        select.innerHTML = '<option value="">Selecione um segmento</option>';

        this.segments.forEach(segment => {
            const option = document.createElement('option');
            option.value = segment.id;
            option.textContent = segment.nome;
            select.appendChild(option);
        });
    }

    selectMethod(method) {
        this.method = method;
        
        // Atualizar UI
        document.querySelectorAll('.method-card').forEach(card => {
            card.classList.remove('selected');
        });
        
        const selectedCard = document.querySelector(`.method-card[data-method="${method}"]`);
        if (selectedCard) {
            selectedCard.classList.add('selected');
        }

        // Mostrar área correta
        if (method === 'colar') {
            document.getElementById('paste-area').classList.remove('hidden');
            document.getElementById('csv-area').classList.add('hidden');
        } else {
            document.getElementById('paste-area').classList.add('hidden');
            document.getElementById('csv-area').classList.remove('hidden');
        }

        this.goToStep(2);
    }

    goToStep(step) {
        // Esconder todas as etapas
        document.querySelectorAll('.step-section').forEach(section => {
            section.classList.add('hidden');
        });

        // Mostrar etapa atual
        const stepElement = document.getElementById(`step-${this.getStepName(step)}`);
        if (stepElement) {
            stepElement.classList.remove('hidden');
        }

        this.currentStep = step;
    }

    getStepName(step) {
        const steps = ['method', 'upload', 'preview', 'config', 'result'];
        return steps[step - 1];
    }

    async previewImport() {
        const method = this.method;
        let data;

        if (method === 'colar') {
            const textData = document.getElementById('text-data').value.trim();
            if (!textData) {
                toastr.error('Por favor, cole os dados para importação.');
                return;
            }
            data = textData;
        } else if (method === 'csv') {
            const fileInput = document.getElementById('csv-file');
            const file = fileInput.files[0];
            
            if (!file) {
                toastr.error('Por favor, selecione um arquivo CSV.');
                return;
            }

            const base64 = await this.fileToBase64(file);
            data = base64;
        }

        try {
            this.previewData = await api.post('/comercial/import/preview', {
                metodo: method,
                dados: data
            });
            this.renderPreview();
            this.goToStep(3);
        } catch (error) {
            console.error('Erro na pré-visualização:', error);
            if (typeof toastr !== 'undefined') {
                toastr.error('Erro ao processar pré-visualização.');
            } else {
                showToast('Erro ao processar pré-visualização.', 'error');
            }
        }
    }

    renderPreview() {
        const data = this.previewData;
        const totalEl = document.getElementById('total-records');
        if (totalEl) totalEl.textContent = data.total;
        document.getElementById('valid-records').textContent = data.total - data.duplicatas - data.invalidos;
        document.getElementById('duplicate-records').textContent = data.duplicatas;
        document.getElementById('invalid-records').textContent = data.invalidos;

        // Renderizar tabela
        const tbody = document.getElementById('preview-table').querySelector('tbody');
        tbody.innerHTML = '';

        data.leads.forEach(lead => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${lead.nome_responsavel}</td>
                <td>${lead.nome_empresa}</td>
                <td>${lead.whatsapp || '-'}</td>
                <td>${lead.email || '-'}</td>
                <td>${lead.cidade || '-'}</td>
                <td><span class="status valid">Válido</span></td>
            `;
            tbody.appendChild(row);
        });
    }

    async executeImport() {
        const method = this.method;
        let data;

        if (method === 'colar') {
            const textData = document.getElementById('text-data').value.trim();
            data = textData;
        } else if (method === 'csv') {
            const fileInput = document.getElementById('csv-file');
            const file = fileInput.files[0];
            const base64 = await this.fileToBase64(file);
            data = base64;
        }

        try {
            const segVal = document.getElementById('segment-select')?.value;
            const segId = segVal ? parseInt(segVal, 10) : null;
            const tplVal = document.getElementById('template-select-import')?.value;
            const templateId = tplVal ? parseInt(tplVal, 10) : null;

            const result = await api.post('/comercial/import/execute', {
                metodo: method,
                dados: data,
                segmento_id: segId != null && !Number.isNaN(segId) ? segId : null,
                campaign_id: templateId != null && !Number.isNaN(templateId) ? templateId : null
            });
            this.renderResult(result);
            this.goToStep(5);
        } catch (error) {
            console.error('Erro na importação:', error);
            if (typeof toastr !== 'undefined') {
                toastr.error('Erro ao processar importação.');
            } else {
                showToast('Erro ao processar importação.', 'error');
            }
        }
    }

    renderResult(result) {
        // Atualizar contadores
        document.getElementById('success-count').textContent = result.total_validos;
        document.getElementById('error-count').textContent = result.total_invalidos;

        // Renderizar sucessos
        const successUl = document.getElementById('success-ul');
        successUl.innerHTML = '';
        
        result.leads_criados.forEach(lead => {
            const li = document.createElement('li');
            li.innerHTML = `<strong>${lead.nome_responsavel}</strong> - ${lead.whatsapp || lead.email}`;
            successUl.appendChild(li);
        });

        // Renderizar erros
        const errorUl = document.getElementById('error-ul');
        errorUl.innerHTML = '';
        
        result.erros.forEach(error => {
            const li = document.createElement('li');
            li.innerHTML = `<span class="error-text">${error}</span>`;
            errorUl.appendChild(li);
        });
    }

    async confirmImport() {
        await this.executeImport();
    }

    resetImport() {
        this.currentStep = 1;
        this.method = null;
        this.previewData = null;
        
        // Limpar campos
        document.getElementById('text-data').value = '';
        document.getElementById('csv-file').value = '';
        document.getElementById('segment-select').value = '';
        const welcomeCb = document.getElementById('send-welcome');
        if (welcomeCb) welcomeCb.checked = true;

        // Voltar para etapa 1
        this.goToStep(1);
    }

    fileToBase64(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.readAsDataURL(file);
            reader.onload = () => {
                const base64 = reader.result.split(',')[1];
                resolve(base64);
            };
            reader.onerror = error => reject(error);
        });
    }
}

// Inicializar quando o DOM estiver pronto
document.addEventListener('DOMContentLoaded', () => {
    new ComercialImport();
});