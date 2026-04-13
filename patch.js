const fs = require('fs');
const path = './sistema/cotte-frontend/js/assistente-ia.js';
let code = fs.readFileSync(path, 'utf8');

// 1. Capture confirmationToken before try
code = code.replace(
    "    let lastError = null;\n    currentAbortController = new AbortController();\n\n    try {",
    "    let lastError = null;\n    currentAbortController = new AbortController();\n    const confirmationToken = window._pendingConfirmationToken;\n\n    try {"
);

// 2. Use confirmationToken inside try
code = code.replace(
    "        if (window._pendingConfirmationToken) {\n            requestBody.confirmation_token = window._pendingConfirmationToken;\n            window._pendingConfirmationToken = null;\n        }",
    "        if (confirmationToken) {\n            requestBody.confirmation_token = confirmationToken;\n            window._pendingConfirmationToken = null;\n        }"
);

// 3. Set lastError in catch
code = code.replace(
    "    } catch (error) {\n        console.error('Error:', error);",
    "    } catch (error) {\n        lastError = error;\n        console.error('Error:', error);"
);

// 4. Update card in finally
const finallyReplacement = `    } finally {
        isLoading = false;
        currentAbortController = null;
        if (sendButton) {
            sendButton.classList.remove('is-loading');
            sendButton.title = 'Enviar';
        }

        if (confirmationToken) {
            const card = document.querySelector(\`.pending-action-card[data-token="\${confirmationToken}"]\`);
            if (card) {
                const status = card.querySelector('.pending-action-status');
                if (status) {
                    if (lastError && lastError.name !== 'AbortError') {
                        status.textContent = '❌ Falha na execução';
                        status.style.color = 'var(--ai-red, #ef4444)';
                        card.querySelectorAll('button').forEach(b => b.disabled = false);
                    } else if (!lastError) {
                        status.textContent = '✅ Ação concluída';
                        status.style.color = 'var(--ai-green, #10b981)';
                    } else {
                        status.textContent = 'Ação interrompida';
                        card.querySelectorAll('button').forEach(b => b.disabled = false);
                    }
                }
            }
        }
    }`;

code = code.replace(
    "    } finally {\n        isLoading = false;\n        currentAbortController = null;\n        if (sendButton) {\n            sendButton.classList.remove('is-loading');\n            sendButton.title = 'Enviar';\n        }\n    }",
    finallyReplacement
);

fs.writeFileSync(path, code);
console.log('Patched assistente-ia.js');
