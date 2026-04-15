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
    var html = text
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
    
    // Code blocks: ```language ... ```
    html = html.replace(/```([a-z0-9]*)\n([\s\S]*?)```/gi, function(match, lang, code) {
      return '<pre class="code-block" data-lang="' + (lang || 'code') + '"><code>' + code + '</code></pre>';
    });
    
    // Inline code: `code`
    html = html.replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>');
    
    // Bold: **text**
    html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    
    // Line breaks
    html = html.replace(/\n/g, '<br>');
    
    return html;
  }

  function addMessage(text, role) {
    if (!messagesEl) return;
    var node = document.createElement("div");
    node.className = "cop-msg " + (role === "user" ? "user" : "bot");
    if (role === "bot") {
      node.innerHTML = parseMarkdown(text || "");
    } else {
      node.textContent = text || "";
    }
    messagesEl.appendChild(node);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function setSending(value) {
    sending = !!value;
    if (!sendBtn || !inputEl) return;
    sendBtn.disabled = sending;
    inputEl.disabled = sending;
    sendBtn.textContent = sending ? "Enviando..." : "Enviar";
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
      addMessage(botReply || "Sem resposta do copiloto.", "bot");
    } catch (err) {
      addMessage((err && err.message) || "Falha ao consultar o copiloto interno.", "bot");
    } finally {
      setSending(false);
      inputEl.focus();
    }
  }

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

    bootstrapCapabilities();
  }

  document.addEventListener("DOMContentLoaded", init);
})();
