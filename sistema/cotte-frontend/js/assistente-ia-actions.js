/**
 * assistente-ia-actions.js
 *
 * Ações operacionais do assistente e mutações com efeitos colaterais.
 */

async function confirmarOrcamento(btn) {
    if (!hasHttpClient()) return;

    const card = btn.closest('.orc-preview-card');
    const scriptEl = card ? card.querySelector('.orc-data') : null;
    if (!scriptEl) return;

    let dados;
    try { dados = JSON.parse(scriptEl.textContent); } catch (e) { return; }

    const select = card.querySelector('#orc-cliente-select');
    const clienteId = select ? (parseInt(select.value) || null) : (dados.cliente_id || null);

    const body = {
        cliente_id: clienteId,
        cliente_nome: dados.cliente_nome || 'A definir',
        servico: dados.servico || 'Serviço',
        valor: dados.valor || 0,
        desconto: dados.desconto || 0,
        desconto_tipo: dados.desconto_tipo || 'percentual',
        observacoes: dados.observacoes || null
    };

    btn.disabled = true;
    btn.textContent = 'Criando...';

    const loadingMsg = addMessage('', false, false, true);
    try {
        const data = await httpClient.post('/ai/orcamento/confirmar', body, { bypassAutoLogout: true });
        if (loadingMsg) loadingMsg.remove();
        if (card) card.remove();
        processAIResponse(data, null);
    } catch (e) {
        if (loadingMsg) loadingMsg.remove();
        btn.disabled = false;
        btn.textContent = 'Confirmar e Criar';
        addMessage('Erro ao criar o orçamento. Tente novamente.', false, true);
    }
}

async function enviarPorWhatsapp(id, numero, btnEl) {
    if (!hasHttpClient()) return;
    if (!id) return;
    let orcInfo = null;
    try {
        orcInfo = await httpClient.get(`/orcamentos/${id}`);
    } catch (_) { /* segue o fluxo */ }
    const stW = (orcInfo?.status || '').toLowerCase();
    const precisaW = !!(orcInfo && (orcInfo.enviado_em || (stW && stW !== 'rascunho')));
    if (precisaW) {
        let ok = true;
        if (typeof cotteConfirmarReenvioSeNecessario === 'function') {
            ok = await cotteConfirmarReenvioSeNecessario(orcInfo, 'whatsapp');
        } else if (!confirm('Este orçamento já foi enviado ao cliente antes. Deseja enviar novamente pelo WhatsApp?')) {
            ok = false;
        }
        if (!ok) return;
    }
    if (btnEl) { btnEl.disabled = true; btnEl.textContent = '⏳ Enviando...'; }
    try {
        await httpClient.post(`/orcamentos/${id}/enviar-whatsapp`, {});
        addMessage(`${escapeHtml(String(numero))} enviado por WhatsApp com sucesso!`, false);
        if (btnEl) { btnEl.textContent = '✓ Enviado'; }
    } catch (err) {
        const rawMsg = err?.detail || err?.message || 'Erro ao enviar por WhatsApp.';
        if (rawMsg.startsWith('cliente_sem_telefone:')) {
            const partes = rawMsg.split(':');
            const clienteNome = partes.slice(2).join(':') || 'O cliente';
            addMessage(
                `❌ <strong>${clienteNome}</strong> não tem WhatsApp cadastrado.<br>` +
                `<a href="clientes.html" style="color:var(--blue);font-weight:600">→ Cadastrar número agora</a>`,
                false, true
            );
        } else {
            addMessage(`❌ ${rawMsg}`, false, true);
        }
        if (btnEl) { btnEl.disabled = false; btnEl.textContent = '📱 WhatsApp'; }
    }
}

async function enviarPorEmail(id, numero, btnEl) {
    if (!hasHttpClient()) return;
    if (!id) return;
    let orcInfo = null;
    try {
        orcInfo = await httpClient.get(`/orcamentos/${id}`);
    } catch (_) { /* segue o fluxo */ }
    const stE = (orcInfo?.status || '').toLowerCase();
    const precisaE = !!(orcInfo && (orcInfo.enviado_em || (stE && stE !== 'rascunho')));
    if (precisaE) {
        let ok = true;
        if (typeof cotteConfirmarReenvioSeNecessario === 'function') {
            ok = await cotteConfirmarReenvioSeNecessario(orcInfo, 'email');
        } else if (!confirm('Este orçamento já foi enviado ao cliente antes. Deseja enviar novamente por e-mail?')) {
            ok = false;
        }
        if (!ok) return;
    }
    if (btnEl) { btnEl.disabled = true; btnEl.textContent = '⏳ Enviando...'; }
    try {
        await httpClient.post(`/orcamentos/${id}/enviar-email`, {});
        addMessage(`✅ ${escapeHtml(String(numero))} enviado por e-mail com sucesso!`, false);
        if (btnEl) { btnEl.textContent = '✓ Enviado'; }
    } catch (err) {
        const msg = err?.detail || err?.message || 'Erro ao enviar por e-mail.';
        addMessage(`❌ ${msg}`, false, true);
        if (btnEl) { btnEl.disabled = false; btnEl.textContent = '📧 E-mail'; }
    }
}

async function _enviarFeedbackApi(pergunta, resposta, avaliacao, comentario, modulo_origem) {
    try {
        await httpClient.post('/ai/feedback', {
            sessao_id: sessaoId,
            pergunta: pergunta || '',
            resposta: resposta || '',
            avaliacao,
            comentario: comentario || null,
            modulo_origem: modulo_origem || null,
        }, { bypassAutoLogout: true });
    } catch (e) {
        // Silencioso.
    }
}

window._pendingConfirmationToken = null;
window._pendingOverrideArgs = null;

function confirmarAcaoIA(token, btnEl) {
    if (!token) return;
    window._pendingConfirmationToken = token;
    if (btnEl && btnEl.dataset.cadastrar === '1') {
        window._pendingOverrideArgs = { cadastrar_materiais_novos: true };
    }
    const card = btnEl.closest('.pending-action-card');
    if (card) {
        card.querySelectorAll('button').forEach(b => b.disabled = true);
        const status = document.createElement('div');
        status.className = 'pending-action-status';
        status.setAttribute('role', 'status');
        status.setAttribute('aria-live', 'polite');
        status.textContent = '⏳ Executando ferramenta…';
        card.appendChild(status);
    }
    const input = document.getElementById('messageInput');
    if (input && _ultimaPergunta) {
        input.value = _ultimaPergunta;
        resizeMessageInput();
        sendMessage();
    }
}

function cancelarAcaoIA(btnEl) {
    window._pendingConfirmationToken = null;
    window._pendingOverrideArgs = null;
    const card = btnEl.closest('.pending-action-card');
    if (card) {
        card.innerHTML = '<div class="pending-action-cancelled" role="status">❌ Ação cancelada.</div>';
    }
    const input = document.getElementById('messageInput');
    if (input) input.focus();
}
