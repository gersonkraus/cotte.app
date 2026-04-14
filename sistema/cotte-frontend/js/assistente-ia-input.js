/**
 * assistente-ia-input.js
 *
 * Entrada do usuário, atalhos, voz e bootstrap da página do assistente.
 */

function initSpeechRecognition() {
  const SpeechRecognition =
    window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    console.warn("Speech Recognition API não suportada neste navegador.");
    const btn = document.getElementById("voiceButton");
    if (btn) {
      btn.style.opacity = "0.5";
      btn.title = "Entrada por voz não suportada nativamente neste navegador";
    }
    return;
  }

  speechRecognition = new SpeechRecognition();
  speechRecognition.continuous = false;
  speechRecognition.interimResults = false;
  speechRecognition.lang = "pt-BR";

  speechRecognition.onstart = function () {
    isRecording = true;
    const btn = document.getElementById("voiceButton");
    if (btn) {
      btn.setAttribute("aria-pressed", "true");
      btn.title = "Gravando... Clique para parar.";
    }
    const ta = document.getElementById("messageInput");
    if (ta && !ta.value.trim()) {
      ta.placeholder = "Ouvindo...";
    }
  };

  speechRecognition.onresult = function (event) {
    let transcript = "";
    let isFinal = false;
    for (let i = event.resultIndex; i < event.results.length; ++i) {
      transcript += event.results[i][0].transcript;
      if (event.results[i].isFinal) {
        isFinal = true;
      }
    }

    const ta = document.getElementById("messageInput");
    if (ta) {
      const currentVal = ta.value;
      if (currentVal && !currentVal.endsWith(" ")) {
        ta.value = currentVal + " " + transcript;
      } else {
        ta.value = currentVal + transcript;
      }
      resizeMessageInput();
      _updateVoiceSendToggle(ta);
      ta.focus();

      if (isFinal) {
        setTimeout(() => {
          if (ta.value.trim() !== "") {
            sendMessage();
          }
        }, 300);
      }
    }
  };

  speechRecognition.onerror = function (event) {
    console.error("Erro no Speech Recognition:", event.error);
    stopSpeechRecognition();
  };

  speechRecognition.onend = function () {
    stopSpeechRecognition();
  };
}

function toggleSpeechRecognition() {
  if (!speechRecognition) {
    if (typeof showNotif === "function") {
      showNotif(
        "⚠️",
        "Sem Suporte",
        "Navegador não possui recurso nativo de voz. Tente Chrome ou Edge.",
        "error",
      );
    } else {
      alert(
        "Seu navegador não suporta reconhecimento de voz nativo. Tente usar o Google Chrome ou Edge.",
      );
    }
    return;
  }

  if (isRecording) {
    speechRecognition.stop();
  } else {
    try {
      speechRecognition.start();
    } catch (e) {
      console.error("Erro ao iniciar gravação:", e);
    }
  }
}

function stopSpeechRecognition() {
  isRecording = false;
  const btn = document.getElementById("voiceButton");
  if (btn) {
    btn.setAttribute("aria-pressed", "false");
    btn.title = "Ditar por voz";
  }
  const ta = document.getElementById("messageInput");
  if (ta) {
    ta.placeholder = getAdaptiveMessagePlaceholder();
  }
}

function initSlashCommands() {
  const ta = document.getElementById("messageInput");
  const menu = document.getElementById("slashCommandsMenu");
  if (!ta || !menu) return;

  ta.addEventListener("input", function () {
    const val = ta.value;
    const cursorPosition = ta.selectionStart;
    const textBeforeCursor = val.substring(0, cursorPosition);
    const match = textBeforeCursor.match(/(?:^|\s)(\/[^\s]*)$/);

    if (match) {
      const query = match[1].toLowerCase();
      showSlashCommands(query);
    } else {
      hideSlashCommands();
    }
  });

  ta.addEventListener("keydown", function (e) {
    const slashMenu = document.getElementById("slashCommandsMenu");
    if (slashMenu.style.display !== "none") {
      const items = slashMenu.querySelectorAll(".slash-item");
      if (items.length === 0) return;

      if (e.key === "ArrowDown") {
        e.preventDefault();
        slashCommandIndex = (slashCommandIndex + 1) % items.length;
        updateSlashCommandSelection(items);
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        slashCommandIndex =
          (slashCommandIndex - 1 + items.length) % items.length;
        updateSlashCommandSelection(items);
      } else if (e.key === "Enter" || e.key === "Tab") {
        e.preventDefault();
        if (slashCommandIndex >= 0 && slashCommandIndex < items.length) {
          items[slashCommandIndex].click();
        } else if (items.length > 0) {
          items[0].click();
        }
      } else if (e.key === "Escape") {
        e.preventDefault();
        hideSlashCommands();
      }
    }
  });
}

function showSlashCommands(query) {
  const menu = document.getElementById("slashCommandsMenu");
  const list = document.getElementById("slashCommandsList");
  if (!menu || !list) return;

  const filtered = SLASH_COMMANDS.filter((cmd) =>
    cmd.cmd.toLowerCase().startsWith(query),
  );

  if (filtered.length === 0) {
    hideSlashCommands();
    return;
  }

  list.innerHTML = "";
  filtered.forEach((cmd) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "slash-item";
    btn.innerHTML = `
            <span class="slash-item-icon">${cmd.icon}</span>
            <div class="slash-item-content">
                <span class="slash-item-cmd">${cmd.cmd}</span>
                <span class="slash-item-desc">${cmd.desc}</span>
            </div>
        `;

    btn.addEventListener("click", () => {
      applySlashCommand(cmd.cmd);
    });

    list.appendChild(btn);
  });

  slashCommandIndex = 0;
  updateSlashCommandSelection(list.querySelectorAll(".slash-item"));
  menu.style.display = "block";
}

function hideSlashCommands() {
  const menu = document.getElementById("slashCommandsMenu");
  if (menu) menu.style.display = "none";
  slashCommandIndex = -1;
}

function updateSlashCommandSelection(items) {
  items.forEach((item, idx) => {
    if (idx === slashCommandIndex) {
      item.classList.add("active");
      item.scrollIntoView({ block: "nearest" });
    } else {
      item.classList.remove("active");
    }
  });
}

function applySlashCommand(command) {
  const ta = document.getElementById("messageInput");
  if (!ta) return;

  const val = ta.value;
  const cursorPosition = ta.selectionStart;
  const textBeforeCursor = val.substring(0, cursorPosition);
  const textAfterCursor = val.substring(cursorPosition);

  const match = textBeforeCursor.match(/(?:^|\s)(\/[^\s]*)$/);
  if (match) {
    const replaceStart = cursorPosition - match[1].length;
    ta.value = val.substring(0, replaceStart) + command + " " + textAfterCursor;
    const newCursorPos = replaceStart + command.length + 1;
    ta.setSelectionRange(newCursorPos, newCursorPos);
  }

  hideSlashCommands();
  resizeMessageInput();
  ta.focus();
}

function handleMessageKeydown(event) {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    sendMessage();
  }
}

function sendQuickMessage(message) {
  const el = document.getElementById("messageInput");
  if (el) {
    el.value = message;
    resizeMessageInput();
  }
  sendMessage();
}

function addMessage(
  content,
  isUser = false,
  isError = false,
  isLoadingState = false,
  options = {},
) {
  const messagesContainer = document.getElementById("chatMessages");
  if (!messagesContainer) return null;

  const time = getCurrentTime();
  const messageDiv = document.createElement("div");
  messageDiv.className =
    "message " +
    (isUser ? "user" : "ai") +
    (isError ? " error" : "") +
    (isLoadingState ? " loading" : "");

  if (isLoadingState) {
    messageDiv.innerHTML = `
            <div class="message-bubble ai-loading-bubble" data-time="${time}">
                <div class="ai-loading-row ai-loading-row--skeleton" aria-label="Carregando resposta">
                    <div class="ai-skeleton-line ai-skeleton-line--w90"></div>
                    <div class="ai-skeleton-line ai-skeleton-line--w70"></div>
                    <div class="ai-skeleton-line ai-skeleton-line--w45"></div>
                </div>
            </div>
        `;
  } else {
    const copyBtn =
      !isUser && !isError
        ? '<button type="button" class="message-copy-btn" aria-label="Copiar resposta" title="Copiar">📋</button>'
        : "";
    messageDiv.innerHTML = `<div class="message-bubble" data-time="${time}">${copyBtn}${content}</div>`;
  }

  const today = new Date();
  const dateKey = [
    today.getFullYear(),
    String(today.getMonth() + 1).padStart(2, "0"),
    String(today.getDate()).padStart(2, "0"),
  ].join("-");
  const hasTodaySeparator = !!messagesContainer.querySelector(
    `.chat-date-separator[data-date="${dateKey}"]`,
  );
  if (!hasTodaySeparator) {
    const separator = document.createElement("div");
    separator.className = "chat-date-separator";
    separator.dataset.date = dateKey;
    const label = today.toLocaleDateString("pt-BR", {
      day: "numeric",
      month: "long",
    });
    separator.innerHTML = `<span class="chat-date-pill">${label}</span>`;
    messagesContainer.appendChild(separator);
  }

  messagesContainer.appendChild(messageDiv);
  if (typeof updateAssistenteMessageDensity === "function") {
    updateAssistenteMessageDensity();
  }
  if (options.forceScroll || isUser) {
    scrollChatToBottom({
      force: true,
      behavior: options.scrollBehavior || "auto",
    });
  } else if (
    typeof shouldAutoFollowChat !== "function" ||
    shouldAutoFollowChat()
  ) {
    scrollChatToBottom({ behavior: options.scrollBehavior || "auto" });
  } else {
    updateScrollBottomButtonVisibility();
  }

  if (!isLoadingState) {
    setTimeout(saveChatHistory, 500);
  }

  return messageDiv;
}

document.addEventListener("DOMContentLoaded", function () {
  mountAssistentePreferenciasLayersToBody();

  const welcomeEl = document.getElementById("welcomeState");
  if (welcomeEl) {
    _assistenteWelcomeHTML = welcomeEl.outerHTML;
  }

  const historico = localStorage.getItem("ai_chat_history");
  if (historico) {
    const box = document.getElementById("chatMessages");
    if (box) {
      box.innerHTML = historico;
      sessaoId = localStorage.getItem("ai_sessao_id") || sessaoId;
      box
        .querySelectorAll(".sugestao-chip")
        .forEach((c) => c.classList.add("visible"));
      box.querySelectorAll(".loading").forEach((b) => b.remove());
      if (typeof restoreAssistenteChatMeta === "function") {
        restoreAssistenteChatMeta();
      }
      if (typeof updateAssistenteMessageDensity === "function") {
        updateAssistenteMessageDensity();
      }
      setTimeout(() => scrollChatToBottom({ force: true }), 100);
    }
  } else if (typeof restoreAssistenteChatMeta === "function") {
    restoreAssistenteChatMeta();
  } else if (typeof renderAssistenteContextBar === "function") {
    renderAssistenteContextBar();
  }

  const input = document.getElementById("messageInput");
  if (input) {
    input.focus();
    input.addEventListener("keydown", handleMessageKeydown);
    input.addEventListener("input", () => {
      resizeMessageInput();
      _updateVoiceSendToggle(input);
      if (input.value.trim().length > 0) _hideQuickReplyChips();
    });
    applyAdaptiveMessagePlaceholder();
    resizeMessageInput();
  }

  window.addEventListener(
    "resize",
    () => {
      applyAdaptiveMessagePlaceholder();
      resizeMessageInput();
    },
    { passive: true },
  );

  window.addEventListener(
    "orientationchange",
    () => {
      applyAdaptiveMessagePlaceholder();
      resizeMessageInput();
    },
    { passive: true },
  );

  const sendBtn = document.getElementById("sendButton");
  if (sendBtn) {
    sendBtn.addEventListener("click", () => {
      if (isLoading) {
        if (currentAbortController) {
          currentAbortController.abort();
          currentAbortController = null;
        }
      } else {
        sendMessage();
      }
    });
  }

  const voiceBtn = document.getElementById("voiceButton");
  if (voiceBtn) {
    voiceBtn.addEventListener("click", () => {
      toggleSpeechRecognition();
    });
  }

  initSpeechRecognition();
  initSlashCommands();
  loadAssistentePreferences();

  const topNew = document.getElementById("btnNovaConversaTop");
  if (topNew) topNew.addEventListener("click", () => novaConversaAssistente());

  const mobNew = document.getElementById("btnNovaConversaMobile");
  if (mobNew) mobNew.addEventListener("click", () => novaConversaAssistente());

  const embedNew = document.getElementById("btnNovaConversaEmbed");
  if (embedNew)
    embedNew.addEventListener("click", () => novaConversaAssistente());

  let prefLastFocused = null;

  function _getAssistentePrefCard() {
    return document.getElementById("assistentePreferenciasCard");
  }

  function _getPrefBackdrop() {
    return document.getElementById("prefBackdrop");
  }

  function _getPrefFocusableElements() {
    const prefCard = _getAssistentePrefCard();
    if (!prefCard) return [];
    const selectors = [
      "button:not([disabled])",
      "select:not([disabled])",
      "textarea:not([disabled])",
      "input:not([disabled])",
      "[href]",
      '[tabindex]:not([tabindex="-1"])',
    ];
    return Array.from(prefCard.querySelectorAll(selectors.join(","))).filter(
      (el) =>
        !el.hasAttribute("disabled") &&
        el.getAttribute("aria-hidden") !== "true",
    );
  }

  function _focusFirstPrefField() {
    const preferred = document.getElementById("assistenteFormatoSelect");
    if (preferred && !preferred.disabled) {
      preferred.focus();
      return;
    }
    const focusables = _getPrefFocusableElements();
    if (focusables.length) focusables[0].focus();
  }

  function _isPrefOpen() {
    const prefCard = _getAssistentePrefCard();
    return !!prefCard && prefCard.classList.contains("is-open");
  }

  function _closePrefSheet() {
    const prefCard = _getAssistentePrefCard();
    const prefBackdrop = _getPrefBackdrop();
    if (prefCard) prefCard.classList.remove("is-open");
    if (prefBackdrop) prefBackdrop.classList.remove("is-open");
    if (prefLastFocused && typeof prefLastFocused.focus === "function") {
      prefLastFocused.focus();
    }
    prefLastFocused = null;
  }

  function _openPrefSheet() {
    mountAssistentePreferenciasLayersToBody();
    const prefCard = _getAssistentePrefCard();
    const prefBackdrop = _getPrefBackdrop();
    if (!prefCard) return;
    prefLastFocused = document.activeElement;
    prefCard.classList.add("is-open");
    if (prefBackdrop) prefBackdrop.classList.add("is-open");
    window.requestAnimationFrame(() => _focusFirstPrefField());
  }

  document.addEventListener(
    "click",
    (ev) => {
      const gear = ev.target.closest(
        "#btnPreferenciasGear, #btnPreferenciasGearDesktop",
      );
      if (!gear) return;
      ev.preventDefault();
      mountAssistentePreferenciasLayersToBody();
      const card = _getAssistentePrefCard();
      if (!card) return;
      const open = card.classList.contains("is-open");
      if (open) _closePrefSheet();
      else _openPrefSheet();
    },
    true,
  );

  const prefBackdropInit = _getPrefBackdrop();
  if (prefBackdropInit) {
    prefBackdropInit.addEventListener("click", _closePrefSheet);
  }
  const prefCloseBtn = document.getElementById(
    "btnFecharPreferenciasAssistente",
  );
  if (prefCloseBtn) {
    prefCloseBtn.addEventListener("click", _closePrefSheet);
  }
  document.addEventListener("keydown", (event) => {
    if (!_isPrefOpen()) return;
    if (event.key === "Escape") {
      event.preventDefault();
      _closePrefSheet();
      return;
    }
    if (event.key === "Tab") {
      const focusables = _getPrefFocusableElements();
      if (!focusables.length) return;
      const first = focusables[0];
      const last = focusables[focusables.length - 1];
      const active = document.activeElement;
      if (event.shiftKey && active === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && active === last) {
        event.preventDefault();
        first.focus();
      }
    }
  });

  (function bindPrefSwipe() {
    const pc = _getAssistentePrefCard();
    if (!pc) return;
    let swipeStartY = 0;
    pc.addEventListener(
      "touchstart",
      (e) => {
        swipeStartY = e.touches[0].clientY;
      },
      { passive: true },
    );
    pc.addEventListener(
      "touchmove",
      (e) => {
        if (e.touches[0].clientY - swipeStartY > 60) {
          _closePrefSheet();
        }
      },
      { passive: true },
    );
  })();

  if (window.visualViewport) {
    const chatHeader = document.querySelector(".chat-header");
    const MOBILE_VW = 768;

    function applyAssistenteVisualViewport() {
      const vv = window.visualViewport;
      if (!vv) return;

      if (window.innerWidth > MOBILE_VW) {
        document.documentElement.style.removeProperty("--assistente-vv-height");
        document.documentElement.style.removeProperty("--assistente-vv-offset-top");
        return;
      }

      const h = Math.max(0, Math.round(vv.height));
      document.documentElement.style.setProperty(
        "--assistente-vv-height",
        `${h}px`,
      );
      document.documentElement.style.setProperty(
        "--assistente-vv-offset-top",
        `${Math.round(vv.offsetTop)}px`,
      );

      if (chatHeader) {
        const isKeyboard = vv.height < window.screen.height * 0.72;
        chatHeader.classList.toggle("chat-header--compact", isKeyboard);
      }
    }

    window.visualViewport.addEventListener(
      "resize",
      applyAssistenteVisualViewport,
      { passive: true },
    );
    window.visualViewport.addEventListener(
      "scroll",
      applyAssistenteVisualViewport,
      { passive: true },
    );
    window.addEventListener("resize", applyAssistenteVisualViewport, {
      passive: true,
    });
    applyAssistenteVisualViewport();
  }

  const sidebarHamburger = document.getElementById("btnSidebarMobile");
  if (sidebarHamburger) {
    sidebarHamburger.addEventListener("click", () => {
      const sidebar = document.querySelector(".sidebar");
      const overlay = document.querySelector(".sidebar-overlay");
      if (sidebar) sidebar.classList.toggle("open");
      if (overlay) overlay.classList.toggle("open");
    });
  }

  const savePrefsBtn = document.getElementById(
    "btnSalvarPreferenciasAssistente",
  );
  if (savePrefsBtn) {
    savePrefsBtn.addEventListener("click", () => {
      saveAssistentePreferences();
    });
  }

  const refreshPromptsBtn = document.getElementById("btnAssistenteRefreshPrompts");
  if (refreshPromptsBtn && typeof loadAssistentePromptLibrary === "function") {
    refreshPromptsBtn.addEventListener("click", () => {
      loadAssistentePromptLibrary({ append: false });
    });
  }

  const loadMorePromptsBtn = document.getElementById("btnAssistentePromptsLoadMore");
  if (loadMorePromptsBtn && typeof loadAssistentePromptLibrary === "function") {
    loadMorePromptsBtn.addEventListener("click", () => {
      loadAssistentePromptLibrary({ append: true });
    });
  }

  const savePromptBtn = document.getElementById("btnAssistentePromptSalvar");
  if (savePromptBtn && typeof saveAssistentePromptLibraryItem === "function") {
    savePromptBtn.addEventListener("click", () => {
      saveAssistentePromptLibraryItem();
    });
  }

  const clearPromptBtn = document.getElementById("btnAssistentePromptLimpar");
  if (clearPromptBtn && typeof clearAssistentePromptEditor === "function") {
    clearPromptBtn.addEventListener("click", () => {
      clearAssistentePromptEditor();
    });
  }

  const promptFilterCategoria = document.getElementById("assistentePromptCategoriaFiltro");
  if (promptFilterCategoria && typeof loadAssistentePromptLibrary === "function") {
    promptFilterCategoria.addEventListener("change", () => {
      loadAssistentePromptLibrary({ append: false });
    });
  }

  const promptBusca = document.getElementById("assistentePromptBusca");
  if (promptBusca && typeof loadAssistentePromptLibrary === "function") {
    let promptBuscaTimer = null;
    promptBusca.addEventListener("input", () => {
      if (promptBuscaTimer) window.clearTimeout(promptBuscaTimer);
      promptBuscaTimer = window.setTimeout(() => {
        loadAssistentePromptLibrary({ append: false });
      }, 260);
    });
  }

  const promptList = document.getElementById("assistentePromptsList");
  if (promptList && typeof handleAssistentePromptLibraryAction === "function") {
    promptList.addEventListener("click", (event) => {
      const actionEl = event.target.closest("[data-assistente-prompt-action]");
      if (!actionEl) return;
      const action = actionEl.getAttribute("data-assistente-prompt-action") || "";
      const promptId = Number(actionEl.getAttribute("data-prompt-id") || 0);
      if (!action || !promptId) return;
      event.preventDefault();
      handleAssistentePromptLibraryAction(action, promptId, {
        nextFavorito: actionEl.getAttribute("data-next-favorito"),
      });
    });
  }

  const scrollBtn = document.getElementById("chatScrollBottomBtn");
  if (scrollBtn) {
    scrollBtn.addEventListener("click", () =>
      scrollChatToBottom({ force: true, behavior: "smooth" }),
    );
  }

  const chatBox = document.getElementById("chatMessages");
  if (chatBox) {
    chatBox.addEventListener(
      "scroll",
      () => {
        if (typeof handleAssistenteChatScroll === "function") {
          handleAssistenteChatScroll();
        } else {
          updateScrollBottomButtonVisibility();
        }
      },
      { passive: true },
    );
    chatBox.addEventListener("click", () => {
      hideSlashCommands();
    });
  }

  initAssistenteChatDelegation();
  if (typeof updateAssistenteMessageDensity === "function") {
    updateAssistenteMessageDensity();
  }
  updateScrollBottomButtonVisibility();

  if (localStorage.getItem("onboarding_pending") === "1") {
    setTimeout(() => sendQuickMessage("começar"), 800);
  }
});

window.initSpeechRecognition = initSpeechRecognition;
window.toggleSpeechRecognition = toggleSpeechRecognition;
window.stopSpeechRecognition = stopSpeechRecognition;
window.initSlashCommands = initSlashCommands;
window.showSlashCommands = showSlashCommands;
window.hideSlashCommands = hideSlashCommands;
window.updateSlashCommandSelection = updateSlashCommandSelection;
window.applySlashCommand = applySlashCommand;
window.sendQuickMessage = sendQuickMessage;
window.addMessage = addMessage;
