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

  function addMessage(text, role) {
    if (!messagesEl) return;
    var node = document.createElement("div");
    node.className = "cop-msg " + (role === "user" ? "user" : "bot");
    node.textContent = text || "";
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
      var payload = res && res.data ? res.data : res;
      addMessage((payload && payload.resposta) || "Sem resposta do copiloto.", "bot");
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
