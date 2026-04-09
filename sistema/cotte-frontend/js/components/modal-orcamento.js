// Componente Modal de Orçamento (compartilhado entre index.html e orcamentos.html)
// Uso: adicione <script src="js/components/modal-orcamento.js"></script> antes de fechar </body>
// Para customizar o footer, defina window.modalOrcamentoFooterConfig antes de carregar este script
(function() {
  if (document.getElementById('modal-novo-orcamento')) return;

  const defaultFooter = `
    <button class="btn btn-ghost" onclick="fecharModal()">Cancelar</button>
    <button class="btn btn-primary" onclick="salvarOrcamento()" id="btn-criar-orc">✅ Criar Orçamento</button>
  `;
  const customFooter = window.modalOrcamentoFooterConfig || defaultFooter;

  const modalHTML = `
<div class="modal-overlay" id="modal-novo-orcamento">
  <div class="modal">
    <div class="modal-header">
      <div class="modal-title" id="modal-orc-title">✨ Novo Orçamento</div>
      <button class="modal-close" onclick="fecharModal()">✕</button>
    </div>
    <div class="modal-body">
      <div class="tabs" id="modal-tabs">
        <button class="tab active" onclick="switchTab(this,'manual')">✍️ Manual</button>
        <button class="tab" id="tab-ia-btn" onclick="switchTab(this,'ia')">🤖 Via IA</button>
      </div>

      <div id="tab-manual" style="display:flex;flex-direction:column;gap:18px">
        <div class="form-row">
          <div class="form-group full">
            <label>Cliente *</label>
            <div class="cliente-autocomplete">
              <input type="text" id="orc-cliente-input" placeholder="Digite o nome do cliente..." autocomplete="off"
                oninput="void filtrarSugestoesCliente(this.value)" onfocus="void filtrarSugestoesCliente(this.value)">
              <div id="cliente-sugestoes" class="cliente-sugestoes-list" style="display:none"></div>
            </div>
            <input type="hidden" id="orc-cliente">
          </div>
        </div>
        <div class="form-group">
          <label>Itens do Orçamento</label>
          <div class="items-section" id="items-list">
            <div class="item-row">
              <div style="position:relative">
                <input type="text" placeholder="Descrição do serviço (digite para buscar no catálogo)"
                  oninput="sugerirItemCatalogo(this)" onfocus="sugerirItemCatalogo(this)"
                  onblur="setTimeout(()=>this.nextElementSibling.style.display='none',150)"
                  style="width:100%;box-sizing:border-box">
                <div class="cliente-sugestoes-list item-catalogo-sugestoes" style="display:none"></div>
              </div>
              <input type="number" placeholder="Qtd" value="1" min="1">
              <input type="number" placeholder="Valor R$" oninput="updateTotal()">
              <button class="remove-btn" onclick="removeItem(this)">−</button>
            </div>
          </div>
          <div style="display:flex;gap:8px;margin-top:8px">
            <button class="add-item-btn" style="flex:1" onclick="addItem()">＋ Adicionar item</button>
            <button class="add-item-btn"
              style="flex:1;color:var(--green);border-color:rgba(16,185,129,0.3);background:var(--green-dim)"
              onclick="void abrirModalCatalogo()">📦 Do Catálogo</button>
          </div>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>Validade</label>
            <select id="orc-validade">
              <option value="7">7 dias</option>
              <option value="15">15 dias</option>
              <option value="30">30 dias</option>
            </select>
          </div>
          <div class="form-group">
            <label>Pagamento</label>
            <select id="orc-pagamento" onchange="atualizarResumoFormaPagamento()">
              <option value="">Carregando...</option>
            </select>
            <div id="resumo-forma-pagamento"
              style="display:none;margin-top:6px;padding:7px 10px;border-radius:7px;background:rgba(0,229,160,0.06);border:1px solid rgba(0,229,160,0.2);font-size:11px;color:var(--muted)">
            </div>
          </div>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>Desconto</label>
            <div style="display:flex;gap:8px;align-items:center">
              <select id="orc-desconto-tipo" onchange="updateTotal()" style="width:130px;flex-shrink:0">
                <option value="percentual">% Percentual</option>
                <option value="fixo">R$ Fixo</option>
              </select>
              <input type="number" id="orc-desconto" placeholder="0" min="0" step="0.01" oninput="updateTotal()"
                style="flex:1">
            </div>
          </div>
          <div class="form-group">
            <label>Observações</label>
            <textarea id="orc-obs" placeholder="Condições, garantias..." style="min-height:60px"></textarea>
          </div>
          <div class="form-group" style="margin-top:12px">
            <label>Agendamento do orçamento</label>
            <select id="orc-agendamento-modo" class="form-control">
              <option value="NAO_USA">Sem agendamento</option>
              <option value="OPCIONAL">Agendamento opcional</option>
              <option value="OBRIGATORIO">Agendamento obrigatório</option>
            </select>
          </div>
          <div class="form-group" style="margin-top:12px">
            <label style="display:flex;align-items:center;gap:8px;font-size:13px;cursor:pointer;user-select:none;color:var(--text);font-weight:500">
              <input type="checkbox" id="orc-exigir-otp" style="width:16px;height:16px;accent-color:var(--accent);cursor:pointer">
              Exigir confirmação por código (OTP)
            </label>
            <div style="font-size:11px;color:var(--muted);margin-left:24px;margin-top:2px">
              Obrigatório para o aceite deste orçamento, independente do valor.
            </div>
          </div>
        </div>
        <div class="total-row" style="flex-direction:column;align-items:stretch;gap:4px;border-bottom:none;padding-bottom:0;margin-bottom:0;background:transparent">
          <div id="subtotal-row" style="display:none;justify-content:space-between;font-size:13px;color:var(--muted)">
            <span>Subtotal</span><span id="subtotal-display">R$ 0,00</span>
          </div>
          <div id="desconto-row" style="display:none;justify-content:space-between;font-size:13px;color:var(--red)">
            <span id="desconto-label">Desconto</span><span id="desconto-display">- R$ 0,00</span>
          </div>
        </div>
      </div>

      <div id="tab-ia" style="display:none;flex-direction:column;gap:14px">
        <div
          style="background:var(--accent-dim);border:1px solid rgba(6,182,212,0.2);border-radius:12px;padding:14px 16px;font-size:13px;color:var(--accent-dark)">
          💡 <strong>Dica:</strong> Ex: <em>"Orçamento de instalação ar-condicionado 700 reais para João"</em>
        </div>
        <div class="form-group">
          <label>Descreva o orçamento</label>
          <textarea style="min-height:120px" id="ia-text"
            placeholder="Descreva o orçamento como você falaria..."></textarea>
        </div>
        <button class="btn btn-primary" style="width:100%;justify-content:center" onclick="processarIA()"
          id="btn-processar-ia">
          🤖 Processar com IA
        </button>
        <div id="ia-result"
          style="display:none;background:var(--surface2);border-radius:12px;padding:16px;font-size:13px;line-height:1.8;border:1px solid var(--border)">
        </div>
      </div>
    </div>
    <div class="modal-footer" id="modal-orcamento-footer-unificado">
      <div style="display:flex; justify-content:space-between; align-items:center; width:100%; gap:12px">
        <div id="footer-total-container" style="text-align:left; line-height:1.2">
          <div style="font-size:10px; color:var(--muted); text-transform:uppercase; font-weight:700; letter-spacing:0.05em">Total do Orçamento</div>
          <div id="footer-total-valor" style="font-size:19px; font-weight:800; color:var(--green)">R$ 0,00</div>
        </div>
        <div style="display:flex; gap:8px; align-items:center">
          ${customFooter}
        </div>
      </div>
    </div>
  </div>
</div>`;

  // Injeta antes do primeiro elemento script ou no final do body
  const script = document.currentScript;
  if (script && script.parentNode) {
    script.parentNode.insertAdjacentHTML('beforebegin', modalHTML);
  } else {
    document.body.insertAdjacentHTML('beforeend', modalHTML);
  }
})();