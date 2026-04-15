
const chatForm = document.getElementById('chat-form');
const chatInput = document.getElementById('chat-input');
const chatMessages = document.getElementById('chat-messages');

let chatHistory = [];

async function carregarDashboard() {
  try {
    const res = await fetch('/api/superadmin/monitor-ai/status', {
      headers: {
        'Authorization': `Bearer ${getToken()}`
      }
    });

    if (res.ok) {
      const data = await res.json();
      if (data.success && data.status) {
        document.getElementById('val-erros').textContent = data.status.erros_24h ?? '--';
        document.getElementById('val-cpu').textContent = data.status.cpu_usage ?? '--';
        document.getElementById('val-db').textContent = data.status.db_status ?? '--';
        document.getElementById('val-jobs').textContent = data.status.jobs_pendentes ?? '--';
      }
    }
  } catch (error) {
    console.error('Erro ao carregar status do Monitor AI:', error);
  }
}

function scrollToBottom() {
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function addMessage(role, content, steps = []) {
  const isUser = role === 'user';
  const msgDiv = document.createElement('div');
  msgDiv.className = `message ${isUser ? 'msg-user' : 'msg-ai'}`;
  
  let avatarIcon = isUser ? '<i class="bi bi-person"></i>' : '<i class="bi bi-robot"></i>';
  let stepsHtml = '';

  if (steps && steps.length > 0) {
    steps.forEach((step, index) => {
      let observationStr = '';
      if (typeof step.observation === 'object') {
          observationStr = JSON.stringify(step.observation, null, 2);
      } else {
          observationStr = step.observation;
      }
      
      stepsHtml += `
        <div class="step-accordion">
          <div class="step-header" onclick="this.nextElementSibling.classList.toggle('open'); this.classList.toggle('open')">
            <span>
              <span class="tool-badge">${step.tool}</span> 
              Executando ação...
            </span>
            <i class="bi bi-chevron-down"></i>
          </div>
          <div class="step-body">
Input: ${JSON.stringify(step.tool_input, null, 2)}
<hr>
Output:
${observationStr}
          </div>
        </div>
      `;
    });
  }

  // Sanitização básica do conteúdo
  const safeContent = content.replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\n/g, '<br>');

  msgDiv.innerHTML = `
    <div class="msg-avatar">${avatarIcon}</div>
    <div class="msg-content">
      ${stepsHtml}
      <p>${safeContent}</p>
    </div>
  `;

  chatMessages.appendChild(msgDiv);
  scrollToBottom();
}

function showLoading() {
  const msgDiv = document.createElement('div');
  msgDiv.className = 'message msg-ai loading-indicator';
  msgDiv.innerHTML = `
    <div class="msg-avatar"><i class="bi bi-robot"></i></div>
    <div class="msg-content">
      <div class="typing-indicator">
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
      </div>
    </div>
  `;
  chatMessages.appendChild(msgDiv);
  scrollToBottom();
  return msgDiv;
}

function hideLoading(element) {
  if (element && element.parentNode) {
    element.parentNode.removeChild(element);
  }
}

chatForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const text = chatInput.value.trim();
  if (!text) return;

  // Mostra mensagem do usuário
  addMessage('user', text);
  chatInput.value = '';
  chatInput.style.height = 'auto'; // Reseta altura

  const loadingEl = showLoading();

  try {
    const res = await fetch('/api/superadmin/monitor-ai/agent', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${getToken()}`
      },
      body: JSON.stringify({ 
        query: text,
        history: chatHistory
      })
    });

    hideLoading(loadingEl);

    if (!res.ok) {
      throw new Error(`Erro HTTP: ${res.status}`);
    }

    const data = await res.json();
    
    // Atualiza histórico
    chatHistory.push({ role: 'user', content: text });
    chatHistory.push({ role: 'assistant', content: data.answer });
    
    // Limita histórico a últimas 10 mensagens
    if (chatHistory.length > 20) chatHistory = chatHistory.slice(-20);

    addMessage('ai', data.answer, data.intermediate_steps);

  } catch (error) {
    hideLoading(loadingEl);
    addMessage('ai', `Erro de comunicação com o Agente: ${error.message}`);
    console.error('Monitor AI Error:', error);
  }
});

// Auto-resize do textarea
chatInput.addEventListener('input', function() {
  this.style.height = 'auto';
  this.style.height = (this.scrollHeight) + 'px';
  if (this.value === '') {
      this.style.height = 'auto';
  }
});

chatInput.addEventListener('keydown', function(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    chatForm.dispatchEvent(new Event('submit'));
  }
});

// Init
document.addEventListener('DOMContentLoaded', () => {
  if (!getToken()) {
    window.location.href = '/app/login.html';
    return;
  }
  
  // Tentar carregar as métricas do dashboard
  carregarDashboard();
});
