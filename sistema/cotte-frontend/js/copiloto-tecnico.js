(function () {
  var messagesEl = null;
  var inputEl = null;
  var sendBtn = null;
  var sending = false;
  var sessaoId = null;

  function ensureSessionId() {
    if (sessaoId) return sessaoId;
    if (typeof crypto !== "undefined" && crypto.randomUUID) {
      sessaoId = crypto.randomUUID();
    } else {
      sessaoId = Math.random().toString(36).slice(2) + Date.now().toString(36);
    }
    return sessaoId;
  }

  function parseMarkdown(text) {
    if (!text) return "";
    if (typeof marked !== "undefined") {
      marked.setOptions({
        breaks: true,
        gfm: true,
        headerIds: false,
        sanitize: true,
      });
      const renderer = new marked.Renderer();
      const linkRenderer = renderer.link;
      renderer.link = function(href, title, text) {
        const html = linkRenderer.call(renderer, href, title, text);
        return html.replace(/^<a /, '<a target="_blank" rel="noopener noreferrer" ');
      };
      return marked.parse(text, { renderer: renderer });
    }
    
    var html = text
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
    
    html = html.replace(/```([a-z0-9]*)\n([\s\S]*?)```/gi, function(match, lang, code) {
      return '<pre class="code-block" data-lang="' + (lang || 'code') + '"><code>' + code + '</code></pre>';
    });
    
    html = html.replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>');
    
    html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    
    html = html.replace(/\n/g, '<br>');
    
    return html;
  }

  function renderChart(config, containerId) {
    try {
      if (typeof Chart === 'undefined') {
        console.error('Chart.js não carregado');
        return null;
      }
      var container = document.getElementById(containerId);
      if (!container) return null;
      
      var canvas = document.createElement('canvas');
      container.appendChild(canvas);

      // Usar variáveis CSS para cores quando possível
      var rootStyle = getComputedStyle(document.documentElement);
      var primaryColor = rootStyle.getPropertyValue('--primary-color').trim() || '#2563eb';
      var secondaryColor = rootStyle.getPropertyValue('--secondary-color').trim() || '#10b981';
      var palette = [
        primaryColor, secondaryColor, '#f59e0b', '#ef4444', 
        '#8b5cf6', '#ec4899', '#0ea5e9', '#f97316'
      ];
      
      // Configuração padrão para responsividade
      var chartConfig = Object.assign({
        options: {
          responsive: true,
          maintainAspectRatio: true,
          plugins: {
            legend: { position: 'bottom' }
          }
        }
      }, config);

      // Aplicar paleta se as cores não foram fornecidas
      if (chartConfig.data && Array.isArray(chartConfig.data.datasets)) {
        chartConfig.data.datasets.forEach(function(ds, idx) {
          var isPie = ['pie', 'doughnut'].indexOf(chartConfig.type) !== -1;
          if (!ds.backgroundColor) {
            ds.backgroundColor = isPie ? palette : palette[idx % palette.length];
          }
          if (!ds.borderColor && chartConfig.type !== 'pie' && chartConfig.type !== 'doughnut') {
            ds.borderColor = palette[idx % palette.length];
          }
        });
      }
      
      return new Chart(canvas.getContext('2d'), chartConfig);
    } catch (e) {
      console.error('Erro ao renderizar gráfico:', e);
      return null;
    }
  }

  function renderActionButtons(actions, container) {
    if (!Array.isArray(actions)) return;
    var btnContainer = document.createElement('div');
    btnContainer.className = 'action-buttons';
    
    actions.forEach(function(act) {
      var btn = document.createElement('button');
      btn.className = 'action-btn';
      
      var isString = typeof act === 'string';
      btn.textContent = isString ? act : (act.label || 'Ação');
      
      if (!isString && act.type) {
        btn.dataset.type = act.type;
      }
      
      btn.onclick = function() {
        if (!inputEl) return;
        var val = isString ? act : (act.payload || act.label || btn.textContent);
        inputEl.value = val;
        sendMessage();
      };
      
      btnContainer.appendChild(btn);
    });
    
    container.appendChild(btnContainer);
  }

  function addMessage(text, role, actions) {
    if (!messagesEl) return null;
    var node = document.createElement("div");
    node.className = "cop-msg " + (role === "user" ? "user" : "bot");
    if (role === "bot") {
      node.innerHTML = parseMarkdown(text || "");
      if(actions) {
        renderActionButtons(actions, node)
      }
    } else {
      node.textContent = text || "";
    }
    messagesEl.appendChild(node);
    messagesEl.scrollTop = messagesEl.scrollHeight;
    return node;
  }

  function _extractTabularRows(payload) {
    if (!payload || typeof payload !== "object") return [];
    var dados = payload.dados && typeof payload.dados === "object" ? payload.dados : null;
    var data = payload.data && typeof payload.data === "object" ? payload.data : null;
    var dataNested = data && data.data && typeof data.data === "object" ? data.data : null;
    var dadosNested = dados && dados.dados && typeof dados.dados === "object" ? dados.dados : null;
    var metaDados = dados && dados._meta_frontend_data && typeof dados._meta_frontend_data === "object"
      ? dados._meta_frontend_data
      : null;
    var metaData = data && data._meta_frontend_data && typeof data._meta_frontend_data === "object"
      ? data._meta_frontend_data
      : null;
    var metaDataNested = dataNested && dataNested._meta_frontend_data && typeof dataNested._meta_frontend_data === "object"
      ? dataNested._meta_frontend_data
      : null;
    var metaDadosNested = dadosNested && dadosNested._meta_frontend_data && typeof dadosNested._meta_frontend_data === "object"
      ? dadosNested._meta_frontend_data
      : null;

    var directOrcamentos = payload.orcamentos || (dados && dados.orcamentos) || (data && data.orcamentos) || (dataNested && dataNested.orcamentos);
    if (Array.isArray(directOrcamentos) && directOrcamentos.length) return directOrcamentos;

    var orcamentos =
      (metaDados && metaDados.orcamentos) ||
      (metaData && metaData.orcamentos) ||
      (metaDataNested && metaDataNested.orcamentos) ||
      (metaDadosNested && metaDadosNested.orcamentos);
    if (Array.isArray(orcamentos) && orcamentos.length) return orcamentos;

    var directClientes = payload.clientes || (dados && dados.clientes) || (data && data.clientes) || (dataNested && dataNested.clientes);
    if (Array.isArray(directClientes) && directClientes.length) return directClientes;

    var clientes =
      (metaDados && metaDados.clientes) ||
      (metaData && metaData.clientes) ||
      (metaDataNested && metaDataNested.clientes) ||
      (metaDadosNested && metaDadosNested.clientes);
    if (Array.isArray(clientes) && clientes.length) return clientes;

    var sqlRows = data && data.sql_result && Array.isArray(data.sql_result.rows)
      ? data.sql_result.rows
      : null;
    if (Array.isArray(sqlRows) && sqlRows.length) return sqlRows;

    return [];
  }

  function renderDataTable(container, rows) {
    if (!container || !Array.isArray(rows) || !rows.length) return;
    var headers = Object.keys(rows[0] || {});
    if (!headers.length) return;

    var pageSize = 12;
    var currentPage = 1;
    var sortState = { key: null, dir: "asc" };
    var workingRows = rows.slice();

    var wrap = document.createElement("div");
    wrap.style.marginTop = "12px";
    wrap.style.overflowX = "auto";

    var table = document.createElement("table");
    table.style.width = "100%";
    table.style.borderCollapse = "collapse";
    table.style.fontSize = "0.9rem";

    var thead = document.createElement("thead");
    var headerRow = document.createElement("tr");
    headers.forEach(function (header) {
      var th = document.createElement("th");
      th.textContent = header;
      th.style.textAlign = "left";
      th.style.padding = "8px";
      th.style.borderBottom = "1px solid var(--border-color, #d1d5db)";
      th.style.cursor = "pointer";
      th.title = "Clique para ordenar";
      th.addEventListener("click", function () {
        var nextDir = "asc";
        if (sortState.key === header && sortState.dir === "asc") nextDir = "desc";
        sortState.key = header;
        sortState.dir = nextDir;
        workingRows.sort(function (a, b) {
          var va = a && Object.prototype.hasOwnProperty.call(a, header) ? a[header] : null;
          var vb = b && Object.prototype.hasOwnProperty.call(b, header) ? b[header] : null;
          var sa = va === null || va === undefined ? "" : String(va).toLowerCase();
          var sb = vb === null || vb === undefined ? "" : String(vb).toLowerCase();
          if (sa < sb) return nextDir === "asc" ? -1 : 1;
          if (sa > sb) return nextDir === "asc" ? 1 : -1;
          return 0;
        });
        currentPage = 1;
        renderRows();
      });
      headerRow.appendChild(th);
    });
    thead.appendChild(headerRow);
    table.appendChild(thead);

    var tbody = document.createElement("tbody");
    function renderRows() {
      tbody.innerHTML = "";
      var totalPages = Math.max(1, Math.ceil(workingRows.length / pageSize));
      if (currentPage > totalPages) currentPage = totalPages;
      var start = (currentPage - 1) * pageSize;
      var end = start + pageSize;
      var pageRows = workingRows.slice(start, end);

      pageRows.forEach(function (row) {
        var tr = document.createElement("tr");
        headers.forEach(function (header) {
          var td = document.createElement("td");
          var val = row && Object.prototype.hasOwnProperty.call(row, header) ? row[header] : "";
          td.textContent = val === null || val === undefined ? "" : String(val);
          td.style.padding = "8px";
          td.style.borderBottom = "1px solid var(--border-color, #f0f0f0)";
          tr.appendChild(td);
        });
        tbody.appendChild(tr);
      });

      if (pageInfo) {
        pageInfo.textContent = "Página " + currentPage + " de " + totalPages + " (" + workingRows.length + " itens)";
      }
      if (prevBtn) prevBtn.disabled = currentPage <= 1;
      if (nextBtn) nextBtn.disabled = currentPage >= totalPages;
    }

    table.appendChild(tbody);

    var controls = document.createElement("div");
    controls.style.display = "flex";
    controls.style.alignItems = "center";
    controls.style.gap = "8px";
    controls.style.marginTop = "10px";

    var prevBtn = document.createElement("button");
    prevBtn.textContent = "Anterior";
    prevBtn.className = "download-btn";
    prevBtn.addEventListener("click", function () {
      if (currentPage > 1) {
        currentPage -= 1;
        renderRows();
      }
    });

    var nextBtn = document.createElement("button");
    nextBtn.textContent = "Próxima";
    nextBtn.className = "download-btn";
    nextBtn.addEventListener("click", function () {
      var totalPages = Math.max(1, Math.ceil(workingRows.length / pageSize));
      if (currentPage < totalPages) {
        currentPage += 1;
        renderRows();
      }
    });

    var pageInfo = document.createElement("span");
    pageInfo.style.fontSize = "0.85rem";
    pageInfo.style.opacity = "0.85";

    controls.appendChild(prevBtn);
    controls.appendChild(nextBtn);
    controls.appendChild(pageInfo);

    wrap.appendChild(table);
    wrap.appendChild(controls);
    container.appendChild(wrap);
    renderRows();
    addDownloadButtons(container, rows);
  }

  function setSending(value) {
    sending = !!value;
    if (!sendBtn || !inputEl) return;
    sendBtn.disabled = sending;
    inputEl.disabled = sending;
    sendBtn.textContent = sending ? "Enviando..." : "Enviar";
    var statusPill = document.getElementById("copilotoStatusPill");
    if (statusPill) {
      statusPill.textContent = sending ? "Processando" : "Pronto";
    }
  }

  function _firstNonEmptyString(values) {
    for (var i = 0; i < values.length; i += 1) {
      if (typeof values[i] === "string" && values[i].trim()) {
        return values[i].trim();
      }
    }
    return "";
  }

  function resolveCopilotReply(payload) {
    if (!payload || typeof payload !== "object") {
      return "";
    }

    var nestedData = payload.data && typeof payload.data === "object" ? payload.data : null;
    var nestedDados = payload.dados && typeof payload.dados === "object" ? payload.dados : null;
    var semanticFromData =
      nestedData &&
      nestedData.semantic_contract &&
      typeof nestedData.semantic_contract === "object"
        ? nestedData.semantic_contract
        : null;
    var semanticFromDados =
      nestedDados &&
      nestedDados.semantic_contract &&
      typeof nestedDados.semantic_contract === "object"
        ? nestedDados.semantic_contract
        : null;

    return _firstNonEmptyString([
      payload.resposta,
      payload.mensagem,
      payload.message,
      payload.error,
      nestedData && nestedData.resposta,
      nestedData && nestedData.mensagem,
      nestedData && nestedData.message,
      nestedDados && nestedDados.resposta,
      nestedDados && nestedDados.mensagem,
      nestedDados && nestedDados.message,
      semanticFromData && semanticFromData.summary,
      semanticFromDados && semanticFromDados.summary,
    ]);
  }

  function _stringifyTechnicalRow(row) {
    if (!row || typeof row !== "object") return "";
    return Object.keys(row)
      .slice(0, 5)
      .map(function (key) {
        return String(key) + ": " + String(row[key]);
      })
      .join(" | ");
  }

  function buildTechnicalFallbackReply(payload) {
    if (!payload || typeof payload !== "object") return "";

    var data = payload.data && typeof payload.data === "object" ? payload.data : payload;
    var codeContext =
      data && data.code_context && typeof data.code_context === "object" ? data.code_context : {};
    var sqlResult =
      data && data.sql_result && typeof data.sql_result === "object" ? data.sql_result : {};
    var metrics =
      payload.metrics && typeof payload.metrics === "object"
        ? payload.metrics
        : data && data.metrics && typeof data.metrics === "object"
          ? data.metrics
          : {};
    var trace = Array.isArray(payload.trace)
      ? payload.trace
      : data && Array.isArray(data.trace)
        ? data.trace
        : [];

    var parts = [];
    if (typeof payload.error === "string" && payload.error.trim()) {
      parts.push(payload.error.trim());
    }
    if (Array.isArray(codeContext.sources) && codeContext.sources.length) {
      parts.push("Fontes encontradas:\n- " + codeContext.sources.join("\n- "));
    }
    if (typeof codeContext.context === "string" && codeContext.context.trim()) {
      parts.push("Trechos relevantes:\n" + codeContext.context.trim().slice(0, 3200));
    }
    if (Array.isArray(sqlResult.rows) && sqlResult.rows.length) {
      var previewRows = sqlResult.rows.slice(0, 3).map(_stringifyTechnicalRow).filter(Boolean);
      if (previewRows.length) {
        parts.push("Prévia SQL:\n- " + previewRows.join("\n- "));
      }
    } else if (typeof sqlResult.row_count === "number") {
      parts.push("Consulta SQL executada com " + String(sqlResult.row_count) + " linha(s).");
    }
    if (typeof metrics.total_steps === "number" && metrics.total_steps > 0) {
      parts.push(
        "Fluxo técnico concluído em " +
          String(metrics.total_steps) +
          " passo(s)" +
          (typeof metrics.total_duration_ms === "number"
            ? " e " + String(metrics.total_duration_ms) + " ms."
            : ".")
      );
    }
    if (!parts.length && trace.length) {
      parts.push(
        "Etapas executadas:\n- " +
          trace
            .slice(0, 5)
            .map(function (step) {
              return String(step.step || "etapa") + " (" + String(step.status || "ok") + ")";
            })
            .join("\n- ")
      );
    }

    return parts.join("\n\n").trim();
  }

  function downloadCSV(data, filename) {
    if (!Array.isArray(data) || data.length === 0) return;
    
    var headers = Object.keys(data[0]);
    var csv = headers.join(',') + '\n';
    data.forEach(function(row) {
      csv += headers.map(function(h) {
        var val = row[h];
        if (val === null || val === undefined) return '';
        if (typeof val === 'string' && (val.includes(',') || val.includes('"'))) {
          return '"' + val.replace(/"/g, '""') + '"';
        }
        return String(val);
      }).join(',') + '\n';
    });
    
    var blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    var url = URL.createObjectURL(blob);
    var link = document.createElement('a');
    link.href = url;
    link.download = filename || 'dados.csv';
    link.click();
    URL.revokeObjectURL(url);
  }

  function downloadJSON(data, filename) {
    var json = JSON.stringify(data, null, 2);
    var blob = new Blob([json], { type: 'application/json;charset=utf-8;' });
    var url = URL.createObjectURL(blob);
    var link = document.createElement('a');
    link.href = url;
    link.download = filename || 'dados.json';
    link.click();
    URL.revokeObjectURL(url);
  }

    function addDownloadButtons(container, data) {
    if (!Array.isArray(data) || data.length === 0) return;
    
    var btnContainer = document.createElement('div');
    btnContainer.className = 'download-buttons';
    
    var csvBtn = document.createElement('button');
    csvBtn.textContent = 'Baixar CSV';
    csvBtn.className = 'download-btn';
    csvBtn.onclick = function() { downloadCSV(data, 'dados.csv'); };
    
    var jsonBtn = document.createElement('button');
    jsonBtn.textContent = 'Baixar JSON';
    jsonBtn.className = 'download-btn';
    jsonBtn.onclick = function() { downloadJSON(data, 'dados.json'); };
    
    btnContainer.appendChild(csvBtn);
    btnContainer.appendChild(jsonBtn);
    container.appendChild(btnContainer);
  }

  function submitForm(form, schema) {
    var formData = new FormData(form);
    var data = {};
    formData.forEach(function(value, key) {
      data[key] = value;
    });
    
    var message = 'Filtrar com: ' + JSON.stringify(data);
    if (inputEl) inputEl.value = message;
    if (sendBtn) sendBtn.click();
  }

  function renderForm(schema, container) {
    if (!schema || !schema.fields) return;
    
    var form = document.createElement('form');
    form.className = 'dynamic-form';
    
    if (schema.title) {
      var title = document.createElement('h4');
      title.textContent = schema.title;
      form.appendChild(title);
    }
    
    schema.fields.forEach(function(field) {
      var fieldWrapper = document.createElement('div');
      fieldWrapper.className = 'form-field';
      
      var label = document.createElement('label');
      label.textContent = field.label || field.name;
      if (field.required) label.className += ' required';
      
      var input;
      if (field.type === 'select') {
        input = document.createElement('select');
        (field.options || []).forEach(function(opt) {
          var optEl = document.createElement('option');
          optEl.value = opt;
          optEl.textContent = opt;
          input.appendChild(optEl);
        });
      } else {
        input = document.createElement('input');
        input.type = field.type || 'text';
      }
      
      input.name = field.name;
      if (field.required) input.required = true;
      
      fieldWrapper.appendChild(label);
      fieldWrapper.appendChild(input);
      form.appendChild(fieldWrapper);
    });
    
    var submitBtn = document.createElement('button');
    submitBtn.type = 'submit';
    submitBtn.textContent = schema.submitLabel || 'Enviar';
    submitBtn.className = 'btn-primary';
    form.appendChild(submitBtn);
    
    form.addEventListener('submit', function(e) {
      e.preventDefault();
      submitForm(form, schema);
    });
    
    container.appendChild(form);
  }

  async function sendMessage() {
    if (sending || !inputEl) return;
    var raw = (inputEl.value || "").trim();
    if (!raw) return;

    var api = window.ApiService || window.api;
    if (!api || typeof api.post !== "function") {
      addMessage("API indisponível no momento.", "bot");
      return;
    }

    addMessage(raw, "user");
    inputEl.value = "";
    setSending(true);
    try {
      var res = await api.post("/ai/copiloto-interno", {
        mensagem: raw,
        sessao_id: ensureSessionId(),
      });
      var payload = res || {};
      var botReply = resolveCopilotReply(payload);
      if (!botReply) {
        botReply = buildTechnicalFallbackReply(payload);
      }
      
      var chartConfig = payload.chart || 
                        (payload.data && payload.data.chart) || 
                         (payload.dados && payload.dados.chart);

      var actions = payload.actions || 
                    (payload.data && payload.data.actions) || 
                    (payload.dados && payload.dados.actions);
                         
      var msgText = botReply || (chartConfig ? "" : "Sem resposta do copiloto.");
      var msgNode = addMessage(msgText, "bot", actions);

      var tableRows = _extractTabularRows(payload);
      if (msgNode && Array.isArray(tableRows) && tableRows.length) {
        renderDataTable(msgNode, tableRows);
      }

      if (chartConfig && msgNode) {
        var chartWrap = document.createElement("div");
        var chartId = "chart-" + Math.random().toString(36).substr(2, 9);
        chartWrap.id = chartId;
        chartWrap.style.width = "100%";
        chartWrap.style.marginTop = "12px";
        chartWrap.style.position = "relative";
        msgNode.appendChild(chartWrap);
        
        renderChart(chartConfig, chartId);
      }

             
      var formSchema = payload.form || 
                       (payload.data && payload.data.form) || 
                       (payload.dados && payload.dados.form);

      if (formSchema && msgNode) {
        renderForm(formSchema, msgNode);
      }

      var tIn = payload.input_tokens;
      var tOut = payload.output_tokens;
      if ((tIn > 0 || tOut > 0) && messagesEl && messagesEl.lastElementChild) {
        var badge = document.createElement("div");
        badge.className = "token-usage-badge";
        badge.textContent = "\uD83D\uDD22 " + ((tIn || 0) + (tOut || 0)) + " tokens (\u2191" + (tIn || 0) + " \u2193" + (tOut || 0) + ")";
        messagesEl.lastElementChild.appendChild(badge);
      }
    } catch (err) {
      addMessage((err && err.message) || "Falha ao consultar o copiloto interno.", "bot");
    } finally {
      setSending(false);
      inputEl.focus();
    }
  }

  (function injectStyles() {
    var style = document.createElement('style');
    style.textContent = `
      .download-buttons { margin-top: 0.5em; display: flex; gap: 0.5em; }
      .download-btn { padding: 0.25em 0.75em; font-size: 0.85em; border: 1px solid #ccc; border-radius: 4px; background: #f5f5f5; cursor: pointer; }
      .download-btn:hover { background: #e5e5e5; }
      .action-buttons { margin-top: 0.75em; display: flex; flex-wrap: wrap; gap: 8px; }
      .action-btn { padding: 6px 12px; font-size: 0.85rem; border: 1px solid var(--border-color, #e5e7eb); border-radius: 16px; background: #ffffff; color: var(--text-color, #374151); cursor: pointer; transition: all 0.2s ease; box-shadow: 0 1px 2px rgba(0,0,0,0.05); }
      .action-btn:hover { background: var(--primary-color, #f3f4f6); border-color: var(--primary-color, #d1d5db); color: var(--primary-color-text, #111827); }
      .action-btn:disabled { opacity: 0.6; cursor: not-allowed; }
    `;
    document.head.appendChild(style);
  })();

  async function bootstrapCapabilities() {
    var caps = window.CapabilityFlagsService;
    if (!caps || typeof caps.getAll !== "function") return;
    var data = await caps.getAll();
    var available = !!(data && data.available_engines && data.available_engines.internal_copilot);
    if (!available) {
      addMessage("Copiloto interno indisponível para seu perfil ou ambiente atual.", "bot");
      setSending(true);
    }
  }

  function showToast(msg) {
    var toast = document.getElementById('copilotoToast');
    if (!toast) return;
    toast.textContent = msg;
    toast.classList.add('show');
    setTimeout(function() {
      toast.classList.remove('show');
    }, 3000);
  }

  function updateCharCount() {
    var ta = document.getElementById('skillTextarea');
    var cc = document.getElementById('charCount');
    if (ta && cc) {
      cc.textContent = ta.value.length;
    }
  }

  async function loadSkill() {
    var ta = document.getElementById('skillTextarea');
    var api = window.ApiService || window.api;
    if (!api || typeof api.get !== 'function' || !ta) return;
    
    try {
      ta.disabled = true;
      var res = await api.get('/ai/copiloto-interno/skill');
      ta.value = res.skill_text || '';
      updateCharCount();
    } catch (e) {
      console.error('Erro ao carregar skill:', e);
      showToast('Erro ao carregar skill');
    } finally {
      ta.disabled = false;
      ta.focus();
    }
  }

  async function saveSkill() {
    var ta = document.getElementById('skillTextarea');
    var api = window.ApiService || window.api;
    if (!api || typeof api.put !== 'function' || !ta) return;
    
    var skillText = ta.value.trim();
    if (skillText.length > 0 && skillText.length < 10) {
      showToast('Skill deve ter pelo menos 10 caracteres');
      return;
    }
    
    var btn = document.getElementById('saveSkillBtn');
    if (btn) {
      btn.disabled = true;
      btn.textContent = 'Salvando...';
    }
    
    try {
      await api.put('/ai/copiloto-interno/skill', { skill_text: skillText });
      showToast('Skill salva com sucesso!');
      var modal = document.getElementById('copilotoSettingsModal');
      if (modal) modal.style.display = 'none';
    } catch (e) {
      console.error('Erro ao salvar skill:', e);
      showToast('Erro ao salvar skill');
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.textContent = 'Salvar';
      }
    }
  }

  function init() {
    if (typeof inicializarLayout === "function") {
      inicializarLayout("copiloto-tecnico");
    }
    messagesEl = document.getElementById("copilotoMessages");
    inputEl = document.getElementById("copilotoInput");
    sendBtn = document.getElementById("copilotoSendBtn");

    if (!messagesEl || !inputEl || !sendBtn) return;
    sendBtn.addEventListener("click", sendMessage);
    inputEl.addEventListener("keydown", function (event) {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
      }
    });

    var quickPromptButtons = document.querySelectorAll(".quick-prompt-btn");
    quickPromptButtons.forEach(function (button) {
      button.addEventListener("click", function () {
        if (!inputEl || sending) return;
        inputEl.value = button.dataset.prompt || "";
        inputEl.focus();
      });
    });

    var sidePanelEl = document.getElementById("copilotoSidePanel");
    var sideToggleEl = document.getElementById("copilotoSideToggleBtn");
    if (sidePanelEl && sideToggleEl) {
      sideToggleEl.addEventListener("click", function () {
        var open = sidePanelEl.classList.toggle("is-open");
        sideToggleEl.setAttribute("aria-expanded", open ? "true" : "false");
      });
    }

    var settingsBtnEl = document.getElementById('copilotoSettingsBtn');
    var modalEl = document.getElementById('copilotoSettingsModal');
    var cancelBtnEl = document.getElementById('cancelSkillBtn');
    var saveSkillBtnEl = document.getElementById('saveSkillBtn');
    var taEl = document.getElementById('skillTextarea');

    if (settingsBtnEl && modalEl) {
      settingsBtnEl.addEventListener('click', function() {
        modalEl.style.display = 'flex';
        loadSkill();
      });
      if (cancelBtnEl) {
        cancelBtnEl.addEventListener('click', function() {
          modalEl.style.display = 'none';
        });
      }
      if (saveSkillBtnEl) {
        saveSkillBtnEl.addEventListener('click', saveSkill);
      }
      if (taEl) {
        taEl.addEventListener('input', updateCharCount);
      }
      modalEl.addEventListener('click', function(e) {
        if (e.target === modalEl) modalEl.style.display = 'none';
      });
    }

    bootstrapCapabilities();
  }

  document.addEventListener("DOMContentLoaded", init);
})();
