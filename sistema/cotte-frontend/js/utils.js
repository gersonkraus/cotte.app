/**
 * utils.js — Funções utilitárias centralizadas do COTTE
 *
 * Carregar ANTES de api.js e de qualquer script de página.
 * NÃO usar import/export — tudo fica em window.* (escopo global).
 *
 *   <script src="js/utils.js?v=1"></script>
 *   <script src="js/api.js?v=8"></script>
 */

// ── Escape / Sanitização ────────────────────────────────────────────────────

function escapeHtml(value) {
  const s = String(value ?? '');
  return s.replace(/[&<>'"]/g, (ch) => {
    switch (ch) {
      case '&': return '&amp;';
      case '<': return '&lt;';
      case '>': return '&gt;';
      case '"': return '&quot;';
      case "'": return '&#39;';
      default: return ch;
    }
  });
}

function escapeHtmlWithBreaks(value) {
  return escapeHtml(value).replace(/\r\n|\n|\r/g, '<br>');
}

function safeClass(value) {
  return String(value ?? '').replace(/[^a-zA-Z0-9_-]/g, '');
}

// ── Formatação monetária ────────────────────────────────────────────────────

function formatarMoeda(value, withSymbol = true) {
  if (value === null || value === undefined || value === '') {
    return withSymbol ? 'R$ 0,00' : '0,00';
  }
  const num = typeof value === 'string'
    ? parseFloat(value.replace(',', '.'))
    : Number(value);
  if (isNaN(num)) {
    return withSymbol ? 'R$ 0,00' : '0,00';
  }
  const formatted = num.toLocaleString('pt-BR', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  });
  return withSymbol ? `R$ ${formatted}` : formatted;
}

function formatarMoedaCompacta(value) {
  if (value === null || value === undefined) return 'R$ 0';
  const num = Number(value);
  if (isNaN(num)) return 'R$ 0';
  if (num >= 1e6) return `R$ ${(num / 1e6).toFixed(1).replace('.', ',')}M`;
  if (num >= 1e3) return `R$ ${(num / 1e3).toFixed(1).replace('.', ',')}k`;
  return formatarMoeda(num);
}

// ── Formatação de data ──────────────────────────────────────────────────────

function formatarData(date, includeTime = false) {
  if (!date) return '—';
  try {
    const d = new Date(date);
    if (isNaN(d.getTime())) return '—';
    const day   = d.getDate().toString().padStart(2, '0');
    const month = (d.getMonth() + 1).toString().padStart(2, '0');
    const year  = d.getFullYear();
    if (!includeTime) return `${day}/${month}/${year}`;
    const hours   = d.getHours().toString().padStart(2, '0');
    const minutes = d.getMinutes().toString().padStart(2, '0');
    return `${day}/${month}/${year} ${hours}:${minutes}`;
  } catch {
    return '—';
  }
}

function formatarDataRelativa(date) {
  if (!date) return '—';
  try {
    const d = new Date(date);
    if (isNaN(d.getTime())) return '—';
    const now      = new Date();
    const diffMs   = now - d;
    const diffDays = Math.floor(diffMs / 86400000);
    if (diffDays === 0) {
      const h = d.getHours().toString().padStart(2, '0');
      const m = d.getMinutes().toString().padStart(2, '0');
      return `Hoje às ${h}:${m}`;
    }
    if (diffDays === 1) return 'Ontem';
    if (diffDays < 7)  return `Há ${diffDays} dias`;
    if (diffDays < 30) {
      const weeks = Math.floor(diffDays / 7);
      return `Há ${weeks} ${weeks === 1 ? 'semana' : 'semanas'}`;
    }
    return formatarData(date);
  } catch {
    return '—';
  }
}

// ── Outras formatações ──────────────────────────────────────────────────────

function formatarNumero(value, decimals = 0) {
  if (value === null || value === undefined || value === '') return '0';
  const num = typeof value === 'string' ? parseFloat(value.replace(',', '.')) : Number(value);
  if (isNaN(num)) return '0';
  return num.toLocaleString('pt-BR', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals
  });
}

function formatarPorcentagem(value, isDecimal = false) {
  if (value === null || value === undefined) return '0%';
  let num = typeof value === 'string' ? parseFloat(value.replace(',', '.')) : Number(value);
  if (isNaN(num)) return '0%';
  if (isDecimal && num <= 1) num *= 100;
  const rounded = Math.round(num * 10) / 10;
  return `${rounded.toFixed(1).replace('.', ',')}%`;
}

function formatarTelefone(telefone) {
  if (!telefone) return '';
  const numeros = telefone.replace(/\D/g, '');
  if (numeros.length === 11) return `(${numeros.substring(0, 2)}) ${numeros.substring(2, 7)}-${numeros.substring(7)}`;
  if (numeros.length === 10) return `(${numeros.substring(0, 2)}) ${numeros.substring(2, 6)}-${numeros.substring(6)}`;
  return telefone;
}

function formatarDocumento(documento) {
  if (!documento) return '';
  const n = documento.replace(/\D/g, '');
  if (n.length === 11) return `${n.substring(0,3)}.${n.substring(3,6)}.${n.substring(6,9)}-${n.substring(9)}`;
  if (n.length === 14) return `${n.substring(0,2)}.${n.substring(2,5)}.${n.substring(5,8)}/${n.substring(8,12)}-${n.substring(12)}`;
  return documento;
}

function truncarTexto(text, maxLength = 50, suffix = '...') {
  if (!text || text.length <= maxLength) return text || '';
  return text.substring(0, maxLength - suffix.length) + suffix;
}

function capitalizar(text) {
  if (!text) return '';
  return text.toLowerCase().split(' ')
    .map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
}

// ── Utilidades de orçamento / UI ────────────────────────────────────────────

function diasRestantes(orc) {
  const criado = new Date(orc.criado_em);
  const validade = orc.validade_dias || 7;
  const diffMs = Date.now() - criado.getTime();
  return validade - Math.floor(diffMs / 86400000);
}

function iniciaisDe(nome) {
  const s = String(nome ?? '').trim();
  if (!s) return '?';
  const parts = s.split(/\s+/).filter(Boolean).slice(0, 2);
  const chars = parts.map(p => (p[0] || '')).join('');
  const cleaned = chars.replace(/[^A-Za-z0-9]/g, '');
  return (cleaned || '?').toUpperCase();
}

function corAvatar(nome) {
  const cores = [
    'linear-gradient(135deg,#00e5a0,#3b82f6)',
    'linear-gradient(135deg,#f97316,#f59e0b)',
    'linear-gradient(135deg,#a855f7,#ec4899)',
    'linear-gradient(135deg,#06b6d4,#3b82f6)',
    'linear-gradient(135deg,#10b981,#059669)',
  ];
  let hash = 0;
  for (let c of String(nome || '')) hash += c.charCodeAt(0);
  return cores[hash % cores.length];
}

// ── Formatação de bytes / duração ───────────────────────────────────────────

function formatarBytes(bytes, decimals = 2) {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

function formatarDuracao(minutes) {
  if (!minutes || minutes < 0) return '0min';
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  if (h === 0) return `${m}min`;
  if (m === 0) return `${h}h`;
  return `${h}h${m.toString().padStart(2, '0')}min`;
}

function gerarIdUnico() {
  return Date.now().toString(36) + Math.random().toString(36).substring(2);
}
