/**
 * KnowledgeBaseManager.js
 * 
 * Gerencia a interface de Base de Conhecimento (RAG) do assistente.
 */

const KnowledgeBaseManager = (function() {
    const listEl = document.getElementById('ragDocumentsList');
    const statusEl = document.getElementById('ragUploadStatus');
    const fileInput = document.getElementById('ragFileInput');
    const uploadBtn = document.getElementById('btnRagUpload');

    return {
        init: function() {
            if (!uploadBtn) return;

            uploadBtn.addEventListener('click', () => fileInput.click());
            
            fileInput.addEventListener('change', (e) => {
                if (e.target.files.length > 0) {
                    this.uploadDocument(e.target.files[0]);
                }
            });

            this.loadDocuments();
        },

        loadDocuments: async function() {
            if (!listEl) return;
            
            try {
                const response = await ApiService.get('/ai/rag/documents');
                if (response.success) {
                    this.renderDocuments(response.documents);
                }
            } catch (err) {
                console.error("[KnowledgeBase] Erro ao carregar documentos:", err);
            }
        },

        renderDocuments: function(documents) {
            if (!listEl) return;
            
            if (documents.length === 0) {
                listEl.innerHTML = '<p class="pref-hint" style="text-align:center; padding: 20px;">Nenhum documento indexado.</p>';
                return;
            }

            // Agrupar por fonte (arquivo) para não mostrar centenas de chunks
            const sources = {};
            documents.forEach(doc => {
                if (!sources[doc.fonte]) {
                    sources[doc.fonte] = {
                        name: doc.fonte,
                        chunks: 0,
                        created_at: doc.criado_em
                    };
                }
                sources[doc.fonte].chunks++;
            });

            listEl.innerHTML = Object.values(sources).map(src => `
                <div class="rag-document-item">
                    <div class="rag-document-info">
                        <div class="rag-document-name">${src.name}</div>
                        <div class="rag-document-meta">${src.chunks} partes indexadas • ${new Date(src.created_at).toLocaleDateString()}</div>
                    </div>
                    <div class="rag-document-actions">
                        <button type="button" class="btn btn-ghost btn-xs btn-danger-text" onclick="KnowledgeBaseManager.deleteSource('${src.name}')" title="Excluir arquivo da base">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
                        </button>
                    </div>
                </div>
            `).join('');
        },

        uploadDocument: async function(file) {
            if (!statusEl) return;
            
            statusEl.textContent = `Subindo ${file.name}...`;
            statusEl.style.color = 'var(--ai-accent)';
            
            const formData = new FormData();
            formData.append('file', file);
            
            try {
                // ApiService.post usually expects JSON. For multipart, we might need a custom call or check ApiService.
                // Assuming ApiService handles FormData correctly or uses fetch underlying.
                const response = await fetch('/api/v1/ai/rag/upload', {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${localStorage.getItem('cotte_token')}`
                    },
                    body: formData
                });
                
                const result = await response.json();
                
                if (result.success) {
                    statusEl.textContent = `Sucesso! ${result.chunks_indexed} partes indexadas.`;
                    statusEl.style.color = 'var(--ai-green)';
                    this.loadDocuments();
                    setTimeout(() => { statusEl.textContent = ''; }, 5000);
                } else {
                    statusEl.textContent = `Erro: ${result.detail || 'Falha no upload'}`;
                    statusEl.style.color = '#ef4444';
                }
            } catch (err) {
                console.error("[KnowledgeBase] Erro no upload:", err);
                statusEl.textContent = "Erro de conexão.";
                statusEl.style.color = '#ef4444';
            }
            
            fileInput.value = ''; // Limpar input
        },

        deleteSource: async function(filename) {
            if (!confirm(`Deseja remover "${filename}" da base de conhecimento?`)) return;
            
            try {
                const response = await ApiService.delete(`/ai/rag/documents/source/${encodeURIComponent(filename)}`);
                if (response.success) {
                    this.loadDocuments();
                }
            } catch (err) {
                console.error("[KnowledgeBase] Erro ao excluir fonte:", err);
            }
        }
    };
})();

window.KnowledgeBaseManager = KnowledgeBaseManager;
