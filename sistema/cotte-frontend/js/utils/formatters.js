/**
 * Utilitários de formatação - Funções para formatar dados
 */

/**
 * Formata um valor monetário para o padrão brasileiro (R$)
 * @param {number|string} value - Valor a ser formatado
 * @param {boolean} withSymbol - Incluir símbolo R$
 * @returns {string} Valor formatado
 */
export function formatarMoeda(value, withSymbol = true) {
  if (value === null || value === undefined || value === '') {
    return withSymbol ? 'R$ 0,00' : '0,00';
  }
  
  // Converter para número
  const num = typeof value === 'string' 
    ? parseFloat(value.replace(',', '.')) 
    : Number(value);
  
  if (isNaN(num)) {
    return withSymbol ? 'R$ 0,00' : '0,00';
  }
  
  // Formatar com 2 casas decimais
  const formatted = num.toLocaleString('pt-BR', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  });
  
  return withSymbol ? `R$ ${formatted}` : formatted;
}

/**
 * Formata um valor monetário de forma compacta (R$ 1,2k, R$ 1,5M)
 * @param {number} value - Valor a ser formatado
 * @returns {string} Valor formatado compacto
 */
export function formatarMoedaCompacta(value) {
  if (value === null || value === undefined) return 'R$ 0';
  
  const num = Number(value);
  if (isNaN(num)) return 'R$ 0';
  
  if (num >= 1000000) {
    return `R$ ${(num / 1000000).toFixed(1).replace('.', ',')}M`;
  }
  
  if (num >= 1000) {
    return `R$ ${(num / 1000).toFixed(1).replace('.', ',')}k`;
  }
  
  return formatarMoeda(num);
}

/**
 * Formata uma data para o padrão brasileiro (DD/MM/YYYY)
 * @param {string|Date} date - Data a ser formatada
 * @param {boolean} includeTime - Incluir hora (DD/MM/YYYY HH:MM)
 * @returns {string} Data formatada
 */
export function formatarData(date, includeTime = false) {
  if (!date) return '—';
  
  try {
    const d = new Date(date);
    
    if (isNaN(d.getTime())) {
      return '—';
    }
    
    const day = d.getDate().toString().padStart(2, '0');
    const month = (d.getMonth() + 1).toString().padStart(2, '0');
    const year = d.getFullYear();
    
    if (!includeTime) {
      return `${day}/${month}/${year}`;
    }
    
    const hours = d.getHours().toString().padStart(2, '0');
    const minutes = d.getMinutes().toString().padStart(2, '0');
    
    return `${day}/${month}/${year} ${hours}:${minutes}`;
  } catch {
    return '—';
  }
}

/**
 * Formata uma data relativa (há 2 dias, hoje, ontem)
 * @param {string|Date} date - Data a ser formatada
 * @returns {string} Data relativa formatada
 */
export function formatarDataRelativa(date) {
  if (!date) return '—';
  
  try {
    const d = new Date(date);
    
    if (isNaN(d.getTime())) {
      return '—';
    }
    
    const now = new Date();
    const diffMs = now - d;
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    
    if (diffDays === 0) {
      // Hoje - mostrar hora
      const hours = d.getHours().toString().padStart(2, '0');
      const minutes = d.getMinutes().toString().padStart(2, '0');
      return `Hoje às ${hours}:${minutes}`;
    }
    
    if (diffDays === 1) {
      return 'Ontem';
    }
    
    if (diffDays < 7) {
      return `Há ${diffDays} dias`;
    }
    
    if (diffDays < 30) {
      const weeks = Math.floor(diffDays / 7);
      return `Há ${weeks} ${weeks === 1 ? 'semana' : 'semanas'}`;
    }
    
    // Mais de 30 dias - mostrar data completa
    return formatarData(date);
  } catch {
    return '—';
  }
}

/**
 * Formata um número com separadores de milhar
 * @param {number|string} value - Valor a ser formatado
 * @param {number} decimals - Casas decimais (padrão: 0)
 * @returns {string} Número formatado
 */
export function formatarNumero(value, decimals = 0) {
  if (value === null || value === undefined || value === '') {
    return '0';
  }
  
  const num = typeof value === 'string' 
    ? parseFloat(value.replace(',', '.')) 
    : Number(value);
  
  if (isNaN(num)) {
    return '0';
  }
  
  return num.toLocaleString('pt-BR', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals
  });
}

/**
 * Formata uma porcentagem
 * @param {number|string} value - Valor (0-100 ou 0-1)
 * @param {boolean} isDecimal - Se o valor está em decimal (0-1)
 * @returns {string} Porcentagem formatada
 */
export function formatarPorcentagem(value, isDecimal = false) {
  if (value === null || value === undefined) {
    return '0%';
  }
  
  let num = typeof value === 'string' 
    ? parseFloat(value.replace(',', '.')) 
    : Number(value);
  
  if (isNaN(num)) {
    return '0%';
  }
  
  // Converter decimal para porcentagem se necessário
  if (isDecimal && num <= 1) {
    num = num * 100;
  }
  
  // Arredondar para 1 casa decimal
  const rounded = Math.round(num * 10) / 10;
  
  return `${rounded.toFixed(1).replace('.', ',')}%`;
}

/**
 * Formata o status de um orçamento com cor e ícone
 * @param {string} status - Status do orçamento
 * @returns {object} Objeto com texto, classe CSS e ícone
 */
export function formatarStatusOrcamento(status) {
  const statusMap = {
    'rascunho': {
      texto: 'Rascunho',
      classe: 'status-draft',
      icone: '📝',
      cor: '#94a3b8'
    },
    'pendente': {
      texto: 'Pendente',
      classe: 'status-pending',
      icone: '⏳',
      cor: '#f59e0b'
    },
    'enviado': {
      texto: 'Enviado',
      classe: 'status-sent',
      icone: '📤',
      cor: '#06b6d4'
    },
    'aprovado': {
      texto: 'Aprovado',
      classe: 'status-approved',
      icone: '✅',
      cor: '#10b981'
    },
    'expirado': {
      texto: 'Expirado',
      classe: 'status-expired',
      icone: '⏰',
      cor: '#ef4444'
    },
    'em_execucao': {
      texto: 'Em execução',
      classe: 'status-em-execucao',
      icone: '⚙️',
      cor: '#d97706'
    },
    'aguardando_pagamento': {
      texto: 'Aguard. pagamento',
      classe: 'status-aguardando-pagamento',
      icone: '💰',
      cor: '#7c3aed'
    },
    'cancelado': {
      texto: 'Cancelado',
      classe: 'status-cancelled',
      icone: '❌',
      cor: '#64748b'
    }
  };
  
  const defaultStatus = {
    texto: status || 'Desconhecido',
    classe: 'status-unknown',
    icone: '❓',
    cor: '#94a3b8'
  };
  
  return statusMap[status] || defaultStatus;
}

/**
 * Formata um telefone no padrão brasileiro
 * @param {string} telefone - Número de telefone
 * @returns {string} Telefone formatado
 */
export function formatarTelefone(telefone) {
  if (!telefone) return '';
  
  // Remover caracteres não numéricos
  const numeros = telefone.replace(/\D/g, '');
  
  if (numeros.length === 11) {
    // (XX) XXXXX-XXXX
    return `(${numeros.substring(0, 2)}) ${numeros.substring(2, 7)}-${numeros.substring(7)}`;
  }
  
  if (numeros.length === 10) {
    // (XX) XXXX-XXXX
    return `(${numeros.substring(0, 2)}) ${numeros.substring(2, 6)}-${numeros.substring(6)}`;
  }
  
  // Retornar original se não for formato conhecido
  return telefone;
}

/**
 * Formata um CPF/CNPJ
 * @param {string} documento - CPF ou CNPJ
 * @returns {string} Documento formatado
 */
export function formatarDocumento(documento) {
  if (!documento) return '';
  
  // Remover caracteres não numéricos
  const numeros = documento.replace(/\D/g, '');
  
  if (numeros.length === 11) {
    // CPF: XXX.XXX.XXX-XX
    return `${numeros.substring(0, 3)}.${numeros.substring(3, 6)}.${numeros.substring(6, 9)}-${numeros.substring(9)}`;
  }
  
  if (numeros.length === 14) {
    // CNPJ: XX.XXX.XXX/XXXX-XX
    return `${numeros.substring(0, 2)}.${numeros.substring(2, 5)}.${numeros.substring(5, 8)}/${numeros.substring(8, 12)}-${numeros.substring(12)}`;
  }
  
  // Retornar original se não for formato conhecido
  return documento;
}

/**
 * Trunca um texto se for muito longo
 * @param {string} text - Texto a ser truncado
 * @param {number} maxLength - Comprimento máximo
 * @param {string} suffix - Sufixo a ser adicionado (padrão: '...')
 * @returns {string} Texto truncado
 */
export function truncarTexto(text, maxLength = 50, suffix = '...') {
  if (!text || text.length <= maxLength) {
    return text || '';
  }
  
  return text.substring(0, maxLength - suffix.length) + suffix;
}

/**
 * Capitaliza a primeira letra de cada palavra
 * @param {string} text - Texto a ser capitalizado
 * @returns {string} Texto capitalizado
 */
export function capitalizar(text) {
  if (!text) return '';
  
  return text
    .toLowerCase()
    .split(' ')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

/**
 * Formata bytes para unidades legíveis (KB, MB, GB)
 * @param {number} bytes - Bytes a serem formatados
 * @param {number} decimals - Casas decimais
 * @returns {string} Bytes formatados
 */
export function formatarBytes(bytes, decimals = 2) {
  if (bytes === 0) return '0 Bytes';
  
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
  
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

/**
 * Formata a duração em minutos para horas:minutos
 * @param {number} minutes - Minutos totais
 * @returns {string} Duração formatada
 */
export function formatarDuracao(minutes) {
  if (!minutes || minutes < 0) return '0min';
  
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  
  if (hours === 0) {
    return `${mins}min`;
  }
  
  if (mins === 0) {
    return `${hours}h`;
  }
  
  return `${hours}h${mins.toString().padStart(2, '0')}min`;
}

/**
 * Gera um ID único simples
 * @returns {string} ID único
 */
export function gerarIdUnico() {
  return Date.now().toString(36) + Math.random().toString(36).substring(2);
}

// Exportar funções para uso global (opcional)
window.formatarMoeda = formatarMoeda;
window.formatarData = formatarData;
window.formatarNumero = formatarNumero;
window.formatarPorcentagem = formatarPorcentagem;