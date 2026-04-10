/**
 * assistente-ia-feedback.js
 *
 * Coleta de feedback do assistente.
 */

async function enviarFeedback(fbId, avaliacao) {
    const barEl = document.getElementById(fbId);
    if (!barEl) return;

    const fbData = (window._feedbackData || {})[fbId] || {};

    if (avaliacao === 'negativo') {
        barEl.innerHTML = `
            <div class="feedback-negativo">
                <span class="feedback-label">O que você precisava saber?</span>
                <textarea id="${fbId}_txt" class="feedback-textarea" placeholder="Opcional — ajuda a melhorar o assistente" rows="2" maxlength="500"></textarea>
                <div class="feedback-negativo-btns">
                    <button type="button" class="feedback-send-btn">Enviar</button>
                    <button type="button" class="feedback-skip-btn">Pular</button>
                </div>
            </div>`;
        barEl.querySelector('.feedback-send-btn')?.addEventListener('click', () => _confirmarFeedbackNegativo(fbId));
        barEl.querySelector('.feedback-skip-btn')?.addEventListener('click', () => _confirmarFeedbackNegativo(fbId, true));
        window._feedbackData[fbId].avaliacao = 'negativo';
        return;
    }

    await _enviarFeedbackApi(fbData.pergunta, fbData.resposta, avaliacao, null, fbData.modulo_origem);
    barEl.innerHTML = '<span class="feedback-enviado">✓ Obrigado!</span>';
    delete (window._feedbackData || {})[fbId];
}

async function _confirmarFeedbackNegativo(fbId, pular = false) {
    const barEl = document.getElementById(fbId);
    const fbData = (window._feedbackData || {})[fbId] || {};
    const comentario = pular ? null : (document.getElementById(fbId + '_txt') || {}).value || null;
    await _enviarFeedbackApi(fbData.pergunta, fbData.resposta, 'negativo', comentario, fbData.modulo_origem);
    barEl.innerHTML = '<span class="feedback-enviado">✓ Obrigado pelo retorno!</span>';
    delete (window._feedbackData || {})[fbId];
}
